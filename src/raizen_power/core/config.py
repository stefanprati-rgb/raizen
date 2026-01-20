"""
Módulo de configuração centralizada.

Carrega configurações do arquivo config/settings.yaml e fornece valores padrão.
Permite ajustar parâmetros sem alterar código-fonte.

Uso:
    from raizen_power.core.config import settings
    
    print(settings.ocr.resolution_dpi)  # 200
    print(settings.blacklist.threshold_percent)  # 80
"""
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Caminho padrão para o arquivo de configuração
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "settings.yaml"


@dataclass
class OCRConfig:
    """Configurações de OCR."""
    resolution_dpi: int = 200
    timeout_seconds: int = 30
    max_workers: int = 2


@dataclass
class BlacklistConfig:
    """Configurações de blacklist dinâmica."""
    threshold_percent: int = 80
    min_docs_for_analysis: int = 10
    output_file: str = "output/blacklist_codigos.json"


@dataclass
class ValidationConfig:
    """Configurações de validação."""
    min_confidence_score: int = 70
    validate_cnpj: bool = True
    validate_math: bool = True
    tolerance_percent: float = 5.0


@dataclass
class GeminiConfig:
    """Configurações da API Gemini."""
    model: str = "gemini-2.0-flash"
    rpm: int = 5  # Requisições por minuto
    rpd: int = 20  # Requisições por dia
    tpm: int = 250000  # Tokens por minuto
    delay_seconds: int = 15
    max_text_length: int = 50000


@dataclass
class ParallelConfig:
    """Configurações de processamento paralelo."""
    text_max_workers: int = 8
    ocr_max_workers: int = 2


@dataclass
class ExtractionConfig:
    """Configurações de extração."""
    max_pages: int = 10
    batch_size: int = 50


@dataclass
class LoggingConfig:
    """Configurações de logging."""
    level: str = "INFO"
    file: str = "extractor.log"


@dataclass
class Settings:
    """Configurações centralizadas do projeto."""
    ocr: OCRConfig = field(default_factory=OCRConfig)
    blacklist: BlacklistConfig = field(default_factory=BlacklistConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    gemini: GeminiConfig = field(default_factory=GeminiConfig)
    parallel: ParallelConfig = field(default_factory=ParallelConfig)
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    @classmethod
    def from_yaml(cls, config_path: Path = None) -> 'Settings':
        """
        Carrega configurações de um arquivo YAML.
        
        Args:
            config_path: Caminho para o arquivo YAML (default: config/settings.yaml)
            
        Returns:
            Instância de Settings com valores do YAML
        """
        config_path = config_path or CONFIG_FILE
        
        if not config_path.exists():
            logger.warning(f"Arquivo de configuração não encontrado: {config_path}")
            logger.info("Usando valores padrão")
            return cls()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            return cls(
                ocr=OCRConfig(
                    resolution_dpi=data.get('ocr', {}).get('resolution_dpi', 200),
                    timeout_seconds=data.get('ocr', {}).get('timeout_seconds', 30),
                    max_workers=data.get('ocr', {}).get('max_workers', 2),
                ),
                blacklist=BlacklistConfig(
                    threshold_percent=data.get('blacklist', {}).get('threshold_percent', 80),
                    min_docs_for_analysis=data.get('blacklist', {}).get('min_docs_for_analysis', 10),
                    output_file=data.get('blacklist', {}).get('output_file', 'output/blacklist_codigos.json'),
                ),
                validation=ValidationConfig(
                    min_confidence_score=data.get('validation', {}).get('min_confidence_score', 70),
                    validate_cnpj=data.get('validation', {}).get('validate_cnpj', True),
                    validate_math=data.get('validation', {}).get('validate_math', True),
                    tolerance_percent=data.get('validation', {}).get('tolerance_percent', 5.0),
                ),
                gemini=GeminiConfig(
                    model=data.get('gemini', {}).get('model', 'gemini-2.0-flash'),
                    rpm=data.get('gemini', {}).get('rpm', 5),
                    rpd=data.get('gemini', {}).get('rpd', 20),
                    tpm=data.get('gemini', {}).get('tpm', 250000),
                    delay_seconds=data.get('gemini', {}).get('delay_seconds', 15),
                    max_text_length=data.get('gemini', {}).get('max_text_length', 50000),
                ),
                parallel=ParallelConfig(
                    text_max_workers=data.get('parallel', {}).get('text_max_workers', 8),
                    ocr_max_workers=data.get('parallel', {}).get('ocr_max_workers', 2),
                ),
                extraction=ExtractionConfig(
                    max_pages=data.get('extraction', {}).get('max_pages', 10),
                    batch_size=data.get('extraction', {}).get('batch_size', 50),
                ),
                logging=LoggingConfig(
                    level=data.get('logging', {}).get('level', 'INFO'),
                    file=data.get('logging', {}).get('file', 'extractor.log'),
                ),
            )
        except Exception as e:
            logger.error(f"Erro ao carregar configurações: {e}")
            return cls()
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            'ocr': self.ocr.__dict__,
            'blacklist': self.blacklist.__dict__,
            'validation': self.validation.__dict__,
            'gemini': self.gemini.__dict__,
            'parallel': self.parallel.__dict__,
            'extraction': self.extraction.__dict__,
            'logging': self.logging.__dict__,
        }


# Singleton: instância global de configurações
settings = Settings.from_yaml()


def reload_settings(config_path: Path = None):
    """Recarrega configurações do arquivo YAML."""
    global settings
    settings = Settings.from_yaml(config_path)
    logger.info("Configurações recarregadas")
    return settings


# Aliases para compatibilidade com código existente
def get_ocr_config() -> OCRConfig:
    return settings.ocr

def get_blacklist_config() -> BlacklistConfig:
    return settings.blacklist

def get_gemini_config() -> GeminiConfig:
    return settings.gemini

def get_validation_config() -> ValidationConfig:
    return settings.validation
