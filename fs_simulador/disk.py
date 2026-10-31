import math

class VirtualDisk:
    def __init__(self, block_size=4096, total_blocks=16):
        self.block_size = block_size
        self.total_blocks = total_blocks
        self.blocks = [None] * self.total_blocks

    def allocate_indexed(self, file_name, size_bytes):
        """
        Recebe o tamanho do arquivo, acha blocos vazios, marca como ocupados
        e retorna a lista de blocos alocados.
        """
        blocks_needed = math.ceil(size_bytes / self.block_size)
        allocated = []
        
        # TODO: Implementar a lógica de varrer self.blocks, achar espaços 'None'
        # e preenchê-los com o file_name. Lançar erro se não houver espaço.
        
        return allocated

    def calc_fragmentation(self, file_node):
        """
        Calcula a fragmentação interna baseada nos blocos do node.
        """
        # TODO: Retornar a sobra de espaço do último bloco
        pass