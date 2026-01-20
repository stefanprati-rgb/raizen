"""
UC Extractor V5 - Versão de Teste
Consolida 3 abordagens:
1. Dual Extractor (Cliente vs Instalação)
2. Mascaramento prévio de CNPJ/CPF
3. Validação negativa (datas, percentuais, etc)

Status: BETA - Para validação antes de solidificar
"""

import re
import json
import time
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

import fitz  # PyMuPDF

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


# ============================================================================
# REGRAS DE NEGÓCIO CPFL
# ============================================================================

class CPFLBusinessRules:
    """
    Regras de negócio para classificar números CPFL
    """
    
    @staticmethod
    def is_numero_cliente(number: str) -> bool:
        """
        Nº do Cliente CPFL:
        - SEMPRE 9 dígitos
        - SEMPRE começa com 70 ou 71
        """
        return len(number) == 9 and number.startswith(('70', '71'))
    
    @staticmethod
    def is_instalacao(number: str, from_label: bool = False) -> bool:
        """
        Nº da Instalação (UC) CPFL:
        - 5-8 dígitos (padrão comum, inclui formato legado)
        - OU 10 dígitos começando com 40
        - NUNCA começa com 70/71 (a menos que venha de label explícito)
        
        Args:
            from_label: Se True, veio de label explícito "Nº da Instalação"
                       e aceita formatos mais flexíveis
        """
        length = len(number)
        
        # Se veio de label explícito, aceitar formatos legados (5-12 dígitos)
        if from_label:
            # Aceita 5-12 dígitos quando de label explícito
            if 5 <= length <= 12:
                # Ainda rejeita se parece CNPJ (14 dígitos) mas aceita o resto
                return True
            return False
        
        # Modo padrão (sem label): NÃO pode começar com 70/71 (é Cliente)
        if number.startswith(('70', '71')):
            return False
        
        # 5-8 dígitos: instalação (inclui formato legado)
        if 5 <= length <= 8:
            return True
        
        # 10 dígitos começando com 40: instalação especial
        if length == 10 and number.startswith('40'):
            return True
        
        return False
    
    @staticmethod
    def classify(number: str, from_label: bool = False) -> Tuple[str, float]:
        """
        Classifica um número
        Returns: (tipo, confiança)
        """
        if CPFLBusinessRules.is_numero_cliente(number):
            return 'cliente', 0.99
        if CPFLBusinessRules.is_instalacao(number, from_label=from_label):
            return 'instalacao', 0.95
        return 'unknown', 0.0


# ============================================================================
# MASCARAMENTO PRÉVIO (CNPJ, CPF)
# ============================================================================

class TextSanitizer:
    """
    Remove padrões conhecidos do texto antes de extrair UCs
    Evita capturar partes de CNPJ/CPF como UCs
    """
    
    @staticmethod
    def sanitize(text: str) -> Tuple[str, Set[str]]:
        """
        Mascara CNPJ/CPF no texto
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


# ============================================================================
# BLACKLIST DINÂMICA (CÓDIGOS RECORRENTES)
# ============================================================================

class DynamicBlacklist:
    """
    Detecta e filtra códigos que aparecem em mais de N% dos documentos.
    Esses são tipicamente códigos de sistema (usina, formulário, protocolo).
    """
    
    BLACKLIST_FILE = Path("output/blacklist_codigos.json")
    THRESHOLD_PERCENT = 80  # Se aparece em >80% dos docs, é código de sistema
    
    def __init__(self):
        self.blacklist: Set[str] = set()
        self.frequency: Dict[str, int] = {}
        self.total_docs: int = 0
        self._load_blacklist()
    
    def _load_blacklist(self):
        """Carrega blacklist de arquivo se existir"""
        if self.BLACKLIST_FILE.exists():
            try:
                with open(self.BLACKLIST_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.blacklist = set(data.get('blacklist', []))
                    self.frequency = data.get('frequency', {})
                    self.total_docs = data.get('total_docs', 0)
            except:
                pass
    
    def save_blacklist(self):
        """Salva blacklist em arquivo"""
        self.BLACKLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(self.BLACKLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'blacklist': list(self.blacklist),
                'frequency': self.frequency,
                'total_docs': self.total_docs
            }, f, indent=2)
    
    def update_frequency(self, numbers: List[str]):
        """Atualiza contagem de frequência após processar um documento"""
        self.total_docs += 1
        seen_in_doc = set(numbers)
        
        for num in seen_in_doc:
            self.frequency[num] = self.frequency.get(num, 0) + 1
    
    def analyze_and_update_blacklist(self):
        """Analisa frequências e atualiza blacklist"""
        if self.total_docs < 10:  # Precisa de pelo menos 10 docs
            return
        
        threshold = self.total_docs * (self.THRESHOLD_PERCENT / 100)
        
        new_blacklist = set()
        for num, count in self.frequency.items():
            if count >= threshold:
                new_blacklist.add(num)
        
        self.blacklist = new_blacklist
        self.save_blacklist()
    
    def is_blacklisted(self, number: str) -> bool:
        """Verifica se número está na blacklist"""
        return number in self.blacklist
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas da blacklist"""
        return {
            'total_docs': self.total_docs,
            'blacklist_size': len(self.blacklist),
            'blacklist': list(self.blacklist)[:10]  # Primeiros 10
        }


# ============================================================================
# VALIDAÇÃO NEGATIVA (RUÍDO)
# ============================================================================

class NoiseFilter:
    """
    Identifica números que parecem UCs mas são outros campos
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
        """Verifica se 8 dígitos formam uma data válida"""
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
        """Valida CPF pelo Módulo 11"""
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
    def is_noise(number: str, context: str = "") -> Tuple[bool, str]:
        """
        Verifica se número é ruído
        Returns: (é_ruído, motivo)
        """
        length = len(number)
        
        # Tamanho inválido (mas aceita 5-6 se for de label explícito - tratado no caller)
        if length < 5 or length > 12:
            return True, f"tamanho_invalido_{length}"
        
        # Nº do Cliente (70/71) - é ruído para UC
        if CPFLBusinessRules.is_numero_cliente(number):
            return True, "numero_cliente_70_71"
        
        # Data
        if NoiseFilter.is_date(number):
            return True, "data_ddmmaaaa"
        
        # CPF válido
        if length == 11 and NoiseFilter.is_valid_cpf(number):
            return True, "cpf_valido"
        
        # Código de sistema (blacklist)
        if number in NoiseFilter.SYSTEM_CODES:
            return True, "codigo_sistema"
        
        # Percentual (% no contexto)
        if "%" in context:
            return True, "percentual"
        
        # Monetário (R$ próximo ao número)
        if context:
            # Se R$ aparece até 10 chars antes do número
            if re.search(r'R\$\s*.{0,10}' + re.escape(number), context):
                return True, "valor_monetario"
            # Se "reais" aparece após o número
            if re.search(re.escape(number) + r'.{0,10}reais', context, re.IGNORECASE):
                return True, "valor_monetario"
        
        # Começa com 0 (inválido para UC)
        if number.startswith('0'):
            return True, "comeca_com_zero"
        
        # Contexto de CEP (evitar capturar partes de CEP)
        if context:
            # Se "CEP" aparece próximo ao número
            if re.search(r'CEP.{0,15}' + re.escape(number), context, re.IGNORECASE):
                return True, "parte_de_cep"
            if re.search(re.escape(number) + r'.{0,5}[-]\d{3}', context):  # Formato XXXXX-XXX
                return True, "parte_de_cep"
            # Se Piracicaba aparece próximo (endereço da sede)
            if re.search(r'Piracicaba.{0,30}' + re.escape(number), context, re.IGNORECASE):
                return True, "endereco_sede"
        
        return False, "valido"


# ============================================================================
# EXTRATOR DUAL (CLIENTE + INSTALAÇÃO)
# ============================================================================

class DualExtractor:
    """
    Extrai separadamente Nº do Cliente e Nº da Instalação
    """
    
    # Padrões para Instalação (ordem de prioridade)
    # NOTA: Se o número vem de label explícito, aceitamos MESMO sendo 70/71* ou curto
    INSTALACAO_PATTERNS = [
        # Label explícito "Instalação" - ACEITA 5-12 DÍGITOS (alta confiança)
        (r'(?:N[ºo°]\s*(?:da\s+)?)?(?:Instalação|Instalacao)\s*(?:da\s+)?(?:Unidade\s+)?(?:Consumidora)?[:\s]+(\d{5,12})', 'label_instalacao', True),
        # Label "Conta Contrato" ou "Número Conta Contrato (UC)" - ACEITA 5-12 DÍGITOS
        (r'(?:Número\s+)?Conta\s+Contrato\s*(?:\(UC\))?[:\s]+(\d{5,12})', 'conta_contrato', True),
        # Label UC - ACEITA 5-12 DÍGITOS
        (r'(?:UC|U\.C)[:\s]+(\d{5,12})', 'label_uc', True),
        # Formato 40XXXXXXXX (sempre instalação)
        (r'\b(40\d{8})\b', 'formato_40', False),
    ]
    
    # Padrões para Cliente (para classificar, não para extrair)
    CLIENTE_PATTERNS = [
        (r'(?:N[ºo°]\s*(?:do\s+)?)?Cliente[:\s]+(\d{9})', 'label_cliente'),
        (r'\b((?:70|71)\d{7})\b', 'formato_70_71'),
    ]
    
    def _extract_list_after_label(self, text: str) -> List[str]:
        """
        Extrai LISTA de UCs após label "Instalação" (separadas por ; , ou espaço)
        Ex: "Nº da Instalação: 22661549; 20572891; 37231995"
        """
        results = []
        
        # Padrão: label seguido de lista de números
        pattern = r'(?:N[ºo°]\s*(?:da\s+)?)?(?:Instalação|Instalacao)\s*(?:\(Unidade\s+Consumidora\))?[:\s]+([^:\n]{5,500})'
        
        for match in re.finditer(pattern, text, re.IGNORECASE):
            block = match.group(1)
            
            # Extrair todos os números de 5-12 dígitos do bloco (inclui legados)
            numbers = re.findall(r'\b(\d{5,12})\b', block)
            
            for num in numbers:
                # Como veio de label explícito, usar validação mais flexível
                # Apenas rejeitar se for CNPJ (14 dígitos) ou data válida
                if len(num) == 14:  # CNPJ
                    continue
                if NoiseFilter.is_date(num):
                    continue
                if CPFLBusinessRules.is_instalacao(num, from_label=True):
                    results.append(num)
        
        return results
    
    def extract(self, text: str) -> Dict[str, List[Dict]]:
        """
        Extrai ambos os tipos separadamente
        """
        results = {
            'instalacao': [],
            'cliente': [],
            'unknown': []
        }
        
        seen = set()
        
        # PRIMEIRO: Extrair listas de UCs (novo!)
        list_ucs = self._extract_list_after_label(text)
        for number in list_ucs:
            if number not in seen:
                results['instalacao'].append({
                    'number': number,
                    'source': 'lista_instalacao',
                    'confidence': 0.98
                })
                seen.add(number)
        
        # DEPOIS: Buscar Instalação individual (padrões simples)
        for pattern, source, skip_noise_filter in self.INSTALACAO_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                number = match.group(1)
                number = re.sub(r'\D', '', number)
                
                if number in seen:
                    continue
                
                # Se veio de label explícito, pular filtro de ruído (pode ser 71* válido)
                if not skip_noise_filter:
                    is_noise, reason = NoiseFilter.is_noise(number)
                    if is_noise:
                        continue
                
                results['instalacao'].append({
                    'number': number,
                    'source': source,
                    'confidence': 0.98
                })
                seen.add(number)
        
        # Buscar Cliente (para classificar/descartar)
        for pattern, source in self.CLIENTE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                number = match.group(1)
                number = re.sub(r'\D', '', number)
                
                if number in seen:
                    continue
                    
                if CPFLBusinessRules.is_numero_cliente(number):
                    results['cliente'].append({
                        'number': number,
                        'source': source,
                        'confidence': 0.99
                    })
                    seen.add(number)
        
        return results


# ============================================================================
# EXTRATOR DE FALLBACK
# ============================================================================

class FallbackExtractor:
    """
    Fallback: buscar qualquer número 7-10 dígitos que passe nos filtros
    """
    
    def extract(self, text: str, already_found: Set[str]) -> List[Dict]:
        """
        Busca números genéricos que possam ser UCs
        """
        results = []
        
        # Buscar qualquer número de 5-10 dígitos (inclui legados curtos)
        pattern = r'\b(\d{5,10})\b'
        
        for match in re.finditer(pattern, text):
            number = match.group(1)
            
            if number in already_found:
                continue
            
            # Validar: não é ruído?
            is_noise, reason = NoiseFilter.is_noise(number)
            if is_noise:
                continue
            
            # Validar: é instalação válida?
            if not CPFLBusinessRules.is_instalacao(number):
                continue
            
            results.append({
                'number': number,
                'source': 'fallback',
                'confidence': 0.60
            })
        
        return results


# ============================================================================
# EXTRATOR PRINCIPAL V5
# ============================================================================

@dataclass
class ExtractionResult:
    file: str
    path: str
    ucs: List[str]
    uc_count: int
    confidence: float
    method: str
    clientes_descartados: List[str]
    ruido_filtrado: int
    duration: float
    errors: List[str]


class UCExtractorV5:
    """
    Extrator V5 - Combina todas as estratégias
    """
    
    def __init__(self, use_dynamic_blacklist: bool = True):
        self.sanitizer = TextSanitizer()
        self.dual_extractor = DualExtractor()
        self.fallback_extractor = FallbackExtractor()
        self.use_dynamic_blacklist = use_dynamic_blacklist
        if use_dynamic_blacklist:
            self.dynamic_blacklist = DynamicBlacklist()
        else:
            self.dynamic_blacklist = None
    
    def extract_from_pdf(self, pdf_path: str) -> ExtractionResult:
        """Pipeline completo de extração"""
        start_time = time.time()
        errors = []
        ucs_final = []
        clientes = []
        method = "v5_dual_fallback"
        ruido_count = 0
        
        try:
            doc = fitz.open(pdf_path)
            
            # Extrair texto de todas as páginas
            full_text = ""
            for page in doc:
                full_text += page.get_text() + "\n"
            doc.close()
            
            # PASSO 1: Sanitizar (mascarar CNPJ/CPF)
            clean_text, cnpjs_found = self.sanitizer.sanitize(full_text)
            
            # PASSO 2: Extração dual (Cliente + Instalação)
            dual_result = self.dual_extractor.extract(clean_text)
            
            # Coletar instalações com alta confiança
            for item in dual_result['instalacao']:
                ucs_final.append(item['number'])
            
            # Coletar clientes descartados
            for item in dual_result['cliente']:
                clientes.append(item['number'])
            
            # PASSO 3: Fallback (se não encontrou instalações)
            if not ucs_final:
                already_found = set([c['number'] for c in dual_result['cliente']])
                fallback_ucs = self.fallback_extractor.extract(clean_text, already_found)
                for item in fallback_ucs:
                    ucs_final.append(item['number'])
                if fallback_ucs:
                    method = "v5_fallback"
            
            # Deduplicar
            ucs_final = list(dict.fromkeys(ucs_final))
            
            # PASSO 4: Filtrar pela blacklist dinâmica
            if self.dynamic_blacklist:
                # Atualizar frequência (para aprendizado)
                self.dynamic_blacklist.update_frequency(ucs_final)
                
                # Filtrar números que estão na blacklist
                ucs_pre_filter = len(ucs_final)
                ucs_final = [uc for uc in ucs_final if not self.dynamic_blacklist.is_blacklisted(uc)]
                ruido_count = ucs_pre_filter - len(ucs_final)
            
            # Calcular confiança média
            avg_conf = 0.98 if method == "v5_dual_fallback" else 0.60
            
        except Exception as e:
            errors.append(f"Error: {str(e)[:50]}")
            ucs_final = []
            avg_conf = 0
        
        duration = time.time() - start_time
        
        return ExtractionResult(
            file=Path(pdf_path).name,
            path=str(pdf_path),
            ucs=ucs_final,
            uc_count=len(ucs_final),
            confidence=avg_conf,
            method=method,
            clientes_descartados=clientes,
            ruido_filtrado=ruido_count,
            duration=duration,
            errors=errors
        )
    
    def finalize_batch(self):
        """
        Finaliza processamento de lote - atualiza blacklist dinâmica.
        Chamar após processar todos os documentos de um lote.
        """
        if self.dynamic_blacklist:
            self.dynamic_blacklist.analyze_and_update_blacklist()
            stats = self.dynamic_blacklist.get_stats()
            print(f"\n[STATS] Blacklist atualizada: {stats['blacklist_size']} codigos em {stats['total_docs']} docs")
            if stats['blacklist']:
                print(f"   Códigos: {stats['blacklist']}")


# ============================================================================
# TESTE NOS CASOS PROBLEMÁTICOS
# ============================================================================

def test_validation_samples():
    """Testa V5 nos 20 documentos de validação"""
    
    extractor = UCExtractorV5()
    
    # Carregar dados de validação
    validation_path = Path("output/validacao_gemini/validacao_dados.json")
    if not validation_path.exists():
        print("Arquivo de validação não encontrado!")
        return
    
    with open(validation_path, 'r', encoding='utf-8') as f:
        validation = json.load(f)
    
    print("=" * 70)
    print("TESTE V5 - COMPARATIVO COM V3/V4")
    print("=" * 70)
    print()
    
    total_v3 = 0
    total_v5 = 0
    
    for v in validation[:10]:  # Rodada 1
        result = extractor.extract_from_pdf(v['path_original'])
        
        v3_count = len(v['ucs_extraidas'])
        v5_count = result.uc_count
        
        total_v3 += v3_count
        total_v5 += v5_count
        
        status = "[OK]" if v5_count > 0 else "[FALHA]"
        
        print(f"{v['id']:02d}. {v['arquivo'][:45]}...")
        print(f"    V3: {v3_count} UCs | V5: {v5_count} UCs {status}")
        if result.clientes_descartados:
            print(f"    Clientes descartados: {result.clientes_descartados}")
        if result.ucs:
            print(f"    UCs V5: {result.ucs}")
        print()
    
    print("=" * 70)
    print(f"TOTAL: V3={total_v3} | V5={total_v5}")
    print("=" * 70)


if __name__ == "__main__":
    test_validation_samples()
