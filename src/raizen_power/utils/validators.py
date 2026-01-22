"""
Validadores para garantir qualidade dos dados extraídos.
Inclui validação de CNPJ, CPF, email, e verificações matemáticas.
"""
import re
import logging
from typing import Optional, List, Dict, Any, Union

# Configurar logging
logger = logging.getLogger(__name__)


def normalize_cnpj(cnpj: Optional[str]) -> str:
    """Remove formatação do CNPJ, mantendo apenas dígitos."""
    if not cnpj:
        return ''
    return re.sub(r'[^\d]', '', str(cnpj))


def normalize_cpf(cpf: Optional[str]) -> str:
    """Remove formatação do CPF, mantendo apenas dígitos."""
    if not cpf:
        return ''
    return re.sub(r'[^\d]', '', str(cpf))


def validate_cnpj_checksum(cnpj: Optional[str]) -> bool:
    """Valida os dígitos verificadores do CNPJ."""
    cnpj = normalize_cnpj(cnpj)
    
    if len(cnpj) != 14:
        return False
    
    # Verifica CNPJs com todos dígitos iguais
    if len(set(cnpj)) == 1:
        return False
    
    # Cálculo do primeiro dígito verificador
    weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    sum1 = sum(int(cnpj[i]) * weights1[i] for i in range(12))
    d1 = 11 - (sum1 % 11)
    d1 = 0 if d1 >= 10 else d1
    
    if int(cnpj[12]) != d1:
        return False
    
    # Cálculo do segundo dígito verificador
    weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    sum2 = sum(int(cnpj[i]) * weights2[i] for i in range(13))
    d2 = 11 - (sum2 % 11)
    d2 = 0 if d2 >= 10 else d2
    
    return int(cnpj[13]) == d2


def validate_cpf_checksum(cpf: Optional[str]) -> bool:
    """Valida os dígitos verificadores do CPF."""
    cpf = normalize_cpf(cpf)
    
    if len(cpf) != 11:
        return False
    
    # Verifica CPFs com todos dígitos iguais
    if len(set(cpf)) == 1:
        return False
    
    # Cálculo do primeiro dígito verificador
    sum1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
    d1 = (sum1 * 10) % 11
    d1 = 0 if d1 == 10 else d1
    
    if int(cpf[9]) != d1:
        return False
    
    # Cálculo do segundo dígito verificador
    sum2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
    d2 = (sum2 * 10) % 11
    d2 = 0 if d2 == 10 else d2
    
    return int(cpf[10]) == d2


def validate_email(email: Optional[str]) -> bool:
    """
    Valida formato de email com regras mais rigorosas.
    - Mínimo 2 caracteres no domínio
    - Mínimo 2 caracteres na extensão
    """
    if not email:
        return False
    # Padrão mais rigoroso: local@dominio.ext (min 2 chars cada parte)
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]{2,}\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def parse_currency(value: Union[str, float, int, None], force_br: bool = True) -> Optional[float]:
    """
    Converte string de moeda para float.
    
    MODO PT-BR (padrão): Vírgula = decimal, Ponto = milhar
    - Brasileiro: R$ 1.234,56 | 7.653,00
    - Negativo entre parênteses: (123,45)
    - Com texto adicional: 7.653,00 kWh
    
    Args:
        value: String com valor monetário
        force_br: Se True, força interpretação PT-BR (vírgula = decimal)
        
    Returns:
        float ou None se conversão falhar
    """
    if value is None:
        return None
        
    str_val = str(value).strip()
    if not str_val:
        return None
    
    # Remover R$, $, espaços e texto adicional (ex: "kWh", "reais")
    clean = re.sub(r'[^\d.,\-()]', '', str_val)
    
    # Detectar negativo entre parênteses: (1.234,56)
    is_negative = clean.startswith('(') and clean.endswith(')')
    if is_negative:
        clean = clean[1:-1]
    
    # Extrair apenas números, pontos, vírgulas e sinal
    match = re.match(r'^([\d.,]+)', clean)
    if not match:
        return None
    
    clean = match.group(1)
    
    # Contar pontos e vírgulas
    num_dots = clean.count('.')
    num_commas = clean.count(',')
    
    if force_br:
        # =================================================================
        # MODO PT-BR ESTRITO: Vírgula SEMPRE é decimal, Ponto é milhar
        # =================================================================
        if num_commas > 0:
            # Vírgula presente: é o decimal
            # Ex: 1.234,56 -> 1234.56
            clean = clean.replace('.', '').replace(',', '.')
        elif num_dots > 0:
            # Sem vírgula, com pontos: verificar se é milhar ou decimal
            parts = clean.split('.')
            if len(parts[-1]) == 2:
                # Último grupo tem 2 dígitos: provavelmente centavos
                # Ex: 1234.56 -> 1234.56 (já está OK)
                pass
            elif len(parts[-1]) == 3:
                # Último grupo tem 3 dígitos: é milhar
                # Ex: 1.234 -> 1234
                clean = clean.replace('.', '')
            else:
                # Manter como está (provavelmente já é decimal)
                pass
    else:
        # Modo híbrido antigo (não recomendado)
        if num_commas > 0 and num_dots > 0:
            if clean.rfind(',') > clean.rfind('.'):
                clean = clean.replace('.', '').replace(',', '.')
            else:
                clean = clean.replace(',', '')
        elif num_commas == 1 and num_dots == 0:
            clean = clean.replace(',', '.')
    
    try:
        result = float(clean)
        return -result if is_negative else result
    except ValueError:
        logger.warning(f"EXTRACTION_FAILED: Falha ao converter moeda: '{value}' -> '{clean}'")
        return None


def validate_math_consistency(record: Dict[str, Any], relative_tolerance: float = 0.05) -> Optional[str]:
    """
    Valida consistência matemática entre valor_cota, qtd_cotas e pagamento_mensal.
    
    A fórmula esperada é:
    Pagamento Mensal ≈ Valor da Cota × Quantidade de Cotas
    
    Args:
        record: Registro com campos de valor
        relative_tolerance: Tolerância relativa (0.05 = 5% de variação permitida)
                           Reduzido para 5% para maior rigor na validação
    
    Retorna mensagem de erro se inconsistente, None se OK.
    """
    valor_cota = parse_currency(str(record.get('valor_cota', '')))
    qtd_cotas = parse_currency(str(record.get('qtd_cotas', '')))
    pagamento_mensal = parse_currency(str(record.get('pagamento_mensal', '')))
    
    # Se algum valor não foi extraído, não podemos validar
    if valor_cota is None or qtd_cotas is None or pagamento_mensal is None:
        return None
    
    # Evitar divisão por zero
    if qtd_cotas == 0 or valor_cota == 0:
        return None
    
    # Cálculo esperado (aproximado, pois há fórmulas de aluguel/performance)
    expected = valor_cota * qtd_cotas
    
    if expected > 0:
        difference_ratio = abs(pagamento_mensal - expected) / expected
        if difference_ratio > relative_tolerance:
            return (f"MATH_INCONSISTENCY: Cota R${valor_cota:.2f} × "
                    f"{qtd_cotas:.2f} cotas = R${expected:.2f}, "
                    f"mas Pagamento = R${pagamento_mensal:.2f} "
                    f"(diferença: {difference_ratio*100:.1f}%, tolerância: {relative_tolerance*100:.0f}%)")
    
    return None


def validate_record(record: Dict[str, Any]) -> List[str]:
    """
    Valida um registro completo e retorna lista de alertas/erros.
    
    Prefixos de erro:
    - MISSING_IN_DOC: Campo não existe no documento
    - EXTRACTION_FAILED: Campo existe mas extração falhou
    - INVALID_FORMAT: Formato inválido (checksum, email, etc)
    - MATH_INCONSISTENCY: Valores não batem matematicamente
    """
    alerts = []
    
    # Validação de CNPJ
    cnpj = record.get('cnpj', '')
    if cnpj:
        if not validate_cnpj_checksum(cnpj):
            alerts.append(f"INVALID_FORMAT: CNPJ inválido: {cnpj}")
    else:
        alerts.append("MISSING_IN_DOC: CNPJ ausente")
    
    # Validação de Razão Social
    razao_social = record.get('razao_social', '')
    if not razao_social:
        alerts.append("MISSING_IN_DOC: Razão Social ausente")
    elif len(razao_social) < 3:
        alerts.append(f"EXTRACTION_FAILED: Razão Social muito curta: {razao_social}")
    
    # Validação de Email (se presente)
    email = record.get('email', '')
    if email and not validate_email(email):
        alerts.append(f"INVALID_FORMAT: Email inválido: {email}")
    
    # Validação de CPF do representante (se presente)
    cpf = record.get('representante_cpf', '')
    if cpf and not validate_cpf_checksum(cpf):
        alerts.append(f"INVALID_FORMAT: CPF do representante inválido: {cpf}")
    
    # Validação matemática
    math_error = validate_math_consistency(record)
    if math_error:
        alerts.append(math_error)
    
    # Verificação de campos numéricos
    for campo in ['qtd_cotas', 'valor_cota', 'pagamento_mensal']:
        valor = record.get(campo, '')
        if valor:
            parsed = parse_currency(str(valor))
            if parsed is None:
                alerts.append(f"EXTRACTION_FAILED: Valor não numérico em {campo}: {valor}")
            elif parsed < 0:
                alerts.append(f"INVALID_FORMAT: Valor negativo em {campo}: {valor}")
    
    return alerts


def calculate_confidence_score(record: Dict[str, Any], alerts: List[str]) -> int:
    """
    Calcula score de confiança de 0-100 baseado nos dados extraídos e alertas.
    """
    score = 100
    
    # Campos obrigatórios (-30 cada)
    required_fields = ['razao_social', 'cnpj']
    for field in required_fields:
        if not record.get(field):
            score -= 30
    
    # Campos importantes (-10 cada)
    important_fields = ['email', 'num_instalacao', 'pagamento_mensal']
    for field in important_fields:
        if not record.get(field):
            score -= 10
    
    # Penalidade por alertas (máximo -50 pontos total)
    alert_penalty = min(len(alerts) * 5, 50)
    score -= alert_penalty
    
    # Garantir que score está entre 0 e 100
    return max(0, min(100, score))


def is_umbrella_contract(text: str) -> bool:
    """
    Detecta se o contrato é um "Guarda-Chuva" (agregador de múltiplas unidades).
    """
    indicators = [
        r'Contrato\s+Guarda[-\s]?Chuva',
        r'ANEXO\s+II\s*[-–]\s*TABELA\s+DE\s+DESCONTOS',  # SmartFit tem ANEXO II
        r'TABELA\s+DE\s+DESCONTOS',
        r'\d{2,}\s+UCS',  # Ex: "72 UCS"
        r'Volume\s+Agregado',
    ]
    
    for pattern in indicators:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    return False


def validate_cep(cep: Optional[str]) -> bool:
    """Valida formato de CEP brasileiro."""
    if not cep:
        return False
    clean_cep = re.sub(r'[^\d]', '', cep)
    return len(clean_cep) == 8


def validate_dates_order(
    emissao: Optional[str],
    vencimento: Optional[str],
    allow_same_day: bool = True
) -> bool:
    """
    Valida que data_emissao <= data_vencimento.
    
    Args:
        emissao: Data de emissão em formato DD/MM/AAAA ou AAAA-MM-DD
        vencimento: Data de vencimento em formato DD/MM/AAAA ou AAAA-MM-DD
        allow_same_day: Se True, permite emissão == vencimento
        
    Returns:
        bool: True se ordem está correta, False caso contrário
        
    Examples:
        >>> validate_dates_order("01/01/2024", "31/01/2024")
        True
        >>> validate_dates_order("31/01/2024", "01/01/2024")
        False
        >>> validate_dates_order("2024-01-01", "2024-01-31")
        True
    """
    if not emissao or not vencimento:
        return True  # Se alguma data ausente, não validar (não é erro de ordem)
    
    from datetime import datetime
    
    def parse_date(date_str: str) -> Optional[datetime]:
        """Parser flexível para datas BR (DD/MM/AAAA) e ISO (AAAA-MM-DD)."""
        date_str = str(date_str).strip()
        
        # Tentar formato brasileiro DD/MM/AAAA
        for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y']:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Tentar formato ISO AAAA-MM-DD
        for fmt in ['%Y-%m-%d', '%Y/%m/%d']:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    dt_emissao = parse_date(emissao)
    dt_vencimento = parse_date(vencimento)
    
    if not dt_emissao or not dt_vencimento:
        logger.warning(f"Falha ao parsear datas: emissao='{emissao}', vencimento='{vencimento}'")
        return False
    
    if allow_same_day:
        return dt_emissao <= dt_vencimento
    else:
        return dt_emissao < dt_vencimento

