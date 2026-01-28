#!/usr/bin/env python3
"""
Investiga regexes de datas e aviso prévio em contratos CPFL Paulista.
Busca padrões no texto bruto para ajustar extração.
"""

import sys
import re
from pathlib import Path
import logging
import pdfplumber

# Suprimir logs do pdfplumber
logging.getLogger("pdfminer").setLevel(logging.ERROR)


# Adicionar src ao path
sys.path.append(str(Path("C:/Projetos/Raizen")))
from src.raizen_power.extraction.extractor import ContractExtractor

# Configurações
BASE_DIR = Path("C:/Projetos/Raizen/data/processed")
AMOSTRAS = 5

def find_cpfl_pdfs():
    """Encontra PDFs específicos do Modelo 1 para diagnóstico"""
    # Amostra conhecida de Modelo 1: CNPJ 31144518000112 (MARTINS & KOHLE)
    target = "31144518" 
    pdfs = list(BASE_DIR.rglob(f"*{target}*.pdf"))
    
    if not pdfs:
        # Tentar outra amostra de Modelo 1 que falhou: 61189288015615 (MARISA LOJAS)
        target = "61189288"
        pdfs = list(BASE_DIR.rglob(f"*{target}*.pdf"))
        
    return pdfs[:3] # Retornar no máximo 3

def find_context(text, keywords, window=100):
    """Encontra contexto ao redor de keywords"""
    results = []
    text_lower = text.lower()
    
    for kw in keywords:
        matches = [m.start() for m in re.finditer(re.escape(kw.lower()), text_lower)]
        for pos in matches:
            start = max(0, pos - window)
            end = min(len(text), pos + len(kw) + window)
            results.append(f"...{text[start:end].replace(chr(10), ' ')}...")
    return results
    return results

def main():
    # Redirecionar output para arquivo
    output_file = Path("C:/Projetos/Raizen/output/debug/diagnostico_cpfl.txt")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        def log(msg):
            print(msg)
            f.write(str(msg) + "\n")
            
        log("=" * 60)
        log("DIAGNÓSTICO DE REGEX - CPFL PAULISTA")
        log("=" * 60)
        
        # Encontrar alguns PDFs da CPFL
        pdfs = find_cpfl_pdfs()
        
        if not pdfs:
            log("Nenhum PDF encontrado em data/processed/*/CPFL_PAULISTA!")
            return
            
        log(f"Analisando {len(pdfs)} amostras...")
        
        extractor = ContractExtractor()
        
        for pdf_path in pdfs:
            log("\n" + "-" * 60)
            log(f"Arquivo: {pdf_path.name}")
            
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    full_text = "\n".join([p.extract_text() or "" for p in pdf.pages])
                    
                log(f"Tamanho texto: {len(full_text)} chars")
                
                # 1. Tentar extração atual
                result = extractor.extract_from_pdf(str(pdf_path))
                # O resultado é um objeto ExtractionResult, não dict
                # Pegando dados do primeiro registro se houver
                dados_extraidos = result.registros[0] if result.registros else {}
                
                log(f"Extração atual:")
                log(f"  Data Adesão: {dados_extraidos.get('data_adesao')}")
                log(f"  Aviso Prévio: {dados_extraidos.get('aviso_previo')}")
                
                # 2. Buscar contexto para Representante (Modelo 1)
                log("\nContexto 'Representante' (Modelo 1):")
                keywords_rep = ["representante", "assinado por", "procurador", "sócio", "administrador", "abaixo assinado"]
                ctx_rep = find_context(full_text, keywords_rep)
                for ctx in ctx_rep[:10]:
                    log(f"  FOUND: {ctx}")
                    
                # 3. Buscar contexto para Participação/Cota (Modelo 1)
                log("\nContexto 'Participação/Cota' (Modelo 1):")
                keywords_part = ["participação", "rateio", "percentual", "cota", "alocação", "energia contratada", "%"]
                ctx_part = find_context(full_text, keywords_part)
                for ctx in ctx_part[:10]:
                    log(f"  FOUND: {ctx}")
                    
            except Exception as e:
                log(f"Erro: {e}")
                import traceback
                f.write(traceback.format_exc())

    print(f"\nRelatório salvo em: {output_file}")

if __name__ == "__main__":
    main()
