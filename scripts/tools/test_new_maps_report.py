import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path.cwd()))

from src.extrator_contratos.table_extractor import open_pdf, extract_all_text_from_pdf
from scripts.apply_map import extract_with_map, normalize_all

MAPS_DIR = Path("maps")
FILES_DIR = Path("output/revisao_manual_gemini")

NEW_MAPS = [
    "DISTRATO_CPFL_v1.json",
    "DISTRATO_CEMIG_v1.json",
    "CEMIG_Aditivo_Condicoes_Comerciais_v1.json",
    "CEMIG_Aditivo_Condicoes_V2_v1.json",
    "CEMIG_Aditivo_2_Termo_v1.json"
]

results = []

for map_name in NEW_MAPS:
    map_path = MAPS_DIR / map_name
    if not map_path.exists():
        results.append({"map": map_name, "status": "NOT_FOUND", "matches": []})
        continue
        
    with open(map_path, 'r', encoding='utf-8') as f:
        mapa = json.load(f)
    
    map_result = {
        "map": map_name,
        "modelo": mapa.get('modelo_identificado'),
        "status": "OK",
        "matches": []
    }
    
    # Try all files in the folder to see which one matches best
    for pdf_file in FILES_DIR.glob("*.pdf"):
        try:
            with open_pdf(str(pdf_file)) as pdf:
                # Limit content for speed, these serve for 5 pages max anyway
                text = extract_all_text_from_pdf(pdf, max_pages=5, use_ocr_fallback=False)
                
            dados = extract_with_map(text, mapa)
            
            # Check if critical fields were found
            found_count = sum(1 for v in dados.values() if v)
            if found_count >= 3: # Threshold to consider as "matched"
                map_result["matches"].append({
                    "file": pdf_file.name,
                    "fields_found": found_count,
                    "data": {k: v for k, v in dados.items() if v}
                })
        except Exception as e:
            pass
    
    results.append(map_result)

# Save results
output_path = Path("scripts/validation_results.json")
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"Resultados salvos em: {output_path}")
print(f"Total de mapas testados: {len(results)}")
for r in results:
    match_count = len(r.get('matches', []))
    print(f"  - {r['map']}: {match_count} match(es)")
