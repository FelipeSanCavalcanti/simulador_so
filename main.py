from fs_simulador.filesystem import FileSystem

def main():
    fs = FileSystem()
    print("Simulador de Sistema de Arquivos Iniciado. Digite 'help' para comandos ou 'exit' para sair.")
    
    while True:
        try:
            comando_bruto = input("\nroot@simulador:~# ").strip()
            if not comando_bruto:
                continue
                
            partes = comando_bruto.split()
            comando = partes[0].lower()

            if comando == "exit":
                break
            elif comando == "mkdir":
                # Ex: mkdir /sistema
                fs.mkdir(partes[1])
            elif comando == "create":
                # Ex: create /sistema/app.log 10240
                fs.create_file(partes[1], int(partes[2]))
            elif comando == "tree":
                fs.show_tree()
            else:
                print(f"Comando '{comando}' não reconhecido.")
                
        except IndexError:
            print("Erro: Faltam argumentos para o comando.")
        except Exception as e:
            print(f"Erro inesperado: {e}")

if __name__ == "__main__":
    main()