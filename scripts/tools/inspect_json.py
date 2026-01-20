import json
from pathlib import Path

files = list(Path('output').rglob('*_relatorio.json'))
if files:
    f = files[0]
    print(f"Inspecting {f}")
    data = json.load(open(f, encoding='utf-8', errors='ignore'))
    print("Keys:", data.keys())
    if 'detalhes' in data:
        print("First item in detalhes:", data['detalhes'][0].keys() if data['detalhes'] else "Empty")
    if 'resultados' in data:
        print("First item in resultados:", data['resultados'][0].keys() if data['resultados'] else "Empty")
else:
    print("No report files found.")
