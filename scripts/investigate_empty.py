import json

with open('output/multi_uc_robust_v3_test2.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

empty = [d for d in data if d['uc_count'] == 0]
print(f"Documentos sem UC: {len(empty)}")
print()

for d in empty:
    print(f"Arquivo: {d['file']}")
    print(f"  Path: {d['path']}")
    print(f"  CNPJs encontrados: {d.get('cnpjs_found', [])}")
    print(f"  Páginas com candidatos: {d.get('pages_with_ucs', [])}")
    print(f"  Erros: {d.get('errors', [])}")
    print()
