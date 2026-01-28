import pandas as pd
import json
import argparse
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from scripts.contract_extractor import ContractFieldExtractor
from scripts.enrichment_logger import log_error
import time

# Config
DATASET_PATH = Path('output/cpfl_paulista_final/cpfl_dataset_final_padronizado.xlsx')
OUTPUT_DIR = Path('output/enrichment')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_RESULTS = OUTPUT_DIR / 'temp_results.jsonl'

def process_single_doc(file_info):
    """
    Função worker para processar um único documento.
    file_info: tuple (index, path)
    """
    idx, path_str = file_info
    path = Path(path_str)
    
    if not path.exists():
        log_error(str(path), "File not found")
        return idx, {}

    try:
        extractor = ContractFieldExtractor()
        data = extractor.extract_fields(str(path))
        return idx, data
    except Exception as e:
        log_error(str(path), f"Worker error: {e}")
        return idx, {}

def main():
    parser = argparse.ArgumentParser(description="Enrich CPFL dataset with missing fields")
    parser.add_argument('--sample', type=int, default=0, help="Run on N samples only")
    parser.add_argument('--workers', type=int, default=4, help="Number of parallel workers")
    args = parser.parse_args()

    print(f"Carregando dataset de referência: {DATASET_PATH}...")
    df = pd.read_excel(DATASET_PATH)
    
    # Reconstruir caminho completo dos arquivos
    # O dataset tem 'nome_arquivo_origem' e 'pasta_origem'
    # Mas precisamos saber a raiz. Assumindo C:\Projetos\Raizen\cpfl_paulista_por_tipo
    # Ou tentando encontrar o arquivo.
    # O dataset original tinha o caminho completo? O 'explode' removeu?
    # Vamos verificar se conseguimos reconstruir.
    # Se 'pasta_origem' for o caminho completo da pasta, ótimo.
    
    # Se pasta_origem for apenas o nome da pasta (ex: TERMO_ADESAO), precisamos da raiz
    ROOT_DIR = Path(r"C:\Projetos\Raizen\cpfl_paulista_por_tipo")
    
    files_to_process = []
    
    print("Preparando lista de arquivos...")
    for idx, row in df.iterrows():
        fname = row.get('nome_arquivo_origem')
        folder = row.get('pasta_origem')
        
    # Carregar mapeamento de caminhos do JSON original (mais confiável)
    json_results_path = Path('output/cpfl_paulista_final/cpfl_v5_full_results.json')
    path_map = {}
    if json_results_path.exists():
        print(f"Carregando mapa de arquivos de {json_results_path}...")
        with open(json_results_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                # Normalizar nome do arquivo
                fname = item.get('file')
                path = item.get('path')
                if fname and path:
                    path_map[fname] = path
    
    files_to_process = []
    ROOT_DIR = Path(r"C:\Projetos\Raizen") # Base do projeto
    
    print("Preparando lista de arquivos...")
    for idx, row in df.iterrows():
        fname = row.get('nome_arquivo_origem')
        
        if pd.isna(fname) or str(fname).strip() == '':
            continue
            
        fname = str(fname)
        
        # Tentar obter caminho do mapa
        rel_path = path_map.get(fname)
        
        candidate = None
        if rel_path:
            candidate = ROOT_DIR / rel_path
        
        # Se não achou no mapa ou arquivo não existe, tentar heurísticas antigas (fallback)
        if not candidate or not candidate.exists():
             folder = row.get('pasta_origem')
             if not pd.isna(folder):
                 # Tentar adivinhar
                 # Buscar em todas as pastas possíveis
                 for parent in ['TERMO_ADESAO', 'TERMO_CONDICOES', 'ADITIVO', 'DISTRATO', 'TERMO_CONDICOES_SOLAR']:
                     p = ROOT_DIR / 'cpfl_paulista_por_tipo' / parent / str(folder) / fname
                     if p.exists():
                         candidate = p
                         break
        
        if candidate and candidate.exists():
            files_to_process.append((idx, str(candidate)))
        else:
            # Logar missing (opcional)
            pass


    total_docs = len(files_to_process)
    print(f"Arquivos encontrados para processar: {total_docs}")

    if args.sample > 0:
        files_to_process = files_to_process[:args.sample]
        print(f"MODO AMOSTRA: Processando apenas {len(files_to_process)} documentos.")

    results_map = {}
    
    print(f"Iniciando extração com {args.workers} workers...")
    start_time = time.time()
    
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process_single_doc, item): item for item in files_to_process}
        
        processed = 0
        for future in as_completed(futures):
            idx, data = future.result()
            if data:
                results_map[idx] = data
            
            processed += 1
            if processed % 10 == 0:
                print(f"Progresso: {processed}/{len(files_to_process)} concluídos...", end='\r')

    print(f"\nProcessamento concluído em {time.time() - start_time:.1f}s")
    
    # Integrar resultados ao DataFrame
    print("Atualizando DataFrame...")
    
    cols_to_update = ['fidelidade', 'aviso_previo_dias', 'representante_nome', 'representante_cpf', 'participacao_percentual']
    
    updates_count = {col: 0 for col in cols_to_update}
    
    for idx, data in results_map.items():
        for col in cols_to_update:
            if col in data: # Se encontrou valor
                # Só atualiza se o valor atual for nulo ou vazio
                current_val = df.at[idx, col]
                if pd.isna(current_val) or str(current_val).strip() == '':
                    df.at[idx, col] = data[col]
                    updates_count[col] += 1
    
    print("Resumo das atualizações:")
    for col, count in updates_count.items():
        print(f"  - {col}: {count} novos valores")

    output_file = OUTPUT_DIR / f"cpfl_dataset_enriched_{'sample' if args.sample else 'full'}.xlsx"
    df.to_excel(output_file, index=False)
    print(f"Dataset salvo em: {output_file}")

if __name__ == "__main__":
    main()
