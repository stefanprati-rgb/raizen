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
        # Razão Social - buscar após "CONSORCIADA (VOCÊ)" ou "Contratante:" ou isolado
        'razao_social': [
            r'(?:CONSORCIADA\s*\(VOC[ÊE]\)|Contratante:).*?Raz[ãa]o\s+Social:\s*(.+?)(?:\s*[–-]\s*CNPJ|\n|$)',
            r'(?:CONSORCIADA\s*\(VOC[ÊE]\)|Contratante:).*?Raz[ãa]o\s+Social:\s*([^\n]+)',
            r'Raz[ãa]o\s+Social:\s*([A-Z][A-Z0-9\s\.\-]+?)(?:\s*[-–]|CNPJ|NIRE|\n)',
            r'Raz[ãa]o\s+Social:\s*([^\n]{5,60})',
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
        
        # Email Secundário (segundo email na mesma linha ou próxima)
        'email_secundario': [
            r'E-?mail:\s*[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\s*\n\s*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)',
            r'E-?mail:\s*[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+[;,]\s*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)',
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
        # =====================================================================
        # DISTRIBUIDORA / CONCESSIONÁRIA
        # Sinônimos: Concessionária, Prestadora de Serviços, Operadora
        # =====================================================================
        'distribuidora': [
            r'Distrib\s*uidora:\s*([^\n]+)',
            r'Distribuidora:\s*([^\n]+)',
            r'Concession[áa]ria(?:\s+de\s+Energia)?:\s*([^\n]+)',
            r'Prestadora\s+de\s+Servi[çc]os:\s*([^\n]+)',
            r'Operadora\s+de\s+Distribui[çc][ãa]o:\s*([^\n]+)',
        ],
        
        # =====================================================================
        # UNIDADE CONSUMIDORA (UC) / NÚMERO DA INSTALAÇÃO
        # Sinônimos: Código da Instalação, Instalação, Código Único
        # =====================================================================
        'num_instalacao': [
            r'N[º°]\s*da\s+Instala[çc][ãa]o\s*\([^)]+\)[:\s]*(\d{5,})',
            r'N[º°]\s*da\s+Instala[çc][ãa]o.*?:\s*(\d+)',
            r'Instala[çc][ãa]o.*?Consumidora[):\s]*(\d+)',
            r'C[óo]digo\s+(?:da\s+)?Instala[çc][ãa]o[:\s]*(\d{5,})',
            r'Unidade\s+Consumidora[:\s]*(\d{5,})',
            r'UC[:\s]*(\d{5,})',
            r'C[óo]digo\s+[úu]nico[:\s]*(\d{5,})',
        ],
        
        # =====================================================================
        # NÚMERO DO CLIENTE
        # Sinônimos: Código do Cliente, Identificação do Cliente, Cadastro
        # =====================================================================
        'num_cliente': [
            r'N[º°]\s*do\s+Cliente:\s*(\d+)',
            r'C[óo]digo\s+(?:do\s+)?Cliente[:\s]*(\d+)',
            r'Identifica[çc][ãa]o\s+(?:do\s+)?Cliente[:\s]*(\d+)',
            r'Cadastro\s+(?:do\s+)?Cliente[:\s]*(\d+)',
            r'Cliente\s+N[º°][:\s]*(\d+)',
        ],
        
        # Quantidade de Cotas
        'qtd_cotas': [
            r'Quantidade\s+de\s+Cotas:\s*([\d.,]+)',
            r'Qtd\.?\s+Cotas[:\s]*([\d.,]+)',
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
            r'Performance\s+Alvo[:\s]*(\d[\d\.,]*\d?)\s*kWh',
            r'Performance[:\s]+(\d[\d\.,]*\d?)\s*kWh',
        ],
        
        # =====================================================================
        # PARTICIPAÇÃO CONTRATADA
        # Sinônimos: Quota, Percentual, Cota de Energia, Alocação Contratual
        # =====================================================================
        'participacao_percentual': [
            r'Participa[çc][ãa]o\s+no\s+Cons[óo]rcio[/\s]*Rateio[:\s]*([\d.,]+)\s*%',
            r'Rateio[:\s]*([\d.,]+)\s*%',
            r'Quota\s+Contratada[:\s]*([\d.,]+)\s*%',
            r'Percentual\s+(?:de\s+)?Participa[çc][ãa]o[:\s]*([\d.,]+)\s*%',
            r'Cota\s+(?:de\s+)?Energia[:\s]*([\d.,]+)\s*%',
            r'Energia\s+Contratada[:\s]*([\d.,]+)\s*%',
            r'Aloca[çc][ãa]o\s+Contratual[:\s]*([\d.,]+)\s*%',
        ],
        
        # =====================================================================
        # FIDELIDADE / DURAÇÃO DO CONTRATO
        # Sinônimos: Período de Fidelização, Prazo de Permanência, Tempo de Contrato
        # =====================================================================
        'duracao_meses': [
            r'Dura[çc][ãa]o:\s*(\d+)\s*meses',
            r'Vig[êe]ncia\s+Inicial:\s*(\d+)\s*meses',
            r'prazo\s+(?:m[íi]nimo\s+)?de\s+(\d+)\s*(?:\(.*?\))?\s*meses',
            r'fidelidade\s+(?:de\s+)?(\d+)\s*meses',
            r'(\d+)\s*meses\s+(?:de\s+)?(?:dura[çc][ãa]o|vig[êe]ncia)',
            r'Per[íi]odo\s+(?:de\s+)?Fideliza[çc][ãa]o[:\s]*(\d+)\s*meses',
            r'Prazo\s+(?:de\s+)?Perman[êe]ncia[:\s]*(\d+)\s*meses',
            r'Tempo\s+(?:de\s+)?Contrato[:\s]*(\d+)\s*meses',
            r'Per[íi]odo\s+Contratual\s+M[íi]nimo[:\s]*(\d+)\s*meses',
        ],
        
        # =====================================================================
        # DATA DE ADESÃO
        # Sinônimos: Data de Contratação, Data de Início, Data de Ingresso
        # =====================================================================
        'data_adesao': [
            r'Data\s+(?:de\s+)?Ades[ãa]o[:\s]*(\d{2}/\d{2}/\d{4})',
            r'Data\s+(?:de\s+)?Assinatura[:\s]*(\d{2}/\d{2}/\d{4})',
            r'Data\s+(?:de\s+)?Contrata[çc][ãa]o[:\s]*(\d{2}/\d{2}/\d{4})',
            r'Data\s+(?:de\s+)?In[íi]cio(?:\s+do\s+Contrato)?[:\s]*(\d{2}/\d{2}/\d{4})',
            r'Data\s+(?:de\s+)?Ingresso[:\s]*(\d{2}/\d{2}/\d{4})',
            r'assinado\s+(?:em|na\s+data\s+de)\s*(\d{2}/\d{2}/\d{4})',
            r'firmado\s+em\s*(\d{2}/\d{2}/\d{4})',
            r'Data\s+de\s+emiss[ãa]o[:\s]*(\d{2}/\d{2}/\d{4})',
        ],
        
        # =====================================================================
        # AVISO PRÉVIO
        # Sinônimos: Prazo de Notificação, Antecedência para Rescisão
        # =====================================================================
        'aviso_previo': [
            r'aviso\s+pr[ée]vio\s+(?:m[íi]nimo\s+)?(?:de\s+)?(\d+)\s*(?:\(.*?\))?\s*dias',
            r'antec[êe]nd[êe]ncia\s+(?:m[íi]nima\s+)?(?:de\s+)?(\d+)\s*dias',
            r'(\d+)\s*dias\s+(?:de\s+)?aviso\s+pr[ée]vio',
            r'Prazo\s+(?:de\s+)?Notifica[çc][ãa]o[:\s]*(\d+)\s*dias',
            r'Per[íi]odo\s+(?:de\s+)?Comunica[çc][ãa]o\s+Pr[ée]via[:\s]*(\d+)\s*dias',
            r'Antec[êe]nd[êe]ncia\s+para\s+Rescis[ãa]o[:\s]*(\d+)\s*dias',
            r'Notifica[çc][ãa]o\s+(?:de\s+)?T[ée]rmino[:\s]*(\d+)\s*dias',
        ],
        
        # =====================================================================
        # REPRESENTANTE LEGAL
        # Sinônimos: Procurador Legal, Responsável Legal, Signatário, Mandatário
        # =====================================================================
        'representante_nome': [
            r'Representante\s+Legal[:\s]*([A-Z][a-zA-ZÀ-ú\s]+?)(?:\s*[-–]|CPF|,|\n)',
            r'Nome\s+(?:do\s+)?Representante[:\s]*([A-Z][a-zA-ZÀ-ú\s]+?)(?:\n|CPF)',
            r'Procurador\s+Legal[:\s]*([A-Z][a-zA-ZÀ-ú\s]+?)(?:\s*[-–]|CPF|\n)',
            r'Respons[áa]vel\s+Legal[:\s]*([A-Z][a-zA-ZÀ-ú\s]+?)(?:\s*[-–]|CPF|\n)',
            r'Signat[áa]rio\s+Autorizado[:\s]*([A-Z][a-zA-ZÀ-ú\s]+?)(?:\s*[-–]|CPF|\n)',
            r'Mandat[áa]rio\s+Legal[:\s]*([A-Z][a-zA-ZÀ-ú\s]+?)(?:\s*[-–]|CPF|\n)',
            # Formato do Protocolo de Assinaturas: Nome CPF
            r'Representante\s+CPF\s*\n\s*([A-Z][a-zA-ZÀ-ú\s]+?)\s+\d{3}\.\d{3}\.\d{3}-\d{2}',
        ],
        
        # =====================================================================
        # CPF DO REPRESENTANTE
        # Sinônimos: CPF do Responsável, Cadastro PF do Representante
        # =====================================================================
        'representante_cpf': [
            r'CPF\s+(?:do\s+)?(?:Representante|Respons[áa]vel)?[:\s]*(\d{3}[.\s]?\d{3}[.\s]?\d{3}[-\s]?\d{2})',
            r'Representante.*?CPF[:\s]*(\d{3}[.\s]?\d{3}[.\s]?\d{3}[-\s]?\d{2})',
            r'Cadastro\s+(?:de\s+)?Pessoa\s+F[íi]sica[:\s]*(\d{3}[.\s]?\d{3}[.\s]?\d{3}[-\s]?\d{2})',
            r'Identifica[çc][ãa]o\s+(?:do\s+)?Procurador[:\s]*(\d{3}[.\s]?\d{3}[.\s]?\d{3}[-\s]?\d{2})',
            # Formato Protocolo: Nome + CPF na mesma linha
            r'[A-Z][a-zA-ZÀ-ú\s]+\s+(\d{3}\.\d{3}\.\d{3}-\d{2})',
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
        
        # Email Secundário (segundo email na próxima linha)
        'email_secundario': [
            r'E-?mail:\s*[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\s*\n\s*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)',
            r'E-?mail:\s*[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+[;,]\s*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)',
        ],
        
        'endereco': [
            r'DADOS\s+DA\s+CONSORCIADA:.*?Endere[çc]o:\s*(.+?)(?:\n|CEP)',
            r'E\s*n\s*d\s*e\s*r\s*e\s*[çc]\s*o\s*:\s*([^\n]+)',
        ],
        
        'representante_nome': [
            r'DADOS\s+DO\s+REPRESENTANTE\s+LEGAL:.*?Nome:\s*([^\n]+)',
        ],
        
        # Nome Secundário do Representante (segundo nome na próxima linha)
        'representante_nome_secundario': [
            r'DADOS\s+DO\s+REPRESENTANTE\s+LEGAL:.*?Nome:\s*[^\n]+\n\s*([A-Z][a-zA-Z\s]+?)(?:\n|CPF|$)',
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
            r'N[º°]\s*da\s+Instala[çc][ãa]o\s*\([^)]+\)[:\s]*(\d{5,})',  # Com parênteses
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
            
            # Normalizar valores numéricos para formato americano
            # Campos que precisam de normalização BR -> US
            numeric_fields = ['performance_alvo', 'qtd_cotas', 'valor_cota', 'pagamento_mensal', 'participacao_percentual']
            if field_name in numeric_fields:
                # Formato BR: 7.653,00 -> 7653.00
                if '.' in value and ',' in value and value.rfind('.') < value.rfind(','):
                    value = value.replace('.', '').replace(',', '.')
            
            return value
    
    return ''
