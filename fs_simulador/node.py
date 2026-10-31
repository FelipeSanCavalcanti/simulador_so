class Node:
    def __init__(self, name, is_dir=False, size_bytes=0):
        self.name = name
        self.is_dir = is_dir
        self.size = size_bytes
        self.children = {}  # Guarda os filhos se for diretório
        self.blocks = []    # Guarda os IDs dos blocos físicos que este arquivo ocupa no disco