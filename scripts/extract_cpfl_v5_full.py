import json
import time
import sys
import csv
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
from collections import Counter

# Adicionar pasta scripts ao path
sys.path.insert(0, 'scripts')
from uc_extractor_v5 import UCExtractorV5, DynamicBlacklist

SOURCE_DIR = Path("cpfl_paulista_por_tipo")
OUTPUT_DIR = Path("output/cpfl_paulista_final")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Usar mais workers para CPU bound tasks, mas deixar alguns livres
MAX_WORKERS = max(1, min(6, cpu_count() - 2))

def process_file_v5(pdf_path):
    # Instanciar extrator (cada processo tem o seu isolation)
    # Importante: use_dynamic_blacklist=True vai ler o arquivo de blacklist atual
    extractor = UCExtractorV5(use_dynamic_blacklist=True)
    
    try:
        result = extractor.extract_from_pdf(str(pdf_path))
        
        return {
            "status": "SUCCESS" if result.uc_count > 0 else "VAZIO",
            "file": result.file,
            "path": result.path,
            "folder": Path(result.path).parent.name,
            "type": Path(result.path).parent.parent.name,
            "ucs": result.ucs,
            "uc_count": result.uc_count,
            "confidence": result.confidence,
            "method": result.method,
            "duration": result.duration,
            "errors": result.errors
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "file": pdf_path.name,
            "path": str(pdf_path),
            "folder": pdf_path.parent.name,
            "type": pdf_path.parent.parent.name,
            "ucs": [],
            "uc_count": 0,
            "confidence": 0,
            "method": "error",
            "duration": 0,
            "errors": [str(e)]
        }

def update_global_blacklist(all_results):
    """
    Atualiza a blacklist global baseada nos resultados de todos os workers
    """
    print("\nAtualizando Blacklist Global...")
    blacklist_mgr = DynamicBlacklist()
    
    # Coletar todas as UCs encontradas
    all_ucs = []
    for r in all_results:
        if r.get('ucs'):
            all_ucs.extend(r['ucs'])
            
    # Simular atualização em bulk
    # Como o DynamicBlacklist espera update per doc, vamos simular
    # Mas é melhor apenas incrementar a frequência globalmente
    
    # Carregar estado atual
    current_freq = blacklist_mgr.frequency
    
    # Atualizar com o novo lote
    batch_counter = Counter(all_ucs)
    for uc, count in batch_counter.items():
        current_freq[uc] = current_freq.get(uc, 0) + count
        
    blacklist_mgr.frequency = current_freq
    blacklist_mgr.total_docs += len(all_results)
    
    # Recalcular e salvar
    blacklist_mgr.analyze_and_update_blacklist()
    stats = blacklist_mgr.get_stats()
    print(f"Blacklist atualizada: {stats['blacklist_size']} códigos ignorados (Threshold > 80% em {stats['total_docs']} docs)")

def main():
    print(f"=== EXTRAÇÃO V5 CPFL (FULL) ===")
    print(f"Fonte: {SOURCE_DIR.absolute()}")
    print(f"Workers: {MAX_WORKERS}")
    
    all_pdfs = list(SOURCE_DIR.rglob("*.pdf"))
    total_files = len(all_pdfs)
    print(f"Total: {total_files} arquivos para processar")
    
    results = []
    success_count = 0
    empty_count = 0
    error_count = 0
    
    start_time = time.time()
    
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_pdf = {executor.submit(process_file_v5, pdf): pdf for pdf in all_pdfs}
        
        for i, future in enumerate(as_completed(future_to_pdf), 1):
            res = future.result()
            results.append(res)
            
            if res['status'] == 'SUCCESS':
                success_count += 1
                sym = "SUCCESS"  # Evitar emoji no console se der erro
            elif res['status'] == 'VAZIO':
                empty_count += 1
                sym = "EMPTY"
            else:
                error_count += 1
                sym = "ERROR"
            
            pct = (i / total_files) * 100
            if i % 10 == 0 or i == total_files:
                sys.stdout.write(f"\rProcessando: {pct:.1f}% ({i}/{total_files}) - Sucesso: {success_count} | Vazios: {empty_count}")
                sys.stdout.flush()
            
    print("\n\n=== FINALIZADO ===")
    print(f"Tempo total: {time.time() - start_time:.1f}s")
    print(f"Total Processado: {len(results)}")
    print(f"Sucesso (com UCs): {success_count} ({(success_count/total_files)*100:.1f}%)")
    print(f"Vazios: {empty_count}")
    print(f"Erros: {error_count}")

    # Atualizar Blacklist para o futuro
    try:
        update_global_blacklist(results)
    except Exception as e:
        print(f"Erro ao atualizar blacklist: {e}")

    # Salvar JSON
    json_file = OUTPUT_DIR / "cpfl_v5_full_results.json"
    print(f"Salvando JSON em {json_file}...")
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Salvar CSV
    csv_file = OUTPUT_DIR / "cpfl_v5_full.csv"
    print(f"Salvando CSV em {csv_file}...")
    with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['Arquivo', 'Tipo', 'Pasta', 'Status', 'Qtd_UCs', 'Lista_UCs', 'Confiança', 'Método', 'Path'])
        for r in results:
            writer.writerow([
                r['file'], r['type'], r['folder'], r['status'], 
                r['uc_count'], json.dumps(r['ucs']), r['confidence'], r['method'], r['path']
            ])
    
    print("Concluído com sucesso!")

if __name__ == "__main__":
    main()
