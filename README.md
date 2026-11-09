# Simulador de Sistema Operacional

Este projeto é um simulador de um Sistema Operacional, desenvolvido para a disciplina de **Sistemas Operacionais** para o curso de **Licenciatura em Computação** da **UFRPE**. O objetivo é simular o funcionamento lógico de diretórios em árvore, além da camada física de alocação de blocos em um disco rígido virtual e operações de hardware.

## Equipe
<<<<<<< Updated upstream
* Felipe Santana Cavalcanti 
* Maria Eduarda Menezes de Oliveira 
* Andresa Americo Rodrigues de Araujo
  
## Funcionalidades Implementadas (Etapa 1)
=======
* Andresa Americo Rodrigues de Araujo
* Maria Eduarda Menezes de Oliveira
* Felipe Santana Cavalcanti

## Funcionalidades Implementadas

### Etapa 1: Sistema de Arquivos e Alocação
* **Hierarquia em Árvore:** Estrutura navegável de diretórios e arquivos com suporte a caminhos absolutos e relativos.
* **Operações CRUD:** Criação, leitura, atualização e deleção de arquivos e diretórios via comandos de terminal.
* **Alocação Física de Blocos:** Simulação de um disco dividido em blocos de tamanho fixo.
  * Estratégias implementadas: Alocação Indexada (i-node).
* **Diagnóstico do Disco:**
  * Exibição do mapa do disco (ocupação exata e blocos livres).
  * Relatório completo contendo o cálculo automático de Fragmentação Interna e Externa.
  * Análise de necessidade de compactação.

### Etapa 2: Escalonamento de E/S e Redundância (RAID)
* **Integração E/S:** Operações lógicas do sistema de arquivos acionam chamadas mecânicas de disco.
* **Escalonamento do Braço do Disco:** 
  * Fila de requisições de blocos físicos simulada.
  * Algoritmos de escalonamento disponíveis e intercambiáveis via CLI: **FCFS, SSTF, SCAN e C-SCAN**.
  * Cálculo detalhado do deslocamento total da cabeça de leitura.
* **Arranjo RAID 5:** 
  * Abstração de armazenamento utilizando 3 discos físicos simultâneos.
  * Fracionamento e gravação de blocos de dados (Striping).
  * Cálculo e gravação simultânea de Paridade via operação lógica XOR.
  * **Tolerância a Falhas:** Sistema de simulação de quebra de disco com recuperação matemática completa dos dados perdidos utilizando os discos restantes.

## Arquitetura do Projeto

    simulador_so/
    ├── README.md
    ├── main.py                 # Interface de linha de comando (CLI)
    └── fs_simulador/
        ├── __init__.py
        ├── disk.py             # Camada Física (Disco virtual)
        ├── filesystem.py       # Camada Lógica (Árvore de diretórios e CRUD)
        ├── io_scheduler.py     # Gerenciamento de E/S (SSTF, SCAN, C-SCAN)
        ├── node.py             # Estrutura de nós para arquivos e diretórios
        └── raid.py             # Controladora RAID 5 e tolerância a falhas

## Comandos Disponíveis (CLI)

Ao iniciar o `main.py`, o terminal interativo suporta os seguintes comandos principais:

* `help` - Lista todos os comandos
* `mkdir /caminho` - Cria diretório
* `create /caminho <tamanho>` - Cria arquivo (Gera chamadas no Escalonador de Disco e RAID)
* `read /caminho` - Lê informações do arquivo
* `update /caminho <tamanho>` - Atualiza o tamanho do arquivo
* `rm /caminho` - Exclui arquivo
* `rmdir /caminho` - Exclui diretório
* `ls [caminho]` - Lista conteúdo do diretório
* `cd /caminho` - Navega na árvore
* `pwd` - Exibe caminho atual
* `tree` - Exibe árvore completa graficamente
* `fs_status` - Exibe diagnóstico e relatório de fragmentação do disco
* `io
>>>>>>> Stashed changes
