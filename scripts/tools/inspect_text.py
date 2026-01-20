import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path.cwd()))

from src.extrator_contratos.table_extractor import open_pdf, extract_all_text_from_pdf

PDF_PATH = Path("OneDrive_2026-01-06/TERMO DE ADESÃO/TERMO_ADESAO_0016105 - CASA FONSECA MATERIAIS DE CONSTRUCAO LTDA - Clicksign.pdf")

print("🔍 INSPECTING TEXT")
with open_pdf(str(PDF_PATH)) as pdf:
    # Get text from page 2 (distribuidora, duracao) and page 6 (date)
    text = extract_all_text_from_pdf(pdf, use_ocr_fallback=True)

print(f"RAW TEXT LEN: {len(text)}")
print("=" * 60)
print(text)
print("=" * 60)
