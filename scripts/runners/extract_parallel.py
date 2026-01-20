"""
Script de Extração em Lote - Versão PARALELA
Versão: 3.0

Processa PDFs em paralelo usando multiprocessing.
Ordena por tamanho de arquivo (menores primeiro).

Uso:
    python scripts/extract_parallel.py [--timeout MINUTES] [--workers N]
"""

import argparse
import json
import sys
import time
import warnings
import logging
import os
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta
from multiprocessing import Pool, cpu_count, Manager
from functools import partial

# Suppress warnings
warnings.filterwarnings('ignore')
logging.getLogger('pdfplumber').setLevel(logging.ERROR)

# Paths
SOURCE_DIR = Path("OneDrive_2026-01-06/TERMO DE ADESÃO")
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

def select_best_map(text: str, pages: int, distributor: str, maps: dict) -> tuple:
    """Seleciona o melhor mapa para um documento."""
    candidates = []
    text_lower = text.lower()
    
    for map_name, mapa in maps.items():
        score = 0
        
        # Match distribuidora
        map_dist = mapa.get("distribuidora_principal", "").upper()
        if map_dist and map_dist in distributor.upper():
            score += 10
        
        # Match páginas - peso maior para match exato
        map_pages = mapa.get("paginas_analisadas", 0)
        if map_pages == pages:
            score += 15  # Aumentado de 5 para 15
        elif abs(map_pages - pages) <= 1:
            score += 3
        
        # Bonus se o nome do mapa contém o número de páginas correto
        if f"_{pages}p" in map_name.lower() or f"_{pages:02d}p" in map_name.lower():
            score += 10
        
        # Match tipo de documento
        map_model = mapa.get("modelo_identificado", "").lower()
        map_name_lower = map_name.lower()
        
        # Se o documento é ADITIVO/DISTRATO, priorizar esses mapas
        if "distrato" in text_lower:
            if "distrato" in map_model or "distrato" in map_name_lower:
                score += 20
            else:
                score -= 5  # Penalizar mapas não-distrato
        elif "aditivo" in text_lower:
            if "aditivo" in map_model or "aditivo" in map_name_lower:
                score += 20
            else:
                score -= 5  # Penalizar mapas não-aditivo
        else:
            # Documento normal (adesão), penalizar mapas de aditivo/distrato MUITO FORTE
            if "aditivo" in map_name_lower or "distrato" in map_name_lower:
                score -= 30  # Penalizar MUITO fortemente
            if "adesão" in map_model or "adesao" in map_model:
                score += 5
        
        if score > 0:
            candidates.append((map_name, mapa, score))
    
    candidates.sort(key=lambda x: x[2], reverse=True)
    
    if candidates:
        return candidates[0][0], candidates[0][1]
    return None, None

def process_single_pdf(pdf_path_str: str, maps: dict) -> dict:
    """Processa um único PDF (função para multiprocessing)."""
    # Re-import dentro do processo filho
    import warnings
    warnings.filterwarnings('ignore')
    
    pdf_path = Path(pdf_path_str)
    
    result = {
        "file": pdf_path.name,
        "path": str(pdf_path),
        "pages": 0,
        "distributor": "DESCONHECIDA",
        "map_used": None,
        "fields_extracted": 0,
        "data": {},
        "error": None
    }
    
    try:
        # Import dentro do processo
        from raizen_power.extraction.table_extractor import open_pdf, extract_all_text_from_pdf
        from raizen_power.analysis.classifier import identify_distributor_from_text
        from raizen_power.apply_map import extract_with_map
        
        with open_pdf(str(pdf_path)) as pdf:
            result["pages"] = len(pdf.pages)
            text = extract_all_text_from_pdf(pdf, max_pages=10, use_ocr_fallback=False)
        
        result["distributor"] = identify_distributor_from_text(text)
        
        map_name, mapa = select_best_map(text, result["pages"], result["distributor"], maps)
        
        if mapa:
            result["map_used"] = map_name
            extracted = extract_with_map(text, mapa)
            
            for field, value in extracted.items():
                if value:
                    result["data"][field] = value
                    result["fields_extracted"] += 1
        else:
            result["error"] = "No matching map"
            
    except Exception as e:
        result["error"] = str(e)[:100]
    
    return result

def extract_all_parallel(source_dir: Path, timeout_minutes: int = 60, num_workers: int = None):
    """Extrai dados em paralelo com timeout."""
    
    if num_workers is None:
        num_workers = max(1, cpu_count() - 1)  # Deixa 1 core livre
    
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=timeout_minutes)
    
    print(f"{'='*60}")
    print(f"EXTRAÇÃO PARALELA - INÍCIO: {start_time.strftime('%H:%M:%S')}")
    print(f"WORKERS: {num_workers} processos")
    print(f"TIMEOUT: {timeout_minutes} minutos (até {end_time.strftime('%H:%M:%S')})")
    print(f"{'='*60}")
    
    print("\nCarregando mapas...")
    maps = load_maps()
    print(f"  {len(maps)} mapas carregados")
    
    # Get PDFs sorted by file size
    print("\nListando PDFs...")
    pdf_files = list(source_dir.glob("*.pdf"))
    pdf_files.sort(key=lambda x: x.stat().st_size)
    total = len(pdf_files)
    print(f"  {total} PDFs encontrados")
    
    # Convert to strings for multiprocessing
    pdf_paths = [str(p) for p in pdf_files]
    
    # Stats
    stats = {
        "total": total,
        "processed": 0,
        "success": 0,
        "partial": 0,
        "failed": 0,
        "by_map": defaultdict(int),
        "by_distributor": defaultdict(int),
        "by_pages": defaultdict(int)
    }
    
    results = []

    # Check for existing progress to resume
    progress_file = OUTPUT_DIR / "extraction_progress.json"
    if progress_file.exists():
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
                
            # Load stats (except total, which we recalculated)
            saved_stats = saved_data.get("stats", {})
            stats["processed"] = saved_stats.get("processed", 0)
            stats["success"] = saved_stats.get("success", 0)
            stats["partial"] = saved_stats.get("partial", 0)
            stats["failed"] = saved_stats.get("failed", 0)
            
            # Load counts
            for k, v in saved_stats.get("by_map", {}).items():
                stats["by_map"][k] = v
            for k, v in saved_stats.get("by_distributor", {}).items():
                stats["by_distributor"][k] = v
            for k, v in saved_stats.get("by_pages", {}).items():
                stats["by_pages"][int(k) if k.isdigit() else k] = v
                
            # Load results and get processed filenames (ONLY successful ones)
            results = saved_data.get("results", [])
            processed_files = {r.get("path") for r in results if r.get("fields_extracted", 0) >= 5}
            
            # Filter pdf_files to only those NOT in successful processed_files
            initial_count = len(pdf_files)
            pdf_files = [p for p in pdf_files if str(p) not in processed_files]
            
            # Keep only successful results in the list to avoid duplicate entries in final JSON
            results = [r for r in results if r.get("path") in processed_files]
            
            print(f"\n🔄 RETOMANDO EXECUÇÃO")
            print(f"  Encontrados {len(results)} processados anteriormente.")
            print(f"  Restam {len(pdf_files)} para processar de {initial_count} totais.")
            
        except Exception as e:
            print(f"⚠️ Erro ao carregar progresso anterior: {e}")
            print("  Iniciando do zero.")
    
    # Update paths and total after potential filtering
    pdf_paths = [str(p) for p in pdf_files]
    total = len(pdf_files)
    
    print(f"\n{'='*60}")
    print(f"PROCESSANDO EM {num_workers} WORKERS...")
    print(f"{'='*60}\n")
    
    # Create partial function with maps
    process_func = partial(process_single_pdf, maps=maps)
    
    # Process in batches for better progress tracking
    batch_size = 100
    
    with Pool(processes=num_workers) as pool:
        for batch_start in range(0, total, batch_size):
            # Check timeout
            if datetime.now() >= end_time:
                print(f"\n⏱️ TIMEOUT atingido")
                break
            
            batch_end = min(batch_start + batch_size, total)
            batch = pdf_paths[batch_start:batch_end]
            
            # Process batch
            batch_results = pool.map(process_func, batch)
            
            # Collect results
            for result in batch_results:
                results.append(result)
                stats["processed"] += 1
                
                if result["error"]:
                    stats["failed"] += 1
                elif result["fields_extracted"] >= 5:
                    stats["success"] += 1
                else:
                    stats["partial"] += 1
                
                if result["map_used"]:
                    stats["by_map"][result["map_used"]] += 1
                stats["by_distributor"][result["distributor"]] += 1
                stats["by_pages"][result["pages"]] += 1
            
            # Progress
            elapsed = (datetime.now() - start_time).total_seconds() / 60
            rate = stats["processed"] / elapsed if elapsed > 0 else 0
            remaining = (total - stats["processed"]) / rate if rate > 0 else 0
            
            print(f"[{stats['processed']:5d}/{total}] {100*stats['processed']/total:5.1f}% | "
                  f"{elapsed:.1f}min | {rate:.0f} PDFs/min | ~{remaining:.0f}min restantes", flush=True)
            
            # Save progress
            if stats["processed"] % 500 == 0:
                save_results(stats, results, OUTPUT_DIR / "extraction_progress.json")
                print(f"  💾 Progresso salvo")
    
    # Final save
    output_file = OUTPUT_DIR / "extraction_full_results.json"
    save_results(stats, results, output_file)
    
    # Print summary
    elapsed_total = (datetime.now() - start_time).total_seconds() / 60
    
    print(f"\n{'='*60}")
    print("RESUMO FINAL")
    print(f"{'='*60}")
    print(f"Tempo total: {elapsed_total:.1f} minutos")
    print(f"PDFs processados: {stats['processed']}/{total}")
    print(f"Taxa: {stats['processed']/max(elapsed_total,0.1):.1f} PDFs/min")
    print()
    print(f"✅ Sucesso (5+ campos): {stats['success']} ({100*stats['success']/max(stats['processed'],1):.1f}%)")
    print(f"⚠️  Parcial (<5 campos): {stats['partial']} ({100*stats['partial']/max(stats['processed'],1):.1f}%)")
    print(f"❌ Falha: {stats['failed']} ({100*stats['failed']/max(stats['processed'],1):.1f}%)")
    
    print(f"\n🗺️ Top 10 Mapas:")
    for map_name, count in sorted(stats["by_map"].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {map_name:35s}: {count:5d}")
    
    print(f"\n🏢 Top 10 Distribuidoras:")
    for dist, count in sorted(stats["by_distributor"].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {dist:25s}: {count:5d}")
    
    print(f"\n📁 Resultados: {output_file}")
    
    return stats, results

def save_results(stats, results, output_file):
    """Salva resultados em JSON."""
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "stats": {
                "total": stats["total"],
                "processed": stats["processed"],
                "success": stats["success"],
                "partial": stats["partial"],
                "failed": stats["failed"],
                "by_map": dict(stats["by_map"]),
                "by_distributor": dict(stats["by_distributor"]),
                "by_pages": dict(stats["by_pages"])
            },
            "results": results
        }, f, indent=2, ensure_ascii=False)

def main():
    parser = argparse.ArgumentParser(description="Extrai dados em paralelo")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout em minutos")
    parser.add_argument("--workers", type=int, help="Número de workers (default: CPUs-1)")
    parser.add_argument("--source", type=Path, default=SOURCE_DIR, help="Pasta com PDFs")
    
    args = parser.parse_args()
    
    if not args.source.exists():
        print(f"❌ Pasta não encontrada: {args.source}")
        sys.exit(1)
    
    extract_all_parallel(args.source, args.timeout, args.workers)

if __name__ == "__main__":
    main()
