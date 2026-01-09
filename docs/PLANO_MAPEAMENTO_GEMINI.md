# Plano de Mapeamento Manual com Gemini Web
## Versão 2.0 | Atualizado: 2026-01-09 14:48

---

## 1. Objetivo

Criar mapas de extração confiáveis para cada modelo de contrato, usando o Gemini Web para análise visual do PDF e geração de regex otimizados.

---

## 2. Progresso por Pasta

### Pasta `02_paginas` ✅ CONCLUÍDA

| Modelo | PDFs | Mapa | Status | Taxa |
|--------|------|------|--------|------|
| CEMIG | 1 | `maps/CEMIG_02p_v1.json` | ✅ Testado | 100% |
| CPFL Paulista | 4 | `maps/CPFL_02p_v1.json` | ✅ Testado | 100% |

### Pasta `05_paginas` ⏳ Pendente

| Modelo | Qtd Estimada | Arquivo Amostra | Status |
|--------|--------------|-----------------|--------|
| CEMIG | 135 | output/pdfs_para_gemini/DESCONHECIDO_CEMIG_AMOSTRA.pdf | ⏳ |
| CPFL | ? | output/pdfs_para_gemini/DESCONHECIDO_CPFL_AMOSTRA.pdf | ⏳ |
| ELEKTRO | ? | output/pdfs_para_gemini/DESCONHECIDO_ELEKTRO_AMOSTRA.pdf | ⏳ |
| ENEL | ? | output/pdfs_para_gemini/DESCONHECIDO_ENEL_AMOSTRA.pdf | ⏳ |
| ENERGISA | ? | output/pdfs_para_gemini/DESCONHECIDO_ENERGISA_AMOSTRA.pdf | ⏳ |

---

## 3. Fluxo de Trabalho

```
1. PREPARAÇÃO           →  python scripts/export_samples.py
                            (exporta 1 PDF de cada modelo)

2. GEMINI WEB           →  Upload PDF + Prompt → Copia JSON

3. CRIAR MAPA           →  Salvar em maps/<MODELO>_<PAGINAS>_v1.json

4. APLICAR EM LOTE      →  python scripts/apply_map.py maps/X.json pasta_pdfs

5. VERIFICAR RESULTADO  →  Checar CSVs em output/
```

---

## 4. Prompt para Gemini Web

Ao fazer upload do PDF no Gemini, use:

```
Analise este contrato de energia solar e extraia todos os dados em formato JSON estruturado.

Campos a extrair:
- sic_ec_cliente (código SIC/EC)
- razao_social
- cnpj  
- nire
- endereco
- email
- representante_nome
- consorcio_nome
- consorcio_cnpj
- distribuidora
- numero_instalacao (UC)
- numero_conta_contrato
- participacao_percentual (rateio)
- vigencia_meses
- data_assinatura

Retorne em formato JSON estruturado.
```

---

## 5. Scripts de Apoio

| Script | Comando | Função |
|--------|---------|--------|
| `detect_models.py` | `python scripts/detect_models.py <pasta>` | Detecta modelos diferentes |
| `export_samples.py` | `python scripts/export_samples.py` | Exporta 1 PDF por modelo |
| `validate_map.py` | `python scripts/validate_map.py maps/X.json` | Testa regex contra PDF |
| `apply_map.py` | `python scripts/apply_map.py maps/X.json <pasta>` | Extrai em lote |

---

## 6. Mapas Criados

```
maps/
├── CEMIG_02p_v1.json    ✅ Testado (100%)
└── CPFL_02p_v1.json     ✅ Testado (100%)
```

---

## 7. Resultados

### Pasta 02_paginas (5 PDFs)

| Métrica | Valor |
|---------|-------|
| Total PDFs | 5 |
| Válidos (>=70%) | 5 |
| Taxa de sucesso | **100%** |

Arquivos gerados:
- `output/teste_02p_cemig/`
- `output/teste_02p_cpfl/`

---

## 8. Próximos Passos

1. ✅ Workflow testado com sucesso (02_paginas)
2. ⏳ Mapear pasta `04_paginas`
3. ⏳ Mapear pasta `05_paginas` 
4. ⏳ Mapear pasta `09_paginas` (maior volume)
5. ⏳ Extração massiva final
