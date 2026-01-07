"""
Padrões regex para extração de dados dos contratos.
Inclui âncoras fortes para evitar captura de dados incorretos.
"""
import re

# Flags padrão para regex multilinha
FLAGS = re.IGNORECASE | re.DOTALL | re.MULTILINE


class PatternsMixin:
    """Mixin com padrões regex organizados por tipo de campo."""
    
    # =========================================================================
    # IDENTIFICAÇÃO DO TIPO DE DOCUMENTO
    # =========================================================================
    
    DOCUMENT_TYPE_PATTERNS = {
        'DISTRATO': r'TERMO\s+DE\s+DISTRATO',
        'ADITIVO': r'TERMO\s+ADITIVO|ADITIVO\s+AO\s+CONTRATO',
        'CONFISSAO_DIVIDA': r'CONFISS[ÃA]O\s+DE\s+D[IÍ]VIDA',
        'TERMO_ADESAO': r'TERMO\s+DE\s+ADES[ÃA]O\s+AO\s+CONS[ÓO]RCIO',
        'TERMO_CONDICOES': r'TERMO\s+DE\s+CONDI[CÇ][ÕO]ES\s+COMERCIAIS',
    }
    
    # =========================================================================
    # IDENTIFICAÇÃO DO MODELO (Layout)
    # =========================================================================
    
    MODEL_INDICATORS = {
        'MODELO_1_VISUAL': [
            r'CONSORCIADA\s*\(VOC[ÊE]\)',
            r'Contratante:',
            r'Sua\s+parceria\s+com\s+a\s+Ra[íi]zen',
        ],
        'MODELO_2_TABULAR': [
            r'DA\s+QUALIFICA[CÇ][ÃA]O\s+DA\s+CONSORCIADA',
            r'DADOS\s+DA\s+CONSORCIADA:',
            r'DADOS\s+DO\s+REPRESENTANTE\s+LEGAL:',
        ],
        'GUARDA_CHUVA': [
            r'Contrato\s+Guarda[-\s]?Chuva',
            r'TABELA\s+DE\s+DESCONTOS',
            r'\d+\s+UCS',
        ],
    }
    
    # =========================================================================
    # PADRÕES PARA MODELO 1 (Visual/Clicksign)
    # Com âncoras fortes para buscar no bloco correto
    # =========================================================================
    
    MODELO_1_PATTERNS = {
        # Razão Social - buscar após "CONSORCIADA (VOCÊ)" ou "Contratante:"
        'razao_social': [
            r'(?:CONSORCIADA\s*\(VOC[ÊE]\)|Contratante:).*?Raz[ãa]o\s+Social:\s*(.+?)(?:\s*[–-]\s*CNPJ|\n|$)',
            r'(?:CONSORCIADA\s*\(VOC[ÊE]\)|Contratante:).*?Raz[ãa]o\s+Social:\s*([^\n]+)',
        ],
        
        # CNPJ - buscar padrão numérico após identificador
        'cnpj': [
            r'(?:CONSORCIADA|Contratante).*?CNPJ[^0-9]*(\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2})',
            r'CNPJ\s*(?:n[º°]|:)?\s*(\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2})',
        ],
        
        # Email
        'email': [
            r'E-?mail:\s*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)',
        ],
        
        # Endereço
        'endereco': [
            r'Endere[çc]o:\s*(.+?)(?:,\s*CEP|CEP:|$)',
        ],
        
        # CEP
        'cep': [
            r'CEP[:\s]*(\d{5}-?\d{3})',
        ],
        
        # Distribuidora
        'distribuidora': [
            r'Distrib\s*uidora:\s*([^\n]+)',
            r'Distribuidora:\s*([^\n]+)',
        ],
        
        # Número da Instalação
        'num_instalacao': [
            r'N[º°]\s*da\s+Instala[çc][ãa]o.*?:\s*(\d+)',
            r'Instala[çc][ãa]o.*?Consumidora[):]?\s*(\d+)',
        ],
        
        # Número do Cliente
        'num_cliente': [
            r'N[º°]\s*do\s+Cliente:\s*(\d+)',
        ],
        
        # Quantidade de Cotas
        'qtd_cotas': [
            r'Quantidade\s+de\s+Cotas:\s*([\d.,]+)',
        ],
        
        # Valor da Cota
        'valor_cota': [
            r'Valor\s+(?:da\s+)?Cota:\s*R?\$?\s*([\d.,]+)',
        ],
        
        # Pagamento Mensal
        'pagamento_mensal': [
            r'Valor\s+Base\s+do\s+Pagamento\s+Mensal:\s*R?\$?\s*([\d.,]+)',
            r'Pagamento\s+Mensal.*?:\s*R?\$?\s*([\d.,]+)',
        ],
        
        # Vencimento
        'vencimento': [
            r'Vencimento:\s*([^\n]+)',
        ],
        
        # Performance Alvo
        'performance_alvo': [
            r'Performance\s+Alvo:\s*([\d.,]+)\s*kWh',
        ],
        
        # Duração
        'duracao_meses': [
            r'Dura[çc][ãa]o:\s*(\d+)\s*meses',
            r'Vig[êe]ncia\s+Inicial:\s*(\d+)\s*meses',
        ],
    }
    
    # =========================================================================
    # PADRÕES PARA MODELO 2 (Tabular/Docusign)
    # =========================================================================
    
    MODELO_2_PATTERNS = {
        'razao_social': [
            r'DADOS\s+DA\s+CONSORCIADA:.*?Raz[ãa]o\s+Social:\s*([^\n]+)',
            r'Raz[ãa]o\s+Social:\s*([A-Z][^\n]+?)(?:\s*NIRE|\n)',
        ],
        
        'cnpj': [
            # Buscar CNPJ com formato específico após DADOS DA CONSORCIADA
            r'DADOS\s+DA\s+CONSORCIADA:.*?CNPJ:\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})',
            # Buscar qualquer CNPJ formatado corretamente
            r'CNPJ:?\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})',
            r'CNPJ/MF\s*n[º°]:?\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})',
        ],
        
        'email': [
            # Capturar apenas primeiro email
            r'E-?mail:\s*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)(?:\s|\n|$)',
        ],
        
        'endereco': [
            r'DADOS\s+DA\s+CONSORCIADA:.*?Endere[çc]o:\s*(.+?)(?:\n|CEP)',
            r'E\s*n\s*d\s*e\s*r\s*e\s*[çc]\s*o\s*:\s*([^\n]+)',
        ],
        
        'representante_nome': [
            r'DADOS\s+DO\s+REPRESENTANTE\s+LEGAL:.*?Nome:\s*([^\n]+)',
        ],
        
        'representante_cpf': [
            r'DADOS\s+DO\s+REPRESENTANTE\s+LEGAL:.*?CPF:\s*(\d{3}[.\s]?\d{3}[.\s]?\d{3}[-\s]?\d{2})',
        ],
        
        'participacao_percentual': [
            r'Participa[çc][ãa]o\s+no\s+Cons[óo]rcio/?\s*Rateio:\s*([\d.,]+)\s*%',
        ],
        
        # Padrões específicos para Modelo 2 que diferem do Modelo 1
        'valor_cota': [
            r'Valor\s+de\s+cada\s+cota:\s*R\$\s*([\d.,]+)',
            r'Valor\s+(?:da\s+)?Cota:\s*R\$\s*([\d.,]+)',
        ],
        
        'pagamento_mensal': [
            r'Pagamento\s+Mensal\s*\([^)]+\)\s*R\$\s*([\d.,]+)',
            r'R\$\s*([\d.,]+)(?:\s*por\s*m[êe]s)',
        ],
        
        'num_instalacao': [
            r'N[º°]\s*da\s+Instala[çc][ãa]o\s*\(?.*?\)?:?\s*(\d{5,})',
            r'Instala[çc][ãa]o.*?:\s*(\d{5,})',
        ],
        
        'num_cliente': [
            r'N[º°]\s*do\s+Cliente:\s*(\d+)',
        ],
    }
    
    # =========================================================================
    # PADRÕES PARA ANEXO I (Tabela de Instalações)
    # =========================================================================
    
    ANEXO_I_INDICATOR = r'ANEXO\s+I|UNIDADE\(S\)\s+CONSUMIDORA\(S\)'
    
    ANEXO_I_TABLE_HEADERS = [
        'Unidade Consumidora',
        'Nº Instalação',
        'Nº Cliente', 
        'Qtd Cotas',
        'Valor Cota',
        'Performance Alvo',
    ]
    
    # =========================================================================
    # PADRÕES PARA CONSÓRCIO (Dados da Raízen)
    # =========================================================================
    
    CONSORCIO_PATTERNS = {
        'consorcio_nome': [
            r'CONS[ÓO]RCIO.*?Raz[ãa]o\s+Social:\s*([^\n–-]+)',
            r'Cons[óo]rcio\s+RZ\s+([^\s–-]+)',
        ],
        
        'consorcio_cnpj': [
            r'CONS[ÓO]RCIO.*?CNPJ\s*n?[º°]?\s*(\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2})',
        ],
    }


def get_pattern_for_field(field_name: str, model: str = 'MODELO_1') -> list:
    """Retorna lista de padrões regex para um campo específico."""
    mixin = PatternsMixin()
    
    if model == 'MODELO_1':
        patterns = mixin.MODELO_1_PATTERNS.get(field_name, [])
    elif model == 'MODELO_2':
        patterns = mixin.MODELO_2_PATTERNS.get(field_name, [])
        if not patterns:
            patterns = mixin.MODELO_1_PATTERNS.get(field_name, [])
    else:
        patterns = mixin.MODELO_1_PATTERNS.get(field_name, [])
    
    return patterns


def extract_field(text: str, field_name: str, model: str = 'MODELO_1') -> str:
    """Extrai um campo do texto usando os padrões definidos."""
    patterns = get_pattern_for_field(field_name, model)
    
    for pattern in patterns:
        match = re.search(pattern, text, FLAGS)
        if match:
            value = match.group(1).strip()
            # Limpar caracteres especiais e quebras de linha
            value = re.sub(r'\s+', ' ', value)
            # Remover vírgula final
            value = value.rstrip(',')
            return value
    
    return ''
