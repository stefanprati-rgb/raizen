"""
Analyze sample empty PDFs - cleaner output version.
"""
import sys
sys.path.insert(0, 'scripts')

from pathlib import Path
import pdfplumber
import re

INVESTIGATION_DIR = Path('output/investigar_vazios')

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:3]:
                page_text = page.extract_text() or ""
                text += page_text + "\n"
    except Exception as e:
        text = f"ERROR: {e}"
    return text

def find_uc_patterns(text):
    patterns = [
        (r'(?:UC|Instala[çc][ãa]o|Conta\s*Contrato)[:\s]*(\d{7,12})', 'labeled'),
        (r'\b(40\d{8})\b', 'CPFL_40'),
        (r'\b(70\d{7})\b', 'CPFL_70'),
        (r'\b(71\d{7})\b', 'CPFL_71'),
    ]
    
    found = []
    for pattern, pattern_type in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            found.append((m, pattern_type))
    
    return list(set(found))

def main():
    categories = ['TERMO_ADESAO', 'SOLAR', 'TERMO_CONDICOES']
    
    for category in categories:
        cat_dir = INVESTIGATION_DIR / category
        if not cat_dir.exists():
            continue
            
        print(f"\n{'='*60}")
        print(f"CATEGORY: {category}")
        print('='*60)
        
        samples = list(cat_dir.glob("sample_*.pdf"))
        
        for sample in samples:
            print(f"\nFile: {sample.name[:55]}...")
            
            text = extract_text_from_pdf(sample)
            
            # Determine document type
            text_lower = text.lower()
            if 'condições comerciais' in text_lower or 'termo de condições' in text_lower:
                doc_type = "CONDITIONS (expected empty)"
            elif 'termo de adesão' in text_lower and 'procuração' in text_lower:
                doc_type = "ADHESION+PROCURACAO (should have UCs)"
            elif 'termo de adesão' in text_lower:
                doc_type = "ADHESION (should have UCs)"
            else:
                doc_type = "UNKNOWN"
            
            print(f"  Type: {doc_type}")
            
            # Find potential UCs
            potential_ucs = find_uc_patterns(text)
            if potential_ucs:
                print(f"  POTENTIAL UCs: {potential_ucs[:5]}")
            else:
                print(f"  No UC patterns found")
                
    print("\n" + "="*60)
    print("SUMMARY:")
    print("- CONDITIONS docs = Valid negatives (no UCs expected)")
    print("- ADHESION docs without UCs = Possible extraction failures")
    print("="*60)

if __name__ == "__main__":
    main()
