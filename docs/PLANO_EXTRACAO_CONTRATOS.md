# 📋 Plano de Extração de Dados - Contratos Raízen GD

**Versão**: 2.0  
**Data**: 2026-01-08  
**Autor**: Equipe de Automação  
**Status**: Revisado conforme feedback do time

---

## 📌 Resumo Executivo

Este documento descreve a estratégia de extração de dados de **6.309 contratos PDF** utilizando uma abordagem **multi-fase** que combina processamento automatizado com inteligência artificial seletiva.

### Objetivo
Extrair os seguintes campos de cada contrato com **>90% de precisão REAL** (validada por Golden Set):

| Campo | Criticidade |
|-------|-------------|
| UC (Unidade Consumidora) | 🔴 Alta |
| Número do Cliente | 🟡 Média |
| Distribuidora | 🔴 Alta |
| Razão Social | 🔴 Alta |
| CNPJ | 🔴 Alta |
| Data de Adesão | 🟡 Média |
| Fidelidade (meses) | 🟡 Média |
| Aviso Prévio (dias) | 🟡 Média |
| Representante Legal | 🟡 Média |
| CPF Representante | 🟡 Média |
| Participação Contratada (%) | 🔴 Alta |

---

## 🏗️ Arquitetura do Pipeline (v2.0)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PIPELINE DE EXTRAÇÃO v2.0                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌────────────┐  │
│   │   FASE 1    │───▶│  FASE 1.5   │───▶│   FASE 2    │───▶│   FASE 3   │  │
│   │  Extração   │    │  Golden Set │    │   Análise   │    │  Gemini    │  │
│   │   Massiva   │    │  Validação  │    │  de Falhas  │    │  Mapping   │  │
│   └─────────────┘    └─────────────┘    └─────────────┘    └────────────┘  │
│         │                  │                                     │          │
│         ▼                  ▼                                     ▼          │
│   ┌─────────────┐    ┌─────────────┐                      ┌────────────┐   │
│   │  Validados  │    │  Precisão   │                      │   FASE 4   │   │
│   │   (~67%)    │◀───│   REAL      │◀─────────────────────│ Re-Extração│   │
│   └─────────────┘    └─────────────┘                      └────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Mudanças da Versão 2.0 (Feedback do Time)

> [!IMPORTANT]
> Esta versão incorpora 4 correções críticas identificadas na revisão técnica.

| # | Mudança | Motivo |
|---|---------|--------|
| 1 | **FASE 1.5 Golden Set** | Validar precisão REAL, não apenas score de confiança |
| 2 | **Patterns externalizados** | Manutenibilidade (YAML em vez de hardcoded) |
| 3 | **OCR workers separados** | Prevenir OOM (2 workers OCR vs 8 texto) |
| 4 | **Validação de Regex da IA** | Gemini extrai dados + regex, Python valida antes de aplicar |

---

## 📊 Análise do Dataset

### Distribuição por Grupo (Top 10)

| # | Grupo | PDFs | % do Total |
|---|-------|------|------------|
| 1 | CPFL_PAULISTA (9 pág) | 914 | 14.5% |
| 2 | CPFL_PAULISTA (11 pág) | 634 | 10.0% |
| 3 | CPFL_PAULISTA (10 pág) | 415 | 6.6% |
| 4 | ROOT (5 pág) | 289 | 4.6% |
| 5 | CEMIG-D (9 pág) | 221 | 3.5% |
| 6 | CEMIG (11 pág) | 208 | 3.3% |
| 7 | LIGHT (11 pág) | 199 | 3.2% |
| 8 | ELEKTRO (11 pág) | 198 | 3.1% |
| 9 | ENEL_CE (11 pág) | 192 | 3.0% |
| 10 | NEOENERGIA (11 pág) | 169 | 2.7% |

### Análise Pareto
- **27 grupos** cobrem **80%** dos PDFs (5.048 documentos)
- **235 grupos** no total
- Focar nos 27 grupos prioritários maximiza ROI

---

## 🔧 Fases de Implementação

### FASE 1: Extração Massiva Inicial

**Objetivo**: Processar todos os PDFs e identificar o baseline de qualidade.

**Ferramentas Utilizadas**:
- `pdfplumber` - Extração de texto e tabelas
- `EasyOCR` - Fallback para PDFs escaneados (Workers limitados)
- `ProcessPoolExecutor` - Paralelização

> [!WARNING]
> **Configuração de Workers (Previne OOM)**:
> - Extração de texto nativo: **8 workers**
> - OCR fallback: **2 workers** (separados)
> - Timeout OCR: **30 segundos** por página

**Padrões de Extração**:
- 70+ patterns regex externalizados em `config/patterns.yaml`
- Suporte a variações de nomenclatura por distribuidora

**Comandos**:
```bash
python -m src.extrator_contratos.main -i ./contratos_por_paginas --parallel -w 8
```

**Saídas**:
| Arquivo | Descrição |
|---------|-----------|
| `contratos_extraidos.csv` | Registros com confiança ≥ 70% |
| `contratos_revisao.csv` | Registros com confiança < 70% |
| `relatorio.html` | Dashboard visual de resultados |

**Estimativas**:
| Métrica | Valor |
|---------|-------|
| Tempo de execução | ~5 minutos |
| Taxa de sucesso esperada | 60-70% |
| Registros para revisão | ~2.000-2.500 |

---

### FASE 1.5: Validação Golden Set (NOVA)

> [!IMPORTANT]
> Esta fase é crítica para medir a precisão REAL do extrator.

**Objetivo**: Validar que os registros "Sucesso" estão realmente corretos (detectar falsos positivos).

**Metodologia**:
1. Selecionar **100 PDFs aleatórios** dos registros validados
2. Revisar manualmente os 11 campos de cada
3. Comparar com dados extraídos automaticamente
4. Calcular precisão real por campo

**Script**:
```bash
python scripts/create_golden_set.py --sample 100
```

**Saída (Golden Set)**:
```json
{
  "pdf": "SOLAR_9290.pdf",
  "extraido": {"cnpj": "03.389.281/0001-04", "uc": "701855912"},
  "real": {"cnpj": "03.389.281/0001-04", "uc": "701855912"},
  "correto": {"cnpj": true, "uc": true}
}
```

**Critério de Aceite**:
| Campo | Precisão Mínima |
|-------|-----------------|
| Campos críticos (UC, CNPJ, Razão) | ≥ 95% |
| Campos médios (Data, Fidelidade) | ≥ 85% |

**Se falhar**: Voltar para ajustar patterns antes de FASE 2.

---

### FASE 2: Análise de Falhas

**Objetivo**: Entender os padrões de falha para otimizar o mapeamento IA.

**Atividades**:
1. Agrupar falhas por `distribuidora + páginas`
2. Identificar campos com maior taxa de erro
3. Classificar motivos de falha:
   - Layout não reconhecido
   - OCR de baixa qualidade
   - Formato de dados inesperado
   - Campo ausente no documento

**Script**:
```bash
python scripts/analyze_failures.py
```

**Saída Esperada**:
```json
{
  "CPFL_PAULISTA_09p": {
    "total": 914,
    "falhas": 120,
    "taxa_falha": "13.1%",
    "campos_problematicos": ["data_adesao", "num_cliente"],
    "prioridade_mapeamento": "ALTA"
  }
}
```

**Critérios de Priorização para FASE 3**:
| Critério | Peso |
|----------|------|
| Volume de falhas | 40% |
| Criticidade dos campos | 30% |
| Facilidade de mapeamento | 20% |
| Impacto no negócio | 10% |

---

### FASE 3: Mapeamento com Gemini AI (REVISADA)

**Objetivo**: Gerar mapas de extração customizados para layouts problemáticos.

**Modelo**: `gemini-2.5-flash`

> [!NOTE]
> **Opção de API Paga**: Para emergências ou iterações rápidas, considerar pay-as-you-go.
> Custo estimado: **~$0.02** (2 centavos) para mapear todos os 27 grupos Pareto.

**Limites da API (Plano Gratuito)**:
| Limite | Valor |
|--------|-------|
| Requisições por dia | 20 |
| Requisições por minuto | 5 |
| Tokens por minuto | 250-400K |

**Estratégia de Otimização**:
- Agregar 3-5 PDFs similares por requisição
- Focar nos 27 grupos Pareto (80% dos PDFs)
- Executar em 2 dias para respeitar limites

**Cronograma**:
| Dia | Requisições | Grupos Mapeados |
|-----|-------------|-----------------|
| Dia 1 | 20 | Grupos 1-20 |
| Dia 2 | 7 | Grupos 21-27 |

**Prompt Estruturado (v2.0)**:
```
Analise os contratos PDF anexados e retorne:

1. DADOS EXTRAÍDOS: Para cada campo, extraia o valor real encontrado
2. REGEX SUGERIDO: Padrão regex para capturar o campo
3. ÂNCORA: Texto que aparece antes do campo
4. VALIDAÇÃO: Formato esperado (ex: CPF = NNN.NNN.NNN-NN)

Campos requeridos: UC, CNPJ, Razão Social, Data Adesão, Fidelidade,
                   Aviso Prévio, Representante, CPF Rep, Participação
```

> [!CAUTION]
> **Validação de Regex da IA**: Antes de aplicar em massa, o Python DEVE:
> 1. Testar o regex gerado na amostra fornecida
> 2. Verificar se extrai o mesmo valor que a IA retornou
> 3. Se falhar: log + fallback para pattern manual

**Saída (JSON Map com Versionamento)**:
```json
{
  "grupo": "CPFL_PAULISTA_09p",
  "versao": "v1",
  "data_geracao": "2026-01-08",
  "campos": {
    "data_adesao": {
      "pagina": 1,
      "ancora": "Data de Assinatura",
      "regex": "\\d{2}/\\d{2}/\\d{4}",
      "valor_amostra": "15/03/2024",
      "regex_validado": true
    }
  }
}
```

**Versionamento de Mapas**:
```
maps/
├── CPFL_PAULISTA_09p_v1.json
├── CPFL_PAULISTA_09p_v2.json  ← Se layout mudar
└── CEMIG_11p_v1.json
```

---

### FASE 4: Re-Extração com Maps

**Objetivo**: Reprocessar os registros de revisão usando os mapas gerados.

**Fluxo**:
1. Carregar mapa JSON do grupo (versão mais recente)
2. Validar que regex do mapa funciona
3. Aplicar regras específicas do mapa
4. Normalizar dados extraídos (ex: "12 meses" → 12)
5. Recalcular score de confiança
6. Reclassificar registros

**Comandos**:
```bash
python scripts/reextract_with_maps.py --input contratos_revisao.csv --maps ./maps/
```

**Normalização de Dados**:
| Campo | Entrada | Saída |
|-------|---------|-------|
| Fidelidade | "12 meses", "1 ano", "doze meses" | `12` (int) |
| Participação | "1,939%", "1.939%" | `1.939` (float) |
| CNPJ | "03389281000104" | `03.389.281/0001-04` |

**Estimativas**:
| Métrica | Valor |
|---------|-------|
| Taxa de recuperação | 80-90% |
| Registros recuperados | ~1.700-2.000 |
| Residual para revisão manual | ~300-400 |

---

## 📈 Projeção de Resultados

### Por Fase

| Fase | Input | Validados | Revisão | Taxa |
|------|-------|-----------|---------|------|
| FASE 1 | 6.309 | ~4.200 | ~2.100 | 67% |
| FASE 1.5 | 100 (amostra) | Precisão medida | - | - |
| FASE 4 | 2.100 | ~1.700 | ~400 | 81% |
| **TOTAL** | 6.309 | **~5.900** | **~400** | **94%** |

### Por Esforço

| Atividade | Horas | Responsável |
|-----------|-------|-------------|
| Setup inicial | 2h | Dev |
| Execução FASE 1 | 0.5h | Automatizado |
| Golden Set (FASE 1.5) | 3h | QA + Analista |
| Análise FASE 2 | 2h | Analista |
| Mapeamento FASE 3 | 4h (2 dias) | Dev + API |
| Re-extração FASE 4 | 0.5h | Automatizado |
| Validação Final | 2h | QA |
| **Total** | **~14h** | - |

---

## ⚠️ Riscos e Mitigações (ATUALIZADO)

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Limite API Gemini | Alta | Médio | API paga para emergências (~$0.02) |
| Regex da IA inválido | Média | Alto | **Validação Python antes de aplicar** |
| OCR causa OOM | Média | Alto | **Workers separados (2 OCR, 8 texto)** |
| Falsos positivos | Média | Alto | **Golden Set valida precisão real** |
| Novos layouts | Média | Baixo | Versionamento de mapas |
| Campos ausentes | Média | Baixo | Marcar como N/A, não como erro |

---

## 🔧 Stack Técnica

| Componente | Tecnologia | Versão |
|------------|------------|--------|
| Extração de PDF | pdfplumber | ≥0.10.0 |
| OCR Fallback | EasyOCR | ≥1.7.0 |
| Paralelização | ProcessPoolExecutor | Python 3.10+ |
| Configuração | PyYAML | ≥6.0 |
| IA Mapeamento | Gemini API | 2.5-flash |
| Dados | pandas | ≥2.0.0 |
| **Patterns** | **YAML externo** | `config/patterns.yaml` |

---

## ✅ Critérios de Aceite (ATUALIZADO)

| Critério | Meta | Validação |
|----------|------|-----------|
| Taxa de extração total | ≥ 90% | Contagem automática |
| Precisão campos críticos | ≥ 95% | **Golden Set (100 PDFs)** |
| Precisão campos médios | ≥ 85% | **Golden Set (100 PDFs)** |
| Tempo total de processamento | < 1 hora | Cronômetro |
| Registros para revisão manual | < 500 | Contagem automática |

---

## 📅 Cronograma Proposto (REVISADO)

| Semana | Dia | Atividade |
|--------|-----|-----------|
| S1 | Dia 1 | FASE 1: Extração inicial |
| S1 | Dia 2 | FASE 1.5: Golden Set + FASE 2: Análise |
| S1 | Dia 3-4 | FASE 3: Mapeamento Gemini (20+7 requisições) |
| S1 | Dia 5 | FASE 4: Re-extração |
| S2 | Dia 1-2 | Validação final + Ajustes |
| S2 | Dia 3-5 | Buffer + Revisão manual do residual |

> [!NOTE]
> Cronograma inclui buffer de 3 dias para iterações na FASE 3 se API falhar.

---

## 📎 Anexos

| Arquivo | Descrição | Status |
|---------|-----------|--------|
| `scripts/analyze_distribution.py` | Análise de distribuição | ✅ Criado |
| `scripts/distribution_analysis.json` | Resultado da análise | ✅ Criado |
| `scripts/create_golden_set.py` | Gerador de Golden Set | ✅ Criado |
| `config/patterns.yaml` | Patterns externalizados | ✅ Criado |
| `scripts/generate_maps.py` | Gerador de maps Gemini | 🔜 A criar |
| `scripts/reextract_with_maps.py` | Re-extração com maps | 🔜 A criar |
| `src/extrator_contratos/normalizers.py` | Normalizadores de dados | 🔜 A criar |

---

## 🤝 Aprovações

| Nome | Cargo | Data | Status |
|------|-------|------|--------|
| | Product Owner | | ⬜ Pendente |
| | Tech Lead | | ⬜ Pendente |
| | QA Lead | | ⬜ Pendente |

---

**Próximo Passo**: Após aprovação, iniciar FASE 1 com extração massiva.
