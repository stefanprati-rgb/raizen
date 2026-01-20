"""Lista combos e verifica quais precisam de mapas."""
import json
from pathlib import Path
from collections import Counter
import re

# Carregar mapas existentes
maps_dir = Path('maps')
maps = {}
for f in maps_dir.glob('*.json'):
    maps[f.stem.upper()] = f.stem

# Listar combos na pasta organizada
source_dir = Path('contratos_organizados')
combos = Counter()

for pages_folder in source_dir.iterdir():
    if not pages_folder.is_dir():
        continue
    match = re.match(r'(\d+)_paginas', pages_folder.name)
    if not match:
        continue
    pages = int(match.group(1))
    
    for dist_folder in pages_folder.iterdir():
        if not dist_folder.is_dir():
            continue
        
        distributor = dist_folder.name
        pdf_count = len(list(dist_folder.glob('*.pdf')))
        if pdf_count > 0:
            combo = f'{distributor}_{pages:02d}p'
            combos[combo] = pdf_count

# Verificar quais tem mapa EXATO
print('COMBOS SEM MAPA EXATO (ordenados por quantidade)')
print('=' * 60)

sem_mapa = []
com_mapa = []

for combo, count in combos.most_common():
    # Verificar se existe mapa
    has_map = False
    for map_name in maps:
        combo_check = combo.upper().replace('-', '_')
        if combo_check in map_name.replace('-', '_'):
            has_map = True
            break
    
    if has_map:
        com_mapa.append((combo, count))
    else:
        sem_mapa.append((combo, count))

print(f'\n❌ SEM MAPA ({len(sem_mapa)} combos):')
for combo, count in sem_mapa[:25]:
    print(f'   {combo}: {count} arquivos')

print(f'\n   ... Total: {sum(c for _,c in sem_mapa)} arquivos precisam de mapas')

print(f'\n✅ COM MAPA ({len(com_mapa)} combos):')
for combo, count in com_mapa[:15]:
    print(f'   {combo}: {count} arquivos')
print(f'   ... Total: {sum(c for _,c in com_mapa)} arquivos já tem mapas')
