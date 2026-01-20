"""
UC Extractor V5 - Versão Refatorada
Consolida 3 abordagens:
1. Dual Extractor (Cliente vs Instalação)
2. Mascaramento prévio de CNPJ/CPF
3. Validação negativa (datas, percentuais, etc)

Status: STABLE
Refatorado: Classes utilitárias movidas para raizen_power.utils
"""

import re
import json
import time
from pathlib import Path
from typing import List, Dict, Set
from dataclasses import dataclass

import fitz  # PyMuPDF

# Importar classes refatoradas
from raizen_power.utils.distributor_rules import CPFLRules, get_rules
from raizen_power.utils.text_sanitizer import TextSanitizer, NoiseFilter
from raizen_power.utils.blacklist import DynamicBlacklist

# Alias para compatibilidade
CPFLBusinessRules = CPFLRules


# ============================================================================
# EXTRATOR DUAL (CLIENTE + INSTALAÇÃO)
# ============================================================================

class DualExtractor:
    """
    Extrai separadamente Nº do Cliente e Nº da Instalação.
    Suporta múltiplas distribuidoras via injeção de regras.
    """
    
    # Padrões para Instalação (ordem de prioridade)
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
    
    # Padrões para Cliente (para classificar/descartar)
    CLIENTE_PATTERNS = [
        (r'(?:N[ºo°]\s*(?:do\s+)?)?Cliente[:\s]+(\d{9})', 'label_cliente'),
        (r'\b((?:70|71)\d{7})\b', 'formato_70_71'),
    ]
    
    def __init__(self, rules_class=None):
        """
        Args:
            rules_class: Classe de regras da distribuidora (default: CPFLRules)
        """
        self.rules = rules_class or CPFLRules
    
    def _extract_list_after_label(self, text: str) -> List[str]:
        """
        Extrai LISTA de UCs após label "Instalação" (separadas por ; , ou espaço)
        Ex: "Nº da Instalação: 22661549; 20572891; 37231995"
        """
        results = []
        
        pattern = r'(?:N[ºo°]\s*(?:da\s+)?)?(?:Instalação|Instalacao)\s*(?:\(Unidade\s+Consumidora\))?[:\s]+([^:\n]{5,500})'
        
        for match in re.finditer(pattern, text, re.IGNORECASE):
            block = match.group(1)
            numbers = re.findall(r'\b(\d{5,12})\b', block)
            
            for num in numbers:
                if len(num) == 14:  # CNPJ
                    continue
                if NoiseFilter.is_date(num):
                    continue
                if self.rules.is_instalacao(num, from_label=True):
                    results.append(num)
        
        return results
    
    def extract(self, text: str) -> Dict[str, List[Dict]]:
        """Extrai ambos os tipos separadamente."""
        results = {
            'instalacao': [],
            'cliente': [],
            'unknown': []
        }
        
        seen = set()
        
        # PRIMEIRO: Extrair listas de UCs
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
                
                if not skip_noise_filter:
                    is_noise, reason = NoiseFilter.is_noise(number, rules_class=self.rules)
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
                    
                if self.rules.is_numero_cliente(number):
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
    """Fallback: buscar qualquer número 5-10 dígitos que passe nos filtros."""
    
    def __init__(self, rules_class=None):
        self.rules = rules_class or CPFLRules
    
    def extract(self, text: str, already_found: Set[str]) -> List[Dict]:
        """Busca números genéricos que possam ser UCs."""
        results = []
        
        pattern = r'\b(\d{5,10})\b'
        
        for match in re.finditer(pattern, text):
            number = match.group(1)
            
            if number in already_found:
                continue
            
            is_noise, reason = NoiseFilter.is_noise(number, rules_class=self.rules)
            if is_noise:
                continue
            
            if not self.rules.is_instalacao(number):
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
    Extrator V5 - Combina todas as estratégias.
    Suporta múltiplas distribuidoras via parâmetro distributor.
    """
    
    def __init__(self, use_dynamic_blacklist: bool = True, distributor: str = "CPFL"):
        """
        Args:
            use_dynamic_blacklist: Se True, usa blacklist dinâmica
            distributor: Nome da distribuidora (ex: 'CPFL', 'CEMIG')
        """
        self.rules = get_rules(distributor)
        self.sanitizer = TextSanitizer()
        self.dual_extractor = DualExtractor(rules_class=self.rules)
        self.fallback_extractor = FallbackExtractor(rules_class=self.rules)
        self.use_dynamic_blacklist = use_dynamic_blacklist
        if use_dynamic_blacklist:
            self.dynamic_blacklist = DynamicBlacklist()
        else:
            self.dynamic_blacklist = None
    
    def extract_from_pdf(self, pdf_path: str) -> ExtractionResult:
        """Pipeline completo de extração."""
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
                self.dynamic_blacklist.update_frequency(ucs_final)
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
    """Testa V5 nos 20 documentos de validação."""
    
    extractor = UCExtractorV5()
    
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
    
    for v in validation[:10]:
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
