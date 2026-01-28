"""
Script simplificado: Cole o JSON do Gemini e execute.
"""
import json
from pathlib import Path
import re

MAPS_DIR = Path("maps")
MAPS_DIR.mkdir(exist_ok=True)

# COLE SEU JSON AQUI (substitua tudo entre as aspas triplas):
JSON_INPUT = """

"""

def process():
    if not JSON_INPUT.strip():
        print("Cole o JSON do Gemini no script primeiro!")
        return
        
    try:
        data = json.loads(JSON_INPUT)
        if isinstance(data, dict):
            data = [data]
            
        for item in data:
            model_id = item.get("modelo_identificado", "")
            match = re.search(r'\[(.*?)\]', model_id)
            cluster_key = match.group(1) if match else "UNKNOWN"
            
            filename = f"{cluster_key}_v1.json"
            filepath = MAPS_DIR / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(item, f, indent=4, ensure_ascii=False)
                
            print(f"[OK] {filename}")
            
        print(f"\nTotal: {len(data)} mapas salvos!")
        
    except Exception as e:
        print(f"[ERRO] {e}")

if __name__ == "__main__":
    process()
