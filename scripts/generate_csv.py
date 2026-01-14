import json
import pandas as pd
from pathlib import Path
from datetime import datetime

def generate_csv(json_path: str, csv_path: str):
    """Converts the extraction JSON results to a flattened CSV."""
    path = Path(json_path)
    if not path.exists():
        print(f"❌ Arquivo não encontrado: {json_path}")
        return

    print(f"Lendo {json_path}...")
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data.get("results", [])
    print(f"Processando {len(results)} registros...")
    
    flattened_data = []
    
    for item in results:
        # Basic info
        row = {
            "Arquivo": item.get("file"),
            "Caminho": item.get("path"),
            "Paginas": item.get("pages"),
            "Distribuidora_Identificada": item.get("distributor"),
            "Mapa_Usado": item.get("map_used"),
            "Campos_Extraidos_Qtd": item.get("fields_extracted"),
            "Erro": item.get("error")
        }
        
        # Extracted data fields
        extracted_data = item.get("data", {})
        for key, value in extracted_data.items():
            row[f"Extraido_{key}"] = value
            
        flattened_data.append(row)
        
    df = pd.DataFrame(flattened_data)
    
    # Reorder columns to have "Extraido_" columns at the end, but sorted alphabetically
    base_cols = ["Arquivo", "Caminho", "Paginas", "Distribuidora_Identificada", "Mapa_Usado", "Campos_Extraidos_Qtd", "Erro"]
    
    # Identify dynamic columns
    data_cols = [c for c in df.columns if c not in base_cols]
    data_cols.sort()
    
    final_cols = base_cols + data_cols
    
    # Reorder if columns exist in DF (some might be missing if result list was empty or different structure)
    existing_cols = [c for c in final_cols if c in df.columns]
    df = df[existing_cols]
    
    print(f"Salvando CSV em {csv_path}...")
    df.to_csv(csv_path, index=False, sep=';', encoding='utf-8-sig')
    print("✅ CSV gerado com sucesso!")

if __name__ == "__main__":
    INPUT_FILE = "output/extraction_full_results.json"
    OUTPUT_FILE = "output/extraction_full_results.csv"
    generate_csv(INPUT_FILE, OUTPUT_FILE)
