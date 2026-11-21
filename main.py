import getpass
import re
import shlex

from fs_simulador.ambiente import bootstrap
from fs_simulador.antivirus import AntivirusScanner
from fs_simulador.filesystem import FileSystem
from fs_simulador.memory_manager import MemoryManager
from fs_simulador.raid import RAID5Controller
from fs_simulador.security import (
    AccessDenied,
    SecurityManager,
    mode_to_string,
    parse_mode,
)


def parse_size(value):
    """Converte tamanhos como 10KB, 2MB e 512B para bytes."""
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(B|KB|MB)?", value.upper())

    if not match:
        raise ValueError("Tamanho inválido. Exemplo: 10KB, 2MB ou 512B.")

    number = float(match.group(1))
    unit = match.group(2) or "B"
    multipliers = {"B": 1, "KB": 1024, "MB": 1024 * 1024}

    return int(number * multipliers[unit])


def parse_arguments(args):
    """Separa argumentos posicionais de opções no formato --chave valor."""
    positional = []
    options = {}
    index = 0

    while index < len(args):
        token = args[index]

        if token.startswith("--"):
            name = token[2:].lower()

            if index + 1 < len(args) and not args[index + 1].startswith("--"):
                options[name] = args[index + 1]
                index += 2
            else:
                options[name] = True
                index += 1
        else:
            positional.append(token)
            index += 1

    return positional, options


def show_help():
    print("""
========== ETAPAS 1 e 2: ARQUIVOS, E/S E RAID 5 ==========
mkdir /caminho                  Criar diretório
create /caminho 10KB            Criar arquivo (i-node + blocos)
write_file /caminho "texto"     Gravar conteúdo em texto claro
read /caminho                   Ler metadados e conteúdo
cat /caminho                    Exibir apenas o conteúdo
update /caminho 20KB            Atualizar tamanho (re-alocação)
rm /caminho                     Excluir arquivo
rmdir /caminho                  Excluir diretório vazio
ls [-l] [caminho]               Listar (-l exibe ACL rwx, dono e grupo)
cd /caminho                     Navegar entre diretórios
pwd                             Mostrar diretório atual
tree                            Exibir árvore completa
fs_status                       Diagnóstico do disco + resumo de segurança
io_algorithm SSTF               Selecionar algoritmo de E/S
fail_disk 2                     Simular falha física no disco 1, 2 ou 3

========== ETAPA 3: SEGURANÇA ==========
login --user <nome>             Autenticar (senha solicitada na hora)
logout                          Encerrar a sessão
whoami | id | users             Identidade da sessão e cadastros
useradd <nome> --group <g>      [MODO_KERNEL] Cadastrar usuário
groupadd <nome>                 [MODO_KERNEL] Cadastrar grupo
passwd [--user <nome>]          Trocar senha (própria ou via MODO_KERNEL)
su --user root                  Elevar privilégios para MODO_KERNEL
kernel_mode off                 Retornar ao MODO_USUARIO
chmod <750|rwxr-x---> <caminho> Alterar permissões (dono ou MODO_KERNEL)
chown <usuario>[:<grupo>] <p>   [MODO_KERNEL] Alterar proprietário
encrypt_file <p> --key "K"      Criptografar o conteúdo nos blocos físicos
decrypt_file <p> --key "K"      Descriptografar e exibir (valida SHA-256)
antivirus_scan [caminho]        Varredura de integridade + assinaturas
tamper_block <n> --content "X"  [MODO_KERNEL] Adulterar bloco (demonstração)
security_log                    Registro de auditoria da sessão

========== ETAPA 4: GERENCIAMENTO DE MEMÓRIA ==========
create_process --name "P" --size 512KB --type <critical|normal>  Alocar processo (Reservada ou Virtual)
terminate_process --name "P"                                     Finalizar processo e liberar memória
memory_status [--reserved|--virtual]                             Mapa da RAM, fragmentação e Page Faults
memory_compact --reserved                                        [MODO_KERNEL] Compactar Área Reservada
translate_address --process P --page <n>                         Traduzir Página Lógica -> Moldura Física
execute_step --process P --instruction "LOAD_DATA Página <n>"    Simular acesso à memória / Page Fault / Swap
page_algorithm <LRU|SECOND_CHANCE>                               Selecionar política de substituição

========== GERAL ==========
help                            Mostrar comandos
exit                            Encerrar simulador
==========================================================
""")


def build_prompt(fs, security):
    if security.current_user is None:
        return "\nvisitante@simulador:/$ "

    symbol = "#" if security.kernel_mode else "$"
    return f"\n{security.current_user.name}@simulador:{fs.current_path}{symbol} "


def main():
    security = SecurityManager()
    fs = FileSystem(security=security)
    raid = RAID5Controller()
    scanner = AntivirusScanner(fs, security)
    mem = MemoryManager(filesystem=fs)

    print("==========================================================")
    print("   SIMULADOR DE SISTEMA OPERACIONAL")
    print("   Etapas 1-4: Arquivos | E/S + RAID | Segurança | Memória")
    print("==========================================================")

    bootstrap(fs, security)
    print("\nFaça login para operar o sistema. Digite 'help' para os comandos.")

    while True:
        try:
            raw = input(build_prompt(fs, security)).strip()

            if not raw:
                continue

            parts = shlex.split(raw)
            command = parts[0].lower()
            positional, options = parse_arguments(parts[1:])

            if command == "exit":
                print("Encerrando simulador...")
                break

            elif command == "help":
                show_help()

            # ---------- Etapa 3: identidade e autenticação ----------
            elif command == "login":
                name = options.get("user") or (positional[0] if positional else None)

                if not name:
                    raise ValueError("Uso: login --user <nome>")

                password = options.get("senha") or getpass.getpass("Senha: ")
                security.login(name, password)

            elif command == "logout":
                security.logout()
                print("Sessão encerrada.")

            elif command == "whoami":
                if security.current_user is None:
                    print("visitante (nenhuma sessão autenticada)")
                else:
                    print(security.current_user.name)

            elif command == "id":
                security.require_session()
                security.show_current_identity()

            elif command == "users":
                security.require_session()
                security.show_identity()

            elif command == "useradd":
                security.require_session()

                if not positional:
                    raise ValueError("Uso: useradd <nome> --group <grupo>")

                name = positional[0]
                group = options.get("group") or options.get("grupo")

                if not group:
                    raise ValueError("Informe o grupo: useradd <nome> --group <grupo>")

                password = options.get("senha") or getpass.getpass(
                    f"Nova senha para '{name}': "
                )
                user = security.add_user(
                    name, group, password, is_admin=bool(options.get("admin"))
                )

                print(
                    f"Usuário '{user.name}' cadastrado (uid={user.uid}, "
                    f"grupo='{group}', admin={user.is_admin})."
                )
                print(
                    f"Senha armazenada como SHA-256(salt + senha): "
                    f"{user.password_hash[:16]}..."
                )

            elif command == "groupadd":
                security.require_session()

                if not positional:
                    raise ValueError("Uso: groupadd <nome>")

                security.add_group(positional[0])

            elif command == "passwd":
                security.require_session()
                target = options.get("user") or (
                    positional[0] if positional else security.current_user.name
                )

                if target != security.current_user.name:
                    security.require_kernel(f"troca de senha do usuário '{target}'")

                new_password = options.get("senha") or getpass.getpass(
                    f"Nova senha para '{target}': "
                )

                if not options.get("senha"):
                    if getpass.getpass("Confirme a nova senha: ") != new_password:
                        raise ValueError("As senhas não coincidem.")

                security.change_password(target, new_password)
                print(f"Senha de '{target}' atualizada (novo salt + novo hash).")

            elif command == "su":
                security.require_session()
                target = options.get("user") or options.get("usuario") or "root"
                password = options.get("senha") or getpass.getpass(
                    f"Senha de '{target}': "
                )
                security.su(target, password)

            elif command == "kernel_mode":
                option = positional[0].lower() if positional else ""

                if option in ("off", "usuario", "user"):
                    security.drop_kernel()
                elif option in ("on", "kernel"):
                    print("Para elevar privilégios use: su --user root")
                else:
                    raise ValueError("Uso: kernel_mode off")

            # ---------- Etapa 3: matriz de acesso (ACL) ----------
            elif command == "chmod":
                security.require_session()

                if len(positional) < 2:
                    raise ValueError("Uso: chmod <modo> <caminho>")

                node = fs.resolve(positional[1])
                security.require_owner_or_kernel(
                    node, fs.get_path(node), "alteração de permissões (chmod)"
                )
                fs.set_mode(positional[1], parse_mode(positional[0]))

                updated = fs.resolve(positional[1])
                print(
                    f"Permissões de '{fs.get_path(updated)}' alteradas para "
                    f"{mode_to_string(updated.mode)} ({updated.mode:o})."
                )

            elif command == "chown":
                security.require_session()
                security.require_kernel("alteração de proprietário (chown)")

                if len(positional) < 2:
                    raise ValueError("Uso: chown <usuario>[:<grupo>] <caminho>")

                spec = positional[0]
                path = positional[1]

                if ":" in spec:
                    owner, group = spec.split(":", 1)
                else:
                    owner, group = spec, None

                if owner not in security.users:
                    raise ValueError(f"Usuário '{owner}' não existe.")

                if group is None:
                    group = fs.resolve(path).group

                if group not in security.groups:
                    raise ValueError(f"Grupo '{group}' não existe.")

                node = fs.set_ownership(path, owner, group)
                print(
                    f"Proprietário de '{fs.get_path(node)}' agora é "
                    f"{node.owner}:{node.group}."
                )

            # ---------- Etapa 3: criptografia e integridade ----------
            elif command == "encrypt_file":
                security.require_session()

                if not positional:
                    raise ValueError(
                        'Uso: encrypt_file /caminho --key "MinhaChave123"'
                    )

                key = options.get("key") or options.get("chave")

                if not key:
                    raise ValueError(
                        'Informe a chave: encrypt_file /caminho --key "MinhaChave123"'
                    )

                fs.encrypt_file(positional[0], key)

            elif command == "decrypt_file":
                security.require_session()

                if not positional:
                    raise ValueError(
                        'Uso: decrypt_file /caminho --key "MinhaChave123"'
                    )

                key = options.get("key") or options.get("chave")

                if not key:
                    raise ValueError(
                        'Informe a chave: decrypt_file /caminho --key "MinhaChave123"'
                    )

                fs.decrypt_file(positional[0], key)

            elif command == "antivirus_scan":
                security.require_session()
                scanner.scan(positional[0] if positional else "/")

            elif command == "tamper_block":
                security.require_session()

                if not positional:
                    raise ValueError(
                        'Uso: tamper_block <indice> --content "conteudo"'
                    )

                fs.tamper_block(
                    int(positional[0]),
                    options.get("content") or "conteudo adulterado"
                )

            elif command == "security_log":
                security.require_session()
                security.show_logs()

            # ---------- Etapa 4: gerenciamento de memória ----------
            elif command == "create_process":
                security.require_session()

                name = options.get("name") or (positional[0] if positional else None)
                size_str = options.get("size") or (
                    positional[1] if len(positional) > 1 else None
                )
                ptype = str(options.get("type", "normal")).lower()

                if not name or not size_str:
                    raise ValueError(
                        'Uso: create_process --name "Processo" --size 512KB --type <critical|normal>'
                    )

                if ptype == "critical":
                    security.require_kernel(
                        f"alocação do processo crítico '{name}' na Área Reservada"
                    )

                mem.create_process(name, parse_size(size_str), ptype)

            elif command == "terminate_process":
                security.require_session()

                name = options.get("name") or (positional[0] if positional else None)

                if not name:
                    raise ValueError('Uso: terminate_process --name "Processo"')

                proc_info = mem.process_registry.get(name)
                if proc_info and proc_info["type"] == "critical":
                    security.require_kernel(
                        f"encerramento do processo crítico '{name}'"
                    )

                mem.terminate_process(name)

            elif command == "memory_status":
                security.require_session()

                if options.get("reserved"):
                    mem.show_status("reserved")
                elif options.get("virtual"):
                    mem.show_status("virtual")
                else:
                    mem.show_status("all")

            elif command == "memory_compact":
                security.require_session()
                security.require_kernel("compactação da Área Reservada da RAM")

                if options.get("reserved") or not options:
                    mem.compact_reserved()
                else:
                    raise ValueError("Uso: memory_compact --reserved")

            elif command == "translate_address":
                security.require_session()

                proc = options.get("process") or (positional[0] if positional else None)
                page_val = (
                    options.get("page")
                    if "page" in options
                    else (positional[1] if len(positional) > 1 else None)
                )

                if not proc or page_val is None or isinstance(page_val, bool):
                    raise ValueError(
                        "Uso: translate_address --process <nome> --page <numero>"
                    )

                mem.translate_address(proc, int(page_val))

            elif command == "execute_step":
                security.require_session()

                proc = options.get("process") or (positional[0] if positional else None)
                instr = options.get("instruction") or (
                    positional[1] if len(positional) > 1 else None
                )

                if not proc or not instr:
                    raise ValueError(
                        'Uso: execute_step --process <nome> --instruction "LOAD_DATA Página 2"'
                    )

                mem.execute_step(proc, instr)

            elif command == "page_algorithm":
                security.require_session()

                algo = options.get("algorithm") or (
                    positional[0] if positional else None
                )

                if not algo:
                    raise ValueError("Uso: page_algorithm <LRU|SECOND_CHANCE>")

                mem.virtual.set_algorithm(algo)

            # ---------- Etapas 1 e 2: arquivos, E/S e RAID ----------
            elif command == "mkdir":
                security.require_session()
                fs.mkdir(positional[0])

            elif command == "create":
                security.require_session()

                if not positional:
                    raise ValueError("Uso: create /caminho 10KB")

                caminho = positional[0]
                tamanho = parse_size(positional[1]) if len(positional) > 1 else 0

                fs.create_file(caminho, tamanho, content=options.get("content"))

                # Localiza o arquivo recém-criado para pegar os blocos alocados
                node_criado = fs.resolve(caminho)

                # Dispara a controladora RAID para distribuir dados e paridade
                raid.write_stripe(caminho, node_criado.data_blocks)

            elif command == "write_file":
                security.require_session()

                if not positional:
                    raise ValueError('Uso: write_file /caminho "conteúdo"')

                content = options.get("content")

                if content is None:
                    if len(positional) < 2:
                        raise ValueError('Uso: write_file /caminho "conteúdo"')
                    content = " ".join(positional[1:])

                fs.write_file(positional[0], content)

            elif command == "read":
                security.require_session()
                fs.read_file(positional[0])

            elif command == "cat":
                security.require_session()
                fs.cat(positional[0])

            elif command == "update":
                security.require_session()
                fs.update_file(positional[0], parse_size(positional[1]))

            elif command == "rm":
                security.require_session()
                fs.remove_file(positional[0])

            elif command == "rmdir":
                security.require_session()
                fs.remove_directory(positional[0])

            elif command == "ls":
                security.require_session()
                long_format = "-l" in positional
                targets = [item for item in positional if not item.startswith("-")]
                fs.ls(targets[0] if targets else ".", long_format)

            elif command == "cd":
                security.require_session()
                fs.cd(positional[0])

            elif command == "pwd":
                security.require_session()
                fs.pwd()

            elif command == "tree":
                security.require_session()
                fs.show_tree()

            elif command == "fs_status":
                security.require_session()
                fs.fs_status()

            elif command == "io_algorithm":
                security.require_session()
                fs.set_io_algorithm(positional[0])

            elif command == "fail_disk":
                security.require_session()
                raid.simulate_failure(int(positional[0]))

            else:
                print(f"Comando '{command}' não reconhecido. Digite 'help'.")

        except AccessDenied:
            # O laudo de negação já foi impresso pela camada de segurança.
            continue
        except EOFError:
            print("\nEncerrando simulador...")
            break
        except KeyboardInterrupt:
            print("\nEncerrando simulador...")
            break
        except IndexError:
            print("Erro: faltam argumentos. Digite 'help'.")
        except Exception as error:
            print(f"Erro: {error}")


if __name__ == "__main__":
    main()