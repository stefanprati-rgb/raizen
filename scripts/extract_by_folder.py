"""
Extração OTIMIZADA usando estrutura de pastas:
  contratos_por_paginas/XX_paginas/DISTRIBUIDORA/*.pdf

Usa nome das pastas para determinar páginas e distribuidora diretamente.
"""
import json
import re
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import sys
import warnings
import argparse

warnings.filterwarnings('ignore')

sys.path.insert(0, str(Path(__file__).parent.parent))

# Paths
SOURCE_DIR = Path("contratos_organizados")  # Nova pasta CORRETAMENTE organizada
MAPS_DIR = Path("maps")
OUTPUT_DIR = Path("output")


def load_maps():
    """Carrega todos os mapas disponíveis."""
    maps = {}
    for map_file in MAPS_DIR.glob("*.json"):
        try:
            with open(map_file, 'r', encoding='utf-8') as f:
                mapa = json.load(f)
                maps[map_file.stem] = mapa
        except Exception:
            pass
    return maps


def select_map_direct(pages: int, distributor: str, text: str, maps: dict) -> tuple:
    """Seleciona mapa usando páginas e distribuidora das pastas."""
    text_lower = text.lower()
    
    candidates = []
    
    for map_name, mapa in maps.items():
        score = 0
        map_name_lower = map_name.lower()
        
        # Match distribuidora - usar nome da pasta
        map_dist = mapa.get("distribuidora_principal", "").upper().replace("-", "_").replace(" ", "_")
        dist_normalized = distributor.upper().replace("-", "_").replace(" ", "_")
        
        if map_dist and (map_dist in dist_normalized or dist_normalized in map_dist):
            score += 20  # Alto peso para match de distribuidora
        
        # Match páginas - usar número da pasta
        map_pages = mapa.get("paginas_analisadas", 0)
        if map_pages == pages:
            score += 25  # Peso muito alto para match exato
        elif abs(map_pages - pages) <= 1:
            score += 5
        
        # Bonus se o nome do mapa contém o número de páginas E distribuidora
        if f"_{pages}p" in map_name_lower or f"_{pages:02d}p" in map_name_lower:
            score += 10
        if dist_normalized.lower() in map_name_lower:
            score += 10
        
        # Match tipo de documento
        map_model = mapa.get("modelo_identificado", "").lower()
        
        # Penalizar ADITIVO/DISTRATO para documentos normais
        if "distrato" in text_lower:
            if "distrato" in map_model or "distrato" in map_name_lower:
                score += 20
        elif "aditivo" in text_lower:
            if "aditivo" in map_model or "aditivo" in map_name_lower:
                score += 20
        else:
            if "aditivo" in map_name_lower or "distrato" in map_name_lower:
                score -= 40  # Penalização MUITO forte
            if "adesão" in map_model or "adesao" in map_model:
                score += 5
        
        if score > 0:
            candidates.append((map_name, mapa, score))
    
    candidates.sort(key=lambda x: x[2], reverse=True)
    
    if candidates:
        return candidates[0][0], candidates[0][1]
    return None, None


def process_single_pdf(args: tuple) -> dict:
    """Processa um único PDF."""
    pdf_path_str, pages, distributor, maps = args
    
    import warnings
    warnings.filterwarnings('ignore')
    
    pdf_path = Path(pdf_path_str)
    
    result = {
        "file": pdf_path.name,
        "path": str(pdf_path),
        "pages": pages,
        "distributor": distributor,
        "map_used": None,
        "fields_extracted": 0,
        "data": {},
        "error": None
    }
    
    try:
        from src.extrator_contratos.table_extractor import open_pdf, extract_all_text_from_pdf
        from scripts.apply_map import extract_with_map
        
        with open_pdf(str(pdf_path)) as pdf:
            text = extract_all_text_from_pdf(pdf, max_pages=10, use_ocr_fallback=False)
        
        # Selecionar mapa usando info das pastas
        map_name, mapa = select_map_direct(pages, distributor, text, maps)
        
        if mapa:
            result["map_used"] = map_name
            extracted = extract_with_map(text, mapa)
            
            for field, value in extracted.items():
                if value is not None:
                    result["data"][field] = value
                    result["fields_extracted"] += 1
    
    except Exception as e:
        result["error"] = str(e)
    
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    
    print("=" * 60)
    print("EXTRAÇÃO OTIMIZADA (PASTAS → MAPAS)")
    print(f"Início: {datetime.now().strftime('%H:%M:%S')}")
    print(f"WORKERS: {args.workers}")
    print("=" * 60)
    
    # Carregar mapas
    print("\nCarregando mapas...")
    maps = load_maps()
    print(f"  {len(maps)} mapas carregados")
    
    # Listar PDFs usando estrutura de pastas
    print("\nListando PDFs...")
    pdf_tasks = []
    
    for pages_folder in SOURCE_DIR.iterdir():
        if not pages_folder.is_dir():
            continue
        
        # Extrair número de páginas
        match = re.match(r"(\d+)_paginas", pages_folder.name)
        if not match:
            continue
        pages = int(match.group(1))
        
        for dist_folder in pages_folder.iterdir():
            if not dist_folder.is_dir():
                continue
            
            distributor = dist_folder.name
            
            for pdf in dist_folder.glob("*.pdf"):
                pdf_tasks.append((str(pdf), pages, distributor, maps))
    
    print(f"  {len(pdf_tasks)} PDFs encontrados")
    
    # Mostrar distribuição
    by_pages = {}
    for _, pages, dist, _ in pdf_tasks:
        key = f"{pages}p"
        by_pages[key] = by_pages.get(key, 0) + 1
    print(f"\n  Distribuição por páginas:")
    for k, v in sorted(by_pages.items(), key=lambda x: int(x[0].replace('p', '')))[:10]:
        print(f"    {k}: {v}")
    
    # Processar
    print(f"\n{'=' * 60}")
    print("PROCESSANDO...")
    print("=" * 60)
    
    results = []
    start_time = datetime.now()
    
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process_single_pdf, task): task for task in pdf_tasks}
        
        for i, future in enumerate(as_completed(futures), 1):
            try:
                result = future.result(timeout=120)
                results.append(result)
            except Exception as e:
                task = futures[future]
                results.append({
                    "file": Path(task[0]).name,
                    "path": task[0],
                    "pages": task[1],
                    "distributor": task[2],
                    "error": str(e)
                })
            
            if i % 500 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                success = len([r for r in results if r.get('fields_extracted', 0) >= 5])
                rate = i / elapsed * 60 if elapsed > 0 else 0
                print(f"[{i}/{len(pdf_tasks)}] {success} sucesso | {rate:.0f} PDFs/min")
    
    # Estatísticas
    total = len(results)
    success = len([r for r in results if r.get('fields_extracted', 0) >= 5])
    partial = len([r for r in results if 0 < r.get('fields_extracted', 0) < 5])
    failed = len([r for r in results if r.get('fields_extracted', 0) == 0])
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print(f"\n{'=' * 60}")
    print("RESUMO FINAL")
    print(f"{'=' * 60}")
    print(f"Tempo total: {elapsed/60:.1f} minutos")
    print(f"Total processados: {total}")
    print(f"\n✅ Sucesso (5+ campos): {success} ({100*success/total:.1f}%)")
    print(f"⚠️  Parcial (<5 campos): {partial} ({100*partial/total:.1f}%)")
    print(f"❌ Falha: {failed} ({100*failed/total:.1f}%)")
    
    # Top mapas usados
    map_usage = {}
    for r in results:
        m = r.get('map_used', 'None')
        map_usage[m] = map_usage.get(m, 0) + 1
    
    print(f"\n🗺️ Top 10 Mapas:")
    for m, c in sorted(map_usage.items(), key=lambda x: -x[1])[:10]:
        print(f"  {m:40}: {c:5}")
    
    # Salvar
    output_file = OUTPUT_DIR / "extraction_optimized_results.json"
    output = {
        "timestamp": datetime.now().isoformat(),
        "source": str(SOURCE_DIR),
        "total": total,
        "success": success,
        "partial": partial,
        "failed": failed,
        "success_rate": round(100 * success / total, 1),
        "results": results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 Resultados: {output_file}")


if __name__ == "__main__":
    main()
