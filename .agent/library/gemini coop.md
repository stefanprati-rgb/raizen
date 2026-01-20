Para impedir que valores numéricos como CNPJs, datas e prazos sejam confundidos com Unidades Consumidoras (UCs), a estratégia mais robusta não é apenas melhorar a busca da UC, mas sim implementar um sistema agressivo de **Filtragem Negativa**.

O conceito central é: **"Se parece com outra coisa, assuma que não é uma UC"**. Como as UCs da CPFL são sequências numéricas arbitrarias (geralmente entre 8 e 12 dígitos), elas não possuem uma "cara" única, mas os dados concorrentes (datas, documentos, prazos) possuem padrões muito fortes que podemos usar para eliminá-los.

Aqui está a estratégia técnica e o código para blindar seu pipeline contra esses 6 casos específicos:

---

### 1. Estratégia de "Mascaramento Prévio" (Resolvendo o problema das partes do CNPJ)

O maior erro é tentar extrair a UC diretamente do texto sujo. Se você rodar um regex de 8 dígitos em `CNPJ: 17.352.251/0001-38`, você vai capturar `17352251` (os primeiros 8 dígitos).

**Solução:** Antes de buscar UCs, você deve **encontrar e "cegar"** os padrões de CPF e CNPJ no texto original.

* **Lógica:**
1. Localize padrões de CNPJ/CPF com pontuação ou 11/14 dígitos contínuos.
2. Substitua esses trechos por uma máscara (ex: ``).
3. Só então rode a busca de UCs no texto restante.



### 2. Validação Lógica (Resolvendo Datas e CPFs)

Para números que *parecem* UCs (ex: `16012025` tem 8 dígitos, igual a uma UC, mas é uma data), usamos validação lógica.

* **Datas (`data_adesao`):** Se um número de 8 dígitos puder ser convertido para uma data válida (dia 01-31, mês 01-12, ano 2000-2030), assumimos que é uma data e descartamos. A chance de uma UC coincidir exatamente com uma data válida recente é estatisticamente baixa e aceitável de descartar.
* **CPF (`representante_cpf`):** Se tem 11 dígitos, aplicamos o cálculo do Módulo 11 (dígito verificador). Se for um CPF matemático válido, descartamos.

### 3. Filtros de Contexto e Tamanho (Resolvendo Fidelidade, Percentual e Avisos)

* **Fidelidade/Aviso Prévio:** Geralmente são números pequenos ("12 meses", "30 dias").
* *Regra:* Rejeitar qualquer número com **menos de 7 dígitos**. (UCs da CPFL costumam ser maiores).


* **Participação (`participacao_percentual`):**
* *Regra:* Rejeitar se o caractere imediatamente seguinte for `%` ou se houver `R$` imediatamente antes.



---

### Implementação em Python

Aqui está uma função de filtragem (`is_noise`) pronta para ser inserida no seu loop de extração.

```python
import re
from datetime import datetime

# Instalar biblioteca leve para validar docs brasileiros se necessário
# pip install validate-docbr
from validate_docbr import CPF, CNPJ

def sanitize_text(text):
    """
    Passo 1: Mascaramento Prévio.
    Remove CNPJs e CPFs formatados ou longos para evitar que partes deles
    sejam capturadas como UCs errôneas.
    """
    # Regex para CNPJ formatado ou bloco de 14 dígitos
    text = re.sub(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', '', text)
    text = re.sub(r'\d{14}', '', text)
    
    # Regex para CPF formatado ou bloco de 11 dígitos
    text = re.sub(r'\d{3}\.\d{3}\.\d{3}-\d{2}', '', text)
    # Nota: Não mascaramos 11 dígitos puros cegamente aqui pois algumas UCs podem ter 11 dígitos.
    # Deixamos a validação de 11 dígitos para a função is_noise.
    return text

def is_noise(candidate_str, context_window=""):
    """
    Passo 2: Filtragem Negativa.
    Retorna True se o candidato for identificado como ruído (Data, CPF, Percentual, etc).
    """
    clean_val = re.sub(r'\D', '', candidate_str)
    
    # --- A. Filtro de Tamanho (Fidelidade, Aviso Prévio) ---
    # UCs da CPFL/Raízen geralmente têm entre 8 e 12 dígitos.
    # Números pequenos (12, 30, 60, 90) são descartados aqui.
    if len(clean_val) < 7 or len(clean_val) > 13:
        return True

    # --- B. Filtro de Datas (Data de Adesão) ---
    # Verifica se os 8 dígitos formam uma data válida (DDMMYYYY ou YYYYMMDD)
    if len(clean_val) == 8:
        try:
            # Tenta formato DDMMAAAA
            dt = datetime.strptime(clean_val, "%d%m%Y")
            # Se o ano for razoável (ex: contratos recentes), é data, não UC.
            if 2000 <= dt.year <= 2035: 
                return True
        except ValueError:
            pass # Não é data DDMMAAAA
            
        try:
            # Tenta formato AAAAMMDD (ISO)
            dt = datetime.strptime(clean_val, "%Y%m%d")
            if 2000 <= dt.year <= 2035:
                return True
        except ValueError:
            pass # Não é data

    # --- C. Filtro de CPF (Representante) ---
    # Se tiver 11 dígitos, verifica se é um CPF matemático válido.
    # UCs raramente satisfazem a regra do dígito verificador do CPF por coincidência.
    if len(clean_val) == 11:
        cpf_validator = CPF()
        if cpf_validator.validate(clean_val):
            return True

    # --- D. Filtro de Percentual e Monetário (Participação) ---
    # Olha o texto original do candidato. Se tiver "%" colado ou próximo.
    if "%" in candidate_str:
        return True
    
    # Verifica contexto (se fornecido)
    # Ex: se o texto ao redor for "Valor: R$ 17113911" -> Descarta
    if context_window:
        if "R$" in context_window or "%" in context_window:
            # Lógica simples: se R$ aparece até 5 chars antes
            if re.search(r'R\$\s*.{0,5}' + re.escape(candidate_str), context_window):
                return True

    return False

# --- Exemplo de Uso no Pipeline ---

raw_text = "O cliente CPF 123.456.789-00 assinou em 16012025 com fidelidade de 12 meses. CNPJ da Usina: 17.352.251/0001-38. UCs: 17113911 e 4001324252."

# 1. Sanitizar
safe_text = sanitize_text(raw_text)
# safe_text agora é: "... CPF assinou em 16012025... CNPJ da Usina:. UCs: 17113911 e 4001324252."
# Observe que o "17352251" (parte do CNPJ) sumiu, resolvendo o problema 4.1.

# 2. Extrair Candidatos (Regex amplo)
candidates = re.findall(r'\b\d{7,12}\b', safe_text)

# 3. Validar
valid_ucs =
for c in candidates:
    # Passamos uma janela de contexto simulada (na prática, pegue o texto ao redor do match)
    if not is_noise(c):
        valid_ucs.append(c)

print(f"Candidatos brutos: {candidates}")
print(f"UCs Validadas: {valid_ucs}")
# Resultado esperado: Apenas ['17113911', '4001324252']
# 16012025 (Data) -> Removido pelo filtro de data
# 12 (Fidelidade) -> Removido pelo regex (len < 7) ou filtro de tamanho

```

### Dica Adicional: Lista Negra de Frequência ("Blacklist Dinâmica")

Para resolver o problema dos **"Números Recorrentes"** (como o código da usina `160741512` que aparece em 49 de 50 documentos):

Não tente adivinhar o que é esse número. Use estatística.

1. Ao processar um lote de 100+ documentos, conte a frequência de todos os números extraídos.
2. Se um número aparece em mais de **80% dos documentos**, adicione-o automaticamente a uma `BLACKLIST_CODES`.
3. Rejeite qualquer candidato que esteja nessa lista.

Isso elimina códigos de formulário, telefones da ouvidoria (0800), CNPJs da distribuidora e códigos de usina sem que você precise mapeá-los manualmente um a um.