import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path.cwd()))

from src.extrator_contratos.table_extractor import open_pdf, extract_all_text_from_pdf
from scripts.apply_map import extract_with_map

MAP_FILE = "CEMIG_11p_v1.json"
PDF_FILE = "TERMO_ADESAO_0016105 - CASA FONSECA MATERIAIS DE CONSTRUCAO LTDA - Clicksign.pdf"

MAP_PATH = Path(f"maps/{MAP_FILE}")
# Caminho do PDF (ajuste se necessário)
PDF_PATH = Path("data/raw/OneDrive_2026-01-06/TERMO DE ADESÃO") / PDF_FILE

print(f"VALIDANDO MAPA: {MAP_PATH.name}")
print(f"PDF: {PDF_PATH.name}")
print("=" * 60)

if not MAP_PATH.exists():
    print("❌ Mapa não encontrado!")
    sys.exit(1)

if not PDF_PATH.exists():
    print("❌ PDF não encontrado!")
    sys.exit(1)

# Load Map
with open(MAP_PATH, 'r', encoding='utf-8') as f:
    mapa = json.load(f)

# Extract Text
print("⏳ Extraindo texto dp PDF...")
with open_pdf(str(PDF_PATH)) as pdf:
    text = extract_all_text_from_pdf(pdf, use_ocr_fallback=False)

# Apply Map
print("🔍 Aplicando mapa...")
dados = extract_with_map(text, mapa)

# Show Results
found_count = 0
print("\nRESULTADOS:")
for k, v in dados.items():
    status = "✅" if v else "❌"
    if v: found_count += 1
    print(f"   {status} {k:<25}: {v}")

print("-" * 60)
print(f"Campos encontrados: {found_count}/{len(dados)}")

if found_count > 5:
    print("\n✅ SUCESSO! O mapa parece estar funcionando.")
else:
    print("\n⚠️ AVISO: Poucos campos encontrados. Verifique o regex.")
