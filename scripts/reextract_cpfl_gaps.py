"""
Script de Reextração CPFL Paulista - V7 com Fallbacks
Corrige gaps identificados: distribuidora, fidelidade, participacao_percentual
"""
import json
import time
import sys
import csv
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
from datetime import datetime
import argparse

# Ajustar path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extrator_contratos.table_extractor import open_pdf, extract_all_text_from_pdf
from scripts.apply_map import extract_with_map

# Configurações
SOURCE_DIR = Path("cpfl_paulista_por_tipo")
MAP_FILE = Path("maps/CPFL_PAULISTA_completo_v7.json")
OUTPUT_DIR = Path("output/cpfl_paulista_final")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MAX_WORKERS = min(4, cpu_count())

def sanitize_value(value):
    """Remove quebras de linha e caracteres OCR problemáticos"""
    if not value:
        return value
    if isinstance(value, str):
        # Remover quebras de linha, tabs, múltiplos espaços
        value = ' '.join(value.split())
        # Remover caracteres OCR problemáticos
        value = value.replace('"', '').replace('„', '').replace('`', '')
        value = value.strip()
    return value

def apply_fallbacks(extracted, file_path):
    """Aplica fallbacks inteligentes para campos faltantes"""
    
    # FALLBACK 1: Distribuidora sempre é CPFL PAULISTA (baseado na pasta)
    if not extracted.get('distribuidora'):
        # Verificar se o caminho contém "cpfl_paulista"
        if 'cpfl_paulista' in str(file_path).lower():
            extracted['distribuidora'] = 'CPFL PAULISTA'
    
    # FALLBACK 2: Se tiver num_conta_contrato mas não num_instalacao, usar como UC
    if not extracted.get('num_instalacao') and extracted.get('num_conta_contrato'):
        extracted['num_instalacao'] = extracted['num_conta_contrato']
    
    # FALLBACK 3: Normalizar fidelidade para valores padronizados
    fidelidade = extracted.get('fidelidade', '')
    if fidelidade:
        fidelidade_upper = fidelidade.upper().strip()
        if 'ISENTO' in fidelidade_upper or 'SEM' in fidelidade_upper or 'N/A' in fidelidade_upper:
            extracted['fidelidade'] = 'ISENTO'
        elif 'INEXISTENTE' in fidelidade_upper:
            extracted['fidelidade'] = 'ISENTO'
    
    return extracted

def process_file(file_path, mapa):
    """Processa um único arquivo e retorna dict com resultados"""
    start_time = time.time()
    try:
        # Extrair texto
        with open_pdf(str(file_path)) as doc:
            text = extract_all_text_from_pdf(doc, max_pages=12, use_ocr_fallback=False)
        
        # Aplicar mapa
        extracted = extract_with_map(text, mapa)
        
        # Sanitizar valores
        for key in extracted:
            extracted[key] = sanitize_value(extracted[key])
        
        # Aplicar fallbacks
        extracted = apply_fallbacks(extracted, file_path)
        
        # Contar campos preenchidos
        campos_obrigatorios = [
            'num_instalacao', 'num_cliente', 'distribuidora', 'razao_social', 'cnpj',
            'data_adesao', 'fidelidade', 'aviso_previo_dias', 'representante_nome',
            'representante_cpf', 'participacao_percentual'
        ]
        filled_fields = len([c for c in campos_obrigatorios if extracted.get(c)])
        
        duration = time.time() - start_time
        
        return {
            "status": "SUCCESS",
            "file": file_path.name,
            "path": str(file_path),
            "folder": file_path.parent.name,
            "type": file_path.parent.parent.name,
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

def analyze_coverage(results):
    """Analisa cobertura dos campos obrigatórios"""
    campos_obrigatorios = [
        'num_instalacao', 'num_cliente', 'distribuidora', 'razao_social', 'cnpj',
        'data_adesao', 'fidelidade', 'aviso_previo_dias', 'representante_nome',
        'representante_cpf', 'participacao_percentual'
    ]
    
    print("\n📊 COBERTURA POR CAMPO:")
    print("=" * 60)
    
    total = len(results)
    for campo in campos_obrigatorios:
        count = sum(1 for r in results if r.get('data', {}).get(campo))
        pct = (count / total * 100) if total > 0 else 0
        status = '✅' if pct > 90 else '⚠️' if pct > 50 else '❌'
        print(f"  {status} {campo}: {count}/{total} ({pct:.1f}%)")

def main():
    parser = argparse.ArgumentParser(description='Reextração CPFL com fallbacks')
    parser.add_argument('--sample', type=int, default=0, help='Número de arquivos para amostra (0 = todos)')
    parser.add_argument('--output', type=str, default='cpfl_reextracted', help='Nome do arquivo de saída')
    args = parser.parse_args()
    
    print(f"=== REEXTRAÇÃO CPFL PAULISTA v7 ===")
    print(f"Mapa: {MAP_FILE.name}")
    print(f"Pasta Fonte: {SOURCE_DIR}")
    print(f"Workers: {MAX_WORKERS}")
    
    # Carregar mapa
    with open(MAP_FILE, 'r', encoding='utf-8') as f:
        mapa = json.load(f)
    
    # Listar todos os PDFs recursivamente
    all_pdfs = list(SOURCE_DIR.rglob("*.pdf"))
    
    # Aplicar amostragem se solicitado
    if args.sample > 0:
        import random
        random.seed(42)  # Reprodutibilidade
        all_pdfs = random.sample(all_pdfs, min(args.sample, len(all_pdfs)))
    
    total_files = len(all_pdfs)
    print(f"Total de arquivos a processar: {total_files}")
    
    results = []
    success_count = 0
    error_count = 0
    
    start_global = time.time()
    
    # Processamento paralelo
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_file = {
            executor.submit(process_file, pdf, mapa): pdf 
            for pdf in all_pdfs
        }
        
        for i, future in enumerate(as_completed(future_to_file), 1):
            result = future.result()
            results.append(result)
            
            if result['status'] == 'SUCCESS':
                success_count += 1
                symbol = "✅"
            else:
                error_count += 1
                symbol = "❌"
            
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
    
    # Análise de cobertura
    analyze_coverage(results)
    
    # Salvar JSON completo
    json_path = OUTPUT_DIR / f"{args.output}.json"
    print(f"\n💾 Salvando JSON: {json_path}")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Gerar CSV resumo
    csv_path = OUTPUT_DIR / f"{args.output}.csv"
    print(f"💾 Salvando CSV: {csv_path}")
    
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
                if isinstance(val, list):
                    val = '; '.join(str(v) for v in val)
                row.append(val)
                
            writer.writerow(row)
    
    print("\n✅ Extração completa!")

if __name__ == "__main__":
    main()
