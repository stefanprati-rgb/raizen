"""
Pipeline Robusto de Extração de Múltiplas UCs - Versão Completa
Implementa as 4 soluções para os problemas identificados:
  4.1 CNPJFragmentFilter - Filtra fragmentos de CNPJ
  4.2 RecurrentCodeDetector - Detecta códigos recorrentes
  4.3 SpatialRegexExtractor - Extração com contexto semântico
  4.4 RobustCPFLUCExtractor - Integração completa
"""

import re
import json
import time
import os
from pathlib import Path
from typing import List, Set, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from collections import Counter

import fitz  # PyMuPDF

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


# ============================================================================
# SOLUÇÃO 4.1: CNPJFragmentFilter
# ============================================================================

class CNPJFragmentFilter:
    """
    Filtra números que são fragmentos de CNPJs do documento.
    Extrai CNPJ do nome do arquivo e do texto, gera substrings e rejeita matches.
    """
    
    # Regex para CNPJ em diferentes formatos
    CNPJ_PATTERNS = [
        r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}',  # 12.345.678/0001-90
        r'\d{14}',  # 12345678000190
    ]
    
    def __init__(self):
        self.document_cnpjs: Set[str] = set()
        self.cnpj_fragments: Set[str] = set()
    
    def extract_cnpj_from_filename(self, filename: str) -> Optional[str]:
        """Extrai CNPJ do nome do arquivo"""
        # Padrão comum: "EMPRESA - 12345678000190.docx - Clicksign.pdf"
        match = re.search(r'(\d{14})', filename)
        if match:
            return match.group(1)
        
        # Formato com pontuação
        match = re.search(r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})', filename)
        if match:
            return re.sub(r'\D', '', match.group(1))
        
        return None
    
    def extract_cnpjs_from_text(self, text: str) -> Set[str]:
        """Extrai todos os CNPJs do texto"""
        cnpjs = set()
        for pattern in self.CNPJ_PATTERNS:
            for match in re.finditer(pattern, text):
                cnpj = re.sub(r'\D', '', match.group(0))
                if len(cnpj) == 14:
                    cnpjs.add(cnpj)
        return cnpjs
    
    def generate_fragments(self, cnpj: str) -> Set[str]:
        """Gera todos os substrings de 8-10 dígitos de um CNPJ"""
        fragments = set()
        if len(cnpj) != 14:
            return fragments
        
        # Substrings de 8 a 10 dígitos
        for length in range(8, 11):
            for start in range(len(cnpj) - length + 1):
                fragment = cnpj[start:start + length]
                fragments.add(fragment)
        
        return fragments
    
    def setup(self, filename: str, text: str):
        """Configura o filtro com CNPJs do documento"""
        self.document_cnpjs = set()
        self.cnpj_fragments = set()
        
        # CNPJ do nome do arquivo
        cnpj_filename = self.extract_cnpj_from_filename(filename)
        if cnpj_filename:
            self.document_cnpjs.add(cnpj_filename)
        
        # CNPJs do texto
        text_cnpjs = self.extract_cnpjs_from_text(text)
        self.document_cnpjs.update(text_cnpjs)
        
        # Gerar fragmentos
        for cnpj in self.document_cnpjs:
            self.cnpj_fragments.update(self.generate_fragments(cnpj))
    
    def is_cnpj_fragment(self, number: str) -> bool:
        """Verifica se número é fragmento de CNPJ"""
        return number in self.cnpj_fragments


# ============================================================================
# SOLUÇÃO 4.2: RecurrentCodeDetector
# ============================================================================

class RecurrentCodeDetector:
    """
    Detecta códigos que aparecem em muitos documentos (>90% = código padrão do sistema).
    Mantém blacklist para reutilização.
    """
    
    # Blacklist inicial (códigos conhecidos que aparecem em quase todos os docs)
    KNOWN_SYSTEM_CODES = {
        '160741512',   # Aparece em 98% dos docs - provável código de usina/contrato master
        '3523511633',  # Aparece em 60%+ dos docs - provável protocolo padrão
    }
    
    def __init__(self, blacklist_path: str = "output/uc_blacklist.json"):
        self.blacklist_path = Path(blacklist_path)
        self.blacklist: Set[str] = set(self.KNOWN_SYSTEM_CODES)
        self._load_blacklist()
    
    def _load_blacklist(self):
        """Carrega blacklist de arquivo"""
        if self.blacklist_path.exists():
            try:
                with open(self.blacklist_path, 'r') as f:
                    data = json.load(f)
                    self.blacklist.update(data.get('codes', []))
            except:
                pass
    
    def save_blacklist(self):
        """Salva blacklist em arquivo"""
        self.blacklist_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.blacklist_path, 'w') as f:
            json.dump({'codes': list(self.blacklist)}, f, indent=2)
    
    def is_system_code(self, number: str) -> bool:
        """Verifica se número é código de sistema (blacklist)"""
        return number in self.blacklist
    
    @staticmethod
    def analyze_recurrence(results: List[Dict], threshold: float = 0.5) -> Set[str]:
        """
        Analisa resultados de extração e identifica códigos recorrentes.
        
        Args:
            results: Lista de resultados de extração (cada um com 'ucs')
            threshold: Fração mínima de documentos para considerar recorrente (0.5 = 50%)
        
        Returns:
            Set de códigos que aparecem em mais de threshold% dos documentos
        """
        total_docs = len(results)
        if total_docs == 0:
            return set()
        
        # Contar frequência de cada UC
        uc_counter = Counter()
        for r in results:
            for uc in set(r.get('ucs', [])):  # set() para contar cada UC uma vez por doc
                uc_counter[uc] += 1
        
        # Identificar recorrentes
        min_count = int(total_docs * threshold)
        recurrent = {uc for uc, count in uc_counter.items() if count >= min_count}
        
        return recurrent


# ============================================================================
# SOLUÇÃO 4.3: SpatialRegexExtractor
# ============================================================================

class SpatialRegexExtractor:
    """
    Extrator com contexto semântico - atribui confiança baseado no contexto.
    """
    
    # Padrões ordenados por confiança (maior primeiro)
    # IMPORTANTE: "Nº do Cliente" (70/71XXXXXXX) NÃO é UC, é código do cliente na distribuidora
    # A UC real é "Nº da Instalação"
    CONTEXT_PATTERNS = [
        # CAMADA 1: Label "Instalação" - MAIOR PRIORIDADE (98%)
        (r'(?:N[ºo°]\s*(?:da\s+)?Instalação|Instalação|Código\s+(?:da\s+)?(?:UC|Instalação))\s*[:\-]?\s*(\d{7,10})', 0.98, 'instalacao'),
        
        # CAMADA 2: Label UC explícito (95%)
        (r'(?:UC|U\.C|Unidade\s+Consumidora|UNIDADE\s+CONSUMIDORA)\s*[:\-]?\s*(\d{8,10})', 0.95, 'label_uc'),
        
        # CAMADA 3: Conta Contrato (90%)
        (r'(?:Conta\s+Contrato)\s*[:\-]?\s*(\d{8,10})', 0.90, 'conta_contrato'),
        
        # NOTA: "Nº do Cliente" foi REMOVIDO - não é UC!
        # Números 70XXXXXXX/71XXXXXXX são identificadores do cliente, não da instalação
        
        # CAMADA 4: Em contexto de anexo (80%)
        (r'(?:ANEXO|Anexo|Lista|ROL).*?(\d{8,10})', 0.80, 'anexo'),
        
        # CAMADA 5: Número isolado de 8-10 dígitos (50% - baixa confiança)
        (r'\b(\d{8,10})\b', 0.50, 'isolado'),
    ]
    
    # Threshold mínimo de confiança para aceitar
    MIN_CONFIDENCE = 0.60
    
    def extract_with_confidence(self, text: str) -> List[Tuple[str, float, str]]:
        """
        Extrai números com score de confiança baseado no contexto.
        
        Returns:
            Lista de (número, confiança, padrão_match)
        """
        results = []
        seen = set()
        
        for pattern, confidence, pattern_name in self.CONTEXT_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
                # Pegar o grupo de captura
                num = match.group(1) if match.lastindex else match.group(0)
                num_clean = re.sub(r'\D', '', num)
                
                if len(num_clean) not in [8, 9, 10]:
                    continue
                
                if num_clean not in seen:
                    # Verificar contexto negativo
                    context = text[max(0, match.start()-30):match.end()+30].lower()
                    
                    # Penalizar se contexto menciona CNPJ/CPF
                    if 'cnpj' in context or 'cpf' in context:
                        confidence = min(confidence, 0.40)
                    
                    results.append((num_clean, confidence, pattern_name))
                    seen.add(num_clean)
        
        return results
    
    def filter_by_confidence(self, results: List[Tuple[str, float, str]]) -> List[str]:
        """Filtra resultados pelo threshold de confiança"""
        return [num for num, conf, _ in results if conf >= self.MIN_CONFIDENCE]


# ============================================================================
# SOLUÇÃO 4.4: RobustCPFLUCExtractor (Integração)
# ============================================================================

@dataclass
class UCExtractionResult:
    """Resultado da extração de UCs"""
    file: str
    path: str
    ucs: List[str]
    uc_count: int
    confidence: float
    method: str
    pages_with_ucs: List[int]
    duration: float
    errors: List[str]
    cnpjs_found: List[str] = None
    filtered_fragments: int = 0
    filtered_system_codes: int = 0


class RobustCPFLUCExtractor:
    """
    Extrator robusto que integra todas as soluções:
    1. Extração com contexto (SpatialRegex)
    2. Filtro de fragmentos CNPJ
    3. Filtro de códigos de sistema (blacklist)
    4. Validação CPF (Módulo 11)
    """
    
    def __init__(self):
        self.cnpj_filter = CNPJFragmentFilter()
        self.recurrent_detector = RecurrentCodeDetector()
        self.spatial_extractor = SpatialRegexExtractor()
        self.metadata: List[Dict] = []
    
    def extract_from_pdf(self, pdf_path: str) -> UCExtractionResult:
        """Pipeline completo de extração"""
        start_time = time.time()
        errors = []
        all_ucs: List[Tuple[str, float, str]] = []
        pages_with_ucs: Set[int] = set()
        method_used = "robust_v3"
        filtered_fragments = 0
        filtered_system = 0
        
        try:
            doc = fitz.open(pdf_path)
            filename = Path(pdf_path).name
            
            # Extrair texto completo para setup do filtro CNPJ
            full_text = ""
            for page in doc:
                full_text += page.get_text()
            
            # Setup do filtro de CNPJ
            self.cnpj_filter.setup(filename, full_text)
            
            # Extração página por página com contexto
            for page_num, page in enumerate(doc):
                text = page.get_text()
                
                # Extração com confiança
                page_results = self.spatial_extractor.extract_with_confidence(text)
                
                for uc, conf, pattern in page_results:
                    all_ucs.append((uc, conf, pattern, page_num))
                    pages_with_ucs.add(page_num)
            
            doc.close()
            
            # Extração via pdfplumber (tabelas)
            if HAS_PDFPLUMBER:
                try:
                    table_ucs = self._extract_from_tables(pdf_path)
                    for uc, page_num in table_ucs:
                        all_ucs.append((uc, 0.85, 'table', page_num))
                        pages_with_ucs.add(page_num)
                except Exception as e:
                    errors.append(f"pdfplumber: {str(e)[:30]}")
            
            # === APLICAR FILTROS ===
            validated_ucs = []
            
            for uc, conf, pattern, page in all_ucs:
                # Filtro 1: Confiança mínima
                if conf < self.spatial_extractor.MIN_CONFIDENCE:
                    continue
                
                # Filtro 2: Fragmento de CNPJ
                if self.cnpj_filter.is_cnpj_fragment(uc):
                    filtered_fragments += 1
                    continue
                
                # Filtro 3: Código de sistema (blacklist)
                if self.recurrent_detector.is_system_code(uc):
                    filtered_system += 1
                    continue
                
                # Filtro 4: CPF válido
                if len(uc) == 11 and self._is_valid_cpf(uc):
                    continue
                
                # Filtro 5: Tamanho válido
                if len(uc) < 7 or len(uc) > 10:
                    continue
                
                # Filtro 6: "Nº do Cliente" - NUNCA é UC!
                # Números de 9 dígitos começando com 70 ou 71 são SEMPRE códigos de cliente
                # na distribuidora CPFL, não são códigos de instalação (UC)
                if len(uc) == 9 and uc.startswith(('70', '71')):
                    continue
                
                validated_ucs.append((uc, conf, pattern))
            
            # Deduplicar mantendo maior confiança
            uc_best = {}
            for uc, conf, pattern in validated_ucs:
                if uc not in uc_best or conf > uc_best[uc]:
                    uc_best[uc] = conf
            
            final_ucs = list(uc_best.keys())
            avg_confidence = sum(uc_best.values()) / len(uc_best) if uc_best else 0
            
        except Exception as e:
            errors.append(f"Error: {str(e)[:50]}")
            final_ucs = []
            avg_confidence = 0
        
        duration = time.time() - start_time
        
        return UCExtractionResult(
            file=Path(pdf_path).name,
            path=str(pdf_path),
            ucs=final_ucs,
            uc_count=len(final_ucs),
            confidence=avg_confidence,
            method=method_used,
            pages_with_ucs=sorted(pages_with_ucs),
            duration=duration,
            errors=errors,
            cnpjs_found=list(self.cnpj_filter.document_cnpjs),
            filtered_fragments=filtered_fragments,
            filtered_system_codes=filtered_system
        )
    
    def _extract_from_tables(self, pdf_path: str) -> List[Tuple[str, int]]:
        """Extrai UCs de tabelas usando pdfplumber"""
        results = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        for cell in row:
                            if cell:
                                matches = re.findall(r'\d{8,10}', str(cell))
                                for uc in matches:
                                    if 8 <= len(uc) <= 10:
                                        results.append((uc, page_num))
        
        return results
    
    def _is_valid_cpf(self, cpf: str) -> bool:
        """Valida CPF pelo algoritmo Módulo 11"""
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


# ============================================================================
# FUNÇÕES DE EXECUÇÃO
# ============================================================================

def process_single_pdf(pdf_path: str) -> Dict:
    """Função worker para processamento paralelo"""
    try:
        extractor = RobustCPFLUCExtractor()
        result = extractor.extract_from_pdf(pdf_path)
        return asdict(result)
    except Exception as e:
        return {
            'file': Path(pdf_path).name,
            'path': str(pdf_path),
            'ucs': [],
            'uc_count': 0,
            'confidence': 0.0,
            'method': 'error',
            'pages_with_ucs': [],
            'duration': 0.0,
            'errors': [str(e)]
        }


def run_parallel_extraction(
    pdf_dir: str,
    output_json: str,
    max_workers: Optional[int] = None,
    sample: Optional[int] = None
) -> List[Dict]:
    """Executar extração em paralelo"""
    pdf_paths = list(Path(pdf_dir).rglob('*.pdf'))
    
    if sample:
        import random
        random.seed(42)
        pdf_paths = random.sample(pdf_paths, min(sample, len(pdf_paths)))
    
    print(f"=== EXTRAÇÃO ROBUSTA MULTI-UC V3 ===")
    print(f"PDFs: {len(pdf_paths)}")
    
    if max_workers is None:
        max_workers = max(1, (os.cpu_count() or 4) * 3 // 4)
    
    print(f"Workers: {max_workers}")
    
    start_time = time.time()
    results = []
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_single_pdf, str(p)): p for p in pdf_paths}
        
        for i, future in enumerate(as_completed(futures), 1):
            try:
                result = future.result()
                results.append(result)
                
                if i % 100 == 0 or i == len(pdf_paths):
                    elapsed = time.time() - start_time
                    print(f"  [{i}/{len(pdf_paths)}] {elapsed:.1f}s")
                    
            except Exception as e:
                print(f"  ⚠️ {e}")
    
    total_time = time.time() - start_time
    
    # Estatísticas
    total_ucs = sum(r['uc_count'] for r in results)
    total_filtered_frag = sum(r.get('filtered_fragments', 0) for r in results)
    total_filtered_sys = sum(r.get('filtered_system_codes', 0) for r in results)
    success_rate = sum(1 for r in results if r['uc_count'] > 0) / len(results) * 100
    
    print(f"\n=== RESULTADO ===")
    print(f"Tempo: {total_time:.1f}s")
    print(f"Total UCs: {total_ucs}")
    print(f"Fragmentos CNPJ filtrados: {total_filtered_frag}")
    print(f"Códigos sistema filtrados: {total_filtered_sys}")
    print(f"Taxa sucesso: {success_rate:.1f}%")
    
    # Salvar
    output_path = Path(output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Salvo: {output_path}")
    
    # Análise de recorrência (para atualizar blacklist)
    recurrent = RecurrentCodeDetector.analyze_recurrence(results, threshold=0.5)
    if recurrent:
        print(f"\n⚠️ Códigos recorrentes detectados (>50%): {recurrent}")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Extração Robusta Multi-UC V3")
    parser.add_argument("--dir", default="cpfl_paulista_por_tipo", help="Diretório")
    parser.add_argument("--output", default="output/multi_uc_robust_v3.json", help="Saída")
    parser.add_argument("--workers", type=int, default=None, help="Workers")
    parser.add_argument("--sample", type=int, default=None, help="Amostra")
    
    args = parser.parse_args()
    
    run_parallel_extraction(
        pdf_dir=args.dir,
        output_json=args.output,
        max_workers=args.workers,
        sample=args.sample
    )
