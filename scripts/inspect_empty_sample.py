import json
from pathlib import Path

# Load results
with open('output/cpfl_paulista_final/cpfl_v5_full_results.json', 'r', encoding='utf-8') as f:
    results = json.load(f)

# Find first empty TERMO_ADESAO
for r in results:
    if r['status'] == 'VAZIO' and r['type'] == 'TERMO_ADESAO':
        print(f"Path: {r['path']}")
        break
