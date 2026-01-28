"""
Utilitários para sanitização de texto e filtragem de ruído em extração de PDFs.
"""
import re
from datetime import datetime
from typing import Tuple, Set


class TextSanitizer:
    """
    Remove padrões conhecidos do texto antes de extrair UCs.
    Evita capturar partes de CNPJ/CPF como UCs.
    """
    
    @staticmethod
    def sanitize(text: str) -> Tuple[str, Set[str]]:
        """
        Mascara CNPJ/CPF no texto.
        
        Returns: (texto_limpo, cnpjs_encontrados)
        """
        cnpjs_found = set()
        
        # CNPJ formatado: 12.345.678/0001-90
        cnpj_pattern = r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}'
        for match in re.finditer(cnpj_pattern, text):
            cnpj = re.sub(r'\D', '', match.group())
            cnpjs_found.add(cnpj)
        text = re.sub(cnpj_pattern, '<CNPJ>', text)
        
        # CNPJ contínuo: 14 dígitos
        cnpj_raw = r'\b\d{14}\b'
        for match in re.finditer(cnpj_raw, text):
            cnpjs_found.add(match.group())
        text = re.sub(cnpj_raw, '<CNPJ>', text)
        
        # CPF formatado: 123.456.789-01
        cpf_pattern = r'\d{3}\.\d{3}\.\d{3}-\d{2}'
        text = re.sub(cpf_pattern, '<CPF>', text)
        
        return text, cnpjs_found

    @staticmethod
    def repair_id_zeros(value: str, id_type: str = 'CNPJ') -> str:
        """
        Adiciona zeros à esquerda até completar 11 (CPF) ou 14 (CNPJ) dígitos.
        Útil para recuperar IDs truncados pelo Excel.
        """
        if not value: return ""
        clean = re.sub(r'\D', '', str(value))
        target_len = 14 if id_type.upper() == 'CNPJ' else 11
        if len(clean) > 0 and len(clean) < target_len:
            return clean.zfill(target_len)
        return clean

    @staticmethod
    def fuzzy_fix_ocr(value: str) -> str:
        """
        Corrige trocas comuns de OCR que invalidam CNPJ/CPF.
        Ex: 'O' -> '0', 'B' -> '8', 'I' -> '1'.
        """
        if not value: return ""
        replacements = {
            'O': '0', 'o': '0',
            'B': '8',
            'I': '1', 'i': '1', 'l': '1',
            'S': '5', 's': '5',
            'G': '6'
        }
        fixed = str(value)
        for char, replacement in replacements.items():
            fixed = fixed.replace(char, replacement)
        return re.sub(r'\D', '', fixed)


class NoiseFilter:
    """
    Identifica números que parecem UCs mas são outros campos.
    """
    
    # Códigos de sistema conhecidos (aparecem em >80% dos docs)
    # Inclui CEPs da sede Raízen em Piracicaba
    SYSTEM_CODES = {
        '160741512',   # Código de usina/contrato master
        '3523511633',  # Protocolo padrão
        '13414',       # CEP Raízen: 13414-157 (Av. Cezira Giovanoni Moretti)
        '13411',       # CEP Raízen: 13411-900 (Rodovia SP-308)
    }
    
    @staticmethod
    def is_date(number: str) -> bool:
        """Verifica se 8 dígitos formam uma data válida."""
        if len(number) != 8:
            return False
        
        # Tentar DDMMAAAA
        try:
            dt = datetime.strptime(number, "%d%m%Y")
            if 2000 <= dt.year <= 2035:
                return True
        except ValueError:
            pass
        
        # Tentar AAAAMMDD
        try:
            dt = datetime.strptime(number, "%Y%m%d")
            if 2000 <= dt.year <= 2035:
                return True
        except ValueError:
            pass
        
        return False
    
    @staticmethod
    def is_valid_cpf(cpf: str) -> bool:
        """Valida CPF pelo Módulo 11."""
        if len(cpf) != 11 or cpf == cpf[0] * 11:
            return False
        
        try:
            soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
            resto = soma % 11
            d1 = 0 if resto < 2 else 11 - resto
            if int(cpf[9]) != d1:
                return False
            
            soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
            resto = soma % 11
            d2 = 0 if resto < 2 else 11 - resto
            return int(cpf[10]) == d2
        except:
            return False

    @staticmethod
    def is_valid_cnpj(cnpj: str) -> bool:
        """Valida CNPJ pelo Módulo 11."""
        if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
            return False
        
        try:
            # Primeiro dígito
            pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
            soma = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
            resto = soma % 11
            d1 = 0 if resto < 2 else 11 - resto
            if int(cnpj[12]) != d1:
                return False
            
            # Segundo dígito
            pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
            soma = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
            resto = soma % 11
            d2 = 0 if resto < 2 else 11 - resto
            return int(cnpj[13]) == d2
        except:
            return False
    
    @staticmethod
    def is_noise(number: str, context: str = "", rules_class=None) -> Tuple[bool, str]:
        """
        Verifica se número é ruído.
        
        Args:
            number: Número a verificar
            context: Texto ao redor do número (para contexto)
            rules_class: Classe de regras de distribuidora (opcional)
        
        Returns: (é_ruído, motivo)
        """
        length = len(number)
        
        # Tamanho inválido
        if length < 5 or length > 12:
            return True, f"tamanho_invalido_{length}"
        
        # Verifica se é número de cliente (usando regras da distribuidora)
        if rules_class is not None:
            if rules_class.is_numero_cliente(number):
                return True, "numero_cliente"
        else:
            # Fallback: padrão CPFL (70/71)
            if len(number) == 9 and number.startswith(('70', '71')):
                return True, "numero_cliente_70_71"
        
        # Data
        if NoiseFilter.is_date(number):
            return True, "data_ddmmaaaa"
        
        # CPF válido
        if length == 11 and NoiseFilter.is_valid_cpf(number):
            return True, "cpf_valido"
        
        # Código de sistema (blacklist estática)
        if number in NoiseFilter.SYSTEM_CODES:
            return True, "codigo_sistema"
        
        # Percentual (% no contexto)
        if "%" in context:
            return True, "percentual"
        
        # Monetário (R$ próximo ao número)
        if context:
            if re.search(r'R\$\s*.{0,10}' + re.escape(number), context):
                return True, "valor_monetario"
            if re.search(re.escape(number) + r'.{0,10}reais', context, re.IGNORECASE):
                return True, "valor_monetario"
        
        # Começa com 0 (inválido para UC)
        if number.startswith('0'):
            return True, "comeca_com_zero"
        
        # Contexto de CEP
        if context:
            if re.search(r'CEP.{0,15}' + re.escape(number), context, re.IGNORECASE):
                return True, "parte_de_cep"
            if re.search(re.escape(number) + r'.{0,5}[-]\d{3}', context):
                return True, "parte_de_cep"
            if re.search(r'Piracicaba.{0,30}' + re.escape(number), context, re.IGNORECASE):
                return True, "endereco_sede"
        
        return False, "valido"
