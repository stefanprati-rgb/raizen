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

## Estrutura

```
extrator_contratos/
├── __init__.py          # Exports do módulo
├── main.py              # Script principal de execução
├── extractor.py         # Lógica de extração
├── patterns.py          # Padrões regex por modelo
├── validators.py        # Validações (CNPJ, CPF, math)
├── table_extractor.py   # Extração de tabelas com pdfplumber
└── report.py            # Geração de relatório HTML
```

## Instalação

```bash
pip install pdfplumber
```

## Uso

```bash
python -m extrator_contratos.main
```

## Saída

- `output/contratos_extraidos.csv` - Registros validados
- `output/contratos_revisao.csv` - Registros para revisão manual
- `output/relatorio.html` - Relatório visual

## Campos Extraídos

| Campo | Descrição |
|-------|-----------|
| razao_social | Razão Social do cliente |
| cnpj | CNPJ formatado |
| email | Email de contato |
| endereco | Endereço completo |
| distribuidora | Distribuidora de energia |
| num_instalacao | Número da instalação |
| num_cliente | Número do cliente |
| qtd_cotas | Quantidade de cotas |
| valor_cota | Valor de cada cota |
| pagamento_mensal | Valor do pagamento mensal |
| performance_alvo | Performance alvo em kWh |
| ... | E outros campos |

## Licença

Uso interno - Raízen
