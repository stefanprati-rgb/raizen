"""
Validadores para garantir qualidade dos dados extraídos.
Inclui validação de CNPJ, CPF, email, e verificações matemáticas.
"""
import re
from typing import Optional, List, Dict, Any


def normalize_cnpj(cnpj: str) -> str:
    """Remove formatação do CNPJ, mantendo apenas dígitos."""
    if not cnpj:
        return ''
    return re.sub(r'[^\d]', '', cnpj)


def normalize_cpf(cpf: str) -> str:
    """Remove formatação do CPF, mantendo apenas dígitos."""
    if not cpf:
        return ''
    return re.sub(r'[^\d]', '', cpf)


def validate_cnpj_checksum(cnpj: str) -> bool:
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


def validate_cpf_checksum(cpf: str) -> bool:
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


def validate_email(email: str) -> bool:
    """Valida formato básico de email."""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(pattern, email))


def parse_currency(value: str) -> Optional[float]:
    """Converte string de moeda para float."""
    if not value:
        return None
    
    # Remover R$, espaços e texto não numérico
    clean = re.sub(r'[R$\s]', '', str(value))
    
    # Extrair apenas a parte numérica inicial
    match = re.match(r'^([\d.,]+)', clean)
    if not match:
        return None
    
    clean = match.group(1)
    
    # Trata formato brasileiro (1.234,56) e americano (1,234.56)
    if ',' in clean and '.' in clean:
        # Formato brasileiro: 1.234,56
        if clean.rfind('.') < clean.rfind(','):
            clean = clean.replace('.', '').replace(',', '.')
        else:
            # Formato americano: 1,234.56
            clean = clean.replace(',', '')
    elif ',' in clean:
        clean = clean.replace(',', '.')
    
    try:
        return float(clean)
    except ValueError:
        return None


def validate_math_consistency(record: Dict[str, Any], tolerance: float = 5.0) -> Optional[str]:
    """
    Valida consistência matemática entre valor_cota, qtd_cotas e pagamento_mensal.
    
    A fórmula esperada é:
    Pagamento Mensal ≈ Valor da Cota × Quantidade de Cotas
    
    Retorna mensagem de erro se inconsistente, None se OK.
    """
    valor_cota = parse_currency(str(record.get('valor_cota', '')))
    qtd_cotas = parse_currency(str(record.get('qtd_cotas', '')))
    pagamento_mensal = parse_currency(str(record.get('pagamento_mensal', '')))
    
    # Se algum valor não foi extraído, não podemos validar
    if valor_cota is None or qtd_cotas is None or pagamento_mensal is None:
        return None
    
    # Evitar divisão por zero
    if qtd_cotas == 0:
        return None
    
    # Cálculo esperado (aproximado, pois há fórmulas de aluguel/performance)
    # O valor base é aproximadamente: valor_cota * qtd_cotas
    expected = valor_cota * qtd_cotas
    
    # Tolerância relativa de 20% devido às fórmulas de aluguel/performance
    relative_tolerance = 0.20
    
    if expected > 0:
        difference_ratio = abs(pagamento_mensal - expected) / expected
        if difference_ratio > relative_tolerance:
            return (f"Inconsistência matemática: Cota R${valor_cota:.2f} × "
                    f"{qtd_cotas:.2f} cotas = R${expected:.2f}, "
                    f"mas Pagamento = R${pagamento_mensal:.2f}")
    
    return None


def validate_record(record: Dict[str, Any]) -> List[str]:
    """
    Valida um registro completo e retorna lista de alertas/erros.
    """
    alerts = []
    
    # Validação de CNPJ
    cnpj = record.get('cnpj', '')
    if cnpj:
        if not validate_cnpj_checksum(cnpj):
            alerts.append(f"CNPJ inválido: {cnpj}")
    else:
        alerts.append("CNPJ ausente")
    
    # Validação de Razão Social
    razao_social = record.get('razao_social', '')
    if not razao_social:
        alerts.append("Razão Social ausente")
    elif len(razao_social) < 3:
        alerts.append(f"Razão Social muito curta: {razao_social}")
    
    # Validação de Email (se presente)
    email = record.get('email', '')
    if email and not validate_email(email):
        alerts.append(f"Email inválido: {email}")
    
    # Validação de CPF do representante (se presente)
    cpf = record.get('representante_cpf', '')
    if cpf and not validate_cpf_checksum(cpf):
        alerts.append(f"CPF do representante inválido: {cpf}")
    
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
                alerts.append(f"Valor não numérico em {campo}: {valor}")
            elif parsed < 0:
                alerts.append(f"Valor negativo em {campo}: {valor}")
    
    return alerts


def calculate_confidence_score(record: Dict[str, Any], alerts: List[str]) -> int:
    """
    Calcula score de confiança de 0-100 baseado nos dados extraídos e alertas.
    """
    score = 100
    
    # Campos obrigatórios
    required_fields = ['razao_social', 'cnpj']
    for field in required_fields:
        if not record.get(field):
            score -= 30
    
    # Campos importantes
    important_fields = ['email', 'num_instalacao', 'pagamento_mensal']
    for field in important_fields:
        if not record.get(field):
            score -= 10
    
    # Penalidade por alertas
    score -= len(alerts) * 5
    
    # Garantir que score está entre 0 e 100
    return max(0, min(100, score))


def is_umbrella_contract(text: str) -> bool:
    """
    Detecta se o contrato é um "Guarda-Chuva" (agregador de múltiplas unidades).
    """
    indicators = [
        r'Contrato\s+Guarda[-\s]?Chuva',
        r'TABELA\s+DE\s+DESCONTOS',
        r'\d{2,}\s+UCS',  # Ex: "72 UCS"
        r'Volume\s+Agregado',
    ]
    
    for pattern in indicators:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    return False
