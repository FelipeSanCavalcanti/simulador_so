import math


class Disk:
    """Simula o disco usando alocação indexada (i-node)."""

    def __init__(self, block_size=4096, total_blocks=16):
        self.block_size = block_size
        self.total_blocks = total_blocks
        self.blocks = [None] * total_blocks

    def allocate(self, amount, node, block_type):
        """Reserva a quantidade solicitada de blocos livres."""
        free_blocks = [
            index for index, block in enumerate(self.blocks)
            if block is None
        ]

        if len(free_blocks) < amount:
            raise OSError("Espaço insuficiente no disco.")

        selected = free_blocks[:amount]

        for index in selected:
            self.blocks[index] = {
                "node": node,
                "type": block_type
            }

        return selected

    def release(self, indexes):
        """Libera os blocos informados."""
        for index in indexes:
            if 0 <= index < self.total_blocks:
                self.blocks[index] = None

    def free_count(self):
        return sum(block is None for block in self.blocks)

    def used_count(self):
        return self.total_blocks - self.free_count()

    def data_blocks_needed(self, size):
        return math.ceil(size / self.block_size)

    def show_map(self, get_path):
        """Exibe a identificação de cada bloco físico."""
        print("\n[MAPA DE ALOCAÇÃO DO DISCO - INDEXADO]")

        for index, block in enumerate(self.blocks):
            if block is None:
                print(f"Bloco {index:02d}: [LIVRE]")
                continue

            node = block["node"]
            path = get_path(node)

            if block["type"] == "INODE":
                label = "INODE_RAIZ" if node.parent is None else "INODE"
                print(f"Bloco {index:02d}: [{label}] {path}")

            elif block["type"] == "DATA":
                position = node.data_blocks.index(index) + 1
                occupied = min(
                    self.block_size,
                    node.size - ((position - 1) * self.block_size)
                )
                print(
                    f"Bloco {index:02d}: [DADO] {path} "
                    f"(Bloco {position} - {occupied} bytes ocupados)"
                )
