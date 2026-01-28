import logging
import json
from datetime import datetime
from pathlib import Path

# Configuração
LOG_FILE = Path('output/logs/enrichment_log.jsonl')
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Configurar logger
logger = logging.getLogger('enrichment')
logger.setLevel(logging.INFO)

# Handler para arquivo JSONL
file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
formatter = logging.Formatter('%(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Handler para console (apenas avisos/erros para não poluir)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
logger.addHandler(console_handler)

def log_extraction(doc_id, field, value, confidence, status, metadata=None):
    """
    Loga uma tentativa de extração de forma estruturada.
    """
    record = {
        'timestamp': datetime.now().isoformat(),
        'doc_id': str(doc_id),
        'field': field,
        'value': value,
        'confidence': confidence,
        'status': status,  # SUCCESS, LOW_CONFIDENCE, NOT_FOUND, ERROR
        'metadata': metadata or {}
    }
    logger.info(json.dumps(record, ensure_ascii=False))

def log_error(doc_id, error_msg, exception=None):
    """
    Loga um erro de processamento.
    """
    record = {
        'timestamp': datetime.now().isoformat(),
        'doc_id': str(doc_id),
        'status': 'ERROR',
        'error': str(error_msg),
        'exception': str(exception) if exception else None
    }
    logger.info(json.dumps(record, ensure_ascii=False))

if __name__ == '__main__':
    # Teste simples
    log_extraction('TEST_DOC_001', 'fidelidade', '36', 0.95, 'SUCCESS', {'source': 'regex'})
    print(f"Log gravado em: {LOG_FILE}")
