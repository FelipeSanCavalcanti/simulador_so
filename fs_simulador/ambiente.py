"""Ambiente inicial (boot) do simulador.

Cria usuários, grupos e uma árvore mínima equivalente aos exemplos da Etapa 3,
sempre com a sessão de boot em MODO_KERNEL e sem poluir a saída com logs de E/S.
"""

from fs_simulador.security import SecurityManager


def bootstrap(fs, security: SecurityManager):
    security.silent = True
    fs.verbose = False

    security.add_user(
        "root", "admin", "root123", is_admin=True, privilege=False
    )
    security.add_user("carlos", "devs", "carlos123", privilege=False)
    security.add_user("ana", "financeiro", "ana123", privilege=False)

    security.start_system_session()

    fs.mkdir("/sistema")
    fs.mkdir("/sistema/logs")
    fs.mkdir("/home")
    fs.mkdir("/home/carlos")
    fs.mkdir("/home/ana")

    fs.create_file(
        "/sistema/config.sys", 0,
        content="kernel.secure=1\nboot.mode=protected\n"
    )
    fs.set_mode("/sistema/config.sys", 0o750)

    fs.create_file(
        "/sistema/logs/app.log", 0,
        content="12:00 boot ok\n12:01 scheduler=SSTF\n"
    )
    fs.set_mode("/sistema/logs/app.log", 0o640)

    fs.set_mode("/sistema", 0o755)
    fs.set_mode("/sistema/logs", 0o750)

    fs.create_file(
        "/home/carlos/segredo.txt", 0,
        content="Anotacoes privadas do carlos: token=Tr0car!2026"
    )
    fs.set_ownership("/home/carlos/segredo.txt", "carlos", "devs")
    fs.set_mode("/home/carlos/segredo.txt", 0o600)

    fs.create_file(
        "/home/carlos/notas.txt", 0,
        content="Relatorio de E/S da Etapa 2 revisado."
    )
    fs.set_ownership("/home/carlos/notas.txt", "carlos", "devs")
    fs.set_mode("/home/carlos/notas.txt", 0o640)

    fs.set_ownership("/home/carlos", "carlos", "devs")
    fs.set_mode("/home/carlos", 0o700)

    fs.set_ownership("/home/ana", "ana", "financeiro")
    fs.set_mode("/home/ana", 0o700)

    fs.verbose = True
    security.silent = False
    security.logout()

    print("\n[AMBIENTE DE DEMONSTRAÇÃO CARREGADO]")
    print("Contas disponíveis (senha entre parênteses):")
    print("  root   (root123)     -> grupo admin       | MODO_KERNEL")
    print("  carlos (carlos123)   -> grupo devs        | MODO_USUARIO")
    print("  ana    (ana123)      -> grupo financeiro  | MODO_USUARIO")
    print("Árvore inicial: /sistema/config.sys (750 root:admin),")
    print("/sistema/logs/app.log (640), /home/carlos (700), /home/ana (700)")
