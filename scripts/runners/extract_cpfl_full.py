import json
import time
import sys
import csv
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
from datetime import datetime

# Ajustar path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extrator_contratos.table_extractor import open_pdf, extract_all_text_from_pdf
from scripts.apply_map import extract_with_map

# Configurações
SOURCE_DIR = Path("cpfl_paulista_por_tipo")
MAP_FILE = Path("maps/CPFL_PAULISTA_completo_v5.json")
OUTPUT_DIR = Path("output/cpfl_paulista_final")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Limite de workers para não travar o PC do usuário
# Se ele tem outra coisa rodando, usar metade dos núcleos ou fixar em 4
MAX_WORKERS = min(4, cpu_count()) 

def process_file(file_path, mapa):
    """Processa um unico arquivo e retorna dict com resultados"""
    start_time = time.time()
    try:
        # Extrair texto
        with open_pdf(str(file_path)) as doc:
            # CPFL geralmente tem dados nas primeiras páginas ou no final (anexos)
            # 12 páginas é seguro para pegar Anexo I
            text = extract_all_text_from_pdf(doc, max_pages=12, use_ocr_fallback=False)
        
        # Aplicar mapa
        extracted = extract_with_map(text, mapa)
        
        # Contar campos preenchidos
        filled_fields = len([v for v in extracted.values() if v])
        
        duration = time.time() - start_time
        
        return {
            "status": "SUCCESS",
            "file": file_path.name,
            "path": str(file_path),
            "folder": file_path.parent.name, # ex: 09_paginas
            "type": file_path.parent.parent.name, # ex: TERMO_ADESAO
            "fields_count": filled_fields,
            "data": extracted,
            "duration": duration
        }
        
    except Exception as e:
        return {
            "status": "ERROR",
            "file": file_path.name,
            "path": str(file_path),
            "error": str(e),
            "duration": time.time() - start_time
        }

def main():
    print(f"=== INICIANDO EXTRAÇÃO MASSIVA CPFL PAULISTA ===")
    print(f"Mapa: {MAP_FILE.name}")
    print(f"Pasta Fonte: {SOURCE_DIR}")
    print(f"Workers: {MAX_WORKERS}")
    
    # Carregar mapa
    with open(MAP_FILE, 'r', encoding='utf-8') as f:
        mapa = json.load(f)
    
    # Listar todos os PDFs recursivamente
    all_pdfs = list(SOURCE_DIR.rglob("*.pdf"))
    total_files = len(all_pdfs)
    print(f"Total de arquivos encontrados: {total_files}")
    
    results = []
    success_count = 0
    error_count = 0
    
    start_global = time.time()
    
    # Processamento paralelo
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submeter todas as tarefas
        future_to_file = {
            executor.submit(process_file, pdf, mapa): pdf 
            for pdf in all_pdfs
        }
        
        # Processar conforme completam
        for i, future in enumerate(as_completed(future_to_file), 1):
            result = future.result()
            results.append(result)
            
            # Progresso visual simples
            if result['status'] == 'SUCCESS':
                success_count += 1
                symbol = "✅"
            else:
                error_count += 1
                symbol = "❌"
            
            # Barra de progresso estilo texto
            percent = (i / total_files) * 100
            bar_len = 30
            filled_len = int(bar_len * i // total_files)
            bar = '█' * filled_len + '-' * (bar_len - filled_len)
            
            sys.stdout.write(f"\r{symbol} [{bar}] {percent:.1f}% ({i}/{total_files})")
            sys.stdout.flush()
    
    print("\n\n=== CONCLUÍDO ===")
    duration_global = time.time() - start_global
    print(f"Tempo total: {duration_global:.1f}s")
    print(f"Sucesso: {success_count}")
    print(f"Erros: {error_count}")
    
    # Salvar JSON completo
    json_path = OUTPUT_DIR / "cpfl_full_extraction.json"
    print(f"Salvando JSON: {json_path}")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Gerar CSV resumo
    csv_path = OUTPUT_DIR / "cpfl_full_summary.csv"
    print(f"Salvando CSV: {csv_path}")
    
    # Coletar todos os campos possiveis para o header
    all_fields = set()
    for r in results:
        if 'data' in r:
            all_fields.update(r['data'].keys())
            
    header = ['arquivo', 'tipo', 'pasta', 'status', 'campos_preenchidos'] + sorted(list(all_fields))
    
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(header)
        
        for r in results:
            row = [
                r.get('file'),
                r.get('type'),
                r.get('folder'),
                r.get('status'),
                r.get('fields_count', 0)
            ]
            
            data = r.get('data', {})
            for field in sorted(list(all_fields)):
                val = data.get(field, '')
                # Se for lista (multiplas UCs), converter para string JSON ou texto
                if isinstance(val, list):
                    val = json.dumps(val, ensure_ascii=False)
                row.append(val)
                
            writer.writerow(row)

if __name__ == "__main__":
    main()
