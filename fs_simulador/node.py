from dataclasses import dataclass, field


@dataclass
class Node:
    """Representa um diretório ou arquivo na árvore do sistema."""
    name: str
    kind: str  # "DIR" ou "FILE"
    parent: object = None
    size: int = 0
    inode_block: int = None
    data_blocks: list = field(default_factory=list)
    children: dict = field(default_factory=dict)

    # --- Etapa 3: matriz de acesso e proteção de dados ---
    owner: str = "root"
    group: str = "admin"
    mode: int = 0o644
    encrypted: bool = False
    crypto_salt: str = None
    plain_hash: str = None

    def is_directory(self):
        return self.kind == "DIR"

    def is_file(self):
        return self.kind == "FILE"
