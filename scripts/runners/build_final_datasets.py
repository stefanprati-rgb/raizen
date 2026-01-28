import json
import time
import sys
import csv
import logging
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count

# Adicionar raiz ao path para importar modulos
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from raizen_power.extraction.extractor import ContractExtractor

# Definir raiz do projeto dinamicamente
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Configurações
SOURCE_DIRS = [
    PROJECT_ROOT / "data" / "processed",
    # Adicionar outras origens se necessário
]
OUTPUT_DIR = PROJECT_ROOT / "output" / "datasets_finais"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(OUTPUT_DIR / "execution.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def process_pdf_wrapper(pdf_path):
    """Wrapper para rodar no ProcessPoolExecutor."""
    try:
        extractor = ContractExtractor()
        result = extractor.extract_from_pdf(str(pdf_path))
        
        # Converter para dict serializável
        records = result.registros
        
        # Se não tiver registros, criar registro de erro/vazio
        if not records:
            return [{
                'arquivo_origem': Path(pdf_path).name,
                'status': 'VAZIO',
                'caminho_completo': str(pdf_path),
                'distribuidora': 'NAO_IDENTIFICADA',
                'alertas': result.alertas
            }]
            
        # Adicionar metadados extras
        for rec in records:
            rec['caminho_completo'] = str(pdf_path)
            rec['status'] = 'SUCESSO'
            # Garantir que tem distribuidora
            if not rec.get('distribuidora'):
                rec['distribuidora'] = 'NAO_IDENTIFICADA'
                
        return records
        
    except Exception as e:
        return [{
            'arquivo_origem': Path(pdf_path).name,
            'status': 'ERRO',
            'caminho_completo': str(pdf_path),
            'distribuidora': 'ERRO_PROCESSAMENTO',
            'alertas': [str(e)]
        }]

def normalize_distributor_name(name):
    """Padroniza nome da distribuidora para nome de arquivo."""
    if not name:
        return "NAO_IDENTIFICADA"
    return str(name).upper().strip().replace(" ", "_").replace("/", "-").replace("\\", "-")

def main():
    start_time = time.time()
    logger.info("=== INICIANDO CONSTRUÇÃO DE DATASETS FINAIS ===")
    
    # 1. Listar arquivos
    all_pdfs = []
    for src in SOURCE_DIRS:
        if src.exists():
            pdfs = list(src.rglob("*.pdf"))
            logger.info(f"Encontrados {len(pdfs)} PDFs em {src}")
            all_pdfs.extend(pdfs)
        else:
            logger.warning(f"Diretório fonte não existe: {src}")
            
    total_files = len(all_pdfs)
    logger.info(f"Total de arquivos para processar: {total_files}")
    
    if total_files == 0:
        logger.error("Nenhum arquivo encontrado. Encerrando.")
        return

    # 2. Processar em Paralelo
    max_workers = max(1, cpu_count() - 2)
    logger.info(f"Usando {max_workers} workers.")
    
    datasets = defaultdict(list)
    processed_count = 0
    success_count = 0
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_pdf = {executor.submit(process_pdf_wrapper, pdf): pdf for pdf in all_pdfs}
        
        for i, future in enumerate(as_completed(future_to_pdf), 1):
            try:
                results = future.result()
                
                for record in results:
                    dist = normalize_distributor_name(record.get('distribuidora'))
                    datasets[dist].append(record)
                    
                    if record.get('status') == 'SUCESSO':
                        success_count += 1
                
            except Exception as e:
                logger.error(f"Erro fatal no worker: {e}")
            
            processed_count += 1
            if i % 100 == 0:
                print(f"\rProgresso: {i}/{total_files} ({i/total_files*100:.1f}%)", end="")
    
    print("\nProcessamento concluído. Salvando arquivos...")
    
    # 3. Salvar Datasets
    stats = []
    
    # Colunas para o CSV (super set de campos)
    all_fields = set()
    for rows in datasets.values():
        for row in rows:
            all_fields.update(row.keys())
    
    # Priorizar campos importantes na ordem
    fieldnames = [
        'arquivo_origem', 'status', 'distribuidora', 'num_instalacao', 'num_cliente',
        'razao_social', 'cnpj', 'data_adesao', 'duracao_meses', 'aviso_previo',
        'cidade', 'uf', 'metodo_distribuidora', 'confianca_score', 'alertas', 'caminho_completo'
    ]
    # Adicionar o restante
    remaining = [f for f in sorted(list(all_fields)) if f not in fieldnames]
    fieldnames.extend(remaining)
    
    for dist_name, records in datasets.items():
        filename = f"dataset_{dist_name}.csv"
        filepath = OUTPUT_DIR / filename
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore', delimiter=';')
                writer.writeheader()
                writer.writerows(records)
            
            logger.info(f"Salvo: {filename} ({len(records)} registros)")
            stats.append({'distribuidora': dist_name, 'registros': len(records)})
            
        except Exception as e:
            logger.error(f"Erro ao salvar {filename}: {e}")

    # 4. Relatório Final
    duration = time.time() - start_time
    logger.info(f"=== FINALIZADO em {duration:.1f}s ===")
    logger.info(f"Total Arquivos: {total_files}")
    logger.info(f"Total Registros Sucesso: {success_count}")
    logger.info(f"Distribuidoras Identificadas: {len(datasets)}")
    
    # Salvar resumo
    with open(OUTPUT_DIR / "resumo_execucao.json", 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2)

if __name__ == "__main__":
    main()
