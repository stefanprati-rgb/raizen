"""
Classifica PDFs por tipo de documento e aplica o mapa correto.
Tipos: ADESAO, ADITIVO, DISTRATO
"""
import re
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.extrator_contratos.table_extractor import open_pdf, extract_all_text_from_pdf


def classificar_documento(text: str, filename: str) -> str:
    """Classifica o tipo de documento baseado no conteúdo e nome."""
    text_upper = text.upper()
    filename_upper = filename.upper()
    
    # Verificar DISTRATO
    if 'DISTRATO' in text_upper or 'DISTRATO' in filename_upper:
        return 'DISTRATO'
    
    # Verificar ADITIVO
    if any(termo in text_upper for termo in ['ADITIVO CONTRATUAL', 'TERMO DE ADITIVO', 'ADT CONDICOES']):
        return 'ADITIVO'
    if 'ADT' in filename_upper and 'CONDICOES' in filename_upper:
        return 'ADITIVO'
    
    # Default: Termo de Adesão
    return 'ADESAO'


def analisar_pasta(pasta_path: str):
    """Analisa uma pasta e classifica todos os PDFs."""
    pasta = Path(pasta_path)
    
    if not pasta.exists():
        print(f"[X] Pasta nao encontrada: {pasta}")
        return
    
    pdfs = list(pasta.rglob('*.pdf'))
    print(f"\nAnalisando {len(pdfs)} PDFs em: {pasta}")
    print("=" * 70)
    
    classificacao = defaultdict(list)
    erros = []
    
    for i, pdf_path in enumerate(pdfs, 1):
        try:
            with open_pdf(str(pdf_path)) as pdf:
                # Ler apenas primeira página para classificação
                text = extract_all_text_from_pdf(pdf, max_pages=1, use_ocr_fallback=False)
            
            tipo = classificar_documento(text, pdf_path.name)
            classificacao[tipo].append(pdf_path.name)
            
            if i % 50 == 0:
                print(f"  Processados: {i}/{len(pdfs)}")
                
        except Exception as e:
            erros.append((pdf_path.name, str(e)))
    
    # Resumo
    print("\n" + "=" * 70)
    print("RESUMO DA CLASSIFICACAO")
    print("=" * 70)
    
    for tipo, arquivos in sorted(classificacao.items()):
        print(f"\n[{tipo}] - {len(arquivos)} arquivos")
        # Mostrar exemplos
        for arq in arquivos[:3]:
            print(f"  - {arq[:60]}...")
        if len(arquivos) > 3:
            print(f"  ... e mais {len(arquivos) - 3}")
    
    if erros:
        print(f"\n[ERROS] - {len(erros)} arquivos com erro")
        for arq, erro in erros[:3]:
            print(f"  - {arq[:40]}: {erro[:30]}")
    
    # Retornar classificação para uso
    return dict(classificacao)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Classificador de PDFs por tipo")
    parser.add_argument("pasta", type=Path, help="Pasta com PDFs para classificar")
    args = parser.parse_args()
    
    return analisar_pasta(str(args.pasta))


if __name__ == "__main__":
    main()
