# Arquitetura de Confiabilidade de Dados em Pipelines de Extração de Documentos (IDP): Estratégias de Validação, Monitoramento e Governança em Múltiplas Rodadas


## 1. Introdução: O Paradigma da Incerteza em Dados Não Estruturados

A transição digital impulsionou as organizações a automatizar a extração de dados de documentos não estruturados, como PDFs, imagens digitalizadas e formulários físicos. No entanto, diferentemente de bases de dados relacionais onde a integridade é garantida por esquemas rígidos (schemas), os dados provenientes de pipelines de Processamento Inteligente de Documentos (IDP) e Reconhecimento Óptico de Caracteres (OCR) são inerentemente estocásticos. A extração não é um processo determinístico binário de sucesso ou falha, mas sim um espectro probabilístico de confiança. Quando um projeto escala para processar milhares de documentos em múltiplas rodadas, a acumulação de erros sutis — sejam eles alucinações de modelos de linguagem (LLMs), ruídos de OCR ou deslocamentos de layout (*layout drift*) — pode corromper a base de dados analítica, levando a decisões empresariais equivocadas e riscos de *compliance*.<sup>1</sup>

A validação da base criada por um projeto de extração de dados exige uma mudança fundamental de mentalidade: de uma verificação pontual para um ciclo de vida contínuo de Engenharia de Confiabilidade de Dados (*Data Reliability Engineering*). O desafio central, conforme apresentado na necessidade de validar dados extraídos de PDFs em múltiplas rodadas, reside na garantia de consistência temporal e na mitigação de regressões. Uma base confiável na "Rodada 1" não garante a integridade na "Rodada 10" se o modelo de extração for atualizado, se o layout dos documentos de entrada mudar (como frequentemente ocorre com faturas de concessionárias como a CPFL), ou se houver degradação na qualidade das imagens ingeridas.<sup>4</sup>

Este relatório técnico estabelece uma metodologia exaustiva para a validação de bases de dados extraídas de documentos, estruturada em camadas de defesa: validação determinística (regras de negócio e algoritmos), controle estatístico de qualidade (normas ISO), validação semântica e monitoramento de *drift*. A abordagem detalhada a seguir integra práticas de CI/CD para dados (*DataOps*), estratégias de *Human-in-the-Loop* (HITL) e governança de *Golden Sets*, oferecendo um guia definitivo para arquitetar pipelines resilientes em ambientes corporativos complexos.


## 

---
2. Fundamentos da Qualidade de Dados em Ambientes de OCR e NLP

Para desenhar uma estratégia de validação eficaz, é imperativo primeiro desconstruir a natureza dos erros específicos que ocorrem em pipelines de extração de texto. A confiabilidade dos dados extraídos de PDFs não pode ser medida por uma única métrica; ela é multidimensional. A literatura e a prática industrial convergem para dimensões críticas que devem ser monitoradas continuamente: precisão (*accuracy*), completude (*completeness*), consistência (*consistency*) e validade (*validity*).<sup>6</sup>


### 2.1. Taxonomia de Falhas em Extração de Documentos

A validação deve ser projetada para interceptar categorias específicas de falhas que são endêmicas ao OCR e ao NLP. O ruído de OCR (*OCR Noise*) é a forma mais primária de erro, onde a representação visual do caractere é mal interpretada pelo motor. Substituições comuns incluem a troca de "B" por "8", "l" (L minúsculo) por "1" ou "I", e "O" por "0". Em campos de texto livre, isso pode ser tolerável e corrigível via contexto, mas em campos numéricos críticos — como o código de instalação de uma conta de energia ou o valor monetário de uma fatura — um único *bit flip* compromete a integridade de todo o registro.<sup>9</sup> A métrica técnica para monitorar isso é a Taxa de Erro de Caractere (CER) e a Taxa de Erro de Palavra (WER), baseadas na Distância de Levenshtein, que quantifica o número de inserções, deleções ou substituições necessárias para transformar o texto extraído no texto real (*Ground Truth*).<sup>10</sup>

Além do ruído de baixo nível, enfrentamos o desafio das "alucinações" em modelos baseados em *Deep Learning* e LLMs. Quando forçado a extrair um campo que não existe ou está ilegível, um modelo generativo pode inferir um valor plausível estatisticamente, mas factualmente incorreto. Por exemplo, ao processar uma fatura danificada onde a data de vencimento está borrada, o modelo pode "inventar" uma data baseada na data de emissão, criando um dado que é sintaticamente válido (passa em um regex de data) mas semanticamente falso.<sup>1</sup>

A terceira classe de erro é o *Layout Drift* ou Desvio de Estrutura. Documentos corporativos, como contas da CPFL ou boletos bancários, sofrem alterações periódicas de design. Um pipeline configurado para buscar o "Total a Pagar" no quadrante inferior direito pode começar a extrair lixo ou metadados irrelevantes se a concessionária mover esse campo para o topo da página em um novo ciclo de faturamento. A validação em múltiplas rodadas deve, portanto, ser agnóstica à posição sempre que possível, ou capaz de detectar que a estrutura do documento mudou significativamente antes de tentar a extração.<sup>5</sup>


### 2.2. A Arquitetura de Validação em Camadas

A proposta central deste relatório é a implementação de uma arquitetura de "Defesa em Profundidade". Não se deve confiar em um único ponto de validação. A confiabilidade emerge da sobreposição de múltiplas técnicas que filtram diferentes tipos de erros.



1. **Camada de Ingestão e Pré-processamento:** Validação da qualidade da imagem (DPI, contraste, rotação) antes mesmo do OCR. Imagens abaixo de um limiar de qualidade devem ser rejeitadas ou enviadas para aprimoramento, pois "lixo na entrada, lixo na saída" (*Garbage In, Garbage Out*) é uma lei imutável em pipelines de dados.<sup>6</sup>
2. **Camada Determinística (Hard Rules):** Regras binárias baseadas em lógica de negócio, algoritmos de verificação (módulo 10/11 para boletos e CPF/CNPJ) e restrições de formato (Regex). Esta camada é barata computacionalmente e deve filtrar a maioria dos erros grosseiros.<sup>16</sup>
3. **Camada Estatística e Semântica (Soft Rules):** Análise de distribuição, detecção de *outliers* (ex: valor da conta 10x maior que a média histórica), e consistência semântica (verificação cruzada de campos).
4. **Camada de Governança Humana (HITL):** Onde a incerteza residual é resolvida por operadores humanos, cujas correções retroalimentam o sistema.<sup>18</sup>

A seguir, detalharemos a implementação técnica de cada uma dessas camadas, com foco específico na realidade de documentos brasileiros e na necessidade de consistência ao longo do tempo.


## 

---
3. Camada 1: Validação Determinística e Verificação Algorítmica

A base da pirâmide de confiabilidade é a validação determinística. Esta etapa consiste em aplicar regras que não dependem de probabilidade; o dado extraído ou satisfaz a condição lógica ou é inválido. Para documentos brasileiros, que são ricos em dígitos verificadores e estruturas padronizadas, esta camada é excepcionalmente poderosa.


### 3.1. Algoritmos de Verificação de Identificadores (CPF, CNPJ, Boletos)

A extração de identificadores fiscais e bancários nunca deve ser validada apenas por Expressões Regulares (Regex). Embora um regex possa confirmar que uma string possui 11 dígitos, ele não garante que aqueles dígitos formam um CPF válido. A validação deve implementar os algoritmos de *checksum* oficiais (Módulo 11).

No contexto de um pipeline Python, por exemplo, após a extração bruta do OCR, o dado deve passar por uma função de limpeza que remove caracteres não numéricos. Em seguida, aplica-se o cálculo dos dígitos verificadores. Se o CPF extraído for 123.456.789-00, o algoritmo recalcula os dois últimos dígitos com base nos nove primeiros. Se o resultado matemático divergir dos dígitos extraídos, o campo é marcado como inválido.<sup>16</sup> Isso é crucial para detectar erros de OCR sutis, como a confusão entre o dígito 8 e a letra B, que passariam despercebidos visualmente.

Para boletos bancários e contas de consumo (arrecadação), a "Linha Digitável" (o código numérico geralmente localizado no topo do boleto) contém mecanismos de verificação robustos. A linha digitável de boletos bancários (47 dígitos) e de arrecadação (48 dígitos, comum em contas de energia como CPFL) é dividida em blocos, cada um com seu próprio dígito verificador (DAC). A validação deve segmentar a linha extraída, recalcular o DAC de cada bloco e, se houver divergência, tentar corrigir o erro usando o DAC como "dica" ou rejeitar a extração.<sup>21</sup> Mais importante ainda, a linha digitável contém informações codificadas, como o valor do documento e a data de vencimento. Uma estratégia de validação cruzada envolve extrair o valor e a data visualmente do corpo do documento e compará-los com os valores decodificados da linha digitável. Se houver discrepância, há um erro de extração em um dos dois pontos.<sup>21</sup>


### 3.2. Validação Aritmética e Lógica Cruzada (***Cross-Field Validation***)

Documentos financeiros como faturas e contas de serviços públicos (utilities) são governados por lógica aritmética. A soma dos itens individuais deve igualar o total a pagar. Esta propriedade permite criar "armadilhas lógicas" para validar a extração.

Considerando o exemplo de uma conta de energia da CPFL, a validação não deve apenas extrair o "Valor Total". O pipeline deve ser configurado para extrair:



1. Consumo em kWh.
2. Tarifa unitária (com e sem impostos).
3. Valores de Adicionais de Bandeiras Tarifárias.
4. Contribuição de Iluminação Pública (CIP).
5. Valor Total da Fatura.

A regra de validação então aplica a fórmula: (Consumo * Tarifa) + Bandeiras + CIP ≈ Valor Total. Devido a arredondamentos, permite-se uma tolerância mínima (ex: ± R$ 0,05). Se a diferença for maior, o sistema sinaliza um erro de extração. Erros comuns detectados aqui incluem a leitura incorreta da casa decimal (extrair 10000 em vez de 100,00) ou a falha em capturar uma linha de cobrança adicional.<sup>23</sup>

Outra validação lógica crítica é a consistência temporal. Regras como Data de Vencimento >= Data de Emissão e Leitura Atual do Medidor > Leitura Anterior devem ser aplicadas rigorosamente. Em um cenário de múltiplas rodadas, se uma fatura processada na "Rodada 5" (Referente a Maio) apresentar uma "Leitura Anterior" que diverge da "Leitura Atual" extraída na fatura da "Rodada 4" (Referente a Abril), detecta-se uma inconsistência na cadeia histórica dos dados, o que pode indicar fraude ou erro de leitura do medidor.<sup>26</sup>


### 3.3. Padrões de Formato Específicos e Regex

Para campos que não possuem dígitos verificadores universais, como o "Código da Instalação" ou "Seu Código" nas contas da CPFL, a validação depende do conhecimento profundo do domínio. A análise dos documentos revela que o Código de Instalação segue padrões específicos de comprimento e formato (geralmente uma sequência numérica fixa, variando entre distribuidoras como CPFL Paulista ou Piratininga).<sup>28</sup>

A implementação de regex deve ser precisa e ancorada. Em vez de buscar qualquer sequência de 10 dígitos na página (o que poderia capturar um número de telefone ou parte de um CNPJ), o regex deve ser contextual, procurando a sequência numérica apenas quando precedida por âncoras textuais como "SEU CÓDIGO", "INSTALAÇÃO" ou "MATRÍCULA". Técnicas de *Fuzzy Regex* podem ser empregadas aqui para tolerar pequenos erros nas âncoras (ex: aceitar "SEU CODIGO" ou "SEU C0DIGO"), mas o valor extraído deve obedecer estritamente à máscara esperada.<sup>30</sup>

A Tabela 1 abaixo resume as estratégias de validação determinística para campos comuns em documentos brasileiros.

**Tabela 1: Estratégias de Validação Determinística por Tipo de Campo**


<table>
  <tr>
   <td><strong>Campo</strong>
   </td>
   <td><strong>Estratégia Principal</strong>
   </td>
   <td><strong>Validação Cruzada / Lógica</strong>
   </td>
   <td><strong>Ação em Caso de Falha</strong>
   </td>
  </tr>
  <tr>
   <td><strong>CPF / CNPJ</strong>
   </td>
   <td>Algoritmo Módulo 11 (Dígitos Verificadores).
   </td>
   <td>Cruzar com base de cadastro de clientes (CRM/ERP).
   </td>
   <td>Sanitização (remover pontuação) e re-teste; se falhar, HITL.
   </td>
  </tr>
  <tr>
   <td><strong>Linha Digitável</strong>
   </td>
   <td>Módulo 10 e 11 por bloco.
   </td>
   <td>Comparar valor/data decodificados com OCR visual.
   </td>
   <td>Tentar corrigir dígito único via força bruta de <em>checksum</em>; senão HITL.
   </td>
  </tr>
  <tr>
   <td><strong>Valor Monetário</strong>
   </td>
   <td>Regex de formato (R$ \d+,\d{2}).
   </td>
   <td>Soma dos itens (Subtotal + Taxas = Total).
   </td>
   <td>HITL obrigatório (campo crítico).
   </td>
  </tr>
  <tr>
   <td><strong>Datas</strong>
   </td>
   <td>Conversão para objeto datetime e validação de formato.
   </td>
   <td>Emissão &lt;= Vencimento; Leitura Atual > Anterior.
   </td>
   <td>Verificar se ano é corrente ou passado recente; rejeitar datas futuras improváveis.
   </td>
  </tr>
  <tr>
   <td><strong>Código Instalação</strong>
   </td>
   <td>Regex de máscara fixa e verificação de comprimento.
   </td>
   <td>Validar existência na base mestre de instalações.
   </td>
   <td>HITL.
   </td>
  </tr>
</table>



## 

---
4. Camada 2: Controle Estatístico de Qualidade (ISO 2859-1 e AQL)

Enquanto a validação determinística atua no nível do documento individual (*micro*), a garantia da confiabilidade em "múltiplas rodadas" exige uma visão do lote (*macro*). Quando se processam milhares de PDFs, revisar 100% dos documentos é inviável economicamente e operacionalmente. A solução é a aplicação de Controle Estatístico de Processo (CEP), especificamente utilizando a norma **ISO 2859-1**, que define planos de amostragem para inspeção por atributos.<sup>32</sup>


### 4.1. Determinação do Limite de Qualidade Aceitável (AQL)

O conceito central é o AQL (*Acceptable Quality Limit*), que representa a pior qualidade tolerável em um lote para que ele seja aceito. Em um projeto de extração de dados, diferentes campos podem ter diferentes níveis de AQL baseados em sua criticidade <sup>34</sup>:



* **Defeitos Críticos (AQL 0.1% - 0.65%):** Erros que impedem o uso do dado ou geram prejuízo financeiro direto. Exemplos: Valor Total da fatura incorreto, Código de Barras ilegível ou errado, CNPJ do fornecedor trocado.
* **Defeitos Maiores (AQL 1.0% - 2.5%):** Erros que dificultam o uso do dado, mas podem ser contornados ou recuperados. Exemplos: Data de emissão com dia/mês invertidos (mas recuperável pelo contexto), Endereço com erro de digitação no nome da rua.
* **Defeitos Menores (AQL 4.0%+):** Erros cosméticos ou em campos não essenciais. Exemplos: Descrição do item com caracteres estranhos, mas legível.


### 4.2. Metodologia de Amostragem em Múltiplas Rodadas

Para cada rodada de processamento (ex: um lote diário ou semanal de documentos ingestados), o sistema deve calcular o tamanho da amostra estatística necessária para validar a qualidade.



1. **Definição do Tamanho do Lote (N):** Quantidade total de documentos processados na rodada.
2. **Nível de Inspeção:** Geralmente utiliza-se o Nível II para operação normal. Se a qualidade histórica for alta e consistente, pode-se mover para Nível I (menor amostra). Se houver degradação recente, move-se para Nível III (maior rigor).<sup>33</sup>
3. **Seleção da Amostra (n):** A seleção dos documentos para a amostra de validação humana não deve ser puramente aleatória. Recomenda-se uma **Amostragem Aleatória Estratificada**:
    * *Estrato de Confiança:* Incluir desproporcionalmente documentos onde o modelo reportou confiança média (zona de incerteza, ex: 60%-80%). Documentos com confiança >99% e &lt;40% (geralmente rejeitados automaticamente) podem ter menor representação na amostra.
    * *Estrato de Valor:* Para documentos financeiros, validar 100% dos itens acima de um valor de corte (ex: R$ 50.000,00) e amostrar os demais.
    * *Estrato de Fonte:* Garantir representatividade de todos os principais layouts/fornecedores presentes no lote.<sup>36</sup>

Se o número de erros encontrados na amostra n exceder o número de aceitação (Ac) definido pela tabela ISO, o lote inteiro é rejeitado estatisticamente. Na prática de DataOps, isso significa que o lote deve ser colocado em quarentena e submetido a uma revisão humana mais ampla ou reprocessamento com parâmetros ajustados, impedindo que dados sujos contaminem o *Data Warehouse* analítico.<sup>32</sup>


## 

---
5. Camada 3: Monitoramento de ***Data Drift*** e Consistência Temporal

O processamento em "múltiplas rodadas" introduz o risco de degradação silenciosa. Um modelo treinado em janeiro pode funcionar perfeitamente até março, mas falhar em abril se houver uma mudança no padrão dos dados de entrada (*Data Drift*) ou no conceito do que é extraído (*Concept Drift*).


### 5.1. Detecção de Desvios de Distribuição (***Distribution Shift***)

Para validar a base continuamente, é necessário monitorar as propriedades estatísticas dos dados extraídos e compará-las com uma linha de base (*baseline*) ou com a rodada anterior. Ferramentas como **Evidently AI** são fundamentais neste estágio.<sup>38</sup>



* **Drift em Campos Numéricos:** Monitorar a média, mediana e desvio padrão de campos como "Valor da Conta" ou "Consumo". Se a média do consumo de energia de um grupo de clientes saltar 500% de uma rodada para outra, isso é um forte indício de erro sistêmico de extração (ex: o OCR começou a ignorar a vírgula decimal) ou uma mudança real drástica que precisa ser investigada.<sup>40</sup> O teste de Kolmogorov-Smirnov (K-S) ou a métrica de Distância de Wasserstein podem ser usados para quantificar matematicamente a distância entre as distribuições das duas rodadas.
* **Drift em Campos Textuais:** Monitorar a distribuição de comprimentos de strings e a frequência de valores categóricos. Se o campo "Cidade", que costumava ter 95% de preenchimento com nomes de cidades válidas, passar a ter 30% de valores vazios ou caracteres aleatórios, houve uma falha de extração. O *Population Stability Index* (PSI) é uma métrica padrão da indústria para esse tipo de monitoramento; valores de PSI acima de 0.2 indicam uma mudança significativa na população.<sup>13</sup>


### 5.2. Métricas Técnicas de OCR (CER/WER)

Além do drift de dados, deve-se monitorar a saúde técnica do OCR. Periodicamente, deve-se calcular o Character Error Rate (CER) e o Word Error Rate (WER) em uma sub-amostra validada.

O cálculo do CER é dado por:

$$CER = \frac{I + S + D}{N}$$

Onde $I$ é o número de inserções, $S$ de substituições, $D$ de deleções e $N$ o número total de caracteres no Ground Truth. Um aumento súbito no CER pode indicar problemas na ingestão, como scanners descalibrados gerando imagens com muito ruído ou baixa resolução, exigindo uma intervenção na etapa de pré-processamento de imagem.9


## 

---
6. Arquitetura ***Human-in-the-Loop*** (HITL) e Correção Ativa

A automação total em extração de documentos complexos é, muitas vezes, inatingível ou arriscada. A arquitetura HITL integra a inteligência humana nos pontos de falha da IA, não apenas para corrigir dados, mas para gerar novos dados de treino (*Active Learning*).<sup>18</sup>


### 6.1. Workflow de Triagem Inteligente

O sistema de validação deve atuar como um roteador de tráfego complexo, direcionando documentos para diferentes fluxos baseados em sua pontuação de risco:



1. **Fluxo Verde (Straight-Through Processing - STP):** Documentos com alta confiança no OCR (>90%), que passaram em todas as validações determinísticas (CPF, somas, datas) e não apresentaram drift estatístico. Estes vão direto para a base final.
2. **Fluxo Amarelo (Incerteza/Amostragem):** Documentos na zona cinzenta de confiança (ex: 60-90%) ou que caíram na amostragem aleatória da ISO 2859-1. Estes são encaminhados para revisão humana rápida.
3. **Fluxo Vermelho (Exceção/Erro):** Documentos que falharam em validações críticas (ex: CNPJ inválido, soma não bate). Estes requerem intervenção especializada para correção ou rejeição do documento.<sup>24</sup>


### 6.2. Interface e UX de Validação

A ferramenta de validação (como Label Studio, Doccano ou interfaces customizadas no Azure Document Intelligence Studio) deve ser otimizada para velocidade e precisão. O validador humano deve ver o recorte da imagem original (snippet) ao lado do campo extraído. O sistema deve sugerir o valor mais provável e destacar em vermelho onde a validação lógica falhou.

Crucialmente, as correções feitas pelos humanos no Fluxo Amarelo e Vermelho não devem ser descartadas. Elas devem ser armazenadas como novos pares de "Imagem + Texto Correto" para compor o dataset de retreino do modelo, criando um ciclo virtuoso de melhoria contínua da confiabilidade.44


## 

---
7. Múltiplas Rodadas: Testes de Regressão e Gestão do ***Golden Set***

A parte "múltiplas rodadas" da solicitação do usuário exige uma estratégia robusta de testes de regressão. Quando o modelo é atualizado ou novas regras são implementadas, como garantir que o desempenho não piorou em documentos que antes eram processados corretamente?


### 7.1. O Conceito de ***Golden Set*** (Conjunto Dourado)

O *Golden Set* é um subconjunto de documentos representativos (ex: 500-1000 documentos) que foram validados manualmente com 100% de precisão e considerados a "verdade absoluta" (*Ground Truth*). Este conjunto deve ser imutável e versionado. Ele deve conter:



* Exemplos perfeitos de cada tipo de layout.
* *Edge cases* conhecidos (imagens rotacionadas, ruído, manchas).
* Exemplos adversários (documentos que historicamente confundiram o modelo). \
A cada nova rodada de deploy de código ou modelo, o pipeline deve processar o Golden Set e comparar a saída atual com a saída esperada (gabarito).45


### 7.2. Ferramentas de Comparação (Diffing)

Para automatizar a detecção de regressão, ferramentas de *diffing* de dados são essenciais.



* **DeepDiff:** Uma biblioteca Python poderosa para comparar dicionários, JSONs e objetos complexos. Ela permite ignorar caminhos específicos (como *timestamps* de processamento que sempre mudam) e focar nas alterações de valores de negócio. Usando DeepDiff(t1, t2, ignore_order=True), pode-se verificar se os itens extraídos de uma tabela são os mesmos, independentemente da ordem de extração.<sup>31</sup>
* **csv-diff:** Ideal para comparar grandes exportações de dados em formato tabular. Diferente de um git diff textual, o csv-diff entende a estrutura de colunas e linhas, identificando quais células específicas mudaram, quais linhas foram adicionadas ou removidas, facilitando a identificação de *drifts* em larga escala.<sup>50</sup>


### 7.3. Pipeline CI/CD de Dados (DataOps)

A validação deve ser integrada ao pipeline de CI/CD. Nenhuma nova versão do extrator deve ir para produção se não passar nos testes de regressão do *Golden Set*.



1. **Commit:** O engenheiro submete uma alteração no código de extração ou um novo modelo treinado.
2. **Build & Test:** O CI (GitHub Actions, Jenkins) dispara o processamento do *Golden Set* usando a nova versão.
3. **Comparação:** O sistema compara os resultados com o gabarito. Se a acurácia cair abaixo do limiar aceitável (ex: degradação > 0.5%), o *build* falha e o *deploy* é bloqueado.
4. **Relatório:** Um relatório de discrepâncias é gerado, mostrando exatamente quais documentos falharam na nova versão, permitindo *debugging* focado.<sup>52</sup>


## 

---
8. Implementação Técnica com Great Expectations e DQS

Para orquestrar todas essas validações programaticamente, recomenda-se o uso de *frameworks* de qualidade de dados como o **Great Expectations (GX)**.


### 8.1. Configurando Expectativas

O GX permite definir "testes unitários para dados" que são executados a cada rodada de ingestão. Exemplos de expectativas configuráveis para um pipeline de contas de energia:



* expect_column_values_to_not_be_null(column="valor_total"): Garante completude em campo crítico.
* expect_column_values_to_match_regex(column="codigo_instalacao", regex="^\d{10,12}$"): Validação de formato.
* expect_column_values_to_be_between(column="consumo_kwh", min_value=0, max_value=5000): Validação de intervalo (range) para detectar *outliers*.
* expect_table_row_count_to_be_between(min_value=1000, max_value=1200): Validação de volume de lote para detectar falhas na ingestão de arquivos.<sup>55</sup>


### 8.2. Cálculo do ***Data Quality Score*** (DQS) Ponderado

Para fornecer uma visão executiva da confiabilidade, deve-se calcular um *Score* de Qualidade de Dados (DQS) unificado para cada rodada. O DQS não deve ser uma média simples, mas uma média ponderada pela criticidade dos campos.

$$DQS = \frac{\sum (Score_{campo} \times Peso_{campo})}{\sum Pesos}$$

Onde o $Score_{campo}$ pode ser composto por:



* **Validade:** % de registros que passaram no Regex/Algoritmo.
* **Completude:** % de registros não nulos.
* **Consistência:** % de registros que passaram na validação cruzada.

**Exemplo de Ponderação:**



* CPF/CNPJ e Valor Total: Peso 5 (Crítico).
* Data de Vencimento: Peso 3 (Importante).
* Endereço: Peso 1 (Informativo).

Se o DQS do lote cair abaixo de um limiar (ex: 95%), alertas são disparados para a equipe de Engenharia de Dados.<sup>7</sup>


## 

---
9. Conclusão e Roadmap de Implementação

Garantir a confiabilidade de dados extraídos de PDFs em múltiplas rodadas é um exercício de mitigação de incertezas. A validação perfeita é impossível devido à natureza estocástica da fonte, mas a confiabilidade robusta é alcançável através de uma arquitetura defensiva em camadas.

A jornada recomendada para implementação segue três fases de maturidade:



1. **Fase 1 (Fundação):** Implementar validações determinísticas (Módulo 11, Regex, Somas) e sanitização básica. Estabelecer um fluxo manual de revisão de exceções.
2. **Fase 2 (Estatística e Processo):** Adotar amostragem ISO 2859-1 para QA de lotes. Criar o *Golden Set* inicial e implementar testes de regressão manuais antes de grandes mudanças.
3. **Fase 3 (Automação e Observabilidade):** Integrar Great Expectations e DeepDiff no pipeline CI/CD. Automatizar o retreino do modelo com dados do HITL e monitorar *Drift* em tempo real com dashboards (Grafana/Evidently).

Ao tratar a base de dados não como um repositório estático, mas como um produto vivo que requer engenharia de confiabilidade contínua, o projeto transformará dados brutos e incertos em ativos de informação confiáveis e acionáveis.


### Tabela 2: Matriz de Ferramentas Recomendadas por Camada de Validação


<table>
  <tr>
   <td><strong>Camada</strong>
   </td>
   <td><strong>Ferramenta / Biblioteca</strong>
   </td>
   <td><strong>Função Principal</strong>
   </td>
  </tr>
  <tr>
   <td><strong>Ingestão</strong>
   </td>
   <td>OpenCV / ImageMagick
   </td>
   <td>Pré-processamento e verificação de qualidade de imagem.
   </td>
  </tr>
  <tr>
   <td><strong>Validação Lógica</strong>
   </td>
   <td>Pydantic / Pandas
   </td>
   <td>Validação de tipos, <em>schemas</em> e regras de negócio intra-registro.
   </td>
  </tr>
  <tr>
   <td><strong>Identificadores</strong>
   </td>
   <td>validate-docbr (Python)
   </td>
   <td>Algoritmos prontos para CPF, CNPJ, PIS, CNH, etc.
   </td>
  </tr>
  <tr>
   <td><strong>Comparação (Diff)</strong>
   </td>
   <td>DeepDiff / csv-diff
   </td>
   <td>Testes de regressão e comparação detalhada de JSONs/CSVs.
   </td>
  </tr>
  <tr>
   <td><strong>Orquestração QA</strong>
   </td>
   <td>Great Expectations
   </td>
   <td>Definição e execução automatizada de testes de qualidade de dados.
   </td>
  </tr>
  <tr>
   <td><strong>Monitoramento</strong>
   </td>
   <td>Evidently AI
   </td>
   <td>Detecção de <em>Data Drift</em> e <em>Concept Drift</em> em textos e numéricos.
   </td>
  </tr>
  <tr>
   <td><strong>Interface HITL</strong>
   </td>
   <td>Label Studio / Doccano
   </td>
   <td>Interface de anotação e correção humana.
   </td>
  </tr>
  <tr>
   <td><strong>Visualização</strong>
   </td>
   <td>Grafana / Streamlit
   </td>
   <td>Dashboards de métricas de qualidade (DQS, CER, Taxa de HITL).
   </td>
  </tr>
</table>



#### Referências citadas



1. NLP nas empresas | Reconhecimento de textos com Deep Learning em PDFs e imagens, acessado em janeiro 20, 2026, [https://medium.com/@pierre_guillou/nlp-nas-empresas-reconhecimento-de-textos-com-deep-learning-em-pdfs-e-imagens-14d8b9e8d513](https://medium.com/@pierre_guillou/nlp-nas-empresas-reconhecimento-de-textos-com-deep-learning-em-pdfs-e-imagens-14d8b9e8d513)
2. Automatize a extração de dados de PDFs com IA | Evolução - Blog Dynadok, acessado em janeiro 20, 2026, [https://blog.dynadok.com/ia/como-automatizar-extracao-dados-pdfs/](https://blog.dynadok.com/ia/como-automatizar-extracao-dados-pdfs/)
3. Approaches to PDF Data Extraction for Information Retrieval | NVIDIA Technical Blog, acessado em janeiro 20, 2026, [https://developer.nvidia.com/blog/approaches-to-pdf-data-extraction-for-information-retrieval/](https://developer.nvidia.com/blog/approaches-to-pdf-data-extraction-for-information-retrieval/)
4. Data extraction methods for systematic review (semi)automation: Update of a living ... - PMC, acessado em janeiro 20, 2026, [https://pmc.ncbi.nlm.nih.gov/articles/PMC8361807/](https://pmc.ncbi.nlm.nih.gov/articles/PMC8361807/)
5. A Data Quality Pipeline for Industrial Environments: Architecture and ..., acessado em janeiro 20, 2026, [https://www.mdpi.com/2073-431X/14/7/241](https://www.mdpi.com/2073-431X/14/7/241)
6. How To Maintain Data Quality At Every Step Of Your Pipeline | RefinePro, acessado em janeiro 20, 2026, [https://refinepro.com/blog/how-to-maintain-data-quality/](https://refinepro.com/blog/how-to-maintain-data-quality/)
7. Data Quality Score - Knowledge Base, acessado em janeiro 20, 2026, [https://support.ovaledge.com/data-quality-score](https://support.ovaledge.com/data-quality-score)
8. Data quality scores - IBM, acessado em janeiro 20, 2026, [https://www.ibm.com/docs/en/wiam?topic=results-data-quality-scores](https://www.ibm.com/docs/en/wiam?topic=results-data-quality-scores)
9. How to Calculate & Improve OCR Accuracy with Formula? - KlearStack, acessado em janeiro 20, 2026, [https://klearstack.com/how-to-calculate-and-improve-ocr-accuracy](https://klearstack.com/how-to-calculate-and-improve-ocr-accuracy)
10. Analysis and Benchmarking of OCR Accuracy for Data Extraction Models - Docsumo, acessado em janeiro 20, 2026, [https://www.docsumo.com/blogs/ocr/accuracy](https://www.docsumo.com/blogs/ocr/accuracy)
11. Fuzzy String Matching in Python Tutorial - DataCamp, acessado em janeiro 20, 2026, [https://www.datacamp.com/tutorial/fuzzy-string-python](https://www.datacamp.com/tutorial/fuzzy-string-python)
12. Best Libraries for Fuzzy Matching In Python | by Moosa Ali | CodeX | Medium, acessado em janeiro 20, 2026, [https://medium.com/codex/best-libraries-for-fuzzy-matching-in-python-cbb3e0ef87dd](https://medium.com/codex/best-libraries-for-fuzzy-matching-in-python-cbb3e0ef87dd)
13. Data Drift: Key Detection and Monitoring Techniques in 2026 | Label Your Data, acessado em janeiro 20, 2026, [https://labelyourdata.com/articles/machine-learning/data-drift](https://labelyourdata.com/articles/machine-learning/data-drift)
14. Conta de luz da CPFL terá um novo formato para facilitar a visualização dos consumidores, acessado em janeiro 20, 2026, [https://www.youtube.com/watch?v=iY-K1OL3XoA](https://www.youtube.com/watch?v=iY-K1OL3XoA)
15. Do input ao insight: como o OCR é o seu aliado para dados estruturados, acessado em janeiro 20, 2026, [https://www.objective.com.br/insights/ocr/](https://www.objective.com.br/insights/ocr/)
16. Validação de CPF e CNPJ em Python: automatize seus dados com inteligência - Joviano, acessado em janeiro 20, 2026, [https://joviano.com/blog/validacao-cpf-cnpj-python/](https://joviano.com/blog/validacao-cpf-cnpj-python/)
17. Validador de CNPJ e CPF - GitHub, acessado em janeiro 20, 2026, [https://github.com/eduardoranucci/validador-cnpj-cpf](https://github.com/eduardoranucci/validador-cnpj-cpf)
18. Human-in-the-Loop for AI: A Collaborative Future in Research Workflows - metaphacts Blog, acessado em janeiro 20, 2026, [https://blog.metaphacts.com/human-in-the-loop-for-ai-a-collaborative-future-in-research-workflows](https://blog.metaphacts.com/human-in-the-loop-for-ai-a-collaborative-future-in-research-workflows)
19. Human In The Loop (HITL) for AI Document Processing → Unstract ..., acessado em janeiro 20, 2026, [https://unstract.com/blog/human-in-the-loop-hitl-for-ai-document-processing/](https://unstract.com/blog/human-in-the-loop-hitl-for-ai-document-processing/)
20. Como Fazer uma Validação de CPF com Python | Carlos CGS - DIO, acessado em janeiro 20, 2026, [https://www.dio.me/articles/como-fazer-uma-validacao-de-cpf-com-python](https://www.dio.me/articles/como-fazer-uma-validacao-de-cpf-com-python)
21. Projeto: Como criar leitor automático de boletos com Python - YouTube, acessado em janeiro 20, 2026, [https://www.youtube.com/watch?v=MGQbY1PklCw](https://www.youtube.com/watch?v=MGQbY1PklCw)
22. Como extrair dados de um boleto automaticamente usando Python, acessado em janeiro 20, 2026, [https://www.computersciencemaster.com.br/como-extrair-dados-de-um-boleto-automaticamente-usando-python/](https://www.computersciencemaster.com.br/como-extrair-dados-de-um-boleto-automaticamente-usando-python/)
23. Document Understanding - Visão geral da validação de extração de dados, acessado em janeiro 20, 2026, [https://docs.uipath.com/pt-BR/document-understanding/automation-cloud/latest/classic-user-guide/data-extraction-validation-overview](https://docs.uipath.com/pt-BR/document-understanding/automation-cloud/latest/classic-user-guide/data-extraction-validation-overview)
24. Automated Data Extraction from Utility Bills - AI based Intelligent Document Processing Solution, acessado em janeiro 20, 2026, [https://dms-solutions.co/solutions/automated-data-extraction-from-utility-bills/](https://dms-solutions.co/solutions/automated-data-extraction-from-utility-bills/)
25. CPFL | Entenda sua conta - YouTube, acessado em janeiro 20, 2026, [https://www.youtube.com/watch?v=UdkjGkaREFM](https://www.youtube.com/watch?v=UdkjGkaREFM)
26. Como ler seu medidor de energia elétrica - Los Angeles - LADWP.com, acessado em janeiro 20, 2026, [https://www.ladwp.com/pt-br/account/customer-service/meter-information/how-read-your-electric-meter](https://www.ladwp.com/pt-br/account/customer-service/meter-information/how-read-your-electric-meter)
27. Entenda sua Conta - RGE, acessado em janeiro 20, 2026, [https://www.rge-rs.com.br/entenda-sua-conta](https://www.rge-rs.com.br/entenda-sua-conta)
28. Seu Código da Instalação vai mudar | CPFL, acessado em janeiro 20, 2026, [https://www.cpfl.com.br/seunumerodauc](https://www.cpfl.com.br/seunumerodauc)
29. adicionar instalação - CPFL, acessado em janeiro 20, 2026, [https://www.cpfl.com.br/agencia/area-cliente/adicionar-manualmente-instalacao](https://www.cpfl.com.br/agencia/area-cliente/adicionar-manualmente-instalacao)
30. Regex para formato de número - Stack Overflow em Português, acessado em janeiro 20, 2026, [https://pt.stackoverflow.com/questions/137361/regex-para-formato-de-n%C3%BAmero](https://pt.stackoverflow.com/questions/137361/regex-para-formato-de-n%C3%BAmero)
31. Exclude Paths — DeepDiff 8.6.1 documentation - Zepworks, acessado em janeiro 20, 2026, [https://zepworks.com/deepdiff/current/exclude_paths.html](https://zepworks.com/deepdiff/current/exclude_paths.html)
32. Acceptable Quality Level, AQL Sampling Chart and Calculator - QIMA, acessado em janeiro 20, 2026, [https://www.qima.com/aql-acceptable-quality-limit](https://www.qima.com/aql-acceptable-quality-limit)
33. How The AQL Inspection Levels In ISO 2859-1 Affect Sampling Size - QualityInspection.org, acessado em janeiro 20, 2026, [https://qualityinspection.org/inspection-level/](https://qualityinspection.org/inspection-level/)
34. What Is ISO 2859? A Practical Guide to Sampling Inspection - ALEKVS Machinery, acessado em janeiro 20, 2026, [https://www.alekvs.com/what-is-iso-2859-a-practical-guide-to-sampling-inspection/](https://www.alekvs.com/what-is-iso-2859-a-practical-guide-to-sampling-inspection/)
35. Explaining Acceptance Quality Limit (AQL) for product inspection - Eurofins, acessado em janeiro 20, 2026, [https://www.eurofins.com/assurance/resources/articles/explaining-acceptance-quality-limit-aql/](https://www.eurofins.com/assurance/resources/articles/explaining-acceptance-quality-limit-aql/)
36. ISO 2859-1 - UNT Chemistry, acessado em janeiro 20, 2026, [https://chemistry.unt.edu/~tgolden/courses/iso2859-1.pdf](https://chemistry.unt.edu/~tgolden/courses/iso2859-1.pdf)
37. AQL Calculator | Acceptable Quality Limit | AQL Table | AQL Chart - Tetra Inspection, acessado em janeiro 20, 2026, [https://tetrainspection.com/aql-calculator-acceptable-quality-limit/](https://tetrainspection.com/aql-calculator-acceptable-quality-limit/)
38. Detecting Data Drift with Evidently AI | by Oleh Dubetcky - Medium, acessado em janeiro 20, 2026, [https://oleg-dubetcky.medium.com/detecting-data-drift-with-evidently-ai-11bfe378cb00](https://oleg-dubetcky.medium.com/detecting-data-drift-with-evidently-ai-11bfe378cb00)
39. Evidently 0.2.2: Data quality monitoring and drift detection for text data - Evidently AI, acessado em janeiro 20, 2026, [https://www.evidentlyai.com/blog/evidently-data-quality-monitoring-and-drift-detection-for-text-data](https://www.evidentlyai.com/blog/evidently-data-quality-monitoring-and-drift-detection-for-text-data)
40. Data Drift - Evidently AI - Documentation, acessado em janeiro 20, 2026, [https://docs.evidentlyai.com/metrics/preset_data_drift](https://docs.evidentlyai.com/metrics/preset_data_drift)
41. What is data drift in ML, and how to detect and handle it - Evidently AI, acessado em janeiro 20, 2026, [https://www.evidentlyai.com/ml-in-production/data-drift](https://www.evidentlyai.com/ml-in-production/data-drift)
42. Improving OCR Results with Basic Image Processing - PyImageSearch, acessado em janeiro 20, 2026, [https://pyimagesearch.com/2021/11/22/improving-ocr-results-with-basic-image-processing/](https://pyimagesearch.com/2021/11/22/improving-ocr-results-with-basic-image-processing/)
43. OCR Isn't Enough: How Human-in-the-Loop Drives Real Results in Finance - onPhase, acessado em janeiro 20, 2026, [https://www.onphase.com/blog/ocr-isnt-enough-how-human-in-the-loop-drives-real-results-in-finance](https://www.onphase.com/blog/ocr-isnt-enough-how-human-in-the-loop-drives-real-results-in-finance)
44. Human-in-the-Loop Overview | Document AI, acessado em janeiro 20, 2026, [https://docs.cloud.google.com/document-ai/docs/hitl](https://docs.cloud.google.com/document-ai/docs/hitl)
45. How to get gold standard data for NLP - Paul Simmering, acessado em janeiro 20, 2026, [https://simmering.dev/blog/gold-data/](https://simmering.dev/blog/gold-data/)
46. 10 Best Practices for Effective Regression Testing - SGBI, acessado em janeiro 20, 2026, [https://sgbi.us/10-best-practices-for-effective-regression-testing/](https://sgbi.us/10-best-practices-for-effective-regression-testing/)
47. Agent-Driven GenAI Testing: From Golden Data to End-to-End Regression - Medium, acessado em janeiro 20, 2026, [https://medium.com/@mail.sainath.kumar/agent-driven-genai-testing-from-golden-data-to-end-to-end-regression-060408dbc17d](https://medium.com/@mail.sainath.kumar/agent-driven-genai-testing-from-golden-data-to-end-to-end-regression-060408dbc17d)
48. DeepDiff Reference — DeepDiff 4.0.7 documentation - Read the Docs, acessado em janeiro 20, 2026, [https://deepdiff.readthedocs.io/en/latest/diff.html](https://deepdiff.readthedocs.io/en/latest/diff.html)
49. DeepDiff regex_exclude_paths filters out everything, not just the path I want - Stack Overflow, acessado em janeiro 20, 2026, [https://stackoverflow.com/questions/79173187/deepdiff-regex-exclude-paths-filters-out-everything-not-just-the-path-i-want](https://stackoverflow.com/questions/79173187/deepdiff-regex-exclude-paths-filters-out-everything-not-just-the-path-i-want)
50. csvdiff | A fast diff tool for comparing csv files - GitHub Pages, acessado em janeiro 20, 2026, [https://aswinkarthik.github.io/csvdiff/](https://aswinkarthik.github.io/csvdiff/)
51. csv-diff - PyPI, acessado em janeiro 20, 2026, [https://pypi.org/project/csv-diff/](https://pypi.org/project/csv-diff/)
52. CI/CD for Data Teams: Roadmap to Reliable Pipelines - Ascend.io, acessado em janeiro 20, 2026, [https://www.ascend.io/blog/ci-cd-for-data-teams-a-roadmap-to-reliable-data-pipelines](https://www.ascend.io/blog/ci-cd-for-data-teams-a-roadmap-to-reliable-data-pipelines)
53. CI/CD data pipelines in Azure - Microsoft Learn, acessado em janeiro 20, 2026, [https://learn.microsoft.com/en-us/azure/devops/pipelines/apps/cd/azure/cicd-data-overview?view=azure-devops](https://learn.microsoft.com/en-us/azure/devops/pipelines/apps/cd/azure/cicd-data-overview?view=azure-devops)
54. Safe Production Deployments for Data Pipelines: A CI/CD Blueprint | by Ariane Horbach | Data Science Collective, acessado em janeiro 20, 2026, [https://medium.com/data-science-collective/safe-production-deployments-for-data-pipelines-a-ci-cd-blueprint-06e4e477f3ed](https://medium.com/data-science-collective/safe-production-deployments-for-data-pipelines-a-ci-cd-blueprint-06e4e477f3ed)
55. Great Expectations Tutorial: Validating Data with Python - DataCamp, acessado em janeiro 20, 2026, [https://www.datacamp.com/tutorial/great-expectations-tutorial](https://www.datacamp.com/tutorial/great-expectations-tutorial)
56. Tutorial: Validate data using SemPy and Great Expectations (GX) - Microsoft Fabric, acessado em janeiro 20, 2026, [https://learn.microsoft.com/en-us/fabric/data-science/tutorial-great-expectations](https://learn.microsoft.com/en-us/fabric/data-science/tutorial-great-expectations)
57. Data Validation workflow - Great Expectations documentation, acessado em janeiro 20, 2026, [https://docs.greatexpectations.io/docs/0.18/oss/guides/validation/validate_data_overview/](https://docs.greatexpectations.io/docs/0.18/oss/guides/validation/validate_data_overview/)
58. How to calculate a Data Quality score?, acessado em janeiro 20, 2026, [https://www.fujitsu.com/nz/imagesgig5/How%20to%20calculate%20a%20Data%20Quality%20score.pdf](https://www.fujitsu.com/nz/imagesgig5/How%20to%20calculate%20a%20Data%20Quality%20score.pdf)