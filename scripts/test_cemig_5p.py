import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from scripts.apply_map import process_pdf_with_map
import json

def test_map():
    map_path = "maps/CEMIG_05p_v1.json"
    pdf_path = "output/pdfs_problematicos_v2/02_CEMIG_5p_PROBLEMA.pdf"
    
    with open(map_path, 'r', encoding='utf-8') as f:
        mapa = json.load(f)
        
    print(f"Testing {map_path}")
    result = process_pdf_with_map(pdf_path, mapa)
    
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_map()
