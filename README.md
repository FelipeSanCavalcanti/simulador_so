# Simulador de Sistema Operacional

Este projeto é um simulador de um Sistema Operacional, desenvolvido para a disciplina de **Sistemas Operacionais** para o curso de **Licenciatura em Computação** da **UFRPE**. O objetivo é simular o funcionamento lógico de diretórios em árvore, a camada física de alocação de blocos em um disco rígido virtual, operações de hardware, a camada de segurança e o gerenciamento de memória do sistema.

## Equipe
- Andresa Americo Rodrigues de Araujo
- Maria Eduarda Menezes de Oliveira
- Felipe Santana Cavalcanti

## Funcionalidades Implementadas

### Etapa 1: Sistema de Arquivos e Alocação
- **Hierarquia em Árvore:** Estrutura navegável de diretórios e arquivos com suporte a caminhos absolutos e relativos.
- **Operações CRUD:** Criação, leitura, atualização e deleção de arquivos e diretórios via comandos de terminal.
- **Alocação Física de Blocos:** Simulação de um disco dividido em blocos de tamanho fixo.
  - Estratégias implementadas: Alocação Indexada (i-node).
- **Diagnóstico do Disco:**
  - Exibição do mapa do disco (ocupação exata e blocos livres).
  - Relatório completo contendo o cálculo automático de Fragmentação Interna e Externa.
  - Análise de necessidade de compactação.

### Etapa 2: Escalonamento de E/S e Redundância (RAID)
- **Integração E/S:** Operações lógicas do sistema de arquivos acionam chamadas mecânicas de disco.
- **Escalonamento do Braço do Disco:**
  - Fila de requisições de blocos físicos simulada.
  - Algoritmos de escalonamento disponíveis e intercambiáveis via CLI: **FCFS, SSTF, SCAN e C-SCAN**.
  - Cálculo detalhado do deslocamento total da cabeça de leitura.
- **Arranjo RAID 5:**
  - Abstração de armazenamento utilizando 3 discos físicos simultâneos.
  - Fracionamento e gravação de blocos de dados (Striping).
  - Cálculo e gravação simultânea de Paridade via operação lógica XOR.
  - **Tolerância a Falhas:** Sistema de simulação de quebra de disco com recuperação matemática completa dos dados perdidos utilizando os discos restantes.

### Etapa 3: Segurança, Identidade e Proteção de Dados
- **Privilégios e Modos de Execução:** toda sessão opera em `MODO_USUARIO` ou `MODO_KERNEL`
  (superusuário/root). Operações críticas (cadastro de usuários/grupos, `chown`,
  `chmod` em objetos de terceiros, troca de senha de outro usuário, escrita direta
  em bloco físico) exigem `MODO_KERNEL` e são negadas com laudo de privilégios.
  O root também possui bypass de ACL, como em um SO real.
- **Identidade e Autenticação:** cadastro de múltiplos usuários e grupos, com
  senhas armazenadas como `SHA-256(salt + senha)`. O salt é aleatório por usuário
  e a comparação usa `hmac.compare_digest`; nenhuma senha em texto claro é mantida.
- **Controle de Acesso (ACL):** cada nó da árvore possui proprietário, grupo e
  permissões `rwx` para Proprietário, Grupo e Outros (ex.: `rwxr-x---` / `750`).
  Toda operação passa por verificação que imprime o laudo:
- `r` controla leitura (`read`, `cat`, `decrypt_file`, `ls` de diretório);
- `w` controla escrita, criação e remoção de itens;
- `x` controla entrada/percurso de diretórios (`cd` e travessia de caminho).
  Acesso negado é registrado no log de auditoria em memória (`security_log`).
- **Criptografia em Repouso:** `encrypt_file` criptografa o conteúdo **antes** de
  gravá-lo no bloco físico (cifra de fluxo didática derivada de
  `SHA-256(chave + salt + índice do bloco)`, XOR, ciphertext em hexadecimal).
  O disco nunca guarda a chave; `decrypt_file` valida a chave comparando o
  SHA-256 do texto claro com o registro do i-node.
- **Integridade e Anti-Vírus Simulado:** `antivirus_scan` percorre os arquivos,
  recomputa o SHA-256 de cada bloco e compara com o registro oficial mantido pela
  camada de segurança, além de procurar assinaturas maliciosas no texto claro.
  `tamper_block` (MODO_KERNEL) simula uma gravação direta no disco, fora das
  rotinas do SO, e a varredura seguinte aponta o bloco divergente.

### Etapa 4: Gerenciamento de Memória Híbrida
- **Modelo de Alocação Híbrida:** divisão da RAM física em duas áreas distintas:
  - **Região Estática/Fixa (Reservada):** espaço contíguo de 4 MB exclusivo para o
    Núcleo Base do SO e processos críticos (alocação First-Fit sem paginação).
    Alocação, encerramento de processos críticos e compactação exigem `MODO_KERNEL`.
  - **Região Dinâmica (Memória Virtual):** gerenciada por paginação sob demanda
    (*Demand Paging*, páginas de 4 KB) para processos comuns de usuários.
- **Tradução de Endereços:** conversão explícita entre Página Lógica requisitada
  pelo processo e Moldura Física correspondente na RAM (`translate_address`),
  sinalizando ocorrências de `[HIT]` e `[MISS]`.
- **Page Faults, Swapping e Substituição de Páginas:** ao referenciar uma página
  ausente na RAM (`execute_step`), o sistema identifica o *Page Fault*, integra-se
  ao disco e ao escalonador de E/S das Etapas 1 e 2 (`perform_io`) para executar
  operações de `SWAP_OUT` e `SWAP_IN`, e aplica políticas de substituição
  intercambiáveis: **LRU** (*Least Recently Used*) e **Segunda Chance** (*Clock*).
- **Diagnóstico de Fragmentação e Compactação:** relatórios periódicos de
  **Fragmentação Interna** (espaço desperdiçado na última página de processos
  paginados) e **Fragmentação Externa** (lacunas livres não contíguas na Área
  Reservada), além de rotina de compactação (`memory_compact --reserved`) que
  realoca processos críticos para eliminar a fragmentação externa.

## Arquitetura do Projeto

    simulador_so/
    ├── README.md
    ├── main.py                 # Interface de linha de comando (CLI)
    └── fs_simulador/
        ├── __init__.py
        ├── ambiente.py         # Boot: usuários/grupos e árvore de demonstração
        ├── antivirus.py        # Varredura de integridade e assinaturas
        ├── crypto.py           # Criptografia simulada de dados em repouso
        ├── disk.py             # Camada Física (Disco virtual, conteúdo + checksum)
        ├── filesystem.py       # Camada Lógica (árvore, CRUD, ACL, cripto)
        ├── io_scheduler.py     # Gerenciamento de E/S (FCFS, SSTF, SCAN, C-SCAN)
        ├── memory_manager.py   # Controlador híbrido de memória e integração com Swap
        ├── node.py             # Nós com dono, grupo, modo e metadados de cripto
        ├── raid.py             # Controladora RAID 5 e tolerância a falhas
        ├── reserved_memory.py  # Área reservada contígua, frag. externa e compactação
        ├── security.py         # Usuários, grupos, senhas, privilégios, ACL, logs
        └── virtual_memory.py   # Paginação sob demanda, tradução, LRU e Segunda Chance

## Contas de demonstração

O boot cria contas e uma árvore inicial equivalente aos exemplos da Etapa 3:

| Usuário | Senha      | Grupo      | Perfil                          |
|---------|------------|------------|---------------------------------|
| root    | `root123`  | admin      | Administrador (MODO_KERNEL)     |
| carlos  | `carlos123`| devs       | Usuário comum (MODO_USUARIO)    |
| ana     | `ana123`   | financeiro | Usuário comum (MODO_USUARIO)    |

Árvore inicial: `/sistema/config.sys` (750 root:admin), `/sistema/logs/app.log`
(640 root:admin), `/home/carlos` (700 carlos:devs), `/home/ana` (700 ana:financeiro),
com `segredo.txt` e `notas.txt` em `/home/carlos`.

## Comandos Disponíveis (CLI)

### Etapas 1 e 2
- `mkdir /caminho` - Cria diretório
- `create /caminho <tamanho> [--content "texto"]` - Cria arquivo (gera chamadas no Escalonador de Disco e RAID)
- `write_file /caminho "texto"` - Grava conteúdo em texto claro (cria o arquivo se não existir)
- `read /caminho` - Lê metadados, ACL e conteúdo do arquivo
- `cat /caminho` - Exibe apenas o conteúdo
- `update /caminho <tamanho>` - Atualiza o tamanho (re-alocação)
- `rm /caminho` - Exclui arquivo
- `rmdir /caminho` - Exclui diretório vazio
- `ls [-l] [caminho]` - Lista conteúdo (`-l` mostra `rwx`, dono, grupo e criptografia)
- `cd /caminho` - Navega na árvore
- `pwd` - Exibe caminho atual
- `tree` - Exibe árvore completa graficamente
- `fs_status` - Diagnóstico do disco, fragmentação e resumo de segurança
- `io_algorithm <FCFS|SSTF|SCAN|C-SCAN>` - Seleciona o algoritmo de E/S
- `fail_disk <1|2|3>` - Simula falha física e recuperação RAID 5

### Etapa 3
- `login --user <nome>` - Autentica (a senha é pedida sem eco)
- `logout` - Encerra a sessão
- `whoami` / `id` / `users` - Identidade da sessão e cadastros
- `useradd <nome> --group <grupo> [--admin]` - **[MODO_KERNEL]** Cadastra usuário
- `groupadd <nome>` - **[MODO_KERNEL]** Cadastra grupo
- `passwd [--user <nome>]` - Troca a própria senha (de terceiros exige MODO_KERNEL)
- `su --user root` - Eleva para MODO_KERNEL mediante senha do root
- `kernel_mode off` - Retorna ao MODO_USUARIO
- `chmod <750|rwxr-x---> <caminho>` - Altera permissões (dono ou MODO_KERNEL)
- `chown <usuario>[:<grupo>] <caminho>` - **[MODO_KERNEL]** Altera proprietário
- `encrypt_file <caminho> --key "chave"` - Criptografa o conteúdo nos blocos físicos
- `decrypt_file <caminho> --key "chave"` - Descriptografa e exibe, validando o SHA-256
- `antivirus_scan [caminho]` - Varredura de integridade e assinaturas maliciosas
- `tamper_block <indice> --content "texto"` - **[MODO_KERNEL]** Adultera um bloco (demonstração)
- `security_log` - Registro de auditoria da sessão

### Etapa 4
- `create_process --name <nome> --size <tam> --type <critical|normal>` - Aloca processo na Área Reservada (`critical`, exige MODO_KERNEL) ou Memória Virtual (`normal`)
- `terminate_process --name <nome>` - Encerra o processo e libera sua região/molduras de memória (`critical` exige MODO_KERNEL)
- `memory_status [--reserved|--virtual]` - Exibe mapa da RAM, molduras físicas, diagnóstico de fragmentação e contadores de Page Faults
- `memory_compact --reserved` - **[MODO_KERNEL]** Compacta blocos contíguos na Área Reservada da RAM
- `translate_address --process <nome> --page <n>` - Traduz Página Lógica em Moldura Física (`[HIT]` ou `[MISS]`)
- `execute_step --process <nome> --instruction "LOAD_DATA Página <n>"` - Simula instrução de acesso à memória, tratando Page Faults e Swapping
- `page_algorithm <LRU|SECOND_CHANCE>` - Seleciona o algoritmo de substituição de páginas

### Geral
- `help` - Ajuda
- `exit` - Encerra o simulador

## Exemplos de uso

### Autenticação e verificação de ACL (Exemplo 3.1)

    > login --user carlos
    Senha: **********
    Autenticado com sucesso. Usuário: 'carlos' | Grupo: 'devs' | Modo: MODO_USUARIO

    > read /sistema/config.sys
    [SISTEMA DE SEGURANÇA - VERIFICAÇÃO DE ACL]
    Objeto      : /sistema/config.sys
    Proprietário: root (Grupo: admin)
    Permissões  : rwxr-x--- (750)
    Ação Pedida : LEITURA por 'carlos' (Grupo: devs)

    [NEGADO]: O usuário 'carlos' não possui permissão de leitura no objeto '/sistema/config.sys'.
    Tentativa não autorizada registrada nos logs do sistema.

### Criptografia de conteúdo e anti-vírus (Exemplo 3.2)

    > encrypt_file /home/carlos/segredo.txt --key "MinhaChave123"
    Arquivo '/home/carlos/segredo.txt' criptografado com sucesso.
    Conteúdo gravado nos blocos físicos: "0x2E006CCA995CFFADD2260BEC..." (Encrypted Ciphertext)

    > antivirus_scan /
    [MÓDULO DE SEGURANÇA - VARREDURA DE INTEGRIDADE]
    Analisando 4 arquivos em busca de assinaturas maliciosas e hashes corrompidos...
    - /sistema/logs/app.log           : [ALERTA] Hash do bloco 09 difere do registro oficial!
      Resultado: Possível modificação direta não autorizada no bloco do disco.
    - /home/carlos/segredo.txt        : [OK - Criptografado e Íntegro]

Para reproduzir o alerta de integridade acima: entre em MODO_KERNEL
(`su --user root`) e execute `tamper_block 9 --content "invasao"` (ou o índice de
um bloco de dados mostrado por `fs_status`); depois rode `antivirus_scan /`.

### Área Reservada, Fragmentação Externa e Compactação (Exemplo 4.1)

    > su --user root
    > create_process --name "Kernel_DiskDriver" --size 512KB --type critical
    - Alocado de forma contígua na Área Reservada: [1.0 MB até 1.5 MB] (512 KB)

    > create_process --name "Kernel_NetDriver" --size 1024KB --type critical
    - Alocado de forma contígua na Área Reservada: [1.5 MB até 2.5 MB] (1024 KB)

    > create_process --name "Kernel_CryptoEngine" --size 512KB --type critical
    - Alocado de forma contígua na Área Reservada: [2.5 MB até 3.0 MB] (512 KB)

    > terminate_process --name "Kernel_NetDriver"
    [ENCERRAMENTO DE PROCESSO CRÍTICO] Processo 'Kernel_NetDriver' finalizado.
    Área de 1024 KB no intervalo [1.5 MB a 2.5 MB] liberada na Área Reservada da RAM.

    > memory_status --reserved
    --- MAPA DA ÁREA CRÍTICA/RESERVADA DA RAM (Total: 4 MB - Alocação Fixa) ---
    [0.0 MB - 1.0 MB] : Núcleo Base do SO    (1024 KB) [OCUPADO]
    [1.0 MB - 1.5 MB] : Kernel_DiskDriver    (512 KB)  [OCUPADO]
    [1.5 MB - 2.5 MB] : FRAGMENTO LIVRE 1    (1024 KB) [LIVRE - LACUNA]
    [2.5 MB - 3.0 MB] : Kernel_CryptoEngine  (512 KB)  [OCUPADO]
    [3.0 MB - 4.0 MB] : FRAGMENTO LIVRE 2    (1024 KB) [LIVRE - LACUNA]

    --- DIAGNÓSTICO DE FRAGMENTAÇÃO EXTERNA ---
    Total de Memória Livre na Área Reservada : 2048 KB (2.0 MB)
    Maior Bloco Contíguo Disponível          : 1024 KB (1.0 MB)
    Fragmentação Externa Detectada           : SIM (2 fragmentos não contíguos)
    Status: Uma requisição contígua de 1536 KB falhará por ausência de bloco único.

    > memory_compact --reserved
    [EXECUTANDO COMPACTAÇÃO DA ÁREA RESERVADA DA RAM]
    Realocando blocos contíguos para eliminar a fragmentação externa...
    - Mapeamento de 'Kernel_CryptoEngine': [2.5 MB a 3.0 MB] -> Ajustado para: [1.5 MB a 2.0 MB]

    --- MAPA APÓS COMPACTAÇÃO ---
    [0.0 MB - 1.0 MB] : Núcleo Base do SO    (1024 KB) [OCUPADO]
    [1.0 MB - 1.5 MB] : Kernel_DiskDriver    (512 KB)  [OCUPADO]
    [1.5 MB - 2.0 MB] : Kernel_CryptoEngine  (512 KB)  [OCUPADO]
    [2.0 MB - 4.0 MB] : Bloco Livre Contíguo (2048 KB) [LIVRE]
    Resultado: Fragmentação externa eliminada. Maior bloco contíguo: 2048 KB.

### Memória Virtual, Fragmentação Interna e Substituição LRU (Exemplo 4.2)

    > create_process --name "App_Navegador" --size 10KB --type normal
    [CRIAÇÃO DE PROCESSO NÃO CRÍTICO - MEMÓRIA VIRTUAL]
    Tamanho do Processo : 10 KB (10240 Bytes)
    Tamanho da Página   : 4 KB (4096 Bytes)
    Cálculo de Páginas  : 2.5 -> Requer 3 Páginas Lógicas (Páginas 0, 1, 2).

    --- ANÁLISE DE FRAGMENTAÇÃO INTERNA ---
    Página Lógica 0 : 4096 Bytes ocupados (100%)
    Página Lógica 1 : 4096 Bytes ocupados (100%)
    Página Lógica 2 : 2048 Bytes ocupados (50%)
    Fragmentação Interna Total: 2048 Bytes de desperdício na Página Lógica 2.
    Status: Tabela de Páginas gerada sem alocar molduras na RAM (Alocação por demanda).

    > execute_step --process App_Navegador --instruction "LOAD_DATA Página 1"
    > translate_address --process App_Navegador --page 1
    [TRADUÇÃO DE ENDEREÇO: PÁGINA LÓGICA -> MOLDURA FÍSICA]
    Solicitação: Página Lógica 1 -> Mapeada na Moldura Física 88 (RAM Dinâmica) [HIT]

    > execute_step --process App_Navegador --instruction "LOAD_DATA Página 2"
    [CPU - REFERÊNCIA DE MEMÓRIA EM EXECUÇÃO]
    App_Navegador requisita acesso à Página Lógica 2 (LOAD_DATA Página 2)...
    - Consulta Tabela de Páginas -> Página Lógica 2 NÃO ESTÁ NA RAM!

    [PAGE FAULT DETECTADO]: Página Lógica 2 ausente na RAM!
    Memória RAM cheia. Executando Substituição de Página (Algoritmo LRU):
    - Analisando histórico de acesso: Página Lógica 0 do PID 102 (PID_102_SystemDaemon) não é usada há 45ms (Mais antiga).
    - Removendo Página Lógica 0 do PID 102 da RAM -> Salvando no Swap (Disco).
    - Carregando Página Lógica 2 do App_Navegador na Moldura Física 12 (RAM Dinâmica).
    - Tabela de Páginas atualizada: Página Lógica 2 ---> Moldura Física 12.

## Como executar

    python main.py

Requer apenas Python 3 (sem dependências externas). O `teste_escalonamento.py`
continua válido para exercitar os algoritmos de E/S isoladamente.