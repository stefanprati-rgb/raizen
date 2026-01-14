"""
Script de Extração em Lote de Contratos
Versão: 1.0

Processa todos os PDFs e aplica os mapas de extração disponíveis.

Uso:
    python scripts/extract_all_contracts.py [--sample N] [--output FILE]
"""

import argparse
import json
import sys
import random
import warnings
import logging
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Suppress warnings
warnings.filterwarnings('ignore')
logging.getLogger('pdfplumber').setLevel(logging.ERROR)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extrator_contratos.table_extractor import open_pdf, extract_all_text_from_pdf
from src.extrator_contratos.classifier import identify_distributor_from_text
from scripts.apply_map import extract_with_map

# Paths
SOURCE_DIR = Path("OneDrive_2026-01-06/TERMO DE ADESÃO")
MAPS_DIR = Path("maps")
OUTPUT_DIR = Path("output")

# Required fields
REQUIRED_FIELDS = [
    "razao_social",
    "cnpj", 
    "data_adesao",
    "duracao_meses",
    "participacao_percentual",
    "representante_nome",
    "num_instalacao",
    "num_cliente",
    "distribuidora"
]

def load_maps():
    """Carrega todos os mapas disponíveis."""
    maps = {}
    for map_file in MAPS_DIR.glob("*.json"):
        try:
            with open(map_file, 'r', encoding='utf-8') as f:
                mapa = json.load(f)
                maps[map_file.stem] = mapa
        except Exception as e:
            print(f"Erro ao carregar mapa {map_file}: {e}")
    return maps

def select_best_map(text: str, pages: int, distributor: str, maps: dict) -> tuple:
    """Seleciona o melhor mapa para um documento."""
    
    # Try maps in order of specificity
    candidates = []
    
    for map_name, mapa in maps.items():
        score = 0
        
        # Check distributor match
        map_dist = mapa.get("distribuidora_principal", "").upper()
        if map_dist and map_dist in distributor.upper():
            score += 10
        
        # Check page count
        map_pages = mapa.get("paginas_analisadas", 0)
        if map_pages == pages:
            score += 5
        elif abs(map_pages - pages) <= 1:
            score += 2
        
        # Check document type
        map_model = mapa.get("modelo_identificado", "").lower()
        if "distrato" in map_model and "distrato" in text.lower():
            score += 8
        elif "aditivo" in map_model and "aditivo" in text.lower():
            score += 8
        elif "adesão" in map_model or "adesao" in map_model:
            score += 3
        
        if score > 0:
            candidates.append((map_name, mapa, score))
    
    # Sort by score
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
        "missing_fields": [],
        "error": None
    }
    
    try:
        with open_pdf(str(pdf_path)) as pdf:
            result["pages"] = len(pdf.pages)
            text = extract_all_text_from_pdf(pdf, max_pages=10, use_ocr_fallback=False)
        
        result["distributor"] = identify_distributor_from_text(text)
        
        # Select best map
        map_name, mapa = select_best_map(text, result["pages"], result["distributor"], maps)
        
        if mapa:
            result["map_used"] = map_name
            extracted = extract_with_map(text, mapa)
            
            # Count extracted fields
            for field, value in extracted.items():
                if value:
                    result["data"][field] = value
                    result["fields_extracted"] += 1
            
            # Check missing required fields
            for field in REQUIRED_FIELDS:
                if field not in result["data"] or not result["data"][field]:
                    result["missing_fields"].append(field)
        else:
            result["error"] = "No matching map found"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

def extract_all(source_dir: Path, sample: int = None, output_file: str = None):
    """Extrai dados de todos os contratos."""
    
    print("Carregando mapas de extração...")
    maps = load_maps()
    print(f"  {len(maps)} mapas carregados")
    
    # Get PDFs
    pdf_files = list(source_dir.glob("*.pdf"))
    
    if sample and sample < len(pdf_files):
        pdf_files = random.sample(pdf_files, sample)
        print(f"[AMOSTRA] Selecionados {sample} PDFs")
    
    total = len(pdf_files)
    print(f"Processando {total} PDFs...")
    print("=" * 60)
    
    # Stats
    stats = {
        "total": total,
        "success": 0,
        "partial": 0,
        "failed": 0,
        "by_map": defaultdict(int),
        "by_distributor": defaultdict(int)
    }
    
    results = []
    
    for i, pdf_path in enumerate(pdf_files, 1):
        if i % 10 == 0 or i == total:
            print(f"Processando: {i}/{total} ({100*i/total:.1f}%)", flush=True)
        
        result = extract_contract(pdf_path, maps)
        results.append(result)
        
        if result["error"]:
            stats["failed"] += 1
        elif result["fields_extracted"] >= 5:
            stats["success"] += 1
        else:
            stats["partial"] += 1
        
        if result["map_used"]:
            stats["by_map"][result["map_used"]] += 1
        stats["by_distributor"][result["distributor"]] += 1
    
    # Print summary
    print()
    print("=" * 60)
    print("RESUMO DA EXTRAÇÃO")
    print("=" * 60)
    
    print(f"\n✅ Sucesso (5+ campos): {stats['success']} ({100*stats['success']/total:.1f}%)")
    print(f"⚠️  Parcial (<5 campos): {stats['partial']} ({100*stats['partial']/total:.1f}%)")
    print(f"❌ Falha: {stats['failed']} ({100*stats['failed']/total:.1f}%)")
    
    print("\n🗺️ Por Mapa Utilizado:")
    for map_name, count in sorted(stats["by_map"].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {map_name:35s}: {count:5d}")
    
    # Save results
    output_path = Path(output_file) if output_file else OUTPUT_DIR / "extraction_results.json"
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "stats": {
                "total": stats["total"],
                "success": stats["success"],
                "partial": stats["partial"],
                "failed": stats["failed"],
                "by_map": dict(stats["by_map"]),
                "by_distributor": dict(stats["by_distributor"])
            },
            "results": results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 Resultados salvos em: {output_path}")
    
    return stats, results

def main():
    parser = argparse.ArgumentParser(description="Extrai dados de todos os contratos PDF")
    parser.add_argument("--sample", type=int, help="Processar apenas N arquivos")
    parser.add_argument("--output", type=str, help="Arquivo de saída JSON")
    parser.add_argument("--source", type=Path, default=SOURCE_DIR, help="Pasta com PDFs")
    
    args = parser.parse_args()
    
    if not args.source.exists():
        print(f"❌ Pasta não encontrada: {args.source}")
        sys.exit(1)
    
    extract_all(args.source, args.sample, args.output)

if __name__ == "__main__":
    main()
