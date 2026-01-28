"""
Teste de um PDF específico para debug.
"""
import sys
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, str(Path(__file__).parent))

from extrator_contratos.table_extractor import extract_all_text
import re

PDF_DIR = Path(r"c:\Projetos\Raizen\data\raw\OneDrive_2026-01-06\TERMO DE ADESÃO")

# Testar TERMO ADESAO específico
pdf_path = PDF_DIR / "TERMO ADESAO 0013222 - AUTO POSTO E SERVICO MJM DE MARICA LTDA - 07604073Clicksign.pdf"

text = extract_all_text(str(pdf_path), max_pages=3)

# Salvar texto para análise
Path("debug_text.txt").write_text(text[:15000], encoding='utf-8')
print("Texto salvo em debug_text.txt")

# Testar regex de CNPJ
print("\n--- Testando padrões de CNPJ ---")
patterns = [
    r'CNPJ:\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})',
    r'CNPJ/MF\s*n[º°]:?\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})',
    r'CNPJ\s*n?[º°]?:?\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})',
    r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})',  # Capturar qualquer CNPJ formatado
]

for pattern in patterns:
    matches = re.findall(pattern, text, re.IGNORECASE)
    if matches:
        print(f"Padrão: {pattern[:50]}...")
        print(f"  Matches: {matches[:3]}")
