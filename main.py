import re
import shlex

from fs_simulador.filesystem import FileSystem


def parse_size(value):
    """Converte tamanhos como 10KB, 2MB e 512B para bytes."""
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(B|KB|MB)?", value.upper())

    if not match:
        raise ValueError("Tamanho inválido. Exemplo: 10KB, 2MB ou 512B.")

    number = float(match.group(1))
    unit = match.group(2) or "B"
    multipliers = {"B": 1, "KB": 1024, "MB": 1024 * 1024}

    return int(number * multipliers[unit])


def show_help():
    print("""
========== COMANDOS ==========
mkdir /caminho              Criar diretório
create /caminho 10KB        Criar arquivo
read /caminho               Ler informações do arquivo
update /caminho 20KB        Atualizar tamanho do arquivo
rm /caminho                 Excluir arquivo
rmdir /caminho              Excluir diretório vazio
ls [caminho]                Listar diretório
cd /caminho                 Navegar entre diretórios
pwd                         Mostrar diretório atual
tree                        Exibir árvore completa
fs_status                   Diagnóstico e mapa do disco
io_algorithm SSTF       Selecionar algoritmo de E/S
help                        Mostrar comandos
exit                        Encerrar simulador
==============================
""")


def main():
    fs = FileSystem()

    print("======================================")
    print("   SIMULADOR DE SISTEMA DE ARQUIVOS")
    print("======================================")
    print("Digite 'help' para consultar os comandos.")

    while True:
        try:
            raw = input(f"\nroot@simulador:{fs.current_path}# ").strip()

            if not raw:
                continue

            parts = shlex.split(raw)
            command = parts[0].lower()

            if command == "exit":
                print("Encerrando simulador...")
                break
            elif command == "help":
                show_help()
            elif command == "mkdir":
                fs.mkdir(parts[1])
            elif command == "create":
                fs.create_file(parts[1], parse_size(parts[2]))
            elif command == "read":
                fs.read_file(parts[1])
            elif command == "update":
                fs.update_file(parts[1], parse_size(parts[2]))
            elif command == "rm":
                fs.remove_file(parts[1])
            elif command == "rmdir":
                fs.remove_directory(parts[1])
            elif command == "ls":
                fs.ls(parts[1] if len(parts) > 1 else ".")
            elif command == "cd":
                fs.cd(parts[1])
            elif command == "pwd":
                fs.pwd()
            elif command == "tree":
                fs.show_tree()
            elif command == "fs_status":
                fs.fs_status()
            elif command == "io_algorithm":
                fs.set_io_algorithm(parts[1]) 
            else:
                print(f"Comando '{command}' não reconhecido. Digite 'help'.")

        except IndexError:
            print("Erro: faltam argumentos. Digite 'help'.")
        except Exception as error:
            print(f"Erro: {error}")


if __name__ == "__main__":
    main()
