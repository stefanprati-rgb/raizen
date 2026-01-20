"""
Extração INTELIGENTE por Pastas - Nova Estratégia

Fluxo:
1. Ler pasta: XX_paginas/DISTRIBUIDORA/
2. Buscar mapa EXATO: DISTRIBUIDORA_XXp_v*.json
3. Se não existe: Fallback para mapas da mesma distribuidora
4. Se nenhum: Fallback para mapa genérico

Vantagem: Seleção direta, sem scoring, escala com novos mapas.
"""
import json
import re
from pathlib import Path
from datetime import datetime
import sys
import warnings

warnings.filterwarnings('ignore')
sys.path.insert(0, str(Path(__file__).parent.parent))

# Paths
SOURCE_DIR = Path("contratos_organizados")
MAPS_DIR = Path("maps")
OUTPUT_DIR = Path("output")


def load_maps():
    """Carrega todos os mapas e indexa por nome."""
    maps = {}
    for map_file in MAPS_DIR.glob("*.json"):
        try:
            with open(map_file, 'r', encoding='utf-8') as f:
                maps[map_file.stem] = json.load(f)
        except Exception:
            pass
    return maps


def find_exact_map(distributor: str, pages: int, maps: dict) -> tuple:
    """
    Busca mapa EXATO para a combinação distribuidora/páginas.
    
    Tenta variações do nome:
    - CEMIG_11p_v1
    - CEMIG_11p_v2
    - CEMIG-D_11p_v1
    """
    # Normalizar nome da distribuidora
    dist_normalized = distributor.upper().replace('-', '_').replace(' ', '_')
    
    # Padrões a tentar (ordem de prioridade)
    patterns = [
        f"{dist_normalized}_{pages:02d}p",  # CEMIG_11p
        f"{dist_normalized}_{pages}p",       # CEMIG_11p (sem zero)
        f"{distributor}_{pages:02d}p",       # Nome original
        f"{distributor}_{pages}p",           # Nome original sem zero
    ]
    
    # Buscar mapas que correspondem
    for pattern in patterns:
        for map_name in maps:
            if map_name.upper().startswith(pattern.upper()):
                return map_name, maps[map_name], "EXATO"
    
    return None, None, None


def find_fallback_map(distributor: str, pages: int, maps: dict) -> tuple:
    """
    Fallback: busca mapa da mesma distribuidora (qualquer páginas).
    """
    dist_normalized = distributor.upper().replace('-', '_').replace(' ', '_')
    
    candidates = []
    for map_name, mapa in maps.items():
        map_name_upper = map_name.upper()
        
        # Mapa é da mesma distribuidora?
        if dist_normalized in map_name_upper:
            map_pages = mapa.get("paginas_analisadas", 0)
            # Preferir mapas com páginas próximas
            distance = abs(map_pages - pages) if map_pages else 100
            candidates.append((map_name, mapa, distance))
    
    if candidates:
        # Ordenar por distância de páginas
        candidates.sort(key=lambda x: x[2])
        return candidates[0][0], candidates[0][1], "FALLBACK_DIST"
    
    return None, None, None


def find_generic_map(pages: int, maps: dict) -> tuple:
    """
    Último fallback: mapa genérico com páginas próximas.
    """
    candidates = []
    for map_name, mapa in maps.items():
        # Evitar mapas de tipo específico (aditivo, distrato)
        if 'aditivo' in map_name.lower() or 'distrato' in map_name.lower():
            continue
        
        map_pages = mapa.get("paginas_analisadas", 0)
        if map_pages:
            distance = abs(map_pages - pages)
            candidates.append((map_name, mapa, distance))
    
    if candidates:
        candidates.sort(key=lambda x: x[2])
        return candidates[0][0], candidates[0][1], "FALLBACK_GENERICO"
    
    return None, None, None


def select_map_smart(distributor: str, pages: int, maps: dict) -> tuple:
    """
    Seleção inteligente de mapa baseada na pasta.
    Retorna: (map_name, map_data, selection_type)
    """
    # 1. Tentar mapa EXATO
    map_name, mapa, sel_type = find_exact_map(distributor, pages, maps)
    if mapa:
        return map_name, mapa, sel_type
    
    # 2. Fallback para mesma distribuidora
    map_name, mapa, sel_type = find_fallback_map(distributor, pages, maps)
    if mapa:
        return map_name, mapa, sel_type
    
    # 3. Fallback genérico
    map_name, mapa, sel_type = find_generic_map(pages, maps)
    if mapa:
        return map_name, mapa, sel_type
    
    return None, None, "NENHUM"


def process_pdf(pdf_path: Path, pages: int, distributor: str, maps: dict) -> dict:
    """Processa um único PDF usando seleção inteligente."""
    from src.extrator_contratos.table_extractor import open_pdf, extract_all_text_from_pdf
    from scripts.apply_map import extract_with_map
    
    result = {
        "file": pdf_path.name,
        "path": str(pdf_path),
        "pages": pages,
        "distributor": distributor,
        "map_used": None,
        "selection_type": None,
        "fields_extracted": 0,
        "data": {},
        "error": None
    }
    
    try:
        # Selecionar mapa usando estratégia inteligente
        map_name, mapa, sel_type = select_map_smart(distributor, pages, maps)
        
        result["map_used"] = map_name
        result["selection_type"] = sel_type
        
        if not mapa:
            result["error"] = "Nenhum mapa encontrado"
            return result
        
        # Extrair texto
        with open_pdf(str(pdf_path)) as pdf:
            text = extract_all_text_from_pdf(pdf, max_pages=15, use_ocr_fallback=False)
        
        # Aplicar mapa
        extracted = extract_with_map(text, mapa)
        
        for field, value in extracted.items():
            if value is not None:
                result["data"][field] = value
                result["fields_extracted"] += 1
    
    except Exception as e:
        result["error"] = str(e)
    
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10, help="Número de arquivos para testar")
    args = parser.parse_args()
    
    print("=" * 70)
    print("EXTRAÇÃO INTELIGENTE POR PASTAS")
    print("=" * 70)
    
    # Carregar mapas
    print("\n📁 Carregando mapas...")
    maps = load_maps()
    print(f"   {len(maps)} mapas disponíveis")
    
    # Listar PDFs com info das pastas
    print(f"\n📄 Listando PDFs (limite: {args.limit})...")
    
    pdf_tasks = []
    for pages_folder in SOURCE_DIR.iterdir():
        if not pages_folder.is_dir():
            continue
        
        match = re.match(r"(\d+)_paginas", pages_folder.name)
        if not match:
            continue
        pages = int(match.group(1))
        
        for dist_folder in pages_folder.iterdir():
            if not dist_folder.is_dir():
                continue
            
            distributor = dist_folder.name
            
            for pdf in dist_folder.glob("*.pdf"):
                pdf_tasks.append((pdf, pages, distributor))
                
                if len(pdf_tasks) >= args.limit:
                    break
            
            if len(pdf_tasks) >= args.limit:
                break
        
        if len(pdf_tasks) >= args.limit:
            break
    
    print(f"   {len(pdf_tasks)} PDFs selecionados")
    
    # Processar
    print(f"\n{'=' * 70}")
    print("PROCESSANDO...")
    print("=" * 70)
    
    results = []
    for i, (pdf, pages, distributor) in enumerate(pdf_tasks, 1):
        print(f"\n[{i}/{len(pdf_tasks)}] {pdf.name[:50]}...")
        print(f"   Pasta: {pages}_paginas/{distributor}")
        
        result = process_pdf(pdf, pages, distributor, maps)
        results.append(result)
        
        print(f"   Mapa: {result['map_used']} ({result['selection_type']})")
        print(f"   Campos: {result['fields_extracted']}")
        if result['error']:
            print(f"   ❌ Erro: {result['error']}")
    
    # Resumo
    print(f"\n{'=' * 70}")
    print("RESUMO")
    print("=" * 70)
    
    total = len(results)
    success = len([r for r in results if r.get('fields_extracted', 0) >= 5])
    partial = len([r for r in results if 0 < r.get('fields_extracted', 0) < 5])
    
    print(f"Total: {total}")
    print(f"✅ Sucesso (5+ campos): {success} ({100*success/total:.0f}%)")
    print(f"⚠️  Parcial (<5 campos): {partial} ({100*partial/total:.0f}%)")
    
    # Tipos de seleção
    from collections import Counter
    sel_types = Counter(r['selection_type'] for r in results)
    print(f"\n📊 Tipos de Seleção:")
    for t, c in sel_types.items():
        print(f"   {t}: {c}")
    
    # Salvar
    output_file = OUTPUT_DIR / "extraction_smart_test.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({"results": results}, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 Resultados: {output_file}")


if __name__ == "__main__":
    main()
