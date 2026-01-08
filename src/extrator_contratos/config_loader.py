import yaml
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "input": {"path": "./contratos"},
    "output": {"path": "./output", "generate_html": True},
    "extraction": {"max_pages": 10},
    "validation": {"min_confidence_score": 70},
    "logging": {"level": "INFO"}
}

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Carrega configuração de um arquivo YAML.
    Se o arquivo não existir, retorna a configuração padrão e loga um aviso.
    """
    path = Path(config_path)
    config = DEFAULT_CONFIG.copy()
    
    if not path.exists():
        logger.warning(f"Arquivo de configuração '{config_path}' não encontrado. Usando defaults.")
        return config
        
    try:
        with open(path, "r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f)
            if user_config:
                # Merge recursivo simples (profundidade 1)
                for section, values in user_config.items():
                    if section in config and isinstance(values, dict) and isinstance(config[section], dict):
                        config[section].update(values)
                    else:
                        config[section] = values
        logger.info(f"Configuração carregada de '{config_path}'")
    except Exception as e:
        logger.error(f"Erro ao ler config '{config_path}': {e}. Usando defaults.")
    
    return config
