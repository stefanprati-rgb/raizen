# Extrator de Contratos Raízen

Sistema para extração automatizada de dados de contratos PDF para CSV.

## Funcionalidades

- Extração de dados de **6.309+ PDFs** de contratos
- Suporte a **2 modelos** de layout (Visual/Clicksign e Tabular/Docusign)
- Validação de CNPJ/CPF com dígitos verificadores
- Validação matemática de valores
- Detecção de contratos "Guarda-Chuva"
- Geração de relatório HTML para revisão
- Exportação para CSV

## Estrutura do Projeto

```
Raizen/
├── pyproject.toml           # Configuração do projeto (PEP 517/518)
├── requirements.txt         # Dependências
├── README.md
│
├── src/                     # Código fonte
│   └── extrator_contratos/
│       ├── __init__.py      # Exports do módulo
│       ├── main.py          # Script principal de execução
│       ├── extractor.py     # Lógica de extração
│       ├── patterns.py      # Padrões regex por modelo
│       ├── validators.py    # Validações (CNPJ, CPF, math)
│       ├── table_extractor.py # Extração de tabelas
│       └── report.py        # Geração de relatório HTML
│
├── tests/                   # Testes automatizados
│   ├── test_extractor.py
│   └── test_corrections.py
│
├── scripts/                 # Scripts utilitários
│   ├── analyze_pdfs.py
│   └── debug_pdf.py
│
├── docs/                    # Documentação
├── data/                    # Dados de exemplo
└── output/                  # Saída (não versionado)
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

### Produção

```bash
pip install -r requirements.txt
```

## Uso

### Executar extração

```bash
# Sintaxe básica
python -m src.extrator_contratos.main --input <pasta_pdfs> [--output <pasta_saida>]

# Exemplos
python -m src.extrator_contratos.main -i "C:/Contratos/PDFs"
python -m src.extrator_contratos.main -i ./pdfs -o ./resultados
python -m src.extrator_contratos.main --input /path/to/pdfs --output /path/to/output

# Ver ajuda
python -m src.extrator_contratos.main --help
```

### Opções disponíveis

| Argumento | Curto | Descrição |
|-----------|-------|-----------|
| `--input` | `-i` | **(Obrigatório)** Pasta contendo os PDFs |
| `--output` | `-o` | Pasta de saída (padrão: `./output`) |
| `--max-pages` | - | Máximo de páginas por PDF (padrão: 10) |
| `--verbose` | `-v` | Modo verboso (mais detalhes no log) |

### Executar testes

```bash
# Todos os testes
pytest

# Com cobertura
pytest --cov=src/extrator_contratos
```

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
| email_secundario | Email secundário (se houver) |
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
| representante_nome_secundario | Nome secundário do representante |
| representante_cpf | CPF do representante |
| participacao_percentual | Participação no consórcio (%) |
| confianca_score | Score de confiança (0-100) |

## Configurações

Editar `src/extrator_contratos/main.py`:

```python
PDF_DIR = Path(r"caminho/para/pdfs")
OUTPUT_DIR = Path(r"caminho/para/output")
```

## Licença

Uso interno - Raízen
