"""Análise detalhada dos combos parciais restantes."""
import json
from pathlib import Path

# Carregar resultados
d = json.load(open('output/extraction_full_results.json', encoding='utf-8'))
results = d['results']

# Filtrar parciais
parciais = [r for r in results if r.get('fields_extracted', 0) < 5]

# Agrupar por combo
combos = {}
for r in parciais:
    dist = r.get('distributor', 'UNKNOWN')
    pages = r.get('pages', 0)
    combo = f'{dist}_{pages}p'
    mapa = r.get('map_used', 'None')
    
    if combo not in combos:
        combos[combo] = {'count': 0, 'maps': {}, 'fields_total': 0, 'samples': []}
    combos[combo]['count'] += 1
    combos[combo]['fields_total'] += r.get('fields_extracted', 0)
    combos[combo]['maps'][mapa] = combos[combo]['maps'].get(mapa, 0) + 1
    
    if len(combos[combo]['samples']) < 3:
        combos[combo]['samples'].append({
            'file': r['file'][:60],
            'path': r['path'],
            'fields': r.get('fields_extracted', 0)
        })

# Calcular média
for c in combos.values():
    c['fields_avg'] = round(c['fields_total'] / c['count'], 1)

# Ordenar
sorted_combos = sorted(combos.items(), key=lambda x: x[1]['count'], reverse=True)[:15]

print('TOP 15 COMBOS PARCIAIS - ANÁLISE DETALHADA')
print('=' * 70)

for combo, data in sorted_combos:
    print(f"\n🔴 {combo}: {data['count']} casos | Média: {data['fields_avg']} campos")
    print("   Mapas usados:")
    for m, c in sorted(data['maps'].items(), key=lambda x: -x[1])[:3]:
        print(f"     - {m}: {c}")
    print("   Exemplos:")
    for s in data['samples']:
        print(f"     - {s['file']} ({s['fields']} campos)")

# Salvar relatório JSON
report = {
    'total_parciais': len(parciais),
    'combos': {k: {
        'count': v['count'],
        'fields_avg': v['fields_avg'],
        'top_map': max(v['maps'].items(), key=lambda x: x[1])[0] if v['maps'] else None,
        'samples': [s['path'] for s in v['samples']]
    } for k, v in sorted_combos}
}

with open('output/parciais_analysis.json', 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(f"\n📁 Relatório salvo: output/parciais_analysis.json")
