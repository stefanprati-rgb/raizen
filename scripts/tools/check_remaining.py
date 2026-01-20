import json

d = json.load(open('output/extraction_full_results.json', encoding='utf-8'))
results = d['results']

# Filtrar parciais
parciais = [r for r in results if r.get('fields_extracted', 0) < 5]
print(f'Total Parciais: {len(parciais)}')

# Agrupar por combo (distributor + pages)
combos = {}
for r in parciais:
    dist = r.get('distributor', 'UNKNOWN')
    pages = r.get('pages', 0)
    combo = f'{dist}_{pages}p'
    if combo not in combos:
        combos[combo] = {'count': 0, 'samples': []}
    combos[combo]['count'] += 1
    if len(combos[combo]['samples']) < 2:
        path = r.get('path', '')
        combos[combo]['samples'].append(path.split('\\')[-1][:70] if '\\' in path else path.split('/')[-1][:70])

# Ordenar por count
sorted_combos = sorted(combos.items(), key=lambda x: x[1]['count'], reverse=True)

print('\nTop 15 Combos Restantes:')
print('-' * 70)
for combo, data in sorted_combos[:15]:
    print(f"{combo:35}: {data['count']:3} casos")
    for s in data['samples']:
        print(f"  - {s}")
