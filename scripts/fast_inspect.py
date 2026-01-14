import sys
from pathlib import Path
import pdfplumber

def fast_inspect(pdf_path: str):
    path = Path(pdf_path)
    if not path.exists():
        print(f"File not found: {pdf_path}")
        return

    print(f"🔍 INSPECTING: {path.name}")
    try:
        with pdfplumber.open(path) as pdf:
            print(f"Total Pages: {len(pdf.pages)}")
            for i in [0, 1, 2, len(pdf.pages)-1]:
                if i < len(pdf.pages):
                    page_text = pdf.pages[i].extract_text()
                    print(f"\n--- PAGE {i+1} ---")
                    print(page_text)
                    print("-" * 30)
    except Exception as e:
        print(f"Error reading PDF: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        fast_inspect(sys.argv[1])
    else:
        print("Usage: python scripts/fast_inspect.py <path_to_pdf>")
