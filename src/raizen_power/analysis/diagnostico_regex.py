"""
Diagnostico de Regex - testa padroes contra texto real dos PDFs
"""
import sys
import re
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.extrator_contratos.table_extractor import open_pdf, extract_all_text_from_pdf

# Campos criticos e regex alternativas para testar
REGEX_ALTERNATIVAS = {
    'cnpj': [
        r'CNPJ[:\s]*(\d{2,3}\.\d{3}\.\d{3}/\d{4}-\d{2})',  # Original
        r'CNPJ(?:/MF)?[:\s]*(\d{2,3}\.\d{3}\.\d{3}/\d{4}-\d{2})',  # Com /MF
        r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})',  # Somente CNPJ formatado
    ],
    'num_cliente': [
        r'(?:consumidora\s*\(UC\)|UC|Conta\s*Contrato)[:\s]*(\d{6,12})',  # Original
        r'UC[:\s]*(\d{6,15})',  # Mais simples
        r'unidade\s*consumidora[:\s]*(\d{6,15})',  # Por extenso
        r'(?:UC|N[o°]\s*UC)[:\s]*(\d{5,15})',  # Variantes
    ],
    'representante_nome': [
        r'Assinado\s*por[:\s]*([A-ZÁÉÍÓÚÃÕÂÊÎÔÛÇ\s]+)',  # Original
        r'Assinado\s+(?:digitalmente\s+)?por[:\s]*([A-Za-z\s]+)',  # Com digitalmente
        r'(?:Representante|Procurador)[:\s]*([A-ZÁÉÍÓÚÃÕÂÊÎÔÛÇ][a-zA-Z\s]+)',
    ],
}


def testar_pdf(pdf_path, campos_regex):
    """Testa multiplas regex em um PDF."""
    print(f"\n{'='*60}")
    print(f"PDF: {Path(pdf_path).name[:50]}...")
    print('='*60)
    
    with open_pdf(str(pdf_path)) as pdf:
        text = extract_all_text_from_pdf(pdf, max_pages=6, use_ocr_fallback=False)
    
    print(f"Chars: {len(text)}")
    
    for campo, regex_list in campos_regex.items():
        print(f"\n{campo.upper()}:")
        encontrado = False
        
        for i, regex in enumerate(regex_list):
            try:
                match = re.search(regex, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    print(f"  [OK] Regex {i+1}: '{match.group(1)[:40]}'")
                    encontrado = True
                    break
                else:
                    # Mostrar contexto onde deveria estar
                    pass
            except Exception as e:
                print(f"  [ERR] Regex {i+1}: {e}")
        
        if not encontrado:
            print(f"  [X] Nenhuma regex funcionou")
            # Buscar contexto
            if campo == 'cnpj':
                # Procurar qualquer CNPJ no texto
                all_cnpjs = re.findall(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', text)
                if all_cnpjs:
                    print(f"      CNPJs encontrados no texto: {all_cnpjs[:3]}")
                else:
                    print("      Nenhum CNPJ formatado encontrado no texto")
            
            elif campo == 'num_cliente':
                # Procurar UC no texto
                uc_context = re.search(r'.{0,30}UC.{0,50}', text, re.IGNORECASE)
                if uc_context:
                    ctx = uc_context.group(0).replace('\n', ' ')
                    print(f"      Contexto UC: '{ctx}'")
            
            elif campo == 'representante_nome':
                # Procurar Assinado no texto
                assinado_context = re.search(r'.{0,20}Assinado.{0,60}', text, re.IGNORECASE)
                if assinado_context:
                    ctx = assinado_context.group(0).replace('\n', ' ')
                    print(f"      Contexto Assinado: '{ctx}'")


def main():
    # Pegar alguns PDFs de diferentes distribuidoras
    pastas_teste = [
        Path('contratos_por_paginas/05_paginas/CEMIG'),
        Path('contratos_por_paginas/05_paginas/CPFL'),
        Path('contratos_por_paginas/05_paginas/ENEL'),
    ]
    
    print("DIAGNOSTICO DE REGEX")
    print("Testando padroes contra PDFs reais...")
    
    for pasta in pastas_teste:
        if pasta.exists():
            pdfs = list(pasta.glob('*.pdf'))[:2]  # 2 PDFs por pasta
            for pdf in pdfs:
                testar_pdf(pdf, REGEX_ALTERNATIVAS)
    
    print("\n" + "="*60)
    print("CONCLUSAO")
    print("="*60)
    print("Se nenhuma regex funcionou, precisa adaptar o padrao")
    print("Se regex alternativa funcionou, atualizar o mapa")


if __name__ == "__main__":
    main()
