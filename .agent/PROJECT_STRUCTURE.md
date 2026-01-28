# Estrutura do Projeto Raizen Power

## 📋 Visão Geral
Este documento descreve a organização de pastas do projeto de extração de dados de contratos de energia. **TODOS OS AGENTES E NOVAS SESSÕES DEVEM CONSULTAR ESTE ARQUIVO ANTES DE CRIAR NOVOS ARQUIVOS OU PASTAS.**

---

## 📂 Estrutura de Diretórios

### `/src/raizen_power` - **Código Fonte Principal**
Biblioteca Python do extrator. **NÃO MODIFICAR SEM NECESSIDADE.**

```
src/raizen_power/
├── extraction/          # Motores de extração
│   ├── extractor.py    #   ★ PRINCIPAL: ContractExtractor
│   ├── patterns.py     #   Regex patterns para campos
│   ├── table_extractor.py  # Extração de tabelas (Anexo I)
│   └── uc_extractor_v5.py  # Extrator legado de UCs
├── utils/              # Utilitários e regras de negócio
│   ├── validators.py   #   Validação de CNPJ, CPF, datas
│   ├── normalizers.py  #   Padronização de formatos
│   ├── distributor_rules.py  # Regras por distribuidora
│   ├── city_distributor_map.py  # ★ NOVO: Mapa de cidades
│   ├── text_sanitizer.py  # Limpeza de texto OCR
│   └── blacklist.py    #   Filtro de códigos ruidosos
└── analysis/           # Classificadores
    └── classifier.py   #   Identificação de distribuidoras
```

**Convenção**: Novos módulos devem seguir o padrão snake_case e ter docstrings.

---

### `/scripts` - **Scripts Utilitários e Análises**
Scripts one-off, análises e ferramentas. **ORGANIZADOS POR FUNÇÃO.**

```
scripts/
├── runners/            # ★ Scripts de execução em lote
│   ├── build_final_datasets.py  # PRINCIPAL: Processa 6K arquivos
│   └── extract_cpfl_v5_full.py  # Legado CPFL
├── analysis/           # Scripts de análise exploratória
│   ├── analyze_pdf_gemini.py  # Análise com Gemini API
│   └── diagnostico_regex.py   # Debugging de regex
├── tools/              # Ferramentas auxiliares
└── legacy/             # Código obsoleto (não usar)
```

**Scripts Importantes**:
- `compare_golden_set.py` - Compara extrator vs IA
- `fill_golden_set_gemini.py` - Preenche Golden Set com Gemini
- `fill_golden_set_docai.py` - Preenche Golden Set com Document AI
- `create_golden_set.py` - Cria estrutura inicial do Golden Set

**Convenção**: Scripts de teste/debug devem começar com `test_` ou `investigate_`.

---

### `/data` - **Dados do Projeto**
Armazena PDFs e bases de referência. **IGNORADO NO .gitignore (exceto /reference).**

```
data/
├── raw/                # PDFs originais (não tocar)
│   └── OneDrive_*/     # Dumps de input (zips originais)
├── processed/          # ★ PDFs organizados por distribuidora
│   └── cpfl_paulista_por_tipo/
│       ├── SOLAR/      # Contratos tipo SOLAR
│       └── TERMO_ADESAO/  # Termos de Adesão
├── reference/          # Dados de referência (COMMITADO)
│   └── PAINEL DE DESEMPENHO DAS DISTRIBUIDORAS POR MUNICÍPIO.xlsx
└── temp/               # Temporários
```

**Convenção**: Nunca commitar PDFs. Apenas arquivos de referência (Excel, JSON) vão pro git.

---

### `/output` - **Resultados Centralizados**
Outputs de scripts, datasets finais e relatórios. **IGNORADO NO GIT.**

```
output/
├── datasets/           # ★ Bases finais (Excel/CSV)
│   ├── cpfl/           # Datasets CPFL
│   └── enrichment/     # Bases enriquecidas
├── reports/            # Relatórios de validação e status (MD/XLSX)
├── debug/              # Logs brutos e inspeções (TXT)
├── cache/              # JSONs intermediários para reprocessamento
└── logs/               # Logs de execução
```

**Convenção**: Datasets devem seguir o formato `dataset_{DISTRIBUIDORA}.xlsx/.csv`. Todo output deve ser salvo aqui.

---

### `/scripts` - **Scripts Utilitários e Análises**
Scripts organizados por função.

```
scripts/
├── runners/            # ★ Scripts de execução em lote e geração de datasets
├── analysis/           # Scripts de análise exploratória e validação
├── tools/              # Ferramentas auxiliares, limpeza e organização
└── legacy/             # Código obsoleto (não usar)
```

**Convenção**: Nomenclatura `{DISTRIBUIDORA}_{PAGINAS}p_v{VERSAO}.json`.

---

### `/tests` - **Testes Automatizados**
Testes unitários e de regressão.

```
tests/
├── unit/               # Testes unitários
│   └── test_validators_dates.py
└── test_regression.py  # ★ Teste de regressão com Golden Set
```

**Convenção**: Usar `pytest`. Testes devem começar com `test_`.

---

### `/docs` - **Documentação**
Documentos de referência e especificações.

**Convenção**: Markdown para docs técnicos, use diagramas Mermaid quando aplicável.

---

### `/config` - **Configurações**
Arquivos de configuração.

**Convenção**: Configs sensíveis vão no `.env` (não commitado).

---

### `/credentials` - **Credenciais**
Chaves de API e service accounts. **IGNORADO NO GIT.**

```
credentials/
└── raizen-document-ai-*.json  # Service Account Google Cloud
```

**Convenção**: NUNCA commitar credenciais. Sempre usar `.env` ou arquivos JSON ignorados.

---

### `/archive` - **Código Antigo**
Código obsoleto para referência histórica.

**Convenção**: Não usar. Apenas para consulta.

---

## 🚨 Regras Críticas

### 1. Onde Criar Novos Arquivos

| Tipo | Local | Exemplo |
|------|-------|---------|
| Script de análise | `/scripts/analysis/` | `analyze_new_distributor.py` |
| Script de execução | `/scripts/runners/` | `process_enel_batch.py` |
| Utilitário do core | `/src/raizen_power/utils/` | `new_validator.py` |
| Teste | `/tests/` | `test_new_feature.py` |
| Dataset gerado | `/output/datasets_finais/` | `dataset_CEMIG.csv` |
| Documentação | `/docs/` | `api_integration.md` |

### 2. O Que NÃO Fazer

❌ **NUNCA** criar arquivos na raiz do projeto (exceto configs)  
❌ **NUNCA** commitar PDFs, credenciais ou `.env`  
❌ **NUNCA** modificar `/src/raizen_power/extraction/extractor.py` sem revisar impacto  
❌ **NUNCA** usar `/archive` ou `/legacy` como base para novos scripts  

### 3. Convenções de Nomenclatura

- **Scripts**: `snake_case.py` (ex: `build_final_datasets.py`)
- **Classes**: `PascalCase` (ex: `ContractExtractor`)
- **Funções**: `snake_case` (ex: `extract_from_pdf`)
- **Datasets CSV**: `dataset_{DISTRIBUIDORA}.csv` (ex: `dataset_CPFL_PAULISTA.csv`)
- **Constantes**: `UPPER_SNAKE_CASE` (ex: `MAX_WORKERS`)

### 4. Padrão de Commits

```
feat: Descrição curta (max 50 chars)

- Lista de mudanças importantes
- Use bullet points
- Seja específico
```

Prefixos: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`

---

## 📊 Fluxo de Dados Típico

```
PDFs (data/processed) 
  → ContractExtractor (src/raizen_power/extraction)
  → Validação (src/raizen_power/utils/validators.py)
  → Refinamento Geográfico (utils/city_distributor_map.py)
  → Dataset CSV (output/datasets_finais/)
```

---

## 🔧 Scripts Principais (Quick Reference)

| Script | Função | Quando Usar |
|--------|--------|-------------|
| `build_final_datasets.py` | Processa todos os PDFs | Geração final de datasets |
| `compare_golden_set.py` | Compara extrator vs IA | Validação de qualidade |
| `fill_golden_set_gemini.py` | Cria Golden Set com Gemini | Golden Set (20/dia) |
| `create_golden_set.py` | Cria estrutura do Golden Set | Primeira vez |

---

## 📝 Exemplo de Uso

### Adicionar Nova Distribuidora

1. Adicionar regras em: `src/raizen_power/utils/distributor_rules.py`
2. Atualizar mapa: `src/raizen_power/utils/city_distributor_map.py` (DISTRIBUTOR_STATES)
3. Criar mapa de regex (opcional): `maps/NOVA_DIST_11p_v1.json`
4. Testar com: `scripts/runners/build_final_datasets.py`

### Criar Novo Golden Set

```bash
python scripts/create_golden_set.py --samples 100
python scripts/fill_golden_set_gemini.py --limit 20
python scripts/compare_golden_set.py
```

---

## ✅ Checklist de Consistency

Antes de commitar, verifique:

- [ ] Nenhum arquivo criado na raiz do projeto
- [ ] PDFs não foram commitados
- [ ] `.env` e `credentials/` não foram adicionados
- [ ] Scripts em pastas corretas (`/scripts/runners/` ou `/scripts/analysis/`)
- [ ] Código segue convenções de nomenclatura
- [ ] Docstrings adicionadas em funções novas
- [ ] Tests criados para features críticas

---

**Última Atualização**: 2026-01-22  
**Versão**: 1.0
