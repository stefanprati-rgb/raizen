# Documentação Completa do Projeto CPFL - Extração de Dados de Contratos

**Versão:** 1.0  
**Data:** 2026-01-19  
**Autor:** Documentação Técnica de Dados  
**Status:** Produção

---

## 1. Visão Geral do Projeto

### 1.1 Objetivo de Negócio

O projeto **Raízen Power** tem como objetivo principal extrair e consolidar dados estruturados de contratos de adesão a consórcios de energia solar fotovoltaica, gerando uma base de dados centralizada para operações de negócio da Raízen GD.

A Raízen GD atua como **consorciada líder** em projetos de Geração Distribuída (GD), onde múltiplos clientes (consorciados) compartilham a energia gerada por usinas solares. Cada contrato PDF contém informações essenciais sobre:
- Identificação da unidade consumidora (UC) do cliente
- Dados cadastrais da empresa consorciada
- Parâmetros comerciais (cotas, participação, fidelidade)
- Vinculos com distribuidoras de energia

### 1.2 Tipos de Documentos Tratados

| Tipo | Descrição | Volume Estimado |
|------|-----------|-----------------|
| **Termo de Adesão** | Contrato principal de entrada no consórcio | ~80% |
| **Aditivo** | Alterações de condições comerciais ou UCs | ~10% |
| **Distrato/Rescisão** | Encerramento de contrato | ~5% |
| **Reemissão** | Versões atualizadas de contratos | ~3% |
| **Termo de Condições** | Condições gerais de participação | ~2% |

### 1.3 Escopo Atual

**Coberto:**
- Extração de ~6.309 PDFs de contratos
- Suporte a 25+ distribuidoras de energia (CPFL, CEMIG, ELEKTRO, ENEL, LIGHT, NEOENERGIA, etc.)
- 102 mapas de extração customizados por layout/distribuidora
- Validação de CNPJ/CPF com dígitos verificadores
- Detecção de contratos "guarda-chuva" (múltiplas UCs)

**Não Coberto (Limitações):**
- PDFs escaneados sem camada OCR de alta qualidade
- Contratos manuscritos ou com assinaturas sobrepostas ao texto
- Anexos em formatos não-PDF (imagens, Word)

---

## 2. Fontes de Dados e Campos da Base

### 2.1 Origem dos PDFs

```
OneDrive_2026-01-06/
└── TERMO DE ADESÃO/
    ├── [6.309 arquivos PDF]
    ├── Nomenclatura: NomeEmpresa_Tipo_Data.pdf
    └── Tamanhos: 2-16 páginas (maioria 5-11 páginas)
```

**Organização pós-processamento:**
```
contratos_por_paginas/
├── 02_paginas/
│   ├── CEMIG/
│   ├── CPFL_PAULISTA/
│   └── ...
├── 05_paginas/
├── 09_paginas/
├── 10_paginas/
└── ...
```

### 2.2 Schema de Dados de Saída (Target Output)

| Campo | Nome Técnico | Criticidade | Descrição |
|-------|--------------|-------------|-----------|
| UC / Instalação | `num_instalacao` | 🔴 Alta | Código único da unidade consumidora |
| Número do Cliente | `num_cliente` | 🟡 Média | Código do cliente na distribuidora |
| Distribuidora | `distribuidora` | 🔴 Alta | Ex: CPFL_PAULISTA, CEMIG-D, ELEKTRO |
| Razão Social | `razao_social` | 🔴 Alta | Nome completo da empresa consorciada |
| CNPJ | `cnpj` | 🔴 Alta | CNPJ formatado (XX.XXX.XXX/XXXX-XX) |
| Data de Adesão | `data_adesao` | 🟡 Média | Data completa (DD/MM/AAAA) |
| Fidelidade | `fidelidade` | 🟡 Média | Período mínimo em meses |
| Aviso Prévio | `aviso_previo_dias` | 🟡 Média | Prazo para rescisão em dias |
| Representante Legal | `representante_nome` | 🟡 Média | Signatário do contrato |
| CPF Representante | `representante_cpf` | 🟡 Média | CPF do signatário |
| Participação | `participacao_percentual` | 🔴 Alta | % de rateio/cota de energia |

**Campos Adicionais:**
- `email`, `endereco`, `cidade`, `uf`, `cep`
- `qtd_cotas`, `valor_cota`, `performance_alvo`
- `confianca_score` (0-100)

### 2.3 Volume de Dados

| Métrica | Valor |
|---------|-------|
| Total de PDFs | 6.309 |
| Período coberto | 2023-2026 |
| Páginas processadas | ~50.000+ |
| Registros extraídos | ~5.500+ |
| Taxa de sucesso | 67.2% (5+ campos) |

---

## 3. Arquitetura e Métodos de Extração

### 3.1 Pipeline de Alto Nível

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      PIPELINE DE EXTRAÇÃO v2.0                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐    │
│   │  FASE 1   │───►│ FASE 1.5  │───►│  FASE 2   │───►│  FASE 3   │    │
│   │ Extração  │    │ Golden    │    │ Análise   │    │  Gemini   │    │
│   │  Massiva  │    │   Set     │    │ de Falhas │    │ Mapping   │    │
│   └─────┬─────┘    └─────┬─────┘    └─────┬─────┘    └─────┬─────┘    │
│         │                │                │                │          │
│         ▼                ▼                ▼                ▼          │
│   ┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐    │
│   │ Sucesso   │    │ Precisão  │    │ Clusters  │    │  FASE 4   │    │
│   │  (~67%)   │◄───│   REAL    │◄───│  Agrupados│◄───│Re-Extração│    │
│   └───────────┘    └───────────┘    └───────────┘    └───────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Componentes do Sistema

```
src/extrator_contratos/
├── __init__.py          # Exports do módulo
├── main.py              # Entry point CLI
├── extractor.py         # ContractExtractor (orquestrador)
├── patterns.py          # PatternsMixin com 70+ regex
├── validators.py        # Validação CNPJ/CPF e matemática
├── normalizers.py       # Normalização de datas, moedas, %
├── classifier.py        # Classificador de distribuidoras
├── table_extractor.py   # Extração de tabelas via pdfplumber
├── map_manager.py       # Seletor de mapas JSON
├── gemini_client.py     # Integração com API Gemini
├── config_loader.py     # Carregador de YAML
└── report.py            # Gerador de relatório HTML
```

### 3.3 Tecnologias e Bibliotecas

| Componente | Tecnologia | Versão |
|------------|------------|--------|
| Extração de PDF | `pdfplumber` | ≥0.10.0 |
| OCR Fallback | `EasyOCR` | ≥1.7.0 |
| Paralelização | `ProcessPoolExecutor` | Python 3.10+ |
| Configuração | `PyYAML` | ≥6.0 |
| IA Mapeamento | Gemini API | 2.5-flash |
| Dados | `pandas`, `openpyxl` | ≥2.0.0 |
| Validação | `re` (regex nativo) | - |

### 3.4 Estratégias de Extração

#### 3.4.1 Extração por Regex (Principal)

Padrões externalizados em `config/patterns.yaml`:

```yaml
# Exemplo: Campo CNPJ
cnpj:
  - anchor: "CNPJ:"
    regex: "(\\d{2}[.\\s]?\\d{3}[.\\s]?\\d{3}[/\\s]?\\d{4}[-\\s]?\\d{2})"
    priority: 1
  - anchor: "CNPJ/MF"
    regex: "(\\d{2}\\.\\d{3}\\.\\d{3}/\\d{4}-\\d{2})"
    priority: 2
```

**Campos com múltiplos padrões:** `razao_social`, `cnpj`, `num_instalacao`, `num_cliente`, `data_adesao`, `duracao_meses`, `aviso_previo`, `representante_nome`, `representante_cpf`, `participacao_percentual`

#### 3.4.2 Extração de Tabelas

Utiliza `pdfplumber.extract_tables()` para:
- Tabelas de múltiplas UCs (contratos guarda-chuva)
- Tabelas de cotas/participação
- Anexos com lista de instalações

#### 3.4.3 Seleção de Mapas JSON

```python
def select_best_map(text, pages, distributor, maps):
    """
    Ordem de prioridade:
    1. Mapa específico: CPFL_PAULISTA_09p_v2.json
    2. Mapa genérico por distribuidora: CPFL_02p_v1.json
    3. Mapa por tipo: ADITIVO_05p_v1.json
    4. Fallback: regex base
    """
```

**102 mapas disponíveis** em `maps/`, incluindo:
- Distribuidoras: CPFL, CEMIG, ELEKTRO, ENEL, LIGHT, NEOENERGIA, etc.
- Tipos: ADESAO, ADITIVO, DISTRATO, REEMISSAO
- Versões: v1, v2, v3... (evolução contínua)

---

## 4. Processos Operacionais

### 4.1 Comandos de Execução

#### Organização de PDFs por Distribuidora
```powershell
python scripts/super_organizer_v4.py
```

#### Extração Paralela (Principal)
```powershell
python scripts/extract_parallel.py --timeout 60 --workers 7
```

#### Extração Sequencial (Debug)
```powershell
python -m src.extrator_contratos.main -i ./contratos_por_paginas -o ./output
```

#### Validação contra Referência
```powershell
python scripts/validate_against_reference.py
```

### 4.2 Arquivos de Configuração

**`config.yaml`** (Principal)
```yaml
input:
  path: "./contratos_por_paginas"
output:
  path: "./output"
  generate_html: true
  generate_csv: true
extraction:
  max_pages: 10
  batch_size: 50
validation:
  min_confidence_score: 70
  validate_cnpj: true
```

**`config/patterns.yaml`** (Padrões Regex)
- 307 linhas de configuração
- 15+ campos com múltiplos padrões
- Prioridades definidas (1-10)

### 4.3 Estrutura de Saída

```
output/
├── extraction_full_results.json    # Resultados completos
├── extraction_results.csv          # Dados tabulares
├── contratos_extraidos.csv         # Registros validados (≥70%)
├── contratos_revisao.csv           # Para revisão manual (<70%)
├── relatorio.html                  # Dashboard visual
├── validation_results.json         # Cruzamento com referência
└── extractor.log                   # Log de execução
```

### 4.4 Logs e Monitoramento

**Formato de Log:**
```
2026-01-14 10:30:45 - INFO - Processando: 200/6309...
2026-01-14 10:30:46 - WARNING - UC não encontrada: SOLAR_123.pdf
2026-01-14 10:30:47 - ERROR - Falha ao abrir: corrupted.pdf
```

**Métricas em Tempo Real:**
```
📂 Processando: 09_paginas
  🔍 Analisando 1993 arquivos...
    Progresso: 400/1993...
  ✅ Identificados: 1993/1993 (100.0%)
```

---

## 5. Desafios e Problemas Específicos

### 5.1 Variações de Layout

| Problema | Frequência | Impacto |
|----------|------------|---------|
| Layouts diferentes por distribuidora | Alta | Médio |
| Mudanças de template ao longo do tempo | Média | Alto |
| PDFs de plataformas diferentes (Clicksign, Docusign, ZapSign) | Alta | Médio |

**Exemplo de variação:**
- CPFL 9 páginas vs CPFL 11 páginas → layouts completamente diferentes
- Mesma distribuidora, versões de contrato diferentes

### 5.2 PDFs Nativos vs Escaneados

| Tipo | Características | Taxa de Sucesso |
|------|-----------------|-----------------|
| **Nativo** | Texto selecionável, tabelas estruturadas | ~85% |
| **Escaneado (bom)** | OCR de alta qualidade | ~60% |
| **Escaneado (ruim)** | Borrado, rotacionado, carimbo sobre texto | ~20% |

**Problemas de OCR:**
- Carimbos sobrepostos ao texto
- Assinaturas borradas sobre dados
- Rotação de páginas incorreta
- Baixa resolução de escaneamento

### 5.3 Múltiplas UCs por Contrato

**Cenário:** Contratos "guarda-chuva" como FORTBRAS com 10+ UCs em tabela.

**Problema:** Regex simples captura apenas primeira UC.

**Solução Implementada:**
```python
# Em extract_ocr.py e uc_extractor_v5.py
def extract_multi_uc(table):
    ucs = []
    for row in table:
        if is_valid_uc(row[0]):
            ucs.append(row[0])
    return "; ".join(ucs)  # Concatena com separador
```

### 5.4 Erros Típicos de Extração

| Erro | Causa | Mitigação |
|------|-------|-----------|
| UC ausente | Campo não encontrado | Fallback para Anexo I |
| CNPJ truncado | OCR cortando dígitos | Validação de dígitos verificadores |
| Datas trocadas | Captura de datas de emissão | Priorizar "Data de Adesão" |
| Campos invertidos | Layout não-padrão | Mapa específico por distribuidora |
| Falso positivo em distribuidora | "RGE" dentro de "ENERGETICA" | Word boundary (`\b`) em regex |

---

## 6. Soluções Adotadas e Heurísticas

### 6.1 Identificação de Distribuidoras (3 Camadas)

```
Estratégia 1: Nome Explícito
└── Busca "DISTRIBUIDORA: XX - NOME" no documento
    ↓ (se não encontrar)
Estratégia 2: Cidade do Cliente  
└── Cruza cidade do endereço com base de 5.267 municípios
    ↓ (se não encontrar)
Estratégia 3: Busca Global
└── Procura nomes de distribuidoras em todo o texto
    ↓ (se não encontrar)
Resultado: "OUTRAS_DESCONHECIDAS"
```

**Filtros Implementados:**
- Ignorar endereço da sede Raízen (Piracicaba)
- Word boundary para siglas curtas (RGE, EDP)
- Exclusão de palavras genéricas (EMPRESA, COOPERATIVA)

### 6.2 Normalização de Dados

```python
# normalizers.py
def normalize_all(data: dict) -> dict:
    data['cnpj'] = normalize_cnpj(data.get('cnpj'))        # "03389281000104" → "03.389.281/0001-04"
    data['participacao'] = normalize_percentage(data.get('participacao'))  # "1,939%" → 1.939
    data['duracao'] = normalize_duration(data.get('duracao'))  # "12 meses" → 12
    data['data_adesao'] = normalize_date(data.get('data_adesao'))  # Múltiplos formatos → DD/MM/AAAA
    return data
```

### 6.3 Validações Implementadas

| Validação | Implementação | Arquivo |
|-----------|---------------|---------|
| Dígito verificador CNPJ | Algoritmo módulo 11 | `validators.py` |
| Dígito verificador CPF | Algoritmo módulo 11 | `validators.py` |
| Tolerância matemática | 5% de variação aceita | `validators.py` |
| Formato PT-BR | Vírgula como decimal | `validators.py` |

### 6.4 Heurísticas Especiais

**Contratos com múltiplas UCs:**
- Detectar padrão de tabela (headers: "UC", "Instalação", "Código")
- Usar `pdfplumber.extract_tables()` para dados estruturados
- Concatenar UCs com separador ";"

**Documentos de rescisão:**
- Identificar por keywords: "DISTRATO", "RESCISÃO", "TÉRMINO"
- Usar mapa específico (DISTRATO_CPFL_v1.json)
- Extrair data de encerramento além de data de adesão

**Última versão válida (aditivos):**
- Priorizar documentos mais recentes por data
- Sobrescrever campos com valores de aditivos
- Manter histórico de alterações

---

## 7. Qualidade de Dados e Métricas

### 7.1 Resultados da Extração Paralela

| Métrica | Valor |
|---------|-------|
| PDFs processados | 5.500 / 6.309 (87%) |
| Taxa de processamento | 90 PDFs/min |
| ✅ Sucesso (5+ campos) | 3.695 (67.2%) |
| ⚠️ Parcial (<5 campos) | 1.805 (32.8%) |
| ❌ Falhas | 0 (0%) |

### 7.2 Taxa de Extração por Campo

| Campo | Taxa de Preenchimento | Observação |
|-------|----------------------|------------|
| `razao_social` | ~95% | Alta |
| `cnpj` | ~90% | Alta (validado) |
| `distribuidora` | 100% | Estratégia de 3 camadas |
| `num_instalacao` | ~85% | Dependente de layout |
| `data_adesao` | ~75% | Múltiplos formatos |
| `fidelidade` | ~40% | Baixa cobertura |
| `aviso_previo_dias` | ~30% | Baixa cobertura |
| `representante_nome` | ~35% | Páginas de assinatura |
| `representante_cpf` | ~25% | Baixa cobertura |
| `participacao_percentual` | ~50% | Tabelas e texto |

### 7.3 Golden Set - Validação Manual

**Metodologia:**
1. Selecionar 100 PDFs aleatórios estratificados
2. Revisar manualmente os 11 campos
3. Comparar com extração automática
4. Calcular precisão por campo

**Critérios de Aceite:**
| Campo | Precisão Mínima |
|-------|-----------------|
| Campos críticos (UC, CNPJ, Razão) | ≥ 95% |
| Campos médios (Data, Fidelidade) | ≥ 85% |

### 7.4 Script de Validação

```powershell
python scripts/create_golden_set.py --sample 100 --stratified
python scripts/create_golden_set.py --validate
```

---

## 8. Limitações e Roadmap

### 8.1 Limitações Conhecidas

| Limitação | Impacto | Workaround Atual |
|-----------|---------|------------------|
| PDFs escaneados de baixa qualidade | ~10% dos docs | Revisão manual |
| Campos de assinatura (CPF rep) | Baixa cobertura | Detecção de páginas de assinatura |
| Contratos muito antigos (layouts diferentes) | ~5% dos docs | Criação de mapas específicos |
| Múltiplas UCs em texto corrido | Captura parcial | Regex multi-UC |
| Aditivos que sobrescrevem dados | Conflitos | Priorização por data |

### 8.2 Riscos de Negócio

| Risco | Probabilidade | Mitigação |
|-------|---------------|-----------|
| CNPJ incorreto → faturamento errado | Baixa (validação ativa) | Dígito verificador obrigatório |
| UC trocada → crédito em instalação errada | Média | Validação cruzada com base da distribuidora |
| Data de adesão errada → cálculo de fidelidade | Média | Priorizar assinatura digital |

### 8.3 Melhorias Futuras Priorizadas

| Prioridade | Melhoria | Esforço |
|------------|----------|---------|
| 🔴 Alta | Aumentar cobertura de fidelidade/aviso prévio | 2-3 dias |
| 🔴 Alta | OCR robusto para escaneados | 3-5 dias |
| 🟡 Média | Dashboard de monitoramento (Streamlit) | 2 dias |
| 🟡 Média | Automação via Gemini API para novos layouts | 1-2 dias |
| 🟢 Baixa | Integração com base de UCs da distribuidora | 3-5 dias |
| 🟢 Baixa | Detecção automática de aditivos conflitantes | 2-3 dias |

---

## 9. Referências de Arquivos

### Scripts Principais

| Script | Função |
|--------|--------|
| `scripts/super_organizer_v4.py` | Organização por distribuidora |
| `scripts/extract_parallel.py` | Extração paralela (multiprocessing) |
| `scripts/extract_cpfl_v5_full.py` | Extração especializada CPFL |
| `scripts/uc_extractor_v5.py` | Extrator robusto de UCs |
| `scripts/validate_against_reference.py` | Validação cruzada |
| `scripts/create_golden_set.py` | Gerador de Golden Set |

### Documentação Existente

| Documento | Descrição |
|-----------|-----------|
| `docs/PLANO_EXTRACAO_CONTRATOS.md` | Plano detalhado de extração |
| `docs/DOCUMENTACAO_IDENTIFICACAO_DISTRIBUIDORAS.md` | Sistema de classificação |
| `docs/MASTER_PLAN_v3.md` | Status de implementação |
| `docs/melhorias_cpfl.md` | Sugestões de refinamento |
| `README.md` | Visão geral do projeto |

### Configurações

| Arquivo | Descrição |
|---------|-----------|
| `config.yaml` | Configuração principal |
| `config/patterns.yaml` | Padrões regex externalizados |
| `config/extraction_patterns.yaml` | Padrões adicionais |

---

## 10. Glossário

| Termo | Definição |
|-------|-----------|
| **UC** | Unidade Consumidora - ponto de entrega de energia |
| **GD** | Geração Distribuída - modelo de energia solar compartilhada |
| **Consorciada** | Cliente que adere ao consórcio de energia |
| **Consorciada Líder** | Raízen GD - organizadora do consórcio |
| **Distribuidora** | Empresa responsável pela entrega de energia (CPFL, CEMIG, etc.) |
| **Mapa de Extração** | Arquivo JSON com regex e âncoras por layout |
| **Golden Set** | Conjunto de documentos validados manualmente |
| **Guarda-Chuva** | Contrato com múltiplas UCs |
| **Word Boundary** | Delimitador de palavra em regex (`\b`) |

---

*Documento gerado em 2026-01-19. Última atualização reflete estado atual do pipeline de extração.*
