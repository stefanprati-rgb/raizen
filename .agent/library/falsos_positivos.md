Para blindar seu pipeline contra esses "falsos positivos" numéricos, você precisa de uma **estratégia de filtragem negativa** antes da validação final. O segredo não é apenas saber o que é uma UC, mas saber exatamente o que *não* é uma UC.

Aqui está a estratégia técnica para distinguir e descartar cada um desses campos:

### 1. Estratégia de Diferenciação (Regex & Lógica)

Abaixo detalho como identificar e excluir cada caso específico que você listou, garantindo que o extrator de UCs ignore esses valores.

#### A. CNPJ (`xx.xxx.xxx/xxxx-xx` ou 14 dígitos)

O CNPJ é o maior "vilão" pois, se desformatado, vira um número de 14 dígitos que pode parecer uma UC longa.

* **Padrão Visual:** Quase sempre contém `/` ou `-`.
* **Comprimento:** Sempre 14 dígitos. As UCs da CPFL geralmente têm menos (entre 8 e 12 dígitos).
* **Solução:**
1. **Exclusão por Formato:** Se a string capturada contiver `/0001` ou `/000`, descarte imediatamente.
2. **Exclusão por Tamanho:** Se `len(apenas_numeros) == 14`, descarte (a menos que você tenha certeza absoluta que existem UCs de 14 dígitos na sua base, o que é raro para CPFL/Raízen, que costumam usar códigos menores).



#### B. Datas (`DD/MM/AAAA`)

Datas geram sequências de 8 dígitos (ex: `25122023`) que são idênticas ao tamanho de uma UC padrão.

* **Padrão Visual:** Barras `/` ou hífens `-`.
* **Validação Lógica:** O ano (últimos 4 dígitos) ou o dia (primeiros 2) costumam quebrar a lógica de uma UC.
* **Solução (Regex Negativo):**
Use um *Negative Lookahead* ou uma verificação prévia. Se o regex de captura de UC pegar algo que, formatado, bata com `\d{2}/\d{2}/\d{4}`, ignore.
* *Exemplo:* O número `16022024` é capturado. Verifique: "Isso é uma data válida?". Se `16/02/2024` existe, assuma que é data e descarte, a menos que o contexto (âncora) diga explicitamente "Unidade Consumidora".



#### C. Percentuais e Monetários (`participacao_percentual`, `R$`)

* **Padrão Visual:** Presença de `%`, `R$`, ou vírgula decimal (`,`).
* **Solução:** UCs são inteiros. Se o número capturado estiver imediatamente seguido de `%` ou precedido de `R$`, é ruído.
* *Regex:* `\d+(?=%)` (captura números seguidos de percentual) -> **Adicione à lista de exclusão**.



#### D. CPF (`xxx.xxx.xxx-xx` ou 11 dígitos)

* **Risco:** CPFs desformatados têm 11 dígitos, tamanho muito comum para códigos de instalação.
* **Solução:** **Algoritmo de Validação Cruzada**.
1. Tente validar o número como CPF (algoritmo mod 11 de CPF). Se for um CPF válido, **descarte**. A chance de uma UC ser matematicamente um CPF válido é estatisticamente desprezível.
2. Busque âncoras próximas: Se a palavra "CPF" ou "Representante" estiver a menos de 20 pixels (no eixo Y ou X) do número, descarte.



---

### 2. Implementação em Python (Filtro de "Sanidade")

Aqui está uma função de limpeza robusta que você pode adicionar ao seu pipeline antes de tentar validar a UC.

```python
import re

def is_noise(value_str, context_text=""):
    """
    Retorna True se o valor for identificado como Ruído (CNPJ, Data, CPF, %, Monetário).
    """
    # Limpeza básica para análise
    clean_val = re.sub(r'\D', '', value_str)
    
    # 1. Filtro de CNPJ (14 dígitos ou padrão de formatação)
    if len(clean_val) == 14:
        return True # UCs da CPFL raramente têm 14 dígitos (geralmente até 12)
    if "/" in value_str or "0001" in value_str: # Padrão forte de CNPJ
        return True

    # 2. Filtro de CPF (11 dígitos) - Validação algorítmica
    # Se passar na validação de CPF, assumimos que é CPF e não UC
    if len(clean_val) == 11 and validate_cpf_algo(clean_val): 
        return True

    # 3. Filtro de Data (Formato DD/MM/AAAA ou DD/MM/AA)
    # Regex busca padrões como 12/05/2024 ou 12.05.24
    date_pattern = r'\b(?:0[1-9]|[1][0-9]|3[2])[\/\-\.](?:0[1-9]|1[0-2])[\/\-\.](?:19|20)\d{2}\b'
    if re.search(date_pattern, value_str):
        return True
    
    # 4. Filtro de Percentual e Monetário (Contexto Imediato)
    # Verifica se tem % logo depois ou R$ logo antes
    if "%" in value_str or re.search(r'R\$\s*'+re.escape(value_str), context_text):
        return True

    # 5. Filtro de Fidelidade/Prazos (Números pequenos isolados)
    # Se for um número < 1000 (ex: 12 meses, 30 dias), provavelmente não é UC
    if len(clean_val) < 4: 
        return True

    return False

# Função dummy para validação de CPF (você deve usar uma lib robusta ou sua própria implementação)
def validate_cpf_algo(numbers):
    # Implementar algoritmo Mod11 do CPF aqui
    # Retornar True se for um CPF matemático válido
    return False 

```

### 3. Dica de Ouro: Contexto Negativo (Stopwords)

No seu **Spatial Regex** ou **GMFT**, adicione uma lista de "Stopwords Espaciais". Se o número estiver alinhado verticalmente ou horizontalmente com estas palavras, ele é ignorado:

* **Stopwords:** `CNPJ`, `CPF`, `DATA`, `ASSINATURA`, `PRAZO`, `VIGÊNCIA`, `MESES`, `DIAS`, `MULTA`, `CARÊNCIA`, `PERFIL`, `POTÊNCIA`, `KW`.

**Exemplo de Lógica de Exclusão:**

> *"Se o candidato a UC for '12345678' mas a palavra 'CNPJ' estiver na mesma linha (mesmo Y) à esquerda, descarte."*

Essa abordagem combinada (Regex Negativo + Validação de CPF + Stopwords) deve elevar sua precisão para perto de 100%, eliminando a confusão com outros dados contratuais.