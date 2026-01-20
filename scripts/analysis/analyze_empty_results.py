import json
from collections import Counter
from pathlib import Path

# Load results
with open('output/cpfl_paulista_final/cpfl_v5_full_results.json', 'r', encoding='utf-8') as f:
    results = json.load(f)

# Filter Empty
empty_docs = [r for r in results if r['status'] == 'VAZIO']

print(f'Total Empty: {len(empty_docs)}')
print('='*40)

# Analyze by Folder/Type
types = Counter([r['type'] for r in empty_docs])
folders = Counter([f"{r['type']}/{r['folder']}" for r in empty_docs])

print('By Type:')
for t, c in types.most_common():
    print(f'  {t}: {c}')

print('\nBy Folder (Top 10):')
for f, c in folders.most_common(10):
    print(f'  {f}: {c}')

# Sample filenames
print('\nSample Empty Files:')
for r in empty_docs[:5]:
    print(f"  - {r['file']}")
