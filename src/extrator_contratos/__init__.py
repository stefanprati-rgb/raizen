"""
Extrator de Contratos Raízen - Módulo Principal
"""
from .extractor import ContractExtractor, ExtractionResult
from .patterns import PatternsMixin, extract_field
from .validators import (
    validate_record,
    validate_cnpj_checksum,
    validate_cpf_checksum,
    validate_cep,
    parse_currency,
    calculate_confidence_score,
    is_umbrella_contract
)
from .table_extractor import (
    extract_all_text,
    extract_all_text_from_pdf,
    extract_installations_from_anexo,
    extract_installations_from_pdf,
    extract_modelo_2_data,
    extract_modelo_2_data_from_pdf,
    open_pdf
)
from .report import generate_html_report

__all__ = [
    'ContractExtractor',
    'ExtractionResult',
    'PatternsMixin',
    'extract_field',
    'validate_record',
    'validate_cnpj_checksum',
    'validate_cpf_checksum',
    'validate_cep',
    'parse_currency',
    'calculate_confidence_score',
    'is_umbrella_contract',
    'extract_all_text',
    'extract_installations_from_anexo',
    'extract_modelo_2_data',
    'generate_html_report',
]
