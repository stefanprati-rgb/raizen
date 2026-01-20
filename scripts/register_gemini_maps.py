import os
import json
import re
from pathlib import Path

def extract_json_from_text(text):
    """Extracts JSON object from a string, handling potential markdown blocks."""
    # Try finding the first { and last }
    start = text.find('{')
    end = text.rfind('}')
    
    if start != -1 and end != -1:
        json_str = text[start:end+1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
            
    return None

def main():
    base_dir = Path(r"C:\Projetos\Raizen\output\gemini_clusters")
    maps_dir = Path(r"C:\Projetos\Raizen\maps")
    
    if not base_dir.exists():
        print(f"Directory not found: {base_dir}")
        return

    maps_dir.mkdir(parents=True, exist_ok=True)
    
    registered_count = 0
    errors = []

    print(f"Scanning {base_dir} for maps...")

    # Walk through the directory
    for root, dirs, files in os.walk(base_dir):
        if "RESPOSTA.txt" in files:
            file_path = Path(root) / "RESPOSTA.txt"
            folder_name = Path(root).name
            
            # Construct map filename from folder name
            # Remove leading numbers if they are just indices (e.g. 01_...)?
            # User wants "identify maps created", keeping the name seems safest to trace back.
            map_name = f"{folder_name}.json"
            target_path = maps_dir / map_name
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                map_data = extract_json_from_text(content)
                
                if map_data:
                    # Add some metadata if missing
                    if "modelo_identificado" not in map_data:
                        map_data["modelo_identificado"] = folder_name
                    
                    with open(target_path, 'w', encoding='utf-8') as f:
                        json.dump(map_data, f, indent=4, ensure_ascii=False)
                    
                    print(f"Registered: {map_name}")
                    registered_count += 1
                else:
                    errors.append(f"Invalid JSON in {file_path}")
            except Exception as e:
                errors.append(f"Error processing {file_path}: {e}")

    print("\nSummary:")
    print(f"Total maps registered: {registered_count}")
    if errors:
        print("\nErrors:")
        for err in errors:
            print(f"- {err}")

if __name__ == "__main__":
    main()
