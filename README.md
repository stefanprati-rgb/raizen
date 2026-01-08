# Extrator de Contratos Raízen

Sistema para extração automatizada de dados de contratos PDF e classificação por distribuidora.

## Funcionalidades

- **Extração de dados** de 6.309+ PDFs de contratos
- **Classificação automática** por distribuidora de energia
- Suporte a **2 modelos** de layout (Visual/Clicksign e Tabular/Docusign)
- Validação de CNPJ/CPF com dígitos verificadores
- Detecção de contratos "Guarda-Chuva" (múltiplas instalações)
- Geração de relatório HTML para revisão
- Exportação para CSV

## Estrutura do Projeto

```
Raizen/
├── pyproject.toml               # Configuração do projeto (PEP 517/518)
├── requirements.txt             # Dependências Python
├── README.md                    # Este arquivo
├── .gitignore                   # Arquivos ignorados pelo git
│
├── src/                         # Código fonte principal
│   └── extrator_contratos/
│       ├── __init__.py          # Exports do módulo
│       ├── main.py              # Script principal de execução
│       ├── extractor.py         # Lógica de extração
│       ├── patterns.py          # Padrões regex por modelo
│       ├── validators.py        # Validações (CNPJ, CPF, math)
│       ├── table_extractor.py   # Extração de tabelas
│       └── report.py            # Geração de relatório HTML
│
├── scripts/                     # Scripts utilitários
│   ├── super_organizer_v4.py    # Organizador por distribuidora (PRINCIPAL)
│   ├── organize_by_pages.py     # Organizador por número de páginas
│   ├── analyze_pdfs.py          # Análise de PDFs
│   ├── debug_pdf.py             # Debug de PDF específico
│   └── legacy/                  # Scripts antigos/descontinuados
│       ├── super_organizer_v3.py
│       └── organize_by_utility.py
│
├── tests/                       # Testes automatizados
│   ├── __init__.py
│   ├── test_extractor.py        # Testes do extrator
│   ├── test_corrections.py      # Testes de correções
│   ├── test_*.py                # Outros testes
│   └── debug/                   # Scripts de debug
│       ├── debug_brk.py
│       ├── debug_fresh4pet.py
│       └── debug_nyc.py
│
├── data/                        # Dados
│   ├── reference/               # Bases de dados de referência
│   │   ├── AreaatuadistbaseBI.xlsx
│   │   └── PAINEL DE DESEMPENHO DAS DISTRIBUIDORAS POR MUNICÍPIO.xlsx
│   └── samples/                 # Amostras para testes
│
├── docs/                        # Documentação
│   └── DOCUMENTACAO_IDENTIFICACAO_DISTRIBUIDORAS.md
│
├── output/                      # Saída (não versionado)
│
├── contratos_por_paginas/       # Contratos organizados (não versionado)
│   ├── 05_paginas/
│   │   ├── CEMIG/
│   │   ├── CPFL_PAULISTA/
│   │   └── ...
│   ├── 09_paginas/
│   │   └── ...
│   └── ...
│
└── OneDrive_2026-01-06/         # PDFs originais (não versionado)
```

## Instalação

### Desenvolvimento

```bash
# Clonar repositório
git clone https://github.com/stefanprati-rgb/raizen.git
cd raizen

# Criar ambiente virtual
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Instalar dependências
pip install -r requirements.txt

# Instalar em modo desenvolvimento
pip install -e .
```

## Uso

### 1. Organizar PDFs por Número de Páginas

```bash
python scripts/organize_by_pages.py
```

### 2. Classificar por Distribuidora

```bash
python scripts/super_organizer_v4.py
```

### 3. Executar Extração de Dados

```bash
python -m src.extrator_contratos.main --input <pasta_pdfs> [--output <pasta_saida>]

# Exemplos
python -m src.extrator_contratos.main -i ./contratos_por_paginas/09_paginas/CEMIG
python -m src.extrator_contratos.main -i ./pdfs -o ./resultados
```

### Opções Disponíveis

| Argumento | Curto | Descrição |
|-----------|-------|-----------|
| `--input` | `-i` | **(Obrigatório)** Pasta contendo os PDFs |
| `--output` | `-o` | Pasta de saída (padrão: `./output`) |
| `--max-pages` | - | Máximo de páginas por PDF (padrão: 10) |
| `--verbose` | `-v` | Modo verboso (mais detalhes no log) |

### Executar Testes

```bash
# Todos os testes
pytest

# Com cobertura
pytest --cov=src/extrator_contratos
```

## Sistema de Identificação de Distribuidoras

O sistema utiliza **3 estratégias em cascata** para identificar a distribuidora de cada contrato:

1. **Nome Explícito**: Busca por `DISTRIBUIDORA: XX - NOME` no documento
2. **Cidade do Cliente**: Cruza cidade do endereço com base de 5.267 municípios
3. **Busca Global**: Procura nomes de distribuidoras em qualquer parte do texto

### Bases de Dados Utilizadas

| Arquivo | Descrição | Registros |
|---------|-----------|-----------|
| `AreaatuadistbaseBI.xlsx` | Siglas e razões sociais de distribuidoras | 97+ |
| `PAINEL DE DESEMPENHO...xlsx` | Mapeamento município → distribuidora | 5.267 |

### Documentação Técnica Completa

Ver: [docs/DOCUMENTACAO_IDENTIFICACAO_DISTRIBUIDORAS.md](docs/DOCUMENTACAO_IDENTIFICACAO_DISTRIBUIDORAS.md)

## Saída

- `output/contratos_extraidos.csv` - Registros validados
- `output/contratos_revisao.csv` - Registros para revisão manual
- `output/relatorio.html` - Relatório visual
- `output/extractor.log` - Log de execução

## Campos Extraídos

| Campo | Descrição |
|-------|-----------|
| razao_social | Razão Social do cliente |
| cnpj | CNPJ formatado |
| email | Email de contato |
| endereco | Endereço completo |
| cidade | Cidade |
| uf | Estado (UF) |
| distribuidora | Distribuidora de energia |
| num_instalacao | Número da instalação |
| num_cliente | Número do cliente |
| qtd_cotas | Quantidade de cotas |
| valor_cota | Valor de cada cota |
| pagamento_mensal | Valor do pagamento mensal |
| performance_alvo | Performance alvo em kWh |
| representante_nome | Nome do representante legal |
| representante_cpf | CPF do representante |
| participacao_percentual | Participação no consórcio (%) |
| confianca_score | Score de confiança (0-100) |

## Dependências

```
pdfplumber>=0.7.0      # Extração de texto de PDFs
pandas>=1.3.0          # Leitura de Excel e manipulação de dados
openpyxl>=3.0.0        # Engine para ler .xlsx
pytest>=7.0.0          # Testes automatizados
```

## Licença

Uso interno - Raízen GD
