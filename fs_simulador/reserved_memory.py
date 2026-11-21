class ReservedMemory:
    """
    Gerencia a Área Estática/Reservada da RAM física (Alocação Contígua).
    Unidade interna: KB (4 MB = 4096 KB).
    """

    def __init__(self, total_kb=4096):
        self.total_kb = total_kb
        # Lista de blocos: {'start': int, 'size': int, 'process': str | None}
        self.blocks = [
            {"start": 0, "size": 1024, "process": "Núcleo Base do SO"},
            {"start": 1024, "size": total_kb - 1024, "process": None},
        ]

    @staticmethod
    def _kb_to_mb(kb):
        return f"{kb / 1024:.1f} MB"

    def allocate(self, process_name, size_kb):
        """Alocação contígua (First-Fit) na área reservada."""
        if size_kb <= 0:
            raise ValueError("O tamanho do processo deve ser maior que zero.")

        for block in self.blocks:
            if block["process"] == process_name:
                raise ValueError(f"Processo '{process_name}' já está alocado na Área Reservada.")

        for index, block in enumerate(self.blocks):
            if block["process"] is None and block["size"] >= size_kb:
                start = block["start"]
                remaining = block["size"] - size_kb

                allocated_block = {
                    "start": start,
                    "size": size_kb,
                    "process": process_name,
                }

                if remaining > 0:
                    free_block = {
                        "start": start + size_kb,
                        "size": remaining,
                        "process": None,
                    }
                    self.blocks[index : index + 1] = [allocated_block, free_block]
                else:
                    self.blocks[index] = allocated_block

                end = start + size_kb
                print(
                    f"- Alocado de forma contígua na Área Reservada: "
                    f"[{self._kb_to_mb(start)} até {self._kb_to_mb(end)}] ({size_kb} KB)"
                )
                return allocated_block

        free_total, max_block, free_count = self.get_fragmentation_metrics()
        if free_total >= size_kb:
            raise MemoryError(
                f"Falha por Fragmentação Externa: há {free_total} KB livres em {free_count} "
                f"fragmentos, mas o maior bloco contíguo é {max_block} KB. Execute 'memory_compact --reserved'."
            )
        raise MemoryError(f"Memória Reservada insuficiente (livre: {free_total} KB, solicitado: {size_kb} KB).")

    def deallocate(self, process_name):
        """Libera o bloco ocupado pelo processo e faz coalescência de lacunas vizinhas."""
        found = False
        for block in self.blocks:
            if block["process"] == process_name:
                start = block["start"]
                size = block["size"]
                end = start + size
                block["process"] = None
                found = True

                print(f"\n[ENCERRAMENTO DE PROCESSO CRÍTICO] Processo '{process_name}' finalizado.")
                print(
                    f"Área de {size} KB no intervalo [{self._kb_to_mb(start)} a {self._kb_to_mb(end)}] "
                    f"liberada na Área Reservada da RAM."
                )
                break

        if not found:
            raise ValueError(f"Processo crítico '{process_name}' não encontrado na Área Reservada.")

        self._merge_adjacent_free_blocks()

    def _merge_adjacent_free_blocks(self):
        merged = []
        for block in self.blocks:
            if merged and merged[-1]["process"] is None and block["process"] is None:
                merged[-1]["size"] += block["size"]
            else:
                merged.append(dict(block))
        self.blocks = merged

    def get_fragmentation_metrics(self):
        free_blocks = [b["size"] for b in self.blocks if b["process"] is None]
        free_total = sum(free_blocks)
        max_block = max(free_blocks) if free_blocks else 0
        return free_total, max_block, len(free_blocks)

    def show_status(self):
        print(f"\n--- MAPA DA ÁREA CRÍTICA/RESERVADA DA RAM (Total: {self.total_kb // 1024} MB - Alocação Fixa) ---")
        free_idx = 1
        for block in self.blocks:
            start_str = self._kb_to_mb(block["start"])
            end_str = self._kb_to_mb(block["start"] + block["size"])
            if block["process"] is not None:
                print(f"[{start_str} - {end_str}] : {block['process']:<20} ({block['size']} KB) [OCUPADO]")
            else:
                print(f"[{start_str} - {end_str}] : FRAGMENTO LIVRE {free_idx:<4} ({block['size']} KB) [LIVRE - LACUNA]")
                free_idx += 1

        free_total, max_block, free_count = self.get_fragmentation_metrics()
        has_ext_frag = free_count > 1

        print("\n--- DIAGNÓSTICO DE FRAGMENTAÇÃO EXTERNA ---")
        print(f"Total de Memória Livre na Área Reservada : {free_total} KB ({self._kb_to_mb(free_total)})")
        print(f"Maior Bloco Contíguo Disponível          : {max_block} KB ({self._kb_to_mb(max_block)})")
        if has_ext_frag:
            print(f"Fragmentação Externa Detectada           : SIM ({free_count} fragmentos não contíguos)")
            if free_total > max_block:
                exemplo_req = max_block + 512
                print(f"Status: Uma requisição contígua de {exemplo_req} KB falhará por ausência de bloco único.")
        else:
            print("Fragmentação Externa Detectada           : NÃO (Espaço livre unificado)")

    def compact(self):
        """Compacta todos os processos críticos para o início da RAM, eliminando lacunas."""
        print("\n[EXECUTANDO COMPACTAÇÃO DA ÁREA RESERVADA DA RAM]")
        print("Realocando blocos contíguos para eliminar a fragmentação externa...")

        new_blocks = []
        cursor = 0
        moved = False

        for block in self.blocks:
            if block["process"] is not None:
                old_start = block["start"]
                old_end = old_start + block["size"]
                new_start = cursor
                new_end = cursor + block["size"]

                if old_start != new_start:
                    moved = True
                    print(
                        f"- Mapeamento de '{block['process']}': "
                        f"[{self._kb_to_mb(old_start)} a {self._kb_to_mb(old_end)}] -> "
                        f"Ajustado para: [{self._kb_to_mb(new_start)} a {self._kb_to_mb(new_end)}]"
                    )

                new_blocks.append({
                    "start": new_start,
                    "size": block["size"],
                    "process": block["process"],
                })
                cursor = new_end

        if not moved:
            print("- Nenhuma realocação necessária (memória já está compactada).")

        free_remaining = self.total_kb - cursor
        if free_remaining > 0:
            new_blocks.append({
                "start": cursor,
                "size": free_remaining,
                "process": None,
            })

        self.blocks = new_blocks

        print("\n--- MAPA APÓS COMPACTAÇÃO ---")
        for block in self.blocks:
            start_str = self._kb_to_mb(block["start"])
            end_str = self._kb_to_mb(block["start"] + block["size"])
            if block["process"] is not None:
                print(f"[{start_str} - {end_str}] : {block['process']:<20} ({block['size']} KB) [OCUPADO]")
            else:
                print(f"[{start_str} - {end_str}] : Bloco Livre Contíguo ({block['size']} KB) [LIVRE]")

        print(f"Resultado: Fragmentação externa eliminada. Maior bloco contíguo: {free_remaining} KB.")