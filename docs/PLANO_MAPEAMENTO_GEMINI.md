# Plano de Mapeamento Manual com Gemini Web
## Versão 1.0 | Data: 2026-01-09

---

## 1. Objetivo

Criar mapas de extração confiáveis para cada modelo de contrato, usando o Gemini Web para análise visual do PDF e geração de regex otimizados.

---

## 2. Modelos Detectados na Pasta `05_paginas`

| Modelo | Quantidade | Arquivo Amostra | Status |
|--------|------------|-----------------|--------|
| DESCONHECIDO_CEMIG | 135 | DESCONHECIDO_CEMIG_AMOSTRA.pdf | ⏳ Pendente |
| DESCONHECIDO_CPFL | ? | DESCONHECIDO_CPFL_AMOSTRA.pdf | ⏳ Pendente |
| DESCONHECIDO_ELEKTRO | ? | DESCONHECIDO_ELEKTRO_AMOSTRA.pdf | ⏳ Pendente |
| DESCONHECIDO_ENEL | ? | DESCONHECIDO_ENEL_AMOSTRA.pdf | ⏳ Pendente |
| DESCONHECIDO_ENERGISA | ? | DESCONHECIDO_ENERGISA_AMOSTRA.pdf | ⏳ Pendente |
| DESCONHECIDO_CELPE | ? | DESCONHECIDO_CELPE_AMOSTRA.pdf | ⏳ Pendente |
| DESCONHECIDO_OUTRAS | ? | DESCONHECIDO_OUTRAS_AMOSTRA.pdf | ⏳ Pendente |
| SOLAR_RAIZEN_OUTRAS | ? | SOLAR_RAIZEN_OUTRAS_AMOSTRA.pdf | ⏳ Pendente |
| SOLAR_RAIZEN_RGE | ? | SOLAR_RAIZEN_RGE_AMOSTRA.pdf | ⏳ Pendente |

**Total: ~9 modelos** a mapear manualmente.

---

## 3. Fluxo de Trabalho Manual

```
┌─────────────────────────────────────────────────────────────────┐
│  ETAPA 1: PREPARAÇÃO                                            │
│  - PDFs de amostra já exportados em output/pdfs_para_gemini/    │
│  - Prompt técnico preparado (ver abaixo)                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  ETAPA 2: ANÁLISE NO GEMINI WEB (por modelo)                    │
│  1. Abrir https://gemini.google.com                             │
│  2. Fazer upload do PDF de amostra                              │
│  3. Colar o prompt técnico                                      │
│  4. Aguardar resposta (~30s)                                    │
│  5. Copiar JSON gerado                                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  ETAPA 3: VALIDAÇÃO LOCAL                                       │
│  1. Salvar JSON em maps/<MODELO>_v1.json                        │
│  2. Executar script de validação                                │
│  3. Se regex não funcionar: ajustar manualmente ou retry        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  ETAPA 4: EXTRAÇÃO EM MASSA                                     │
│  - Aplicar mapa validado em todos os PDFs do modelo             │
│  - Verificar taxa de sucesso                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Prompt Técnico Otimizado para Gemini

```text
# SOLICITAÇÃO DE MAPEAMENTO DE CONTRATO

Você é um especialista em extração de dados de contratos de energia solar/GD.
Analise este PDF e gere um mapa de extração PRECISO para uso em automação Python.

## CAMPOS OBRIGATÓRIOS (extrair todos)

| Campo | Descrição | Formato Esperado |
|-------|-----------|------------------|
| cnpj | CNPJ da empresa consorciada | XX.XXX.XXX/XXXX-XX |
| razao_social | Nome/Razão Social completo | Texto |
| num_instalacao | Número da UC (Unidade Consumidora) | Numérico |
| num_cliente | Código do cliente na distribuidora | Numérico |
| distribuidora | Nome da distribuidora de energia | CEMIG, CPFL, etc. |
| data_adesao | Data de assinatura do contrato | DD/MM/AAAA |
| duracao_meses | Período de fidelidade | Número (12, 24, 36...) |
| aviso_previo | Prazo de aviso prévio em dias | Número (30, 60, 90...) |
| representante_nome | Nome completo do representante legal | Texto |
| representante_cpf | CPF do representante | XXX.XXX.XXX-XX |
| participacao_percentual | % de participação no consórcio | Decimal (1,939 ou 1.939) |
| email | E-mail de contato | email@dominio.com |

## FORMATO DE SAÍDA (JSON)

Para CADA campo encontrado, retorne:

{
  "modelo_identificado": "Nome descritivo do modelo/layout",
  "distribuidora_principal": "CEMIG/CPFL/ENEL/etc",
  "paginas_analisadas": 5,
  "campos": {
    "cnpj": {
      "encontrado": true,
      "pagina": 1,
      "ancora": "TEXTO QUE APARECE ANTES DO VALOR",
      "regex": "PADRÃO REGEX COM GRUPO DE CAPTURA ()",
      "valor_extraido": "VALOR QUE VOCÊ ENCONTROU",
      "confianca": "alta/media/baixa",
      "observacao": "Notas sobre variações possíveis"
    }
  },
  "campos_nao_encontrados": ["campo1", "campo2"],
  "alertas": ["Observação importante sobre o documento"],
  "sugestoes_validacao": ["Verificar se o CNPJ tem dígito verificador correto"]
}

## REGRAS IMPORTANTES

1. REGEX: Use grupos de captura () para isolar o valor a extrair
2. ÂNCORA: Texto EXATO que aparece imediatamente antes do campo
3. FORMATO BR: Números usam vírgula como decimal (1,939 não 1.939)
4. MÚLTIPLAS UCs: Se houver tabela com várias instalações, informe
5. GUARDA-CHUVA: Identifique se é contrato com múltiplas empresas

## EXEMPLO DE REGEX BEM FORMADO

- CNPJ: CNPJ[:\s]*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})
- UC: (?:UC|Instalação)[:\s]*(\d{6,12})
- CPF: CPF[:\s]*(\d{3}\.\d{3}\.\d{3}-\d{2})
- Data: (?:Data|Assinatura)[:\s]*(\d{2}/\d{2}/\d{4})
- Percentual: (?:Participação|%)[:\s]*([\d,]+)%?

Retorne APENAS o JSON, sem explicações adicionais.
```

---

## 5. Checklist de Execução

### Por Modelo:

- [ ] Upload do PDF no Gemini Web
- [ ] Colar prompt técnico
- [ ] Copiar resposta JSON
- [ ] Salvar em maps/<MODELO>_v1.json
- [ ] Executar validação: python scripts/validate_map.py <MODELO>
- [ ] Se falhar: ajustar regex ou fazer retry
- [ ] Marcar como concluído

### Validação Final:

- [ ] Todos os 9 modelos mapeados
- [ ] Taxa de extração > 90% por modelo
- [ ] Executar extração massiva
- [ ] Comparar com Golden Set

---

## 6. Scripts de Apoio

| Script | Função |
|--------|--------|
| scripts/detect_models.py | Detecta modelos diferentes |
| scripts/export_samples.py | Exporta PDFs de amostra |
| scripts/validate_map.py | Valida regex do mapa contra PDF (A CRIAR) |
| scripts/apply_map.py | Aplica mapa em lote (A CRIAR) |

---

## 7. Tempo Estimado

| Etapa | Tempo/Modelo | Total (9 modelos) |
|-------|--------------|-------------------|
| Upload + Prompt | 2 min | 18 min |
| Análise Gemini | 1 min | 9 min |
| Copiar/Salvar JSON | 1 min | 9 min |
| Validação Local | 2 min | 18 min |
| Ajustes (se necessário) | 5 min | 45 min |
| **TOTAL** | ~11 min | **~1h40** |

---

## 8. Pontos de Atenção

> CRÍTICO: Validar CADA regex localmente antes de usar em produção

> DICA: Se um modelo tiver muitas variações, criar sub-versões (v1, v2)

> INFO: Mapas são salvos com hash para rastreabilidade

---

## 9. Próximos Passos

1. ✅ PDFs de amostra exportados
2. ⏳ Executar mapeamento manual no Gemini Web
3. ⏳ Validar cada mapa localmente
4. ⏳ Aplicar mapas em extração massiva
5. ⏳ Avaliar taxa de sucesso final
