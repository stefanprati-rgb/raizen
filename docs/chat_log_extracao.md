# Chat Log: Pipeline de Extração de Contratos Raízen

**Data:** 13-14 de Janeiro de 2026  
**Objetivo:** Desenvolver estratégia robusta para extração de dados de contratos PDF

---

## Resumo Executivo

Implementado pipeline completo de extração paralela de contratos PDF, processando **5.500 PDFs** em 60 minutos com taxa de sucesso de **67.2%**.

---

## 1. Análise Inicial

### Dados Identificados
- **6.309 PDFs** em `OneDrive_2026-01-06/TERMO DE ADESÃO`
- **11.991 registros** no Excel de referência do outro time (95% preenchidos)
- **20 mapas** de extração existentes

### Campos Necessários
UC, Número do cliente, Distribuidora, Razão Social, CNPJ, Data de Adesão, Fidelidade, Aviso prévio, Representante Legal, CPF Representante legal, Participação contratada

---

## 2. Scripts Criados

### organize_contracts.py
Organiza PDFs por páginas, distribuidora e tipo de documento.
```powershell
python scripts/organize_contracts.py --dry-run --sample 50
```

### extract_all_contracts.py
Extração sequencial com seleção automática de mapas.
```powershell
python scripts/extract_all_contracts.py --sample 30
```

### extract_parallel.py
Extração paralela com multiprocessing (7 workers).
```powershell
python scripts/extract_parallel.py --timeout 60
```

### validate_against_reference.py
Validação cruzada com Excel do outro time.
```powershell
python scripts/validate_against_reference.py
```

---

## 3. Resultados da Extração Paralela

| Métrica | Valor |
|---------|-------|
| PDFs processados | 5.500 / 6.309 (87%) |
| Taxa de processamento | 90 PDFs/min |
| ✅ Sucesso (5+ campos) | 3.695 (67.2%) |
| ⚠️ Parcial (<5 campos) | 1.805 (32.8%) |
| ❌ Falhas | 0 (0%) |

### Top 10 Mapas Utilizados
1. CPFL_02p_v1: 2.205
2. CELPE_05p_v1: 668
3. ENEL_05p_v1: 576
4. ADITIVO_MULTIPLO_PETROPOLIS_v1: 540
5. ELEKTRO_05p_v1: 520
6. ADITIVO_RETIRADA_CEMIG_v1: 436
7. CEMIG_02p_v1: 349
8. CPFL_05p_v1: 130
9. ENERGISA_MT_Aditivo_v1: 52
10. ENERGISA_MT_05p_v1: 23

### Top 10 Distribuidoras
1. CPFL_PAULISTA: 2.107
2. CEMIG: 489
3. LIGHT: 390
4. ELEKTRO: 364
5. ENEL_CE: 314
6. CEMIG-D: 296
7. NEOENERGIA: 227
8. CPFL_PIRATININGA: 197
9. ENEL_RJ: 179
10. NEOENERGIA_ELEKTRO: 156

---

## 4. Arquivos Gerados

| Arquivo | Descrição |
|---------|-----------|
| `output/extraction_full_results.json` | Resultados completos em JSON |
| `output/extraction_results.csv` | Resultados em CSV (5.500 linhas) |
| `output/organization_results.json` | Análise de organização dos PDFs |
| `output/validation_results.json` | Validação cruzada com Excel |

---

## 5. Próximos Passos

1. **Processar PDFs restantes** (809 arquivos)
2. **Criar mapas faltantes** para melhorar extração parcial
3. **Melhorar campos** (Aviso prévio, CPF Representante)
4. **Validação cruzada completa** com Excel de referência

---

## Estrutura de Pastas

```
c:\Projetos\Raizen\
├── scripts/
│   ├── organize_contracts.py
│   ├── extract_all_contracts.py
│   ├── extract_parallel.py
│   ├── extract_full.py
│   └── validate_against_reference.py
├── maps/
│   └── (20 arquivos JSON de mapeamento)
├── output/
│   ├── extraction_full_results.json
│   ├── extraction_results.csv
│   └── validation_results.json
└── OneDrive_2026-01-06/
    └── TERMO DE ADESÃO/ (6.309 PDFs)
```
