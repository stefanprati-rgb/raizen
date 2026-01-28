"""
Script de Organização de Contratos
Versão: 1.0

Organiza os PDFs da pasta OneDrive por:
- Número de páginas
- Distribuidora detectada
- Tipo de documento (ADESÃO, ADITIVO, DISTRATO)

Uso:
    python scripts/organize_contracts.py [--dry-run] [--source PATH] [--dest PATH]
"""

import argparse
import json
import shutil
import sys
import random
import warnings
from pathlib import Path
from collections import defaultdict

# Suppress PDF warnings
warnings.filterwarnings('ignore')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extrator_contratos.table_extractor import open_pdf, extract_all_text_from_pdf
from src.extrator_contratos.classifier import identify_distributor_from_text, classify_contract

# Default paths
DEFAULT_SOURCE = Path("data/raw/OneDrive_2026-01-06/TERMO DE ADESÃO")
DEFAULT_DEST = Path("contratos_por_paginas")

# Document type detection patterns
DOC_TYPE_PATTERNS = {
    "DISTRATO": ["distrato", "rescisão", "rescisao", "término", "termino do contrato"],
    "ADITIVO": ["aditivo", "aditamento", "alteração contratual", "termo de condições comerciais"],
    "ADESAO": ["termo de adesão", "termo de adesao", "adesão ao consórcio", "adesao ao consorcio"]
}

def detect_document_type(text: str) -> str:
    """Detecta o tipo de documento baseado no texto."""
    text_lower = text.lower()
    
    # Check in order of specificity
    for doc_type, patterns in DOC_TYPE_PATTERNS.items():
        for pattern in patterns:
            if pattern in text_lower:
                return doc_type
    
    return "ADESAO"  # Default

def analyze_pdf(pdf_path: Path) -> dict:
    """Analisa um PDF e retorna suas características."""
    result = {
        "path": str(pdf_path),
        "filename": pdf_path.name,
        "pages": 0,
        "distributor": "DESCONHECIDA",
        "doc_type": "ADESAO",
        "error": None
    }
    
    try:
        with open_pdf(str(pdf_path)) as pdf:
            result["pages"] = len(pdf.pages)
            text = extract_all_text_from_pdf(pdf, max_pages=3, use_ocr_fallback=False)
        
        result["distributor"] = identify_distributor_from_text(text)
        result["doc_type"] = detect_document_type(text)
        
    except Exception as e:
        result["error"] = str(e)
    
    return result

def organize_contracts(source_dir: Path, dest_dir: Path, dry_run: bool = False, sample: int = None):
    """Organiza contratos por páginas e distribuidora."""
    
    # Get all PDFs
    pdf_files = list(source_dir.glob("*.pdf"))
    
    # Apply sample if specified
    if sample and sample < len(pdf_files):
        pdf_files = random.sample(pdf_files, sample)
        print(f"[AMOSTRA] Selecionados {sample} PDFs aleatórios")
    total = len(pdf_files)
    
    print(f"Encontrados {total} PDFs em {source_dir}")
    print("=" * 60)
    
    # Statistics
    stats = {
        "by_pages": defaultdict(int),
        "by_distributor": defaultdict(int),
        "by_doc_type": defaultdict(int),
        "errors": 0,
        "processed": 0
    }
    
    results = []
    
    for i, pdf_path in enumerate(pdf_files, 1):
        if i % 20 == 0 or i == total:
            print(f"Processando: {i}/{total} ({100*i/total:.1f}%)", flush=True)
        
        info = analyze_pdf(pdf_path)
        results.append(info)
        
        if info["error"]:
            stats["errors"] += 1
            continue
        
        stats["processed"] += 1
        stats["by_pages"][info["pages"]] += 1
        stats["by_distributor"][info["distributor"]] += 1
        stats["by_doc_type"][info["doc_type"]] += 1
        
        # Create destination path: contratos_por_paginas/XX_paginas/DISTRIBUIDORA/
        pages_folder = dest_dir / f"{info['pages']:02d}_paginas"
        dist_folder = pages_folder / info["distributor"]
        
        if not dry_run:
            dist_folder.mkdir(parents=True, exist_ok=True)
            dest_file = dist_folder / pdf_path.name
            
            # Copy instead of move to preserve original
            if not dest_file.exists():
                shutil.copy2(pdf_path, dest_file)
    
    # Print summary
    print()
    print("=" * 60)
    print("RESUMO DA ORGANIZAÇÃO")
    print("=" * 60)
    
    print(f"\nProcessados: {stats['processed']}/{total}")
    print(f"Erros: {stats['errors']}")
    
    print("\n📄 Por Número de Páginas:")
    for pages in sorted(stats["by_pages"].keys()):
        count = stats["by_pages"][pages]
        print(f"  {pages:2d} páginas: {count:5d} ({100*count/stats['processed']:.1f}%)")
    
    print("\n🏢 Por Distribuidora:")
    for dist in sorted(stats["by_distributor"].keys(), key=lambda x: stats["by_distributor"][x], reverse=True):
        count = stats["by_distributor"][dist]
        print(f"  {dist:25s}: {count:5d} ({100*count/stats['processed']:.1f}%)")
    
    print("\n📋 Por Tipo de Documento:")
    for doc_type in sorted(stats["by_doc_type"].keys()):
        count = stats["by_doc_type"][doc_type]
        print(f"  {doc_type:10s}: {count:5d} ({100*count/stats['processed']:.1f}%)")
    
    # Save results to JSON
    output_file = Path("output/organization_results.json")
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "stats": {
                "total": total,
                "processed": stats["processed"],
                "errors": stats["errors"],
                "by_pages": dict(stats["by_pages"]),
                "by_distributor": dict(stats["by_distributor"]),
                "by_doc_type": dict(stats["by_doc_type"])
            },
            "files": results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 Resultados salvos em: {output_file}")
    
    if dry_run:
        print("\n⚠️  MODO DRY-RUN: Nenhum arquivo foi copiado.")
    
    return stats

def main():
    parser = argparse.ArgumentParser(description="Organiza contratos PDF por páginas e distribuidora")
    parser.add_argument("--dry-run", action="store_true", help="Apenas analisa, não copia arquivos")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Pasta com PDFs originais")
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST, help="Pasta de destino")
    parser.add_argument("--sample", type=int, help="Processar apenas N arquivos (amostra)")
    
    args = parser.parse_args()
    
    if not args.source.exists():
        print(f"❌ Pasta não encontrada: {args.source}")
        sys.exit(1)
    
    organize_contracts(args.source, args.dest, args.dry_run, args.sample)

if __name__ == "__main__":
    main()
