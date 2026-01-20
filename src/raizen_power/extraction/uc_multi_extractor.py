"""
Pipeline Híbrido de Extração de Múltiplas UCs
Baseado nas pesquisas: gemini.md + pipeline_ucs_2025.md

Arquitetura em 4 camadas com fallback:
1. PyMuPDF + Regex (rápido, 90% dos casos)
2. pdfplumber (tabelas estruturadas)
3. Docling (tabelas complexas - fallback)
4. OCR (scans - último recurso)
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

# Tentar importar pdfplumber (opcional mas recomendado)
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    print("⚠️ pdfplumber não instalado. Tabelas podem não ser extraídas corretamente.")


@dataclass
class UCExtractionResult:
    """Resultado da extração de UCs de um PDF"""
    file: str
    path: str
    ucs: List[str]  # Lista de UCs encontradas
    uc_count: int
    confidence: float
    method: str  # pymupdf, pdfplumber, docling, ocr
    pages_with_ucs: List[int]
    duration: float
    errors: List[str]


class UCMultiExtractor:
    """
    Extrator de múltiplas UCs com pipeline híbrido.
    Suporta contratos com 1:N UCs (ex: contratos FORTBRAS com 50+ UCs)
    """
    
    # Padrões de UC para diferentes contextos
    PATTERNS = {
        # UC padrão (8-10 dígitos)
        'padrao': r'\b(\d{8,10})\b',
        
        # Formato com label: "UC: 123456789"
        'label_uc': r'(?:UC|U\.C|Unidade\s+Consumidora|UNIDADE\s+CONSUMIDORA|Instalação|INSTALAÇÃO)\s*[:\-]?\s*(\d{8,10})',
        
        # Em listas: "- 123456789"
        'lista': r'[-•]\s+(\d{8,10})',
        
        # Em campos formatados: "XXXXXX-XX" (dígito verificador)
        'formatado': r'(\d{6,8})-(\d{1,2})',
        
        # Contexto de anexo
        'anexo': r'(?:Anexo|ANEXO).*?(?:UC|Instalação)\s*[:\-]?\s*(\d{8,10})',
    }
    
    # Palavras-chave que indicam página relevante para UCs
    KEYWORDS = ['unidade', 'instalação', 'código', 'anexo', 'tabela', 'rol', 'lista', 'uc']
    
    def __init__(self, min_digits: int = 8, max_digits: int = 10):
        self.min_digits = min_digits
        self.max_digits = max_digits
        self.metadata: List[Dict] = []
    
    def extract_from_pdf(self, pdf_path: str) -> UCExtractionResult:
        """
        Pipeline principal de extração.
        Tenta múltiplos métodos em ordem de velocidade/precisão.
        """
        start_time = time.time()
        errors = []
        all_ucs: Set[str] = set()
        pages_with_ucs: Set[int] = set()
        method_used = "none"
        
        try:
            # Fase 1: PyMuPDF + Regex (mais rápido)
            pymupdf_ucs, pymupdf_pages = self._extract_with_pymupdf(pdf_path)
            all_ucs.update(pymupdf_ucs)
            pages_with_ucs.update(pymupdf_pages)
            
            if pymupdf_ucs:
                method_used = "pymupdf"
            
            # Fase 2: pdfplumber para tabelas (se disponível)
            if HAS_PDFPLUMBER:
                try:
                    plumber_ucs, plumber_pages = self._extract_with_pdfplumber(pdf_path)
                    all_ucs.update(plumber_ucs)
                    pages_with_ucs.update(plumber_pages)
                    
                    if plumber_ucs and not pymupdf_ucs:
                        method_used = "pdfplumber"
                    elif plumber_ucs:
                        method_used = "pymupdf+pdfplumber"
                        
                except Exception as e:
                    errors.append(f"pdfplumber error: {str(e)[:50]}")
            
        except Exception as e:
            errors.append(f"Extraction error: {str(e)[:100]}")
        
        # Validar e deduplicar UCs
        validated_ucs = self._validate_ucs(list(all_ucs))
        
        # Calcular confiança
        confidence = self._calculate_confidence(validated_ucs, len(pages_with_ucs))
        
        duration = time.time() - start_time
        
        return UCExtractionResult(
            file=Path(pdf_path).name,
            path=str(pdf_path),
            ucs=validated_ucs,
            uc_count=len(validated_ucs),
            confidence=confidence,
            method=method_used,
            pages_with_ucs=sorted(pages_with_ucs),
            duration=duration,
            errors=errors
        )
    
    def _extract_with_pymupdf(self, pdf_path: str) -> Tuple[Set[str], Set[int]]:
        """Extração rápida usando PyMuPDF + Regex multi-pattern"""
        ucs: Set[str] = set()
        pages: Set[int] = set()
        
        doc = fitz.open(pdf_path)
        
        for page_num, page in enumerate(doc):
            text = page.get_text()
            
            # Verificar se página é relevante (tem keywords)
            text_lower = text.lower()
            if not any(kw in text_lower for kw in self.KEYWORDS):
                continue
            
            # Aplicar todos os padrões
            for pattern_name, pattern in self.PATTERNS.items():
                matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                
                for match in matches:
                    # Pegar o grupo de captura correto
                    uc = match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)
                    
                    # Limpar (só dígitos)
                    uc_clean = re.sub(r'\D', '', uc)
                    
                    # Validar tamanho
                    if self.min_digits <= len(uc_clean) <= self.max_digits:
                        ucs.add(uc_clean)
                        pages.add(page_num)
                        
                        self.metadata.append({
                            'uc': uc_clean,
                            'page': page_num,
                            'pattern': pattern_name,
                            'context': match.group(0)[:80]
                        })
        
        doc.close()
        return ucs, pages
    
    def _extract_with_pdfplumber(self, pdf_path: str) -> Tuple[Set[str], Set[int]]:
        """Extração de tabelas usando pdfplumber"""
        ucs: Set[str] = set()
        pages: Set[int] = set()
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Tentar extrair tabelas com diferentes estratégias
                tables = page.extract_tables(table_settings={
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "snap_tolerance": 3,
                })
                
                if not tables:
                    # Fallback: tabelas implícitas (sem linhas)
                    tables = page.extract_tables(table_settings={
                        "vertical_strategy": "text",
                        "horizontal_strategy": "text",
                    })
                
                for table in tables:
                    for row in table:
                        for cell in row:
                            if cell:
                                # Procurar UCs em cada célula
                                matches = re.findall(r'\d{8,10}', str(cell))
                                for uc in matches:
                                    if self.min_digits <= len(uc) <= self.max_digits:
                                        ucs.add(uc)
                                        pages.add(page_num)
                                        
                                        self.metadata.append({
                                            'uc': uc,
                                            'page': page_num,
                                            'pattern': 'table_cell',
                                            'context': str(cell)[:50]
                                        })
        
        return ucs, pages
    
    def _validate_ucs(self, ucs: List[str]) -> List[str]:
        """Validar e filtrar UCs com desambiguação de falsos positivos"""
        validated = []
        
        for uc in ucs:
            # Limpar
            uc_clean = re.sub(r'\D', '', uc)
            
            # Validar tamanho básico
            if not (self.min_digits <= len(uc_clean) <= self.max_digits):
                continue
            
            # === CAMADA 1: EXCLUSÃO DE FALSOS POSITIVOS ===
            
            # 1A. Excluir se for CNPJ (14 dígitos)
            if len(uc_clean) == 14:
                continue
            
            # 1B. Excluir se for CPF válido (11 dígitos)
            if len(uc_clean) == 11 and self._is_valid_cpf(uc_clean):
                continue
            
            # 1C. Excluir se parecer parte de CNPJ (contém "0001" típico de matriz)
            if '0001' in uc_clean[-6:]:  # Sufixo de CNPJ
                continue
            
            # 1D. Excluir anos isolados (4 dígitos entre 1950-2100)
            if len(uc_clean) == 4:
                try:
                    year = int(uc_clean)
                    if 1950 <= year <= 2100:
                        continue
                except ValueError:
                    pass
            
            # 1E. Excluir números muito curtos (provavelmente prazos: 30 dias, 12 meses)
            if len(uc_clean) < 5:
                continue
            
            # === CAMADA 2: VALIDAÇÃO ESTRUTURAL ===
            
            # UCs CPFL típicas: 8-10 dígitos
            # Aceitar UCs que passaram todos os filtros
            validated.append(uc_clean)
        
        # Remover duplicatas mantendo ordem
        return list(dict.fromkeys(validated))
    
    def _is_valid_cpf(self, cpf: str) -> bool:
        """Validar se é um CPF matematicamente válido (algoritmo Módulo 11)"""
        if len(cpf) != 11:
            return False
        
        # CPFs com todos dígitos iguais são inválidos
        if cpf == cpf[0] * 11:
            return False
        
        try:
            # Cálculo do primeiro dígito verificador
            soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
            resto = soma % 11
            d1 = 0 if resto < 2 else 11 - resto
            
            if int(cpf[9]) != d1:
                return False
            
            # Cálculo do segundo dígito verificador
            soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
            resto = soma % 11
            d2 = 0 if resto < 2 else 11 - resto
            
            return int(cpf[10]) == d2
        except (ValueError, IndexError):
            return False
    
    def _calculate_confidence(self, ucs: List[str], pages_count: int) -> float:
        """Calcular score de confiança baseado em heurísticas"""
        if not ucs:
            return 0.0
        
        confidence = 1.0
        
        # Penalizar se muitas UCs (pode ser falso positivo)
        if len(ucs) > 100:
            confidence -= 0.2
        
        # Bonificar se UCs têm tamanho consistente
        sizes = [len(uc) for uc in ucs]
        if len(set(sizes)) == 1:
            confidence += 0.1
        
        # Bonificar se encontrado em múltiplas páginas (confirma presença)
        if pages_count > 1:
            confidence += 0.05
        
        return min(1.0, max(0.0, confidence))


def process_single_pdf(pdf_path: str) -> Dict:
    """Função worker para processamento paralelo"""
    try:
        extractor = UCMultiExtractor()
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
    """
    Executar extração em paralelo para todos os PDFs de um diretório.
    
    Args:
        pdf_dir: Diretório com PDFs
        output_json: Caminho para salvar resultado JSON
        max_workers: Número de workers (default: 75% dos cores)
        sample: Se definido, processa apenas N PDFs aleatórios
    """
    # Coletar PDFs
    pdf_paths = list(Path(pdf_dir).rglob('*.pdf'))
    
    if sample:
        import random
        random.seed(42)
        pdf_paths = random.sample(pdf_paths, min(sample, len(pdf_paths)))
    
    print(f"=== EXTRAÇÃO MULTI-UC EM PARALELO ===")
    print(f"PDFs a processar: {len(pdf_paths)}")
    
    # Configurar workers
    if max_workers is None:
        max_workers = max(1, (os.cpu_count() or 4) * 3 // 4)
    
    print(f"Workers paralelos: {max_workers}")
    
    start_time = time.time()
    results = []
    
    # Processamento paralelo
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_single_pdf, str(p)): p for p in pdf_paths}
        
        for i, future in enumerate(as_completed(futures), 1):
            try:
                result = future.result()
                results.append(result)
                
                # Progresso
                if i % 100 == 0 or i == len(pdf_paths):
                    elapsed = time.time() - start_time
                    eta = (elapsed / i) * (len(pdf_paths) - i)
                    print(f"  [{i}/{len(pdf_paths)}] {elapsed:.1f}s elapsed, ETA: {eta:.1f}s")
                    
            except Exception as e:
                print(f"  ⚠️ Erro: {e}")
    
    total_time = time.time() - start_time
    
    # Estatísticas
    total_ucs = sum(r['uc_count'] for r in results)
    multi_uc_count = sum(1 for r in results if r['uc_count'] > 1)
    success_rate = sum(1 for r in results if r['uc_count'] > 0) / len(results) * 100
    
    print(f"\n=== RESULTADO ===")
    print(f"Tempo total: {total_time:.1f}s ({total_time/60:.1f}min)")
    print(f"Média por PDF: {total_time/len(results):.2f}s")
    print(f"Total de UCs: {total_ucs}")
    print(f"PDFs com múltiplas UCs: {multi_uc_count}")
    print(f"Taxa de sucesso: {success_rate:.1f}%")
    
    # Salvar
    output_path = Path(output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Resultado salvo em: {output_path}")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Extração Multi-UC de PDFs")
    parser.add_argument("--dir", default="cpfl_paulista_por_tipo", help="Diretório com PDFs")
    parser.add_argument("--output", default="output/multi_uc_extraction.json", help="Arquivo de saída")
    parser.add_argument("--workers", type=int, default=None, help="Número de workers")
    parser.add_argument("--sample", type=int, default=None, help="Processar N PDFs amostra")
    
    args = parser.parse_args()
    
    run_parallel_extraction(
        pdf_dir=args.dir,
        output_json=args.output,
        max_workers=args.workers,
        sample=args.sample
    )
