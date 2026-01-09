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

## 4. Prompt para Gemini Web (v3.0)

> ⚠️ **IMPORTANTE**: Este prompt solicita regex+âncora, não apenas dados extraídos.

Ao fazer upload do PDF no Gemini, use:

```
Analise o PDF anexo. Para cada campo abaixo, forneça:
1. O valor exato encontrado no texto.
2. A "âncora" (texto fixo que precede o valor).
3. Um REGEX Python robusto para capturar este valor.

Campos obrigatórios:
- sic_ec_cliente (código SIC/EC do cliente)
- razao_social (nome da empresa consorciada)
- cnpj (CNPJ da consorciada, formato XX.XXX.XXX/XXXX-XX)
- num_instalacao (número da UC/instalação)
- num_cliente (conta contrato)
- distribuidora (CEMIG, CPFL, ENEL, ELEKTRO, etc)
- participacao_percentual (% rateio, formato brasileiro com vírgula)
- duracao_meses (vigência em meses)
- data_adesao (data de assinatura)
- representante_nome (representante legal)
- email (e-mail de contato)

Retorne APENAS um JSON neste formato:
{
  "modelo_identificado": "Nome do layout/modelo",
  "distribuidora_principal": "CEMIG/CPFL/etc",
  "campos": {
    "razao_social": {
      "valor_encontrado": "EMPRESA X LTDA",
      "ancora": "Razão Social:",
      "regex": "Raz[ãa]o\\s*Social[:\\s]*([A-Z][A-Z0-9\\s\\.\\-]+)",
      "pagina": 1,
      "confianca": "alta"
    },
    "cnpj": {
      "valor_encontrado": "12.345.678/0001-99",
      "ancora": "CNPJ:",
      "regex": "CNPJ[:\\s]*(\\d{2,3}\\.\\d{3}\\.\\d{3}/\\d{4}-\\d{2})",
      "pagina": 1,
      "confianca": "alta"
    }
  },
  "campos_nao_encontrados": []
}
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
