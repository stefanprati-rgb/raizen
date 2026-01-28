"""
Script de Extração em Lote - Execução Completa
Versão: 2.0

Processa todos os PDFs com timeout de 1 hora.
Ordena por tamanho de arquivo (menores primeiro para mais resultados rápidos).

Uso:
    python scripts/extract_full.py [--timeout MINUTES]
"""

import argparse
import json
import sys
import time
import warnings
import logging
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta

# Suppress warnings
warnings.filterwarnings('ignore')
logging.getLogger('pdfplumber').setLevel(logging.ERROR)

from raizen_power.extraction.table_extractor import open_pdf, extract_all_text_from_pdf
from raizen_power.analysis.classifier import identify_distributor_from_text
from raizen_power.extraction.apply_map import extract_with_map

# Paths
SOURCE_DIR = Path("data/raw/OneDrive_2026-01-06/TERMO DE ADESÃO")
MAPS_DIR = Path("maps")
OUTPUT_DIR = Path("output")
# Required fields
REQUIRED_FIELDS = [
    "razao_social", "cnpj", "data_adesao", "duracao_meses",
    "participacao_percentual", "representante_nome",
    "num_instalacao", "num_cliente", "distribuidora"
]

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
    
    for map_name, mapa in maps.items():
        score = 0
        
        map_dist = mapa.get("distribuidora_principal", "").upper()
        if map_dist and map_dist in distributor.upper():
            score += 10
        
        map_pages = mapa.get("paginas_analisadas", 0)
        if map_pages == pages:
            score += 5
        elif abs(map_pages - pages) <= 1:
            score += 2
        
        map_model = mapa.get("modelo_identificado", "").lower()
        if "distrato" in map_model and "distrato" in text.lower():
            score += 8
        elif "aditivo" in map_model and "aditivo" in text.lower():
            score += 8
        elif "adesão" in map_model or "adesao" in map_model:
            score += 3
        
        if score > 0:
            candidates.append((map_name, mapa, score))
    
    candidates.sort(key=lambda x: x[2], reverse=True)
    
    if candidates:
        return candidates[0][0], candidates[0][1]
    return None, None

def extract_contract(pdf_path: Path, maps: dict) -> dict:
    """Extrai dados de um contrato."""
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

def extract_all(source_dir: Path, timeout_minutes: int = 60):
    """Extrai dados de todos os contratos com timeout."""
    
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=timeout_minutes)
    
    print(f"{'='*60}")
    print(f"EXTRAÇÃO EM LOTE - INÍCIO: {start_time.strftime('%H:%M:%S')}")
    print(f"TIMEOUT: {timeout_minutes} minutos (até {end_time.strftime('%H:%M:%S')})")
    print(f"{'='*60}")
    
    print("\nCarregando mapas...")
    maps = load_maps()
    print(f"  {len(maps)} mapas carregados")
    
    # Get PDFs sorted by file size (smallest first)
    print("\nListando PDFs...")
    pdf_files = list(source_dir.glob("*.pdf"))
    pdf_files.sort(key=lambda x: x.stat().st_size)
    total = len(pdf_files)
    print(f"  {total} PDFs encontrados (ordenados por tamanho)")
    
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
    last_save = time.time()
    
    print(f"\n{'='*60}")
    print("PROCESSANDO...")
    print(f"{'='*60}\n")
    
    for i, pdf_path in enumerate(pdf_files, 1):
        # Check timeout
        if datetime.now() >= end_time:
            print(f"\n⏱️ TIMEOUT atingido após {i-1} PDFs")
            break
        
        # Progress every 50 files
        if i % 50 == 0 or i == 1:
            elapsed = (datetime.now() - start_time).total_seconds() / 60
            rate = i / elapsed if elapsed > 0 else 0
            remaining = (total - i) / rate if rate > 0 else 0
            print(f"[{i:5d}/{total}] {100*i/total:5.1f}% | {elapsed:.1f}min | ~{remaining:.0f}min restantes", flush=True)
        
        result = extract_contract(pdf_path, maps)
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
        
        # Save progress every 5 minutes
        if time.time() - last_save > 300:
            save_results(stats, results, OUTPUT_DIR / "extraction_progress.json")
            last_save = time.time()
            print(f"  💾 Progresso salvo ({stats['processed']} processados)")
    
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
    print(f"Taxa: {stats['processed']/elapsed_total:.1f} PDFs/min")
    print()
    print(f"✅ Sucesso (5+ campos): {stats['success']} ({100*stats['success']/max(stats['processed'],1):.1f}%)")
    print(f"⚠️  Parcial (<5 campos): {stats['partial']} ({100*stats['partial']/max(stats['processed'],1):.1f}%)")
    print(f"❌ Falha: {stats['failed']} ({100*stats['failed']/max(stats['processed'],1):.1f}%)")
    
    print(f"\n🗺️ Top 10 Mapas Utilizados:")
    for map_name, count in sorted(stats["by_map"].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {map_name:35s}: {count:5d}")
    
    print(f"\n🏢 Por Distribuidora:")
    for dist, count in sorted(stats["by_distributor"].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {dist:25s}: {count:5d}")
    
    print(f"\n📄 Por Páginas:")
    for pages in sorted(stats["by_pages"].keys())[:15]:
        count = stats["by_pages"][pages]
        print(f"  {pages:2d} páginas: {count:5d}")
    
    print(f"\n📁 Resultados salvos em: {output_file}")
    
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
    parser = argparse.ArgumentParser(description="Extrai dados de todos os contratos")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout em minutos (default: 60)")
    parser.add_argument("--source", type=Path, default=SOURCE_DIR, help="Pasta com PDFs")
    
    args = parser.parse_args()
    
    if not args.source.exists():
        print(f"❌ Pasta não encontrada: {args.source}")
        sys.exit(1)
    
    extract_all(args.source, args.timeout)

if __name__ == "__main__":
    main()
