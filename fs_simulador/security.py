"""Camada de segurança do simulador.

Reúne identidade (usuários/grupos), autenticação com hash SHA-256 + salt,
privilégios (MODO_USUARIO / MODO_KERNEL), ACLs rwx e o registro de auditoria.
"""

import hashlib
import hmac
import secrets
from datetime import datetime

MODO_USUARIO = "MODO_USUARIO"
MODO_KERNEL = "MODO_KERNEL"

# Ações controladas pela matriz de acesso (ACL).
READ = "LEITURA"
WRITE = "ESCRITA"
EXECUTE = "EXECUÇÃO"

_ACTION_BIT = {READ: 4, WRITE: 2, EXECUTE: 1}
_ACTION_LABEL = {READ: "leitura", WRITE: "escrita", EXECUTE: "execução"}

DEFAULT_GROUPS = ("admin", "devs", "financeiro", "users")


class AccessDenied(Exception):
    """Acesso negado por ACL ou por privilégio insuficiente.

    A mensagem já foi impressa no formato do sistema de segurança, portanto
    a CLI apenas ignora a exceção.
    """

    def __str__(self):
        return ""


def mode_to_string(mode):
    """Converte um modo octal (ex.: 0o750) em rwxr-x---."""
    chars = ""

    for shift in (6, 3, 0):
        bits = (mode >> shift) & 0o7
        chars += "r" if bits & 4 else "-"
        chars += "w" if bits & 2 else "-"
        chars += "x" if bits & 1 else "-"

    return chars


def parse_mode(text):
    """Aceita 750, 0750 ou rwxr-x--- e devolve o modo inteiro."""
    text = text.strip()

    if text and all(char in "01234567" for char in text):
        value = int(text, 8)
        if 0 <= value <= 0o777:
            return value
        raise ValueError("Modo octal fora do intervalo (0 a 777).")

    if len(text) == 9 and all(char in "rwx-" for char in text):
        mode = 0
        for index, char in enumerate(text):
            if char != "-":
                mode |= 1 << (8 - index)
        return mode

    raise ValueError("Modo inválido. Use octal (750) ou simbólico (rwxr-x---).")


class User:
    """Conta de usuário do simulador."""

    def __init__(self, name, group, password_hash, salt, uid, is_admin=False):
        self.name = name
        self.group = group
        self.password_hash = password_hash
        self.salt = salt
        self.uid = uid
        self.is_admin = is_admin

    def __repr__(self):
        return f"User({self.name!r}, uid={self.uid}, grupo={self.group!r})"


class SecurityManager:
    """Registro de identidades, sessão atual, privilégios e ACLs."""

    def __init__(self):
        self.users = {}
        self.groups = {name: set() for name in DEFAULT_GROUPS}
        self.current_user = None
        self.kernel_mode = False
        self.logs = []
        self.integrity_registry = {}
        self.silent = False
        self._kernel_origin = None
        self._next_uid = 1000

    # ---------- Senhas ----------
    @staticmethod
    def hash_password(password, salt=None):
        """Gera SHA-256(salt + senha) e o salt utilizado."""
        if salt is None:
            salt = secrets.token_hex(8)

        digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        return digest, salt

    def verify_password(self, user, password):
        digest, _ = self.hash_password(password, user.salt)
        return hmac.compare_digest(digest, user.password_hash)

    # ---------- Registro de identidades ----------
    def is_in_group(self, user_name, group):
        user = self.users.get(user_name)

        if user is not None and user.group == group:
            return True

        return user_name in self.groups.get(group, set())

    def groups_of(self, user_name):
        memberships = {
            group for group, members in self.groups.items()
            if user_name in members
        }

        user = self.users.get(user_name)
        if user is not None:
            memberships.add(user.group)

        return sorted(memberships)

    def add_group(self, name, privilege=True):
        if privilege:
            self.require_kernel(f"cadastro do grupo '{name}'")

        name = name.strip()

        if not name:
            raise ValueError("Nome de grupo inválido.")

        if name in self.groups:
            raise ValueError(f"Grupo '{name}' já existe.")

        self.groups[name] = set()
        self.log(f"GROUPADD: grupo '{name}' criado")

        if not self.silent:
            print(f"Grupo '{name}' criado com sucesso.")

        return name

    def add_user(self, name, group, password, is_admin=False, privilege=True):
        if privilege:
            self.require_kernel(f"cadastro do usuário '{name}'")

        name = name.strip()

        if not name or any(char in name for char in "/\\:"):
            raise ValueError("Nome de usuário inválido.")

        if name in self.users:
            raise ValueError(f"Usuário '{name}' já existe.")

        if group not in self.groups:
            raise ValueError(
                f"Grupo '{group}' não existe. Cadastre com 'groupadd {group}'."
            )

        if not password:
            raise ValueError("A senha não pode ser vazia.")

        digest, salt = self.hash_password(password)

        uid = 0 if name == "root" else self._next_uid
        if name != "root":
            self._next_uid += 1

        user = User(name, group, digest, salt, uid, is_admin or name == "root")
        self.users[name] = user
        self.groups[group].add(name)
        self.log(f"USERADD: '{name}' (uid={uid}, grupo='{group}', admin={user.is_admin})")

        return user

    def change_password(self, name, password):
        user = self.users.get(name)

        if user is None:
            raise ValueError(f"Usuário '{name}' não existe.")

        if not password:
            raise ValueError("A senha não pode ser vazia.")

        digest, salt = self.hash_password(password)
        user.password_hash = digest
        user.salt = salt
        self.log(f"PASSWD: senha de '{name}' atualizada (novo salt e novo hash)")

    # ---------- Sessão e privilégios ----------
    def mode_label(self):
        return MODO_KERNEL if self.kernel_mode else MODO_USUARIO

    def login(self, name, password):
        user = self.users.get(name)

        if user is None or not self.verify_password(user, password):
            self.log(f"FALHA DE AUTENTICAÇÃO: tentativa de login com o usuário '{name}'")
            raise PermissionError("Credenciais inválidas.")

        self.current_user = user
        self.kernel_mode = user.is_admin
        self._kernel_origin = None
        self.log(f"LOGIN: '{name}' autenticado em {self.mode_label()}")

        if not self.silent:
            print(
                f"Autenticado com sucesso. Usuário: '{user.name}' | "
                f"Grupo: '{user.group}' | Modo: {self.mode_label()}"
            )

    def start_system_session(self):
        """Sessão automática de root usada apenas durante o boot."""
        root = self.users.get("root")

        if root is None:
            raise RuntimeError("Usuário root não cadastrado.")

        self.current_user = root
        self.kernel_mode = True

    def logout(self):
        if self.current_user is None:
            raise PermissionError("Nenhuma sessão ativa.")

        self.log(f"LOGOUT: sessão de '{self.current_user.name}' encerrada")
        self.current_user = None
        self.kernel_mode = False
        self._kernel_origin = None

    def su(self, name, password):
        if self.current_user is None:
            raise PermissionError("Faça login antes de elevar privilégios.")

        target = self.users.get(name)

        if target is None or not self.verify_password(target, password):
            self.log(f"FALHA DE ELEVAÇÃO: 'su {name}' com credenciais inválidas")
            raise PermissionError("Credenciais inválidas.")

        if not target.is_admin:
            self.log(f"ELEVAÇÃO NEGADA: '{target.name}' não é conta administrativa")
            raise PermissionError("Somente contas administrativas ativam o MODO_KERNEL.")

        self._kernel_origin = self.current_user
        self.current_user = target
        self.kernel_mode = True
        self.log(f"SU: elevação de privilégios para MODO_KERNEL como '{name}'")

        print("\n[ELEVAÇÃO DE PRIVILÉGIOS]")
        print(f"Usuário efetivo: '{target.name}' | Modo: {MODO_KERNEL}")
        print("Operações críticas liberadas: useradd, groupadd, chown, passwd de terceiros,")
        print("chmod irrestrito, tamper_block e leitura sem restrição de ACL.")
        print("Use 'kernel_mode off' para retornar ao MODO_USUARIO.")

    def drop_kernel(self):
        if not self.kernel_mode:
            raise PermissionError("A sessão já está em MODO_USUARIO.")

        self.kernel_mode = False
        origin = self._kernel_origin
        self._kernel_origin = None

        if origin is not None:
            self.current_user = origin

        self.log("SU: retorno ao MODO_USUARIO")
        print(
            f"[PRIVILÉGIOS] MODO_USUARIO restaurado. "
            f"Sessão de '{self.current_user.name}'."
        )

    def require_session(self):
        if self.current_user is None:
            if not self.silent:
                print(
                    "\n[SISTEMA DE SEGURANÇA] Nenhuma sessão autenticada. "
                    "Use 'login --user <nome>'."
                )
            raise AccessDenied()

    def require_kernel(self, operation):
        if self.kernel_mode and self.current_user is not None and self.current_user.is_admin:
            return

        self.log(f"PRIVILÉGIO NEGADO: '{operation}' exige MODO_KERNEL")

        if not self.silent:
            print("\n[PRIVILÉGIOS INSUFICIENTES]")
            print(f"Operação crítica   : {operation}")
            print("Privilégio exigido : MODO_KERNEL (superusuário/root)")
            print("Como elevar        : su --user root")
            print("Tentativa registrada nos logs do sistema.")

        raise AccessDenied()

    def require_owner_or_kernel(self, node, path, operation):
        if self.kernel_mode and self.current_user is not None and self.current_user.is_admin:
            return

        if self.current_user is not None and node.owner == self.current_user.name:
            return

        user_name = self.current_user.name if self.current_user else "visitante"
        self.log(f"PRIVILÉGIO NEGADO: '{operation}' por '{user_name}' em '{path}'")

        if not self.silent:
            print("\n[PRIVILÉGIOS INSUFICIENTES]")
            print(f"Operação crítica   : {operation}")
            print(f"Objeto             : {path} (proprietário: {node.owner})")
            print("Exige ser o proprietário do objeto ou estar em MODO_KERNEL.")
            print("Tentativa registrada nos logs do sistema.")

        raise AccessDenied()

    # ---------- Controle de acesso (ACL) ----------
    def _permission_bits(self, node, user_name):
        if node.owner == user_name:
            return (node.mode >> 6) & 0o7

        if self.is_in_group(user_name, node.group):
            return (node.mode >> 3) & 0o7

        return node.mode & 0o7

    def check_access(self, node, action, path, show=True):
        """Verifica a ACL e imprime o laudo de verificação.

        Levanta AccessDenied quando o acesso não é permitido.
        """
        self.require_session()

        user = self.current_user
        required_bit = _ACTION_BIT[action]
        permitted = False

        if user.name == "root":
            permitted = True
            reason = "'root' possui bypass de ACL (superusuário)."
        else:
            bits = self._permission_bits(node, user.name)
            permitted = bool(bits & required_bit)
            reason = ""

        if not self.silent and show:
            print("\n[SISTEMA DE SEGURANÇA - VERIFICAÇÃO DE ACL]")
            print(f"Objeto      : {path}")
            print(f"Proprietário: {node.owner} (Grupo: {node.group})")
            print(f"Permissões  : {mode_to_string(node.mode)} ({node.mode:o})")
            print(
                f"Ação Pedida : {action} por '{user.name}' "
                f"(Grupo: {user.group})"
            )
            print()

        if permitted:
            if not self.silent and show:
                if reason:
                    print(f"[PERMITIDO]: {reason}")
                else:
                    print(
                        f"[PERMITIDO]: o usuário '{user.name}' possui permissão de "
                        f"{_ACTION_LABEL[action]} em '{path}'."
                    )
            return True

        self.log(
            f"ACESSO NEGADO: '{user.name}' tentou {action} em '{path}' "
            f"(modo {mode_to_string(node.mode)})"
        )

        if not self.silent:
            if not show:
                print("\n[SISTEMA DE SEGURANÇA - VERIFICAÇÃO DE ACL]")
                print(f"Objeto      : {path}")
                print(f"Proprietário: {node.owner} (Grupo: {node.group})")
                print(f"Permissões  : {mode_to_string(node.mode)} ({node.mode:o})")
                print(f"Ação Pedida : {action} por '{user.name}' (Grupo: {user.group})")
                print()

            print(
                f"[NEGADO]: O usuário '{user.name}' não possui permissão de "
                f"{_ACTION_LABEL[action]} no objeto '{path}'."
            )
            print("Tentativa não autorizada registrada nos logs do sistema.")

        raise AccessDenied()

    # ---------- Integridade dos blocos ----------
    def register_block(self, index, checksum):
        self.integrity_registry[index] = checksum

    def forget_blocks(self, indexes):
        for index in indexes:
            self.integrity_registry.pop(index, None)

    # ---------- Auditoria ----------
    def log(self, message):
        stamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.logs.append(f"[{stamp}] {message}")

    def show_logs(self, limit=40):
        print("\n[REGISTRO DE AUDITORIA - SECURITY LOG]")

        if not self.logs:
            print("(nenhum evento registrado)")
            return

        for entry in self.logs[-limit:]:
            print(entry)

        if len(self.logs) > limit:
            print(f"... exibindo os {limit} eventos mais recentes de {len(self.logs)}.")

    # ---------- Relatórios ----------
    def show_identity(self):
        print("\n[CADASTRO DE IDENTIDADES]")
        print("USUÁRIOS:")

        for user in self.users.values():
            flag = " [ADMIN]" if user.is_admin else ""
            print(
                f"- {user.name:<10} uid={user.uid:<5} grupo={user.group:<10}"
                f" hash={user.password_hash[:12]}...{flag}"
            )

        print("\nGRUPOS:")

        for name, members in self.groups.items():
            listing = ", ".join(sorted(members)) or "(vazio)"
            print(f"- {name:<10} membros: {listing}")

        if self.current_user is not None:
            print(
                f"\nSessão atual: '{self.current_user.name}' | "
                f"Modo: {self.mode_label()}"
            )
        else:
            print("\nSessão atual: (nenhuma)")

    def show_current_identity(self):
        if self.current_user is None:
            print("Nenhuma sessão autenticada.")
            return

        user = self.current_user
        groups = ", ".join(self.groups_of(user.name))
        print(
            f"uid={user.uid}({user.name}) grupo={user.group} "
            f"grupos=[{groups}] modo={self.mode_label()}"
        )
