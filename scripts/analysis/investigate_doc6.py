import fitz
import re

path = 'cpfl_paulista_por_tipo/TERMO_ADESAO/10_paginas/TERMO_ADESAO_0037764 - Lanchonete Tojur Eurelli - 55935134000196.docx - Clicksign.pdf'
doc = fitz.open(path)

print("=== INVESTIGANDO DOC 06 ===")
print()

# Pattern de instalacao (o que deveria capturar)
pattern_instalacao = r'(?:N[ºo°]\s*(?:da\s+)?Instalação|Instalação|Código\s+(?:da\s+)?(?:UC|Instalação))\s*[:\-]?\s*(\d{7,10})'

for i, page in enumerate(doc):
    text = page.get_text()
    
    # Buscar todas as ocorrências de "Instalação" 
    if 'nstalação' in text.lower() or 'instalacao' in text.lower():
        print(f"=== PÁGINA {i} ===")
        for line in text.split('\n'):
            if 'nstalação' in line.lower() or 'instalacao' in line.lower():
                print(f"  {line.strip()[:100]}")
        
        # Testar pattern
        matches = re.findall(pattern_instalacao, text, re.IGNORECASE)
        if matches:
            print(f"  -> Pattern encontrou: {matches}")
        print()
    
    # Buscar o número correto
    if '8252556' in text:
        print(f"  -> Número 8252556 EXISTE na página {i}!")
        # Mostrar contexto
        idx = text.find('8252556')
        print(f"  Contexto: ...{text[max(0,idx-50):idx+20]}...")
