---
description: Este workflow é acionado quando precisamos investigar por que um contrato (PDF) específico da Raízen/CPFL falhou na extração ou retornou campos "null". O objetivo é gerar um diagnóstico visual e sugerir um novo Regex.
---

1. **Localizar o Arquivo:**
   - Ler o arquivo `output/partial_analysis_report.json`.
   - Identificar o `file_path` do documento com status `SUCCESS_PARTIAL` ou `ERROR`.

2. **Executar Diagnóstico Visual (Gemini):**
   - Rodar o comando: `python scripts/analyze_pdf_gemini.py --file "caminho/do/pdf"`.
   - Este script deve usar o modelo `gemini-2.5-flash` para comparar o texto cru do OCR com a imagem do PDF.

3. **Analisar o Retorno:**
   - Verificar se o campo faltante (ex: `num_instalacao`) existe visualmente no documento.
   - Se existir visualmente mas não no JSON, é erro de Regex ou OCR sujo.

4. **Gerar Solução (Vibe Coding):**
   - Criar uma nova entrada sugerida para o arquivo `maps/cpfl_paulista.json`.
   - O regex deve ser resiliente a quebras de linha e espaçamentos variados.
   - Exemplo de correção: Mudar de `Instalação: (\d+)` para `Instalação[\s\.:]*([\d]+)`.

5. **Salvar e Testar:**
   - Confirmar a criação do novo mapa.
   - Solicitar re-execução do teste apenas para aquele arquivo.
Por que essa estrutura funciona?
Description: Funciona como uma "tag" de busca. Quando pedires "Investiga o erro no arquivo X", o agente lê a descrição e sabe: "Ah, este é o workflow certo para essa tarefa".

Content: São as instruções "hard-coded". O agente não precisa de "pensar" em como fazer o debug, ele apenas segue a lista, garantindo consistência.