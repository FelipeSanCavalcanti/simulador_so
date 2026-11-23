import math
import time


class VirtualMemory:
    """
    Gerencia a Área Dinâmica da RAM (Memória Virtual com Paginação sob Demanda).
    Suporta substituição de páginas via LRU e Segunda Chance.
    """

    def __init__(self, page_size=4096, total_frames=4, frame_pool=None):
        self.page_size = page_size
        # Molduras físicas disponíveis na RAM Dinâmica (ex.: [12, 45, 73, 88])
        self.frame_pool = frame_pool or [12, 45, 73, 88][:total_frames]
        self.frames = {frame_id: None for frame_id in self.frame_pool}
        self.processes = {}  # process_name -> dados do processo e tabela de páginas
        self.replacement_algorithm = "LRU"  # "LRU" ou "SECOND_CHANCE"
        self.access_counter = 0
        self.clock_pointer = 0
        self.swap_area = []  # Registro de páginas enviadas ao Swap (Disco)
        self.page_faults = 0
        self.page_hits = 0

        # Simula processo residente em segundo plano ocupando molduras iniciais
        self._init_background_resident()

    def _init_background_resident(self):
        """Pré-aloca molduras com processo de sistema para demonstrar substituição quando a RAM encher."""
        bg_name = "PID_102_SystemDaemon"
        num_bg_frames = max(0, len(self.frame_pool) - 1)
        if num_bg_frames == 0:
            return

        page_table = {}
        for p in range(num_bg_frames):
            frame_id = self.frame_pool[p]
            self.access_counter += 1
            entry = {
                "process": bg_name,
                "pid": 102,
                "page": p,
                "frame": frame_id,
                "present": True,
                "last_used": self.access_counter,
                "timestamp_ms": time.time() - 0.045,  # Simula página antiga (45ms)
                "ref_bit": 0,
                "used_bytes": self.page_size,
            }
            page_table[p] = entry
            self.frames[frame_id] = entry

        self.processes[bg_name] = {
            "pid": 102,
            "name": bg_name,
            "size_bytes": num_bg_frames * self.page_size,
            "num_pages": num_bg_frames,
            "internal_frag": 0,
            "page_table": page_table,
        }

    def set_algorithm(self, algorithm):
        algo = algorithm.upper().replace("-", "_")
        if algo not in ("LRU", "SECOND_CHANCE"):
            raise ValueError("Algoritmo de página inválido. Use 'LRU' ou 'SECOND_CHANCE'.")
        self.replacement_algorithm = algo
        print(f"Algoritmo de substituição de páginas alterado para {algo}.")

    def create_process(self, process_name, size_bytes, pid):
        if process_name in self.processes:
            raise ValueError(f"Processo '{process_name}' já existe na Memória Virtual.")
        if size_bytes <= 0:
            raise ValueError("O tamanho do processo deve ser maior que zero.")

        num_pages = math.ceil(size_bytes / self.page_size)
        page_table = {}
        internal_frag = 0

        print("\n[CRIAÇÃO DE PROCESSO NÃO CRÍTICO - MEMÓRIA VIRTUAL]")
        print(f"Tamanho do Processo : {size_bytes // 1024} KB ({size_bytes} Bytes)")
        print(f"Tamanho da Página   : {self.page_size // 1024} KB ({self.page_size} Bytes)")
        exact_pages = size_bytes / self.page_size
        pages_list = ", ".join(str(i) for i in range(num_pages))
        print(f"Cálculo de Páginas  : {exact_pages:g} -> Requer {num_pages} Páginas Lógicas (Páginas {pages_list}).")

        print("\n--- ANÁLISE DE FRAGMENTAÇÃO INTERNA ---")
        for page_num in range(num_pages):
            used = min(size_bytes - (page_num * self.page_size), self.page_size)
            waste = self.page_size - used
            internal_frag += waste
            pct = (used / self.page_size) * 100

            page_table[page_num] = {
                "process": process_name,
                "pid": pid,
                "page": page_num,
                "frame": None,
                "present": False,
                "last_used": 0,
                "timestamp_ms": 0.0,
                "ref_bit": 0,
                "used_bytes": used,
            }
            print(f"Página Lógica {page_num} : {used} Bytes ocupados ({pct:.0f}%)")

        if internal_frag > 0:
            print(
                f"Fragmentação Interna Total: {internal_frag} Bytes de desperdício "
                f"na Página Lógica {num_pages - 1}."
            )
        else:
            print("Fragmentação Interna Total: 0 Bytes (alinhamento exato com as páginas).")

        print("Status: Tabela de Páginas gerada sem alocar molduras na RAM (Alocação por demanda).")

        self.processes[process_name] = {
            "pid": pid,
            "name": process_name,
            "size_bytes": size_bytes,
            "num_pages": num_pages,
            "internal_frag": internal_frag,
            "page_table": page_table,
        }

    def terminate_process(self, process_name):
        if process_name not in self.processes:
            raise ValueError(f"Processo '{process_name}' não encontrado na Memória Virtual.")

        proc = self.processes.pop(process_name)
        freed_frames = []
        for entry in proc["page_table"].values():
            if entry["present"] and entry["frame"] is not None:
                self.frames[entry["frame"]] = None
                freed_frames.append(entry["frame"])

        self.swap_area = [s for s in self.swap_area if s["process"] != process_name]
        print(f"\n[ENCERRAMENTO DE PROCESSO] Processo '{process_name}' (PID {proc['pid']}) finalizado.")
        print(f"Molduras físicas liberadas na RAM Dinâmica: {freed_frames if freed_frames else 'Nenhuma'}.")

    def translate_address(self, process_name, page_num):
        if process_name not in self.processes:
            raise ValueError(f"Processo '{process_name}' não encontrado.")

        proc = self.processes[process_name]
        if page_num not in proc["page_table"]:
            raise ValueError(f"Página Lógica {page_num} inválida para '{process_name}'.")

        entry = proc["page_table"][page_num]
        print("\n[TRADUÇÃO DE ENDEREÇO: PÁGINA LÓGICA -> MOLDURA FÍSICA]")

        if entry["present"]:
            self.page_hits += 1
            self.access_counter += 1
            entry["last_used"] = self.access_counter
            entry["timestamp_ms"] = time.time()
            entry["ref_bit"] = 1
            print(
                f"Solicitação: Página Lógica {page_num} -> "
                f"Mapeada na Moldura Física {entry['frame']} (RAM Dinâmica) [HIT]"
            )
            return entry["frame"]

        print(
            f"Solicitação: Página Lógica {page_num} -> "
            f"NÃO MAPEADA na RAM (Ausente / Em Swap) [MISS]"
        )
        return None

    def access_page(self, process_name, page_num, instruction="LOAD_DATA", swap_callback=None):
        """Executa referência de memória, tratando Page Faults e Swapping."""
        if process_name not in self.processes:
            raise ValueError(f"Processo '{process_name}' não encontrado.")

        proc = self.processes[process_name]
        if page_num not in proc["page_table"]:
            raise ValueError(f"Página Lógica {page_num} fora dos limites do processo '{process_name}'.")

        entry = proc["page_table"][page_num]
        print("\n[CPU - REFERÊNCIA DE MEMÓRIA EM EXECUÇÃO]")
        print(f"{process_name} requisita acesso à Página Lógica {page_num} ({instruction})...")

        if entry["present"]:
            self.page_hits += 1
            self.access_counter += 1
            entry["last_used"] = self.access_counter
            entry["timestamp_ms"] = time.time()
            entry["ref_bit"] = 1
            print(f"- Consulta Tabela de Páginas -> HIT na Moldura Física {entry['frame']}!")
            return {"status": "HIT", "frame": entry["frame"]}

        # PAGE FAULT
        self.page_faults += 1
        print(f"- Consulta Tabela de Páginas -> Página Lógica {page_num} NÃO ESTÁ NA RAM!")
        print(f"\n[PAGE FAULT DETECTADO]: Página Lógica {page_num} ausente na RAM!")

        free_frames = [f_id for f_id, occupant in self.frames.items() if occupant is None]

        if free_frames:
            target_frame = free_frames[0]
            print(f"Moldura livre encontrada: Moldura Física {target_frame}.")
        else:
            target_frame = self._evict_page(swap_callback)

        # Carrega página solicitada do Swap/Disco para a RAM
        if swap_callback:
            swap_callback("SWAP_IN", process_name, page_num)

        self.swap_area = [
            s for s in self.swap_area
            if not (s["process"] == process_name and s["page"] == page_num)
        ]

        self.access_counter += 1
        entry["present"] = True
        entry["frame"] = target_frame
        entry["last_used"] = self.access_counter
        entry["timestamp_ms"] = time.time()
        entry["ref_bit"] = 1
        self.frames[target_frame] = entry

        print(
            f"- Carregando Página Lógica {page_num} do {process_name} "
            f"na Moldura Física {target_frame} (RAM Dinâmica)."
        )
        print(f"- Tabela de Páginas atualizada: Página Lógica {page_num} ---> Moldura Física {target_frame}.")
        return {"status": "PAGE_FAULT", "frame": target_frame}

    def _evict_page(self, swap_callback=None):
        """Executa LRU ou Segunda Chance para liberar uma moldura física."""
        print(f"Memória RAM cheia. Executando Substituição de Página (Algoritmo {self.replacement_algorithm}):")

        if self.replacement_algorithm == "LRU":
            victim_entry = min(
                (occ for occ in self.frames.values() if occ is not None),
                key=lambda e: e["last_used"],
            )
            elapsed_ms = max(1, int((time.time() - victim_entry["timestamp_ms"]) * 1000))
            print(
                f"- Analisando histórico de acesso: Página Lógica {victim_entry['page']} "
                f"do PID {victim_entry['pid']} ({victim_entry['process']}) não é usada há {elapsed_ms}ms (Mais antiga)."
            )
        else:
            # Algoritmo Segunda Chance (Relógio)
            victim_entry = None
            n = len(self.frame_pool)
            while victim_entry is None:
                frame_id = self.frame_pool[self.clock_pointer]
                candidate = self.frames[frame_id]
                if candidate["ref_bit"] == 0:
                    victim_entry = candidate
                else:
                    print(
                        f"- Segunda Chance: Moldura {frame_id} (Página {candidate['page']} de "
                        f"{candidate['process']}) teve bit R=1 -> zerado para R=0."
                    )
                    candidate["ref_bit"] = 0
                self.clock_pointer = (self.clock_pointer + 1) % n

            print(
                f"- Vítima selecionada (bit R=0): Página Lógica {victim_entry['page']} "
                f"do PID {victim_entry['pid']} ({victim_entry['process']})."
            )

        victim_frame = victim_entry["frame"]
        victim_entry["present"] = False
        victim_entry["frame"] = None
        self.frames[victim_frame] = None

        self.swap_area.append({
            "process": victim_entry["process"],
            "pid": victim_entry["pid"],
            "page": victim_entry["page"],
        })

        if swap_callback:
            swap_callback("SWAP_OUT", victim_entry["process"], victim_entry["page"])

        print(
            f"- Removendo Página Lógica {victim_entry['page']} do PID {victim_entry['pid']} "
            f"da RAM -> Salvando no Swap (Disco)."
        )
        return victim_frame

    def show_status(self):
        used_frames = sum(1 for v in self.frames.values() if v is not None)
        total_frames = len(self.frame_pool)
        total_internal_frag = sum(p["internal_frag"] for p in self.processes.values())

        print(f"\n--- MAPA DA ÁREA DINÂMICA / MEMÓRIA VIRTUAL (Paginação - {self.page_size // 1024} KB/página) ---")
        print(f"Algoritmo de Substituição: {self.replacement_algorithm}")
        print(f"Molduras na RAM Dinâmica : {used_frames}/{total_frames} ocupadas ({used_frames * 4} KB / {total_frames * 4} KB)")
        print(f"Page Hits: {self.page_hits} | Page Faults: {self.page_faults}")

        print("\n[MOLDURAS FÍSICAS DA RAM DINÂMICA]")
        for f_id, occ in self.frames.items():
            if occ:
                print(
                    f"Moldura {f_id:02d} : {occ['process']} (PID {occ['pid']}) - "
                    f"Página Lógica {occ['page']} [R={occ['ref_bit']}]"
                )
            else:
                print(f"Moldura {f_id:02d} : [LIVRE]")

        print("\n[PROCESSOS PAGINADOS E FRAGMENTAÇÃO INTERNA]")
        for proc in self.processes.values():
            mapped = [f"P{p}->M{e['frame']}" for p, e in proc["page_table"].items() if e["present"]]
            mapped_str = ", ".join(mapped) if mapped else "Nenhuma página na RAM (Demand Paging)"
            print(
                f"- {proc['name']} (PID {proc['pid']}): {proc['num_pages']} páginas | "
                f"Frag. Interna: {proc['internal_frag']} Bytes | Mapeamento: {mapped_str}"
            )

        print(f"\nFragmentação Interna Total (Memória Virtual): {total_internal_frag} Bytes")
        if self.swap_area:
            swap_str = ", ".join(f"{s['process']}:P{s['page']}" for s in self.swap_area)
            print(f"Páginas em Swap (Memória Secundária)        : {swap_str}")
        else:
            print("Páginas em Swap (Memória Secundária)        : Nenhuma")