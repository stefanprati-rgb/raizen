# Desafio Técnico: Extração de UCs em Contratos CPFL

## 1. Contexto do Problema

Nos contratos de energia da CPFL Paulista/Raízen Power, existem **dois campos numéricos distintos** que são facilmente confundidos:

| Campo | Descrição | Formato | Exemplo |
|-------|-----------|---------|---------|
| **Nº da Instalação (UC)** | Código do ponto físico de consumo | 7-8 dígitos ou 40XXXXXXXX | `8252556`, `4002756478` |
| **Nº do Cliente** | Código do cadastro do titular | 9 dígitos, prefixo 70/71 | `713508533`, `715792165` |

**O objetivo é extrair apenas o "Nº da Instalação"**, que é a verdadeira Unidade Consumidora (UC).

---

## 2. Estrutura dos Documentos

### 2.1 Layout Típico de um Contrato CPFL

```
TERMO DE ADESÃO AO CONSÓRCIO

QUEM SÃO AS PARTES?

1.1 CONSORCIADO
    Razão Social: EMPRESA XYZ LTDA
    CNPJ: 12.345.678/0001-90
    
    Nº do Cliente: 713508533          ← IGNORAR (não é UC)
    Nº da Instalação: 8252556         ← EXTRAIR (é a UC real)
```

### 2.2 Problema Visual

No PDF, os dois campos aparecem **próximos** e **com formato similar**:

```
Nº do Cliente: 713508533
Nº da Instalação da Unidade Consumidora: 8252556
```

Um regex simples como `\d{7,10}` captura **ambos**, gerando falsos positivos.

---

## 3. Análise de Padrões Numéricos

### 3.1 Padrões Identificados na Validação

| Tipo | Padrão | Dígitos | Exemplos |
|------|--------|---------|----------|
| **Instalação (UC)** | Variado | 7-8 | `8252556`, `17316847`, `36339962` |
| **Instalação (UC)** | `40XXXXXXXX` | 10 | `4002756478`, `4001499053` |
| **Cliente** ❌ | `70XXXXXXX` | 9 | `701527704`, `704375485` |
| **Cliente** ❌ | `71XXXXXXX` | 9 | `713508533`, `715792165` |

### 3.2 Regra de Ouro

> **Números de 9 dígitos começando com 70 ou 71 são SEMPRE "Nº do Cliente", NUNCA são UCs.**

---

## 4. Desafio de Recall

### 4.1 Problema Atual

O filtro de "Nº do Cliente" (70/71) está funcionando corretamente, mas alguns documentos ficam **sem nenhuma UC** porque:

1. O regex de "Instalação" não está capturando UCs de 7 dígitos
2. O contexto textual é variável entre documentos

### 4.2 Exemplos de Falha de Recall

| Documento | UC Correta (Gemini) | UC Extraída (Pipeline) | Problema |
|-----------|---------------------|------------------------|----------|
| Doc 06 - Lanchonete Tojur | `8252556` | `713508533` ❌ | Capturou Cliente, não Instalação |
| Doc 09 - GHCO | `8152551` | `716818857` ❌ | Capturou Cliente, não Instalação |
| Doc 10 - FARAH BITTAR | `9027076` | `715458369` ❌ | Capturou Cliente, não Instalação |

Após aplicar o filtro 70/71, esses documentos ficam com **0 UCs** porque a Instalação real não foi capturada.

### 4.3 Causa Raiz

O padrão regex de contexto "Instalação" é:
```python
r'(?:N[ºo°]\s*(?:da\s+)?Instalação|Instalação|Código\s+(?:da\s+)?(?:UC|Instalação))\s*[:\-]?\s*(\d{7,10})'
```

**O problema:** O texto extraído do PDF pode ter:
- Quebras de linha entre o label e o número
- Caracteres especiais não tratados
- Variações de grafia ("Instalação" vs "Instalação da Unidade Consumidora")

---

## 5. Soluções Propostas

### 5.1 Solução A: Expandir Regex de Contexto

Adicionar mais variações do label "Instalação":
```python
CONTEXT_PATTERNS = [
    (r'Instalação\s*(?:da\s+)?(?:Unidade\s+)?(?:Consumidora)?[:\s]*(\d{7,10})', 0.98, 'instalacao'),
    (r'Nº\s+da\s+Instalação[:\s]*(\d{7,10})', 0.98, 'instalacao'),
    (r'(?:UC|U\.C)\s*[:\-]?\s*(\d{7,10})', 0.95, 'label_uc'),
]
```

### 5.2 Solução B: Abordagem por Exclusão

Em vez de capturar por contexto positivo, capturar **todos os números 7-10 dígitos** e filtrar:

```python
def is_valid_uc(num):
    # Excluir Nº do Cliente
    if len(num) == 9 and num.startswith(('70', '71')):
        return False
    # Excluir CNPJs, CPFs, datas...
    return True
```

### 5.3 Solução C: Busca em Duas Passadas

1. **Passada 1:** Extrair com regex de alta confiança ("Instalação:")
2. **Passada 2:** Se não encontrou nada, buscar qualquer número 7-10 dígitos, excluindo 70/71

---

## 6. Trade-offs

| Abordagem | Precisão | Recall | Complexidade |
|-----------|----------|--------|--------------|
| Regex rígido (atual) | Alta (~95%) | Baixa (~70%) | Baixa |
| Regex expandido | Alta (~90%) | Média (~85%) | Média |
| Exclusão + fallback | Média (~80%) | Alta (~95%) | Alta |

---

## 7. Métricas de Validação

Baseado na amostra de 20 documentos validados com Gemini:

### 7.1 Antes do Filtro 70/71 (V3)
- **Precisão:** 56.7%
- **Recall:** 100%
- **Problema:** Muitos falsos positivos (Nº do Cliente)

### 7.2 Após Filtro 70/71 (V4)
- **Precisão:** ~90%
- **Recall:** ~70%
- **Problema:** Alguns docs sem UC (regex não captura instalação)

### 7.3 Meta
- **Precisão:** ≥95%
- **Recall:** ≥95%

---

## 8. Próximos Passos Recomendados

1. **Investigar textos dos docs problemáticos** (06, 09, 10) para entender por que o regex falha
2. **Expandir padrões de contexto** para capturar mais variações de "Instalação"
3. **Implementar fallback:** Se não encontrou instalação, buscar números 7-8 dígitos (excluindo 70/71)
4. **Re-validar** com Gemini após ajustes

---

## 9. Código Atual do Filtro

```python
# Filtro 6: "Nº do Cliente" - NUNCA é UC!
# Números de 9 dígitos começando com 70 ou 71 são SEMPRE códigos de cliente
# na distribuidora CPFL, não são códigos de instalação (UC)
if len(uc) == 9 and uc.startswith(('70', '71')):
    continue
```

Este filtro está **correto e validado**. O desafio restante é melhorar o **recall** sem perder precisão.
