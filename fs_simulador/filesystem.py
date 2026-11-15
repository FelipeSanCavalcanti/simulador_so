import hashlib
import hmac
import posixpath

from fs_simulador import crypto
from fs_simulador.disk import Disk
from fs_simulador.io_scheduler import DiskScheduler
from fs_simulador.node import Node
from fs_simulador.security import EXECUTE, READ, WRITE, mode_to_string


class FileSystem:
    """Gerencia a árvore de diretórios, a alocação física e as ACLs."""

    def __init__(self, security=None):
        self.security = security
        self.verbose = True
        self.disk = Disk(block_size=4096, total_blocks=32)
        self.scheduler = DiskScheduler(
            total_tracks=self.disk.total_blocks,
            head_position=0
        )
        self.io_algorithm = "SSTF"
        self.root = Node("/", "DIR", mode=0o755)
        self.current_path = "/"

        # O bloco zero guarda o i-node do diretório raiz.
        self.root.inode_block = self.disk.allocate(
            1, self.root, "INODE"
        )[0]

    # ---------- Auxiliares ----------
    def _say(self, message):
        if self.verbose:
            print(message)

    def _identity(self):
        """Nome e grupo primário da sessão atual (root no boot)."""
        user = self.security.current_user if self.security else None

        if user is None:
            return "root", "admin"

        return user.name, user.group

    def _check(self, node, action, path=None, show=True):
        if self.security is None:
            return True

        return self.security.check_access(
            node, action, path or self.get_path(node), show=show
        )

    def _check_traverse(self, path):
        """Exige permissão de execução (x) nos diretórios intermediários."""
        if self.security is None:
            return

        normalized = self.normalize_path(path)
        parts = [part for part in normalized.strip("/").split("/") if part]
        current = self.root

        for part in parts[:-1]:
            current = current.children.get(part)

            if current is None or not current.is_directory():
                return

            self._check(current, EXECUTE, self.get_path(current), show=False)

    # ---------- Caminhos ----------
    def normalize_path(self, path):
        if not path:
            raise ValueError("Caminho não informado.")

        if path.startswith("/"):
            return posixpath.normpath(path)

        return posixpath.normpath(
            posixpath.join(self.current_path, path)
        )

    def resolve(self, path):
        path = self.normalize_path(path)

        if path == "/":
            return self.root

        current = self.root

        for part in path.strip("/").split("/"):
            if not current.is_directory():
                raise NotADirectoryError("Parte do caminho não é diretório.")

            if part not in current.children:
                raise FileNotFoundError(f"Caminho não encontrado: {path}")

            current = current.children[part]

        return current

    def get_parent(self, path):
        path = self.normalize_path(path)

        if path == "/":
            raise ValueError("Não é permitido criar item na raiz.")

        parent_path = posixpath.dirname(path) or "/"
        name = posixpath.basename(path)
        parent = self.resolve(parent_path)

        if not parent.is_directory():
            raise NotADirectoryError("O destino não é um diretório.")

        return parent, name

    def get_path(self, node):
        if node.parent is None:
            return "/"

        parts = []
        current = node

        while current.parent is not None:
            parts.append(current.name)
            current = current.parent

        return "/" + "/".join(reversed(parts))

    # ---------- Blocos e conteúdo ----------
    def _write_block(self, index, stored):
        """Grava o conteúdo físico e registra o hash de integridade."""
        block = self.disk.blocks[index]
        block["type"] = "DATA"
        block["content"] = stored
        block["checksum"] = hashlib.sha256(
            stored.encode("utf-8")
        ).hexdigest()

        if self.security is not None:
            self.security.register_block(index, block["checksum"])

    def _resize_blocks(self, node, needed):
        current = len(node.data_blocks)
        difference = needed - current

        if difference > 0:
            extra = self.disk.allocate(difference, node, "DATA")
            node.data_blocks.extend(extra)

        elif difference < 0:
            removed = node.data_blocks[needed:]
            self.disk.release(removed)

            if self.security is not None:
                self.security.forget_blocks(removed)

            node.data_blocks = node.data_blocks[:needed]

    def _store_content(self, node, text, key=None):
        """Divide o conteúdo em blocos, criptografando antes de gravar."""
        step = self.disk.block_size
        chunks = [text[i:i + step] for i in range(0, len(text), step)]

        self._resize_blocks(node, len(chunks))
        node.size = len(text.encode("utf-8"))

        if key:
            node.encrypted = True
            node.crypto_salt = crypto.new_salt()
            node.plain_hash = crypto.fingerprint(text)

            for position, index in enumerate(node.data_blocks):
                self._write_block(
                    index,
                    crypto.encrypt_chunk(
                        chunks[position], key, node.crypto_salt, position
                    )
                )
        else:
            node.encrypted = False
            node.crypto_salt = None
            node.plain_hash = None

            for position, index in enumerate(node.data_blocks):
                self._write_block(index, chunks[position])

    def plaintext(self, node):
        """Concatena o conteúdo dos blocos (apenas para arquivos em claro)."""
        parts = []

        for index in node.data_blocks:
            content = self.disk.blocks[index].get("content")
            if content:
                parts.append(content)

        return "".join(parts)

    def decrypt_content(self, node, key):
        """Reverte a criptografia e valida a chave pelo SHA-256 do texto claro."""
        parts = []

        for position, index in enumerate(node.data_blocks):
            cipher = self.disk.blocks[index].get("content") or ""
            parts.append(
                crypto.decrypt_chunk(cipher, key, node.crypto_salt, position)
            )

        text = "".join(parts)

        if node.plain_hash:
            digest = crypto.fingerprint(text)

            if not hmac.compare_digest(digest, node.plain_hash):
                raise ValueError(
                    "Chave incorreta: a verificação SHA-256 do conteúdo falhou."
                )

        return text

    # ---------- Criar ----------
    def mkdir(self, path):
        target = self.normalize_path(path)
        parent, name = self.get_parent(target)

        self._check_traverse(target)
        self._check(parent, WRITE, self.get_path(parent))

        if name in parent.children:
            raise FileExistsError("Já existe um item com esse nome.")

        owner, group = self._identity()
        node = Node(
            name, "DIR", parent=parent,
            owner=owner, group=group, mode=0o755
        )
        node.inode_block = self.disk.allocate(1, node, "INODE")[0]
        parent.children[name] = node

        self._say(f"Diretório '{name}' criado com sucesso.")

    def create_file(self, path, size, content=None):
        if size < 0:
            raise ValueError("O tamanho não pode ser negativo.")

        target = self.normalize_path(path)
        parent, name = self.get_parent(target)

        self._check_traverse(target)
        self._check(parent, WRITE, self.get_path(parent))

        if name in parent.children:
            raise FileExistsError("Já existe um item com esse nome.")

        if content is not None:
            size = len(content.encode("utf-8"))

        owner, group = self._identity()
        node = Node(
            name, "FILE", parent=parent, size=size,
            owner=owner, group=group, mode=0o644
        )
        data_amount = self.disk.data_blocks_needed(size)

        # Reserva i-node e blocos de dados antes de inserir na árvore.
        reserved = self.disk.allocate(
            1 + data_amount, node, "TEMP"
        )

        node.inode_block = reserved[0]
        node.data_blocks = reserved[1:]

        self.disk.blocks[node.inode_block]["type"] = "INODE"
        for index in node.data_blocks:
            self.disk.blocks[index]["type"] = "DATA"

        parent.children[name] = node
        self._say(f"Arquivo '{name}' criado com sucesso.")

        self.perform_io(
            "ESCRITA",
            [node.inode_block] + node.data_blocks
        )

        if content is not None:
            self._store_content(node, content)

    def write_file(self, path, content):
        """Grava conteúdo em texto claro no arquivo.

        Se o arquivo ainda não existir, ele é criado (equivalente a um
        redirecionamento de shell), respeitando a ACL do diretório.
        """
        try:
            node = self.resolve(path)
        except FileNotFoundError:
            self.create_file(path, 0, content=content)
            return

        if not node.is_file():
            raise ValueError("O caminho não é um arquivo.")

        self._check_traverse(self.get_path(node))
        self._check(node, WRITE)

        if node.encrypted:
            raise ValueError(
                "O arquivo está criptografado. Use 'decrypt_file' com a mesma "
                "chave para ler ou recrie o arquivo."
            )

        self._store_content(node, content)
        self._say("Conteúdo gravado com sucesso.")

        self.perform_io("ESCRITA", [node.inode_block] + node.data_blocks)

    # ---------- Ler ----------
    def read_file(self, path):
        node = self.resolve(path)

        if not node.is_file():
            raise ValueError("O caminho não é um arquivo.")

        self._check_traverse(self.get_path(node))
        self._check(node, READ)

        self.perform_io(
            "LEITURA",
            [node.inode_block] + node.data_blocks
        )

        print(f"\nArquivo: {node.name}")
        print(f"Caminho: {self.get_path(node)}")
        print(
            f"Proprietário: {node.owner}:{node.group} | "
            f"Permissões: {mode_to_string(node.mode)} ({node.mode:o})"
        )
        print(f"Tamanho: {node.size} bytes")
        print(f"i-node: bloco {node.inode_block}")
        print(f"Blocos de dados: {node.data_blocks}")

        if node.encrypted:
            print(
                "Conteúdo: [CRIPTOGRAFADO EM REPOUSO] use "
                "'decrypt_file <caminho> --key <chave>'."
            )
        else:
            text = self.plaintext(node)
            preview = text if len(text) <= 120 else text[:120] + "..."
            print(f'Conteúdo: "{preview}"' if preview else "Conteúdo: (vazio)")

    def cat(self, path):
        node = self.resolve(path)

        if not node.is_file():
            raise ValueError("O caminho não é um arquivo.")

        self._check_traverse(self.get_path(node))
        self._check(node, READ)

        if node.encrypted:
            raise ValueError(
                "Arquivo criptografado: use 'decrypt_file <caminho> --key <chave>'."
            )

        self.perform_io("LEITURA", [node.inode_block] + node.data_blocks)
        print(self.plaintext(node) or "(arquivo vazio)")

    # ---------- Criptografia ----------
    def encrypt_file(self, path, key):
        node = self.resolve(path)

        if not node.is_file():
            raise ValueError("O caminho não é um arquivo.")

        self._check_traverse(self.get_path(node))
        self._check(node, WRITE)

        if not key:
            raise ValueError("Informe a chave de criptografia.")

        if node.encrypted:
            raise ValueError("O arquivo já está criptografado.")

        text = self.plaintext(node)

        if not text:
            raise ValueError("O arquivo não possui conteúdo para criptografar.")

        self._store_content(node, text, key)
        self.perform_io("ESCRITA", [node.inode_block] + node.data_blocks)

        first = self.disk.blocks[node.data_blocks[0]]["content"]
        print(f"Arquivo '{self.get_path(node)}' criptografado com sucesso.")
        print(
            f'Conteúdo gravado nos blocos físicos: '
            f'"0x{first[:24].upper()}..." (Encrypted Ciphertext)'
        )
        print("A chave não é armazenada em disco: guarde-a para a descriptação.")

        if self.security is not None:
            self.security.log(
                f"CRYPTO: '{self.get_path(node)}' criptografado em repouso"
            )

    def decrypt_file(self, path, key):
        node = self.resolve(path)

        if not node.is_file():
            raise ValueError("O caminho não é um arquivo.")

        self._check_traverse(self.get_path(node))
        self._check(node, READ)

        if not node.encrypted:
            raise ValueError("O arquivo não está criptografado.")

        if not key:
            raise ValueError("Informe a chave de criptografia.")

        text = self.decrypt_content(node, key)
        self.perform_io("LEITURA", [node.inode_block] + node.data_blocks)

        print("\n[CRIPTOGRAFIA - DESCRIPTAÇÃO]")
        print(f"Arquivo: {self.get_path(node)}")
        print("Verificação SHA-256 do conteúdo: OK (chave correta)")
        print(f'Conteúdo em texto claro: "{text}"')

        if self.security is not None:
            self.security.log(
                f"CRYPTO: '{self.get_path(node)}' descriptografado com sucesso"
            )

    # ---------- Atualizar ----------
    def update_file(self, path, new_size):
        if new_size < 0:
            raise ValueError("O tamanho não pode ser negativo.")

        node = self.resolve(path)

        if not node.is_file():
            raise ValueError("O caminho não é um arquivo.")

        self._check_traverse(self.get_path(node))
        self._check(node, WRITE)

        new_amount = self.disk.data_blocks_needed(new_size)
        self._resize_blocks(node, new_amount)
        node.size = new_size
        self._say("Arquivo atualizado com sucesso.")

        self.perform_io(
            "ESCRITA",
            [node.inode_block] + node.data_blocks
        )

    # ---------- Excluir ----------
    def remove_file(self, path):
        node = self.resolve(path)

        if not node.is_file():
            raise ValueError("O item não é um arquivo.")

        self._check_traverse(self.get_path(node))
        self._check(node.parent, WRITE, self.get_path(node.parent))

        blocks = [node.inode_block] + node.data_blocks
        self.disk.release(blocks)

        if self.security is not None:
            self.security.forget_blocks(blocks)

        del node.parent.children[node.name]
        print("Arquivo removido com sucesso.")

    def remove_directory(self, path):
        node = self.resolve(path)

        if not node.is_directory():
            raise ValueError("O item não é um diretório.")

        if node is self.root:
            raise ValueError("Não é possível excluir a raiz.")

        if node.children:
            raise OSError("O diretório não está vazio.")

        self._check_traverse(self.get_path(node))
        self._check(node.parent, WRITE, self.get_path(node.parent))

        node_path = self.get_path(node)
        if self.current_path == node_path or self.current_path.startswith(node_path + "/"):
            raise OSError("Saia do diretório antes de excluí-lo.")

        blocks = [node.inode_block]
        self.disk.release(blocks)

        if self.security is not None:
            self.security.forget_blocks(blocks)

        del node.parent.children[node.name]
        print("Diretório removido com sucesso.")

    # ---------- Metadados de segurança ----------
    def set_mode(self, path, mode):
        node = self.resolve(path)
        node.mode = mode
        return node

    def set_ownership(self, path, owner, group):
        node = self.resolve(path)
        node.owner = owner
        node.group = group
        return node

    def tamper_block(self, index, content):
        """Simula gravação direta no bloco físico, fora das rotinas do SO."""
        if self.security is not None:
            self.security.require_kernel(
                f"modificação direta do bloco físico {index}"
            )

        if not 0 <= index < self.disk.total_blocks:
            raise ValueError("Índice de bloco inválido.")

        block = self.disk.blocks[index]

        if block is None:
            raise ValueError("O bloco está livre.")

        before = block.get("content")
        block["content"] = content
        # O checksum e o registro oficial permanecem os antigos: essa é a
        # adulteração que a varredura de integridade deve detectar.

        print(f"\n[MODO_KERNEL - ESCRITA DIRETA NO BLOCO {index:02d}]")
        print(f"Conteúdo anterior: {str(before)[:40]}")
        print(f'Conteúdo adulterado: "{content}"')
        print("Registro oficial de integridade NÃO foi atualizado.")
        print("Use 'antivirus_scan /' para detectar a anomalia.")

        if self.security is not None:
            self.security.log(
                f"TAMPER: bloco {index} alterado diretamente (bypass de integridade)"
            )

    # ---------- Navegação e árvore ----------
    def cd(self, path):
        node = self.resolve(path)

        if not node.is_directory():
            raise NotADirectoryError("Não é possível entrar em um arquivo.")

        self._check_traverse(self.get_path(node))
        self._check(node, EXECUTE)

        self.current_path = self.get_path(node)

    def pwd(self):
        print(self.current_path)

    def ls(self, path=".", long_format=False):
        node = self.resolve(path)

        self._check(node, READ, self.get_path(node))

        if not node.is_directory():
            self._print_entry(node, long_format)
            return

        if not node.children:
            print("(diretório vazio)")
            return

        if long_format:
            print(f"total {len(node.children)} itens")

        for child in node.children.values():
            self._print_entry(child, long_format)

    def _print_entry(self, child, long_format=False):
        if not long_format:
            if child.is_directory():
                print(f"{child.name}/ [DIR]")
            else:
                print(f"{child.name} ({child.size} bytes) [ARQ]")
            return

        suffix = "/" if child.is_directory() else ""
        lock = " [CRIPTOGRAFADO]" if child.encrypted else ""
        size = "-" if child.is_directory() else str(child.size)
        print(
            f"{mode_to_string(child.mode)} {child.owner}:{child.group:<10} "
            f"{size:>6} {child.name}{suffix}{lock}"
        )

    def show_tree(self, node=None, prefix=""):
        if node is None:
            node = self.root
            print("\n[ÁRVORE DO SISTEMA DE ARQUIVOS]")
            print("/")

        children = list(node.children.values())

        for index, child in enumerate(children):
            last = index == len(children) - 1
            connector = "└── " if last else "├── "
            next_prefix = prefix + ("    " if last else "│   ")

            if child.is_directory():
                print(f"{prefix}{connector}{child.name}/ [DIR]")
                self.show_tree(child, next_prefix)
            else:
                lock = " [CRIPTOGRAFADO]" if child.encrypted else ""
                print(
                    f"{prefix}{connector}{child.name} "
                    f"({child.size} bytes) [ARQ]{lock}"
                )

    # ---------- Diagnóstico do disco ----------
    def fs_status(self):
        disk = self.disk

        print("\n========== DIAGNÓSTICO DO DISCO ==========")
        print(f"Tamanho do bloco: {disk.block_size} bytes")
        print(f"Total de blocos: {disk.total_blocks}")
        print(f"Capacidade total: {disk.block_size * disk.total_blocks} bytes")
        print(f"Blocos ocupados: {disk.used_count()}")
        print(f"Blocos livres: {disk.free_count()}")

        disk.show_map(self.get_path)

        internal_total = 0
        print("\n--- RELATÓRIO DE FRAGMENTAÇÃO ---")

        for node in self._list_files(self.root):
            allocated = len(node.data_blocks) * disk.block_size
            internal = allocated - node.size
            internal_total += internal

            print(f"Arquivo: {self.get_path(node)}")
            print(f"  Tamanho real: {node.size} bytes")
            print(f"  Espaço alocado: {allocated} bytes")
            print(f"  Fragmentação interna: {internal} bytes")
            print(
                f"  Criptografia em repouso: "
                f"{'SIM' if node.encrypted else 'NÃO'}"
            )

        print(f"\nFragmentação interna total: {internal_total} bytes")
        print("Fragmentação externa: não aplicável à alocação indexada.")
        print("Necessidade de compactação: NÃO.")
        print("Motivo: os blocos de dados não precisam ser contíguos.")

        if self.security is not None:
            encrypted = [
                node for node in self._list_files(self.root) if node.encrypted
            ]
            session = self.security.current_user
            print("\n--- RESUMO DE SEGURANÇA ---")
            print(
                f"Usuários: {len(self.security.users)} | "
                f"Grupos: {len(self.security.groups)}"
            )
            print(f"Arquivos criptografados: {len(encrypted)}")
            print(
                "Sessão: "
                + (
                    f"'{session.name}' ({self.security.mode_label()})"
                    if session is not None else "(nenhuma)"
                )
            )
            print(
                f"Blocos com hash registrado: "
                f"{len(self.security.integrity_registry)}"
            )

        print("==========================================")

    def _list_files(self, directory):
        result = []

        for child in directory.children.values():
            if child.is_file():
                result.append(child)
            else:
                result.extend(self._list_files(child))

        return result

    # ---------- E/S ----------
    def perform_io(self, operation, blocks):
        """Gera requisições de E/S para os blocos do disco."""

        if not blocks:
            self._say("\nNenhuma requisição de E/S necessária.")
            return None

        self._say(f"\n[E/S - {operation}]")
        self._say(f"Blocos solicitados: {blocks}")

        result = self.scheduler.schedule(
            blocks,
            algorithm=self.io_algorithm,
            quiet=not self.verbose
        )

        self._say(f"Operação de {operation} concluída.")

        return result

    def set_io_algorithm(self, algorithm):
        algorithm = algorithm.upper()

        valid_algorithms = ["FCFS", "SSTF", "SCAN", "C-SCAN"]

        if algorithm not in valid_algorithms:
            raise ValueError("Algoritmo inválido.")

        self.io_algorithm = algorithm

        print(f"Algoritmo de E/S alterado para {algorithm}.")
