"""
Teste rápido da migração para PyMuPDF.
"""
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import fitz
from raizen_power.extraction.table_extractor import (
    open_pdf, extract_all_text_from_pdf, extract_tables_from_page_pdf
)

PDF_DIR = Path(r"c:\Projetos\Raizen\OneDrive_2026-01-06\TERMO DE ADESÃO")

def test_pymupdf_migration():
    """Testa se a migração para PyMuPDF está funcionando."""
    
    # Encontrar um PDF qualquer
    pdfs = list(PDF_DIR.glob("*.pdf"))[:3]
    
    if not pdfs:
        print("❌ Nenhum PDF encontrado para teste")
        return False
    
    print(f"Testando com {len(pdfs)} PDFs...")
    print("-" * 50)
    
    success = True
    
    for pdf_path in pdfs:
        print(f"\n📄 {pdf_path.name[:50]}...")
        
        try:
            with open_pdf(str(pdf_path)) as pdf:
                # Teste 1: Contar páginas
                pages = len(pdf)
                print(f"   Páginas: {pages}")
                
                # Teste 2: Extrair texto
                text = extract_all_text_from_pdf(pdf, max_pages=2, use_ocr_fallback=False)
                print(f"   Texto: {len(text)} chars")
                
                # Teste 3: Extrair tabelas
                tables = extract_tables_from_page_pdf(pdf, 0)
                print(f"   Tabelas pág 1: {len(tables)}")
                
                print(f"   ✅ OK")
                
        except Exception as e:
            print(f"   ❌ ERRO: {e}")
            success = False
    
    print("\n" + "-" * 50)
    if success:
        print("✅ MIGRAÇÃO PARA PYMUPDF FUNCIONANDO!")
    else:
        print("❌ HOUVE ERROS - VERIFICAR IMPLEMENTAÇÃO")
    
    return success

if __name__ == "__main__":
    test_pymupdf_migration()
