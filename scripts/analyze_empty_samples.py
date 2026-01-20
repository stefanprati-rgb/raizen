"""
Analyze sample empty PDFs to determine if they are valid negatives or extraction failures.
"""
import sys
sys.path.insert(0, 'scripts')

from pathlib import Path
import pdfplumber

INVESTIGATION_DIR = Path('output/investigar_vazios')

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using pdfplumber."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:5]:  # First 5 pages
                page_text = page.extract_text() or ""
                text += page_text + "\n"
    except Exception as e:
        text = f"ERROR: {e}"
    return text

def analyze_text_for_uc(text):
    """Check if text contains potential UC patterns."""
    import re
    # Common UC patterns
    patterns = [
        r'(?:UC|Instala[çc][ãa]o|Conta\s*Contrato)[:\s]*(\d{7,12})',
        r'\b(40\d{8})\b',  # CPFL pattern
        r'\b(\d{8,10})\b',  # Generic 8-10 digit
    ]
    
    found = []
    for p in patterns:
        matches = re.findall(p, text, re.IGNORECASE)
        found.extend(matches)
    
    return list(set(found))[:10]  # Unique, max 10

def main():
    categories = ['TERMO_ADESAO', 'SOLAR', 'TERMO_CONDICOES']
    
    for category in categories:
        cat_dir = INVESTIGATION_DIR / category
        if not cat_dir.exists():
            continue
            
        print(f"\n{'='*60}")
        print(f"CATEGORY: {category}")
        print('='*60)
        
        # Get sample PDFs
        samples = list(cat_dir.glob("sample_*.pdf"))
        
        for sample in samples:
            print(f"\n--- {sample.name[:50]}... ---")
            
            text = extract_text_from_pdf(sample)
            
            # Show first 500 chars
            preview = text[:500].replace('\n', ' ')
            print(f"Preview: {preview}...")
            
            # Check for UC patterns
            potential_ucs = analyze_text_for_uc(text)
            if potential_ucs:
                print(f"POTENTIAL UCs FOUND: {potential_ucs}")
            else:
                print("No UC patterns detected.")
            
            # Check if it's a conditions document
            if 'condições comerciais' in text.lower() or 'termo de condições' in text.lower():
                print("TYPE: Conditions Document (valid negative)")
            elif 'termo de adesão' in text.lower() or 'procuração' in text.lower():
                print("TYPE: Adhesion Term (should have UCs)")
                
    print("\n" + "="*60)
    print("ANALYSIS COMPLETE")

if __name__ == "__main__":
    main()
