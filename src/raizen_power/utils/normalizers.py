"""
Normalizadores de Dados - Contratos Raízen GD
Versão: 1.0

Este módulo padroniza os valores extraídos antes da validação e exportação.
Trata variações de formato comuns em documentos brasileiros.

Exemplos:
    - "R$ 1.234,56" → 1234.56
    - "12 meses" / "1 ano" / "doze meses" → 12
    - "03389281000104" → "03.389.281/0001-04"
    - "30 dias" / "trinta dias" → 30
"""
import re
from typing import Optional, Union
from datetime import datetime

# =============================================================================
# MAPEAMENTO DE NÚMEROS POR EXTENSO
# =============================================================================
NUMEROS_EXTENSO = {
    'zero': 0, 'um': 1, 'uma': 1, 'dois': 2, 'duas': 2, 'três': 3, 'tres': 3,
    'quatro': 4, 'cinco': 5, 'seis': 6, 'sete': 7, 'oito': 8, 'nove': 9,
    'dez': 10, 'onze': 11, 'doze': 12, 'treze': 13, 'quatorze': 14, 'catorze': 14,
    'quinze': 15, 'dezesseis': 16, 'dezessete': 17, 'dezoito': 18, 'dezenove': 19,
    'vinte': 20, 'trinta': 30, 'quarenta': 40, 'cinquenta': 50,
    'sessenta': 60, 'setenta': 70, 'oitenta': 80, 'noventa': 90,
    'cem': 100, 'cento': 100,
}

# Mapeamento de períodos para meses
PERIODOS_MESES = {
    'ano': 12, 'anos': 12,
    'semestre': 6, 'semestres': 6,
    'trimestre': 3, 'trimestres': 3,
    'bimestre': 2, 'bimestres': 2,
    'mês': 1, 'mes': 1, 'meses': 1,
}


def normalize_decimal(value: Union[str, float, int, None]) -> Optional[float]:
    """
    Normaliza valores decimais para formato Python float.
    
    Trata formatos brasileiros (1.234,56) e americanos (1,234.56).
    Remove símbolos monetários, percentuais e espaços.
    
    Args:
        value: Valor a normalizar (string, float ou int)
        
    Returns:
        Float normalizado ou None se inválido
        
    Examples:
        >>> normalize_decimal("R$ 1.234,56")
        1234.56
        >>> normalize_decimal("1,234.56")
        1234.56
        >>> normalize_decimal("45,5%")
        45.5
        >>> normalize_decimal("(123,45)")  # Negativo em parênteses
        -123.45
    """
    if value is None:
        return None
        
    if isinstance(value, (int, float)):
        return float(value)
    
    if not isinstance(value, str):
        return None
    
    # Limpar string
    text = str(value).strip()
    
    if not text:
        return None
    
    # Detectar valor negativo (parênteses ou sinal)
    is_negative = False
    if text.startswith('(') and text.endswith(')'):
        is_negative = True
        text = text[1:-1]
    elif text.startswith('-'):
        is_negative = True
        text = text[1:]
    
    # Remover símbolos monetários e espaços
    text = re.sub(r'[R$€£¥\s]', '', text)
    
    # Remover sufixos comuns
    text = re.sub(r'(kWh|KWH|kwh|MWh|reais|%|por\s*cento).*$', '', text, flags=re.IGNORECASE)
    
    # Remover caracteres não numéricos exceto . e ,
    text = re.sub(r'[^\d.,+-]', '', text)
    
    if not text:
        return None
    
    # Detectar formato brasileiro vs americano
    # Brasileiro: 1.234,56 (ponto como milhar, vírgula como decimal)
    # Americano: 1,234.56 (vírgula como milhar, ponto como decimal)
    
    # Contar ocorrências
    dots = text.count('.')
    commas = text.count(',')
    
    try:
        if dots == 0 and commas == 0:
            # Número inteiro
            result = float(text)
        elif dots == 0 and commas == 1:
            # Apenas vírgula: assume formato BR (vírgula = decimal)
            result = float(text.replace(',', '.'))
        elif dots == 1 and commas == 0:
            # Apenas ponto: pode ser milhar ou decimal
            # Se tem 3 dígitos após ponto, é milhar
            parts = text.split('.')
            if len(parts[1]) == 3:
                result = float(text.replace('.', ''))
            else:
                result = float(text)
        elif dots >= 1 and commas == 1:
            # Formato brasileiro: 1.234,56
            if text.rfind('.') < text.rfind(','):
                result = float(text.replace('.', '').replace(',', '.'))
            else:
                # Formato americano: 1,234.56
                result = float(text.replace(',', ''))
        elif commas >= 1 and dots == 1:
            # Formato americano: 1,234.56
            if text.rfind(',') < text.rfind('.'):
                result = float(text.replace(',', ''))
            else:
                # Formato brasileiro: 1.234,56
                result = float(text.replace('.', '').replace(',', '.'))
        else:
            # Múltiplos separadores: tentar formato brasileiro
            result = float(text.replace('.', '').replace(',', '.'))
        
        return -result if is_negative else result
        
    except ValueError:
        return None


def normalize_fidelity(value: Union[str, int, None]) -> Optional[int]:
    """
    Normaliza período de fidelidade para meses (inteiro).
    
    Args:
        value: Período em texto ou número
        
    Returns:
        Número de meses (int) ou None se inválido
        
    Examples:
        >>> normalize_fidelity("12 meses")
        12
        >>> normalize_fidelity("1 ano")
        12
        >>> normalize_fidelity("doze meses")
        12
        >>> normalize_fidelity("2 anos")
        24
        >>> normalize_fidelity("18")
        18
    """
    if value is None:
        return None
    
    if isinstance(value, int):
        return value
    
    if isinstance(value, float):
        return int(value)
    
    if not isinstance(value, str):
        return None
    
    text = str(value).strip().lower()
    
    if not text:
        return None
    
    # Tentar extrair número direto
    numero_match = re.search(r'(\d+)', text)
    numero = int(numero_match.group(1)) if numero_match else None
    
    # Verificar se tem número por extenso
    if numero is None:
        for extenso, val in NUMEROS_EXTENSO.items():
            if extenso in text:
                numero = val
                break
    
    if numero is None:
        return None
    
    # Verificar unidade de tempo
    for periodo, multiplicador in PERIODOS_MESES.items():
        if periodo in text:
            if periodo in ['ano', 'anos']:
                return numero * 12
            elif periodo in ['semestre', 'semestres']:
                return numero * 6
            elif periodo in ['trimestre', 'trimestres']:
                return numero * 3
            elif periodo in ['bimestre', 'bimestres']:
                return numero * 2
            else:
                return numero  # mês/meses
    
    # Se não encontrou unidade, assume meses
    return numero


def normalize_days(value: Union[str, int, None]) -> Optional[int]:
    """
    Normaliza período em dias para inteiro.
    
    Args:
        value: Período em texto ou número
        
    Returns:
        Número de dias (int) ou None se inválido
        
    Examples:
        >>> normalize_days("30 dias")
        30
        >>> normalize_days("trinta dias")
        30
        >>> normalize_days("1 mês")
        30
    """
    if value is None:
        return None
    
    if isinstance(value, int):
        return value
    
    if isinstance(value, float):
        return int(value)
    
    if not isinstance(value, str):
        return None
    
    text = str(value).strip().lower()
    
    if not text:
        return None
    
    # Tentar extrair número direto
    numero_match = re.search(r'(\d+)', text)
    numero = int(numero_match.group(1)) if numero_match else None
    
    # Verificar se tem número por extenso
    if numero is None:
        for extenso, val in NUMEROS_EXTENSO.items():
            if extenso in text:
                numero = val
                break
    
    if numero is None:
        return None
    
    # Verificar unidade
    if 'mês' in text or 'mes' in text or 'meses' in text:
        return numero * 30
    elif 'semana' in text:
        return numero * 7
    else:
        return numero  # Assume dias


def normalize_cnpj(value: Union[str, None]) -> Optional[str]:
    """
    Normaliza CNPJ para formato padrão: XX.XXX.XXX/XXXX-XX
    
    Args:
        value: CNPJ em qualquer formato
        
    Returns:
        CNPJ formatado ou None se inválido
        
    Examples:
        >>> normalize_cnpj("03389281000104")
        "03.389.281/0001-04"
        >>> normalize_cnpj("03.389.281/0001-04")
        "03.389.281/0001-04"
    """
    if value is None:
        return None
    
    # Extrair apenas dígitos
    digits = re.sub(r'\D', '', str(value))
    
    if len(digits) != 14:
        return None
    
    # Formatar
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}"


def normalize_cpf(value: Union[str, None]) -> Optional[str]:
    """
    Normaliza CPF para formato padrão: XXX.XXX.XXX-XX
    
    Args:
        value: CPF em qualquer formato
        
    Returns:
        CPF formatado ou None se inválido
        
    Examples:
        >>> normalize_cpf("12345678901")
        "123.456.789-01"
    """
    if value is None:
        return None
    
    # Extrair apenas dígitos
    digits = re.sub(r'\D', '', str(value))
    
    if len(digits) != 11:
        return None
    
    # Formatar
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"


def normalize_date(value: Union[str, None]) -> Optional[str]:
    """
    Normaliza data para formato ISO: YYYY-MM-DD
    
    Args:
        value: Data em formato brasileiro (DD/MM/YYYY) ou outros
        
    Returns:
        Data em formato ISO ou None se inválido
        
    Examples:
        >>> normalize_date("15/03/2024")
        "2024-03-15"
        >>> normalize_date("2024-03-15")
        "2024-03-15"
    """
    if value is None:
        return None
    
    text = str(value).strip()
    
    if not text:
        return None
    
    # Formatos a tentar
    formats = [
        '%d/%m/%Y',  # BR: 15/03/2024
        '%Y-%m-%d',  # ISO: 2024-03-15
        '%d-%m-%Y',  # Alt: 15-03-2024
        '%d.%m.%Y',  # Alt: 15.03.2024
        '%Y/%m/%d',  # Alt: 2024/03/15
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    return None


def normalize_percentage(value: Union[str, float, int, None]) -> Optional[float]:
    """
    Normaliza porcentagem para float (0-100).
    
    Args:
        value: Porcentagem em texto ou número
        
    Returns:
        Float representando a porcentagem ou None se inválido
        
    Examples:
        >>> normalize_percentage("45,5%")
        45.5
        >>> normalize_percentage("1,939")
        1.939
        >>> normalize_percentage(0.5)  # Se < 1, assume que é fração
        50.0
    """
    decimal = normalize_decimal(value)
    
    if decimal is None:
        return None
    
    # Se valor parece ser uma fração (< 1), converter para porcentagem
    # Mas apenas se for muito pequeno, pois 0.5% é válido
    if 0 < decimal < 1 and not (isinstance(value, str) and '%' in value):
        # Verifica se parece ser uma fração intencional
        # Ex: 0.5 -> 50%, mas 0.5% permanece 0.5%
        if ',' not in str(value) and '.' not in str(value):
            return decimal * 100
    
    return decimal


def normalize_phone(value: Union[str, None]) -> Optional[str]:
    """
    Normaliza telefone para formato: (XX) XXXXX-XXXX
    
    Args:
        value: Telefone em qualquer formato
        
    Returns:
        Telefone formatado ou None se inválido
    """
    if value is None:
        return None
    
    # Extrair apenas dígitos
    digits = re.sub(r'\D', '', str(value))
    
    if len(digits) == 11:
        # Celular com DDD
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    elif len(digits) == 10:
        # Fixo com DDD
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    elif len(digits) == 9:
        # Celular sem DDD
        return f"{digits[:5]}-{digits[5:]}"
    elif len(digits) == 8:
        # Fixo sem DDD
        return f"{digits[:4]}-{digits[4:]}"
    
    return None


def normalize_name(value: Union[str, None]) -> Optional[str]:
    """
    Normaliza nome próprio (capitalização adequada).
    
    Args:
        value: Nome em qualquer formato
        
    Returns:
        Nome com capitalização correta
        
    Examples:
        >>> normalize_name("JOÃO DA SILVA")
        "João da Silva"
        >>> normalize_name("maria de jesus")
        "Maria de Jesus"
    """
    if value is None:
        return None
    
    text = str(value).strip()
    
    if not text:
        return None
    
    # Palavras que devem ficar em minúsculo
    lower_words = {'de', 'da', 'do', 'das', 'dos', 'e', 'em', 'para', 'por'}
    
    words = text.lower().split()
    result = []
    
    for i, word in enumerate(words):
        if i == 0 or word not in lower_words:
            result.append(word.capitalize())
        else:
            result.append(word)
    
    return ' '.join(result)


def normalize_all(record: dict) -> dict:
    """
    Aplica todas as normalizações em um registro de contrato.
    
    Args:
        record: Dicionário com dados extraídos
        
    Returns:
        Dicionário com dados normalizados
    """
    normalized = record.copy()
    
    # Aplicar normalizadores por campo
    field_normalizers = {
        'cnpj': normalize_cnpj,
        'representante_cpf': normalize_cpf,
        'data_adesao': normalize_date,
        'duracao_meses': normalize_fidelity,
        'aviso_previo': normalize_days,
        'participacao_percentual': normalize_percentage,
        'razao_social': normalize_name,
        'representante_nome': normalize_name,
        'valor_cota': normalize_decimal,
        'pagamento_mensal': normalize_decimal,
        'performance_alvo': normalize_decimal,
    }
    
    for field, normalizer in field_normalizers.items():
        if field in normalized and normalized[field]:
            try:
                normalized[field] = normalizer(normalized[field])
            except Exception:
                pass  # Manter valor original se normalização falhar
    
    return normalized
