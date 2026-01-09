# Master Plan v3.0 - Estratégia Definitiva
## Status: Em Execução | Data: 2026-01-09

---

## Status de Implementação

### FASE 1: Hardening do Código Base

| Componente | Status | Arquivo | Observação |
|------------|--------|---------|------------|
| normalizers.py | ✅ IMPLEMENTADO | `src/extrator_contratos/normalizers.py` | normalize_currency, normalize_percentage, normalize_date |
| Integração | ✅ IMPLEMENTADO | `src/extrator_contratos/extractor.py` | normalize_all() aplicado pós-extração |
| Tolerância 5% | ✅ IMPLEMENTADO | `src/extrator_contratos/validators.py` | relative_tolerance = 0.05 |
| parse_currency PT-BR | ✅ IMPLEMENTADO | `src/extrator_contratos/validators.py` | Vírgula como decimal por padrão |

### FASE 2: Mapeamento Inteligente

| Componente | Status | Arquivo | Observação |
|------------|--------|---------|------------|
| detect_models.py | ✅ IMPLEMENTADO | `scripts/detect_models.py` | Detecta modelos por fingerprint |
| export_samples.py | ✅ IMPLEMENTADO | `scripts/export_samples.py` | Exporta 1 PDF por modelo |
| Prompt estruturado | ⚠️ ATUALIZAR | `docs/PLANO_MAPEAMENTO_GEMINI.md` | Novo prompt com regex+âncora |
| Mapa CEMIG 02p | ✅ CRIADO/TESTADO | `maps/CEMIG_02p_v1.json` | 100% sucesso |
| Mapa CPFL 02p | ✅ CRIADO/TESTADO | `maps/CPFL_02p_v1.json` | 100% sucesso |

### FASE 3: Validação e Aplicação

| Componente | Status | Arquivo | Observação |
|------------|--------|---------|------------|
| validate_map.py | ✅ IMPLEMENTADO | `scripts/validate_map.py` | Testa regex contra PDF |
| apply_map.py | ✅ IMPLEMENTADO | `scripts/apply_map.py` | Extração em lote |
| caminho_completo | ✅ ADICIONADO | CSV output | Path absoluto em cada linha |

### FASE 4: Auditoria Final

| Componente | Status | Arquivo | Observação |
|------------|--------|---------|------------|
| Golden Set | ✅ IMPLEMENTADO | `scripts/create_golden_set.py` | --stratified para Pareto |
| Validação Golden | ✅ IMPLEMENTADO | `scripts/create_golden_set.py --validate` | Calcula precisão |

---

## Ações Pendentes

### Alta Prioridade

1. **Atualizar prompt no PLANO_MAPEAMENTO_GEMINI.md** com formato que solicita regex+âncora
2. **Mapear pasta 05_paginas** - maior volume, ~9 modelos
3. **Mapear pasta 09_paginas** - grupos CPFL Paulista (Pareto)

### Média Prioridade

4. Criar script `generate_maps.py` para automação via API
5. Executar Golden Set estratificado após extração massiva

---

## Resultados Validados

### Pasta 02_paginas

| Métrica | Resultado |
|---------|-----------|
| PDFs processados | 5 |
| Taxa de sucesso | **100%** |
| Modelos mapeados | 2 (CEMIG, CPFL) |

---

## Novo Prompt Aprovado (v3.0)

```
Analise o PDF anexo. Para cada campo abaixo, forneça:
1. O valor exato encontrado no texto.
2. A "âncora" (texto fixo que precede o valor).
3. Um REGEX Python robusto para capturar este valor.

Campos obrigatórios:
- sic_ec_cliente (código SIC/EC do cliente)
- razao_social (nome da empresa consorciada)
- cnpj (CNPJ da consorciada)
- num_instalacao (número da UC/instalação)
- num_cliente (conta contrato)
- distribuidora (CEMIG, CPFL, ENEL, etc)
- participacao_percentual (% rateio)
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
    }
  },
  "campos_nao_encontrados": []
}
```

---

## Próximos Passos

1. [x] FASE 1 - Hardening (COMPLETO)
2. [/] FASE 2 - Mapeamento (02p COMPLETO, 05p/09p PENDENTE)
3. [ ] FASE 3 - Validação em massa
4. [ ] FASE 4 - Auditoria Golden Set
