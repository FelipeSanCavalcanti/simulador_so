import re
from fs_simulador.reserved_memory import ReservedMemory
from fs_simulador.virtual_memory import VirtualMemory


class MemoryManager:
    """
    Controlador Híbrido de Memória (Etapa 4).
    Integra Área Reservada (Contígua), Memória Virtual (Paginada) e E/S de Swap com o Disco.
    """

    def __init__(self, filesystem=None):
        self.filesystem = filesystem
        self.reserved = ReservedMemory(total_kb=4096)
        self.virtual = VirtualMemory(page_size=4096, frame_pool=[12, 45, 73, 88])
        self.next_pid = 103
        self.process_registry = {}  # name -> {"pid": int, "type": "critical"|"normal"}

    def create_process(self, name, size_bytes, proc_type="normal"):
        proc_type = proc_type.lower()
        if name in self.process_registry:
            raise ValueError(f"Já existe um processo chamado '{name}'.")

        pid = self.next_pid
        if proc_type == "critical":
            size_kb = max(1, size_bytes // 1024)
            self.reserved.allocate(name, size_kb)
            self.process_registry[name] = {"pid": pid, "type": "critical"}
        elif proc_type == "normal":
            self.virtual.create_process(name, size_bytes, pid)
            self.process_registry[name] = {"pid": pid, "type": "normal"}
        else:
            raise ValueError("Tipo de processo inválido. Use 'critical' ou 'normal'.")

        self.next_pid += 1

    def terminate_process(self, name):
        if name not in self.process_registry:
            raise ValueError(f"Processo '{name}' não encontrado.")

        info = self.process_registry.pop(name)
        if info["type"] == "critical":
            self.reserved.deallocate(name)
        else:
            self.virtual.terminate_process(name)

    def _handle_swap_io(self, direction, process_name, page_num):
        """Integra operações de Swap com o Disco e Escalonador das Etapas 1 e 2."""
        if not self.filesystem:
            return
        total_blocks = self.filesystem.disk.total_blocks
        swap_block = (hash(f"{process_name}:{page_num}") % (total_blocks - 1)) + 1
        print(f"[SWAP -> DISCO] Acionando E/S ({direction}) no bloco físico {swap_block} da memória secundária...")
        self.filesystem.perform_io(direction, [swap_block])

    def translate_address(self, process_name, page_num):
        return self.virtual.translate_address(process_name, page_num)

    def execute_step(self, process_name, instruction):
        """Interpreta instruções como 'LOAD_DATA Página 2' e referencia a página na memória."""
        match = re.search(r"(\d+)", instruction)
        if not match:
            raise ValueError("Instrução deve informar o número da página (ex: 'LOAD_DATA Página 2').")

        page_num = int(match.group(1))
        return self.virtual.access_page(
            process_name,
            page_num,
            instruction=instruction,
            swap_callback=self._handle_swap_io,
        )

    def compact_reserved(self):
        self.reserved.compact()

    def show_status(self, mode="all"):
        if mode == "reserved":
            self.reserved.show_status()
        elif mode == "virtual":
            self.virtual.show_status()
        else:
            self.reserved.show_status()
            self.virtual.show_status()