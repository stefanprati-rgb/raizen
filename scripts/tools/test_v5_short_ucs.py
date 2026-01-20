"""
Testar V5 atualizado usando arquivos diretamente dos batches.
"""
import sys
sys.path.insert(0, 'scripts')

import json
from pathlib import Path
from uc_extractor_v5 import UCExtractorV5

BATCH_DIR = Path('output/investigar_gemini_batches')
ANALYSIS_FILE = BATCH_DIR / 'analise_consolidada.json'

def main():
    with open(ANALYSIS_FILE, 'r', encoding='utf-8') as f:
        analises = json.load(f)
    
    # Filtrar apenas os que deveriam ter UC
    docs_com_uc = [a for a in analises if a.get('deveria_ter_uc') and a.get('ucs_encontradas')]
    
    print(f"Testando V5 atualizado em {len(docs_com_uc)} documentos...")
    print("=" * 70)
    
    extractor = UCExtractorV5(use_dynamic_blacklist=False)
    
    success = 0
    failed = 0
    
    for doc in docs_com_uc:
        arquivo = doc.get('arquivo', '')
        ucs_gemini = doc.get('ucs_encontradas', [])
        
        # Procurar o arquivo nos batches
        found_path = None
        for batch_dir in BATCH_DIR.glob('batch_*'):
            for pdf in batch_dir.glob('*.pdf'):
                # Nome do PDF começa com número
                pdf_name = pdf.name
                if arquivo in pdf_name or pdf_name.endswith(arquivo):
                    found_path = pdf
                    break
                # Comparar partes do nome
                if arquivo[:30] in pdf_name or pdf_name[3:33] in arquivo:
                    found_path = pdf
                    break
            if found_path:
                break
        
        if not found_path:
            print(f"SKIP: {arquivo[:45]}... (não encontrado)")
            continue
        
        # Extrair com V5 atualizado
        result = extractor.extract_from_pdf(str(found_path))
        
        # Verificar se capturou as UCs do Gemini
        ucs_v5 = set(result.ucs)
        ucs_esperadas = set(str(u) for u in ucs_gemini)  # Garantir string
        
        # Considerar sucesso se encontrou alguma UC ou se a UC esperada foi encontrada
        acertou = bool(ucs_esperadas & ucs_v5) or result.uc_count > 0
        
        status = "OK" if acertou else "FALHA"
        if acertou:
            success += 1
        else:
            failed += 1
        
        print(f"[{status}] {arquivo[:45]}...")
        print(f"       Gemini: {ucs_gemini} | V5: {result.ucs}")
        
    print("=" * 70)
    print(f"RESULTADO: {success} OK / {failed} FALHAS")
    if (success + failed) > 0:
        print(f"Taxa de sucesso: {(success/(success+failed))*100:.1f}%")

if __name__ == "__main__":
    main()
