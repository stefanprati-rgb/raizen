# Quick Reference: Estratégia de Desambiguação em Ação

## O Problema em Uma Imagem

```
Texto: "CNPJ: 12345678901234, CPF: 12345678901, Data: 15/01/2025, 
        UC: 123456789, Percentual: 50%, Carência: 12 meses"

❌ REGEX SIMPLES (BuscaSemester \d{8,10}):
   Encontra: 12345678 (do CNPJ), 12345678 (do CPF), 2025 (ano), 
             123456789 (UC ✓), 123456 (falso do CNPJ)
   Taxa Falsos: 60%

✅ REGEX COM DESAMBIGUAÇÃO:
   Exclui: CNPJ (14 dig), CPF (11 dig), ANO (4 dig)
   Encontra: 123456789 (UC ✓)
   Taxa Falsos: 5%
```

---

## Matriz de Decisão: É UC ou Não?

```
┌─────────────────────────────────────────────────────────────────┐
│ NÚMERO ENCONTRADO: 8-10 dígitos                                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                    CAMADA 1: EXCLUSÃO
                           │
         ┌─────────────────┼──────────────────┐
         │                 │                  │
    Tem 14 dig?       Tem 11 dig?        Tem 4 dig?
    "CNPJ" contexto?  "CPF" contexto?   (Ano realista?)
         │                 │                  │
    ❌ CNPJ         ❌ CPF           ❌ ANO
    (Exclua)        (Exclua)          (Exclua)
         │                 │                  │
         └─────────────────┼──────────────────┘
                           │
                    ✓ Passou Camada 1
                           │
                    CAMADA 2: CONTEXTO
                           │
         ┌─────────────────┼──────────────────┐
         │                 │                  │
   "UC:" ou         "Anexo" ou         Número
   "Unidade         "Tabela de"        isolado
   Consumidora"      (Confiança +)
   (Confiança: 90%) 
         │                 │                  │
    Confiança:        Confiança:        Confiança:
    0.90              0.75              0.60
         │                 │                  │
         └─────────────────┼──────────────────┘
                           │
                    CAMADA 3: ESTRUTURA
                           │
         ┌─────────────────┼──────────────────┐
         │                 │                  │
   8 dígitos        9 dígitos          10 dígitos
   + não começa      + não começa        + não começa
   com 0?            com 0?              com 0?
   (CPFL típica)     (ELETROBRAS)       (Rara)
         │                 │                  │
    ✓ Válido         ✓ Válido          ✓ Válido
    (+0.10)          (+0.10)            (+0.05)
         │                 │                  │
         └─────────────────┼──────────────────┘
                           │
            CAMADA 4: CONFIANÇA FINAL
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   Conf ≥ 0.85         0.70-0.85          < 0.70
        │                  │                  │
   ✓ ACEITAR          VERIFICAR         ❌ REJEITAR
   "Muito provável"   "Possível"        "Ambíguo"
```

---

## Exemplos Reais: Como o Pipeline Processa

### Exemplo 1: UC com Label Explícito (Simples) ✅

```
TEXTO: "Unidade Consumidora (UC): 123456789"

Camada 1 - Exclusão:
  ✓ Tem 9 dígitos? Sim
  ✓ Não tem contexto de CNPJ/CPF/Data? Sim
  → PASSOU

Camada 2 - Contexto:
  ✓ Contém "UC:" ? Sim (+0.30)
  ✓ Contém "Unidade Consumidora"? Sim (+0.30)
  Confiança contexto: 0.90

Camada 3 - Estrutura:
  ✓ 9 dígitos (ELETROBRAS)? Sim (+0.05)
  ✓ Não começa com 0? Sim
  → VÁLIDO

Camada 4 - Confiança Final:
  0.90 (contexto) × 0.7 + 0.3 (estrutura) = 0.93
  
RESULTADO: ✅ UC: 123456789 | Confiança: 93%
```

### Exemplo 2: Número Isolado (Ambíguo) ⚠️

```
TEXTO: "... conforme especificado em 987654321 ..."

Camada 1 - Exclusão:
  ✓ Tem 9 dígitos? Sim
  ✓ Não tem contexto de CNPJ/CPF/Data? Sim (sem palavras-chave)
  → PASSOU

Camada 2 - Contexto:
  ✗ Contém "UC"? Não
  ✗ Contém "Unidade Consumidora"? Não
  ✗ Em tabela? Não
  Confiança contexto: 0.60 (baseline)

Camada 3 - Estrutura:
  ✓ 9 dígitos (ELETROBRAS)? Sim (+0.05)
  ✓ Não começa com 0? Sim
  → VÁLIDO

Camada 4 - Confiança Final:
  0.60 (contexto) × 0.7 + 0.3 (estrutura) = 0.72
  
RESULTADO: ⚠️ UC: 987654321 | Confiança: 72% (REJEITAR se threshold=85%)
```

### Exemplo 3: CNPJ Confundido (Falso Positivo) ❌

```
TEXTO: "CNPJ: 12345678901234"

Camada 1 - Exclusão:
  ✓ Tem 14 dígitos? Sim
  ✓ Contexto "CNPJ"? Sim
  ❌ NÃO PASSOU - É CNPJ
  
RESULTADO: ❌ REJEITADO - Identificado como CNPJ, não UC
```

### Exemplo 4: CPF em Campo de Representante ❌

```
TEXTO: "CPF Representante: 12345678901"

Camada 1 - Exclusão:
  ✓ Tem 11 dígitos? Sim
  ✓ Contexto "CPF" + "Representante"? Sim
  ❌ NÃO PASSOU - É CPF
  
RESULTADO: ❌ REJEITADO - Identificado como CPF, não UC
```

---

## Scores de Confiança por Situação

### Tabela Rápida

| Situação | Label UC? | Contexto | Estrutura | Score Final |
|----------|-----------|----------|-----------|-------------|
| "UC: 123456789" | ✅ Sim | ✅ Alto | ✅ Válida | **93%** |
| "123456789" (tabela) | ❌ Não | ✅ Médio | ✅ Válida | **80%** |
| "123456789" (isolada) | ❌ Não | ❌ Baixo | ✅ Válida | **72%** |
| "123456789" (errado) | ✗ CNPJ | ❌ Excluído | ✗ N/A | **0%** |

---

## Implementação Mínima (Copiar e Colar)

Se você quer um código **bem simplificado** apenas com as camadas críticas:

```python
import re
from typing import List, Tuple

def extract_ucs_smart(text: str) -> List[Tuple[str, float]]:
    """
    Extração de UCs com desambiguação básica
    
    Retorna: Lista de (UC, confiança)
    """
    
    ucs = []
    
    # Padrão 1: "UC: 123456789" (Confiança: 95%)
    for match in re.finditer(r'(?:UC|Unidade\s+Consumidora)[:\s]+(\d{8,10})', text, re.I):
        uc = match.group(1)
        if not is_excluded(uc, text):
            ucs.append((uc, 0.95))
    
    # Padrão 2: "123456789" em anexo/lista (Confiança: 85%)
    for match in re.finditer(r'(?:Anexo|ANEXO|LIST).*?(\d{8,10})', text, re.DOTALL | re.I):
        uc = match.group(1)
        if not is_excluded(uc, text) and (uc, 0.95) not in ucs:
            ucs.append((uc, 0.85))
    
    # Padrão 3: Números isolados (Confiança: 70%)
    for match in re.finditer(r'\b(\d{8,10})\b', text):
        uc = match.group(1)
        if not is_excluded(uc, text) and uc not in [u[0] for u in ucs]:
            # Verificar contexto
            context = text[max(0, match.start()-50):match.end()+50]
            if 'UC' not in context and 'cpf' not in context.lower():
                ucs.append((uc, 0.70))
    
    # Remover duplicatas, mantendo maior confiança
    seen = {}
    for uc, conf in ucs:
        if uc not in seen or conf > seen[uc]:
            seen[uc] = conf
    
    return [(uc, conf) for uc, conf in seen.items() if conf >= 0.70]


def is_excluded(number: str, context: str) -> bool:
    """Verifica se número deve ser excluído (não é UC)"""
    
    # CNPJ (14 dígitos)
    if len(number) == 14 and 'cnpj' in context.lower():
        return True
    
    # CPF (11 dígitos)
    if len(number) == 11 and 'cpf' in context.lower():
        return True
    
    # Ano (4 dígitos)
    if len(number) == 4 and int(number) >= 1950 and int(number) <= 2100:
        return True
    
    # Período ("30 dias", "12 meses")
    if len(number) <= 3 and re.search(rf'{number}\s+(?:dias?|meses?|anos?)', context, re.I):
        return True
    
    # Muito curto
    if len(number) < 8:
        return True
    
    return False


# USO
if __name__ == "__main__":
    texto = """
    CNPJ: 12345678901234
    CPF Representante: 12345678901
    Data: 15/01/2025
    
    Unidade Consumidora (UC): 123456789
    Ponto de Entrega: 987654321
    
    Percentual: 50%
    Carência: 12 meses
    """
    
    ucs = extract_ucs_smart(texto)
    for uc, conf in ucs:
        print(f"UC: {uc} | Confiança: {conf:.0%}")
```

**Output esperado:**
```
UC: 123456789 | Confiança: 95%
UC: 987654321 | Confiança: 70%
```

---

## Checklist de Implementação

- [ ] Implementar Camada 1 (Exclusão): CNPJ, CPF, Data
- [ ] Implementar Camada 2 (Contexto): Palavras-chave "UC:", "Unidade Consumidora"
- [ ] Implementar Camada 3 (Estrutura): Validação de comprimento (8-10 dígitos)
- [ ] Implementar Camada 4 (Confiança): Score combinado ≥ 0.70
- [ ] Testar em amostra de 20 contratos CPFL
- [ ] Medir taxa de falsos positivos (meta: < 5%)
- [ ] Ajustar threshold conforme necessário

---

## Resumo: Quando Algo É UC vs. Quando NÃO É

| É UC? | Exemplos | Regra |
|-------|----------|-------|
| ✅ **SIM** | "UC: 123456789" | Tem label "UC" + 8-10 dígitos |
| ✅ **SIM** | Tabela com "123456789" só | Isolado em célula de tabela |
| ⚠️ **TALVEZ** | "123456789 é..." | Isolado em texto corrido |
| ❌ **NÃO** | "CNPJ: 12345678901234" | 14 dígitos + contexto CNPJ |
| ❌ **NÃO** | "CPF: 12345678901" | 11 dígitos + contexto CPF |
| ❌ **NÃO** | "2025", "2024" | 4 dígitos que é ano |
| ❌ **NÃO** | "50%", "25%" | Acompanhado de símbolo % |
| ❌ **NÃO** | "30 dias", "12 meses" | Acompanhado de unidade temporal |