import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from scripts.apply_map import process_pdf_with_map
import json
from pathlib import Path

def test_map():
    map_path = "maps/CEMIG_11p_v1.json"
    pdf_path = "OneDrive_2026-01-06/TERMO DE ADESÃO/TERMO_ADESAO_0016105 - CASA FONSECA MATERIAIS DE CONSTRUCAO LTDA - Clicksign.pdf"
    
    with open(map_path, 'r', encoding='utf-8') as f:
        mapa = json.load(f)
        
    print(f"Testing {map_path} on {pdf_path}")
    result = process_pdf_with_map(pdf_path, mapa)
    
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_map()
