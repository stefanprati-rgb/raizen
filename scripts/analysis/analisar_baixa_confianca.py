"""
Analisa os casos de baixa confiança para identificar padrões de falha.
"""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.extrator_contratos.table_extractor import open_pdf, extract_all_text_from_pdf

# PDFs problemáticos (da revisão do CEMIG)
problematicos = [
    r"contratos_por_paginas\05_paginas\CEMIG\SOLAR 70235 - TEREZA CRISTINA_ADT CONDICOES - 00416967000159 - Qualisign.pdf",
    r"contratos_por_paginas\05_paginas\CEMIG\SOLAR 9119 - AUTO POSTO A2 LTDA - 19439445000109.pdf",
]

campos_regex = {
    'CNPJ': r'CNPJ[:\s]*([\d]{2}[\.\d/\-]+)',
    'UC': r'(?:UC|unidade\s+consumidora)[:\s]*(\d{6,15})',
    'Instalacao': r'(?:instala[cç][aã]o|N[o°]\s*instala[cç][aã]o)[:\s]*(\d{6,12})',
    'Razao Social': r'Raz[aã]o\s*Social[:\s]*([A-Za-z\s\-\.,]+?)(?=\s*CNPJ|\s*sede|\n)',
    'Participacao': r'(?:Participa[cç][aã]o|rateio)[:\s]*([\d,]+)\s*%',
}

print("=" * 70)
print("ANALISE DE CASOS DE BAIXA CONFIANCA")
print("=" * 70)

for pdf_path in problematicos:
    path = Path(pdf_path)
    if not path.exists():
        print(f"\n[X] Arquivo nao encontrado: {path.name}")
        continue
    
    print(f"\n{'='*70}")
    print(f"[PDF] {path.name[:60]}...")
    print("=" * 70)
    
    try:
        with open_pdf(str(path)) as pdf:
            text = extract_all_text_from_pdf(pdf, max_pages=5, use_ocr_fallback=False)
        
        print(f"Caracteres extraidos: {len(text)}")
        print()
        
        # Testar cada regex
        print("TESTE DE REGEX:")
        for campo, regex in campos_regex.items():
            match = re.search(regex, text, re.IGNORECASE | re.MULTILINE)
            if match:
                print(f"  [OK] {campo}: '{match.group(1)[:50]}'")
            else:
                print(f"  [X]  {campo}: NAO ENCONTRADO")
        
        # Mostrar contexto
        print()
        print("PRIMEIROS 600 CHARS DO PDF:")
        print("-" * 40)
        texto_limpo = text[:600].replace('\n', ' ').encode('ascii', 'ignore').decode('ascii')
        print(texto_limpo)
        print("-" * 40)
        
        # Verificar se é um ADITIVO
        if 'ADITIVO' in text.upper() or 'ADT' in path.name.upper():
            print()
            print("[!] NOTA: Este parece ser um ADITIVO, nao um termo original!")
        
    except Exception as e:
        print(f"[X] Erro ao processar: {e}")

print()
print("=" * 70)
print("CONCLUSAO")
print("=" * 70)
print("Casos de baixa confianca geralmente sao:")
print("1. Aditivos (estrutura diferente do termo original)")
print("2. PDFs com OCR ruim ou formatacao nao-padrao")
print("3. Modelos novos que precisam de mapa especifico")
