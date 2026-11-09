# fs_simulador/raid.py
from fs_simulador.disk import Disk

class RAID5Controller:
    """
    Simula um arranjo RAID 5 distribuindo blocos de dados e calculando
    a paridade via XOR para tolerância a falhas.
    """
    
    def __init__(self, num_disks=3, block_size=4096, total_blocks=16):
        if num_disks < 3:
            raise ValueError("RAID 5 requer no mínimo 3 discos.")
            
        self.num_disks = num_disks
        self.block_size = block_size
        
        # Cria fisicamente múltiplos discos para o arranjo
        self.physical_disks = {
            i: Disk(block_size=block_size, total_blocks=total_blocks) 
            for i in range(1, num_disks + 1)
        }

    def write_stripe(self, file_path, data_blocks):
        """
        Simula a distribuição de blocos (Striping) e a gravação da Paridade.
        Para simplificar o simulador, consideramos que um 'stripe' preenche 
        Discos 1 e 2 com dados e o Disco 3 com a Paridade XOR.
        """
        print(f"\nArranjo Ativo: RAID 5 ({self.num_disks} Discos Físicos, Blocos de {self.block_size//1024} KB)")
        print("\n[E/S - DISTRIBUIÇÃO EM DISCO (RAID 5)]")

        # Exemplo didático pegando até os 2 primeiros blocos do arquivo
        block1 = f"Dados de {file_path} - Part 1" if len(data_blocks) > 0 else "Vazio"
        block2 = f"Dados de {file_path} - Part 2" if len(data_blocks) > 1 else "Vazio"
        
        # Gravando fisicamente
        self.physical_disks[1].blocks[1] = {"type": "DATA", "content": block1}
        print(f"Disco 1: [Bloco 01: {block1} ({self.block_size} bytes)]")
        
        self.physical_disks[2].blocks[2] = {"type": "DATA", "content": block2}
        print(f"Disco 2: [Bloco 02: {block2} ({self.block_size} bytes)]")
        
        # O Disco 3 guarda a paridade (Simulada em string)
        parity = f"XOR(Disco 1, Disco 2)"
        self.physical_disks[3].blocks[1] = {"type": "PARITY", "content": parity}
        print(f"Disco 3: [PARIDADE : {parity}]")

    def simulate_failure(self, target_disk_id):
        """
        Derruba um disco e aciona a recuperação matemática via Paridade.
        """
        if target_disk_id not in self.physical_disks:
            raise ValueError("ID de disco inválido para falha.")

        print("\n[TESTE DE FALHA SIMULADO]")
        print(f"- Falha forçada no Disco {target_disk_id}!")
        print("- Tentando ler dados...")
        print(f"- ERRO DE E/S: Disco {target_disk_id} inacessível.")
        
        # "Formata" / Destrói os dados do disco alvo
        broken_disk = self.physical_disks[target_disk_id]
        broken_disk.blocks = [{"type": "FREE", "content": None} for _ in range(broken_disk.total_blocks)]
        
        print("\n[RECUPERAÇÃO DE DADOS (RAID 5)]")
        # Simulação de recuperação matemática do Disco 2 usando Disco 1 e Disco 3
        if target_disk_id == 2:
            print("- Calculando: (Disco 1 XOR Disco 3 (Paridade))")
            recovered_data = "Dados Reconstruídos [OK]"
            broken_disk.blocks[2] = {"type": "DATA", "content": recovered_data}
            print(f"- Reconstrução do Bloco 02 do Disco 2 concluída com sucesso.")
        elif target_disk_id == 1:
            print("- Calculando: (Disco 2 XOR Disco 3 (Paridade))")
            print(f"- Reconstrução do Disco 1 concluída com sucesso.")
        else:
            print("- Disco de Paridade perdido. Os dados estão seguros nos Discos 1 e 2.")
            print("- Recalculando e gravando nova paridade no novo Disco 3.")