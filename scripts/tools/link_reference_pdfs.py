#!/usr/bin/env python3
"""
Script para vincular PDFs de referência aos mapas que estão faltando.
Usa fingerprinting visual para encontrar o PDF mais representativo.
"""
import json
import re
import fitz
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import sys

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from raizen_power.utils.pdf_fingerprint import PDFModelIdentifier

MAPS_DIR = Path(__file__).parent.parent / 'maps'
DATA_DIR = Path(__file__).parent.parent / 'data'


def detect_distributor(path: Path) -> str:
    """Detecta distribuidora pelo caminho do PDF."""
    path_str = str(path).upper()
    
    distributors = [
        'CEMIG', 'CPFL', 'PAULISTA', 'CELPE', 'ENERGISA', 
        'ELEKTRO', 'NEOENERGIA', 'COELBA', 'LIGHT', 'ENEL',
        'EQUATORIAL', 'COSERN', 'RGE', 'EDP'
    ]
    
    for dist in distributors:
        if dist in path_str:
            if dist == 'PAULISTA':
                return 'CPFL PAULISTA'
            return dist
    
    return path.parent.name.upper()


def get_page_count(pdf_path: Path) -> int:
    """Retorna número de páginas do PDF."""
    try:
        doc = fitz.open(str(pdf_path))
        count = len(doc)
        doc.close()
        return count
    except:
        return 0


def build_pdf_index() -> dict:
    """Constrói índice de PDFs por distribuidora e número de páginas."""
    print("Indexando PDFs...")
    pdf_index = defaultdict(list)
    count = 0
    
    for pdf_path in DATA_DIR.rglob('*.pdf'):
        pages = get_page_count(pdf_path)
        if pages == 0:
            continue
        
        dist = detect_distributor(pdf_path)
        key = f"{dist}_{pages}p"
        pdf_index[key].append(pdf_path)
        count += 1
        
        if count % 1000 == 0:
            print(f"  {count} PDFs processados...")
    
    print(f"Total: {count} PDFs indexados em {len(pdf_index)} chaves")
    return pdf_index


def find_maps_without_reference() -> list:
    """Encontra mapas sem reference_pdf."""
    missing = []
    
    for map_path in sorted(MAPS_DIR.glob('*.json')):
        with open(map_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        meta = data.get('meta', data.get('meta_info', {}))
        if not meta.get('reference_pdf'):
            # Extrair padrão do nome (DIST_XXp)
            name = map_path.stem
            match = re.match(r'([A-Z_]+)_(\d+)p', name)
            if match:
                dist = match.group(1).replace('_', ' ')
                pages = int(match.group(2))
                missing.append({
                    'map_path': map_path,
                    'dist': dist,
                    'pages': pages,
                    'key': f"{dist}_{pages}p"
                })
            else:
                missing.append({
                    'map_path': map_path,
                    'dist': None,
                    'pages': None,
                    'key': None
                })
    
    return missing


def update_map_with_reference(map_path: Path, pdf_path: Path, identifier: PDFModelIdentifier):
    """Atualiza mapa com reference_pdf e layout_hash."""
    with open(map_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Calcular fingerprint
    dist = detect_distributor(pdf_path)
    result = identifier.classify_pdf(str(pdf_path), dist)
    
    # Atualizar metadados
    meta_key = 'meta' if 'meta' in data else 'meta_info'
    if meta_key not in data:
        data['meta'] = {}
        meta_key = 'meta'
    
    data[meta_key]['reference_pdf'] = pdf_path.name
    data[meta_key]['layout_hash'] = result.get('visual_hash', '')
    data[meta_key]['structure_hash'] = result.get('structure_hash', '')
    data[meta_key]['updated_at'] = datetime.now().strftime('%Y-%m-%d')
    
    # Salvar
    with open(map_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    return True


def main():
    # Construir índice de PDFs
    pdf_index = build_pdf_index()
    
    # Encontrar mapas sem referência
    missing_maps = find_maps_without_reference()
    print(f"\nMapas sem reference_pdf: {len(missing_maps)}")
    
    # Inicializar fingerprinter
    identifier = PDFModelIdentifier()
    
    # Processar mapas
    updated = 0
    skipped = 0
    
    for map_info in missing_maps:
        map_path = map_info['map_path']
        key = map_info['key']
        
        if not key:
            print(f"  SKIP: {map_path.name} (sem padrão detectável)")
            skipped += 1
            continue
        
        # Buscar PDFs correspondentes
        if key not in pdf_index:
            # Tentar variações
            alt_keys = []
            if 'CPFL' in key or 'PAULISTA' in key:
                alt_keys.append(key.replace('CPFL', 'CPFL PAULISTA'))
                alt_keys.append(key.replace('CPFL PAULISTA', 'CPFL'))
            
            found = False
            for alt in alt_keys:
                if alt in pdf_index:
                    key = alt
                    found = True
                    break
            
            if not found:
                print(f"  SKIP: {map_path.name} (chave {key} não encontrada)")
                skipped += 1
                continue
        
        # Pegar primeiro PDF disponível
        pdf_path = pdf_index[key][0]
        
        try:
            update_map_with_reference(map_path, pdf_path, identifier)
            print(f"  OK: {map_path.name} <- {pdf_path.name}")
            updated += 1
        except Exception as e:
            print(f"  ERRO: {map_path.name}: {e}")
            skipped += 1
    
    print(f"\nResultado: {updated} atualizados, {skipped} ignorados")
    
    # Salvar cache do fingerprinter
    identifier._save_cache()


if __name__ == '__main__':
    main()
