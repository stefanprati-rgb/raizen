# Mapeamento Detalhado do Projeto Raízen Power

Este documento descreve a organização técnica das pastas e subpastas para facilitar a navegação e o desenvolvimento.

## 📁 Estrutura de Pastas

### 1. `src/raizen_power/` (Código-Fonte Principal)
Onde reside a lógica de negócio e os motores de extração.
- **`extraction/`**: Contém os extratores específicos.
    - `extractor.py`: Lógica base de extração.
    - `uc_multi_extractor.py`: Especializado em contratos com múltiplas Unidades Consumidoras (Multi-UC).
    - `gemini_client.py`: Integração com a API do Gemini para extração via IA.
    - `map_manager.py`: Gerencia os "mapas" (templates) de extração por distribuidora.
- **`core/`**: Orquestração e configuração do sistema (`config.py`, `main.py`).
- **`utils/`**: Funções auxiliares para tratamento de texto, datas e validações.

### 2. `scripts/` (Automação e Análise)
Scripts de apoio para tarefas específicas, divididos por categoria.
- **`runners/`**: Scripts para execução em massa.
    - `extract_all_contracts.py`: Executa o pipeline completo.
    - `reprocess_cpfl_full.py`: Scripts específicos para retrabalho de distribuidoras.
- **`analysis/`**: Ferramentas de auditoria e qualidade.
    - `analyze_pdf_gemini.py`: Gera diagnósticos de extração usando IA.
    - `compare_excel_stats.py`: Compara resultados entre diferentes versões do dataset.
- **`tools/`**: Utilitários diversos.
    - `organize_pdfs.py`: Renomeia e move PDFs com base nos dados extraídos.
    - `fix_cep_errors.py`: Corrige e padroniza endereços.

### 3. `output/` (Resultados e Entregas)
Tudo o que o sistema gera de valor para o usuário.
- **`termos_renomeados/`**: Pasta contendo os PDFs originais renomeados seguindo o padrão do projeto.
- **`DATASET_FINAL_.xlsx`**: O arquivo consolidado com todos os dados extraídos.
- **`DATASET_OFICIAL_GOLDEN.xlsx`**: Dataset de referência validado (Ground Truth).

### 4. `docs/` (Arquivos de Apoio e Gestão)
- **`BASE DE CLIENTES - Raizen.xlsx`**: Base oficial para cruzamento de dados.
- **`ERROS cadastros RAIZEN.xlsx`**: Planilha de controle para correções manuais e ajustes de Regex.
- **`MASTER_PLAN_v3.md`**: Planejamento das fases do projeto.

### 5. `data/` (Insumos)
- **`golden_source/`**: Amostra selecionada de PDFs usada para testar a precisão da extração.

### 6. `config/` (Parametrização)
- `patterns.yaml`: Definições de Regex e padrões de busca por distribuidora.
- `settings.yaml`: Configurações globais do sistema.

## 🛠️ Arquivos Raiz Importantes
- `save_maps.py`: Script para registrar novos mapas de extração no sistema.
- `.env`: (Oculto) Configurações de chaves de API e credenciais.
- `requirements.txt`: Dependências Python do projeto.

---
*Este mapeamento ignora pastas de ambiente virtual (`.venv`), configurações de IDE (`.vscode`), e arquivos de cache.*
