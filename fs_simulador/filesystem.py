from .node import Node
from .disk import VirtualDisk

class FileSystem:
    def __init__(self):
        self.root = Node(name="/", is_dir=True)
        self.disk = VirtualDisk()

    def mkdir(self, path):
        """
        Cria um novo diretório na árvore.
        """
        # TODO: Separar o path por '/', encontrar o pai, e adicionar um Node(is_dir=True)
        pass

    def create_file(self, path, size_bytes):
        """
        Pede blocos ao disco e cria o arquivo na árvore.
        """
        # 1. TODO: Achar a pasta pai onde o arquivo vai ficar
        # 2. Chamar o disco: blocos = self.disk.allocate_indexed(nome, size_bytes)
        # 3. TODO: Criar o Node do arquivo e injetar a lista de blocos nele
        pass

    def show_tree(self):
        """
        Imprime a árvore de diretórios graficamente.
        """
        pass