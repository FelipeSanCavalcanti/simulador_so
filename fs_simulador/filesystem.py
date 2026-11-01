import math
import posixpath

from fs_simulador.disk import Disk
from fs_simulador.node import Node


class FileSystem:
    """Gerencia a árvore de diretórios e arquivos."""

    def __init__(self):
        self.disk = Disk(block_size=4096, total_blocks=16)
        self.root = Node("/", "DIR")
        self.current_path = "/"

        # O bloco zero guarda o i-node do diretório raiz.
        self.root.inode_block = self.disk.allocate(
            1, self.root, "INODE"
        )[0]

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

    # ---------- Criar ----------
    def mkdir(self, path):
        parent, name = self.get_parent(path)

        if name in parent.children:
            raise FileExistsError("Já existe um item com esse nome.")

        node = Node(name, "DIR", parent=parent)
        node.inode_block = self.disk.allocate(1, node, "INODE")[0]
        parent.children[name] = node

        print(f"Diretório '{name}' criado com sucesso.")

    def create_file(self, path, size):
        if size < 0:
            raise ValueError("O tamanho não pode ser negativo.")

        parent, name = self.get_parent(path)

        if name in parent.children:
            raise FileExistsError("Já existe um item com esse nome.")

        node = Node(name, "FILE", parent=parent, size=size)
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
        print(f"Arquivo '{name}' criado com sucesso.")

    # ---------- Ler ----------
    def read_file(self, path):
        node = self.resolve(path)

        if not node.is_file():
            raise ValueError("O caminho não é um arquivo.")

        print(f"\nArquivo: {node.name}")
        print(f"Caminho: {self.get_path(node)}")
        print(f"Tamanho: {node.size} bytes")
        print(f"i-node: bloco {node.inode_block}")
        print(f"Blocos de dados: {node.data_blocks}")

    # ---------- Atualizar ----------
    def update_file(self, path, new_size):
        if new_size < 0:
            raise ValueError("O tamanho não pode ser negativo.")

        node = self.resolve(path)

        if not node.is_file():
            raise ValueError("O caminho não é um arquivo.")

        old_amount = len(node.data_blocks)
        new_amount = self.disk.data_blocks_needed(new_size)
        difference = new_amount - old_amount

        if difference > 0:
            # Só altera o arquivo depois que a reserva for bem-sucedida.
            extra = self.disk.allocate(difference, node, "DATA")
            node.data_blocks.extend(extra)

        elif difference < 0:
            removed = node.data_blocks[new_amount:]
            self.disk.release(removed)
            node.data_blocks = node.data_blocks[:new_amount]

        node.size = new_size
        print("Arquivo atualizado com sucesso.")

    # ---------- Excluir ----------
    def remove_file(self, path):
        node = self.resolve(path)

        if not node.is_file():
            raise ValueError("O item não é um arquivo.")

        self.disk.release([node.inode_block] + node.data_blocks)
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

        node_path = self.get_path(node)
        if self.current_path == node_path or self.current_path.startswith(node_path + "/"):
            raise OSError("Saia do diretório antes de excluí-lo.")

        self.disk.release([node.inode_block])
        del node.parent.children[node.name]
        print("Diretório removido com sucesso.")

    # ---------- Navegação e árvore ----------
    def cd(self, path):
        node = self.resolve(path)

        if not node.is_directory():
            raise NotADirectoryError("Não é possível entrar em um arquivo.")

        self.current_path = self.get_path(node)

    def pwd(self):
        print(self.current_path)

    def ls(self, path="."):
        node = self.resolve(path)

        if not node.is_directory():
            print(node.name)
            return

        if not node.children:
            print("(diretório vazio)")
            return

        for child in node.children.values():
            if child.is_directory():
                print(f"{child.name}/ [DIR]")
            else:
                print(f"{child.name} ({child.size} bytes) [ARQ]")

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
                print(
                    f"{prefix}{connector}{child.name} "
                    f"({child.size} bytes) [ARQ]"
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

        print(f"\nFragmentação interna total: {internal_total} bytes")
        print("Fragmentação externa: não aplicável à alocação indexada.")
        print("Necessidade de compactação: NÃO.")
        print("Motivo: os blocos de dados não precisam ser contíguos.")
        print("==========================================")

    def _list_files(self, directory):
        result = []

        for child in directory.children.values():
            if child.is_file():
                result.append(child)
            else:
                result.extend(self._list_files(child))

        return result
