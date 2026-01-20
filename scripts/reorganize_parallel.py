"""
Reorganiza PDFs em pastas corretas usando processamento paralelo.
Detecta páginas REAIS e distribuidora do texto de cada PDF.
"""
import json
import shutil
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
import argparse
import sys
import warnings

warnings.filterwarnings('ignore')
sys.path.insert(0, str(Path(__file__).parent.parent))

# Paths
SOURCE_DIR = Path("contratos_por_paginas")  # Pasta atual (organização errada)
TARGET_DIR = Path("contratos_organizados")   # Nova pasta (organização correta)


def detect_and_move(args: tuple) -> dict:
    """Detecta páginas e distribuidora de um PDF e move para pasta correta."""
    pdf_path_str, target_base, do_copy = args
    
    import warnings
    warnings.filterwarnings('ignore')
    
    pdf_path = Path(pdf_path_str)
    
    result = {
        "file": pdf_path.name,
        "source": str(pdf_path),
        "pages": 0,
        "distributor": "DESCONHECIDA",
        "moved": False,
        "error": None
    }
    
    try:
        from src.extrator_contratos.table_extractor import open_pdf
        from src.extrator_contratos.classifier import identify_distributor_from_text
        import pdfplumber
        
        # Detectar páginas reais
        with pdfplumber.open(str(pdf_path)) as pdf:
            result["pages"] = len(pdf.pages)
            
            # Extrair texto da primeira página para detectar distribuidora
            text = ""
            for page in pdf.pages[:3]:
                page_text = page.extract_text() or ""
                text += page_text + "\n"
        
        # Detectar distribuidora
        result["distributor"] = identify_distributor_from_text(text)
        
        # Normalizar nome da distribuidora
        dist = result["distributor"].upper().replace(' ', '_').replace('-', '_')
        pages = result["pages"]
        
        # Criar pasta destino
        dest_folder = Path(target_base) / f"{pages:02d}_paginas" / dist
        dest_folder.mkdir(parents=True, exist_ok=True)
        
        dest_path = dest_folder / pdf_path.name
        
        # Mover ou copiar
        if do_copy:
            shutil.copy2(pdf_path, dest_path)
        else:
            shutil.move(str(pdf_path), str(dest_path))
        
        result["moved"] = True
        result["dest"] = str(dest_path)
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8, help="Número de workers")
    parser.add_argument("--copy", action="store_true", help="Copiar ao invés de mover")
    parser.add_argument("--limit", type=int, default=0, help="Limitar número de arquivos (0=todos)")
    args = parser.parse_args()
    
    print("=" * 60)
    print("REORGANIZADOR PARALELO DE PDFs")
    print(f"Início: {datetime.now().strftime('%H:%M:%S')}")
    print(f"WORKERS: {args.workers} | {'COPIAR' if args.copy else 'MOVER'}")
    print("=" * 60)
    
    # Criar pasta destino
    TARGET_DIR.mkdir(exist_ok=True)
    
    # Listar todos os PDFs
    print("\nListando PDFs...")
    pdf_files = list(SOURCE_DIR.rglob("*.pdf"))
    
    if args.limit > 0:
        pdf_files = pdf_files[:args.limit]
    
    print(f"  {len(pdf_files)} PDFs encontrados")
    
    # Preparar tarefas
    tasks = [(str(pdf), str(TARGET_DIR), args.copy) for pdf in pdf_files]
    
    # Processar em paralelo
    print(f"\n{'=' * 60}")
    print("PROCESSANDO...")
    print("=" * 60)
    
    results = []
    start_time = datetime.now()
    
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(detect_and_move, task): task for task in tasks}
        
        for i, future in enumerate(as_completed(futures), 1):
            try:
                result = future.result(timeout=60)
                results.append(result)
            except Exception as e:
                results.append({"error": str(e), "file": futures[future][0]})
            
            if i % 500 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = i / elapsed * 60 if elapsed > 0 else 0
                moved = len([r for r in results if r.get('moved')])
                print(f"[{i}/{len(tasks)}] {moved} movidos | {rate:.0f} PDFs/min")
    
    # Estatísticas
    elapsed = (datetime.now() - start_time).total_seconds()
    moved = len([r for r in results if r.get('moved')])
    errors = len([r for r in results if r.get('error')])
    
    # Agrupar por combo
    from collections import Counter
    by_combo = Counter()
    for r in results:
        if r.get('moved'):
            combo = f"{r['pages']:02d}p/{r['distributor']}"
            by_combo[combo] += 1
    
    print(f"\n{'=' * 60}")
    print("RESUMO FINAL")
    print(f"{'=' * 60}")
    print(f"Tempo total: {elapsed/60:.1f} minutos")
    print(f"Total: {len(results)}")
    print(f"✅ Movidos: {moved}")
    print(f"❌ Erros: {errors}")
    
    print(f"\n📊 Top 10 combos organizados:")
    for combo, count in by_combo.most_common(10):
        print(f"  {combo}: {count}")
    
    print(f"\n📁 Nova estrutura em: {TARGET_DIR}")
    
    # Salvar log
    log_file = Path("output/reorganize_log.json")
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total": len(results),
            "moved": moved,
            "errors": errors,
            "by_combo": dict(by_combo.most_common()),
            "results": results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"📋 Log salvo: {log_file}")


if __name__ == "__main__":
    main()
