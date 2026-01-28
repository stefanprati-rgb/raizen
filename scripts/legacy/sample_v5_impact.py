"""
Amostragem: Testar V5 atualizado em 100 documentos que já tinham UCs
para verificar se há UCs adicionais (curtas) que foram perdidas.
"""
import sys
sys.path.insert(0, 'scripts')

import json
import random
from pathlib import Path
from uc_extractor_v5 import UCExtractorV5

V5_RESULTS_PATH = Path('output/cpfl_paulista_final/cpfl_v5_full_results.json')
SAMPLE_SIZE = 100

def main():
    print("Carregando resultados V5 anteriores...")
    with open(V5_RESULTS_PATH, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    # Filtrar apenas os que tiveram sucesso
    success_docs = [r for r in results if r['status'] == 'SUCCESS' and r['uc_count'] > 0]
    print(f"Total documentos com sucesso: {len(success_docs)}")
    
    # Amostragem aleatória
    random.seed(42)  # Reproducibilidade
    sample = random.sample(success_docs, min(SAMPLE_SIZE, len(success_docs)))
    print(f"Amostra selecionada: {len(sample)} documentos")
    print()
    
    extractor = UCExtractorV5(use_dynamic_blacklist=False)
    
    docs_com_ucs_extras = 0
    total_ucs_extras = 0
    docs_iguais = 0
    docs_menos_ucs = 0
    
    for i, doc in enumerate(sample, 1):
        path = doc['path']
        ucs_anteriores = set(doc['ucs'])
        
        if not Path(path).exists():
            continue
        
        # Re-extrair com V5 atualizado
        result = extractor.extract_from_pdf(path)
        ucs_novas = set(result.ucs)
        
        # Comparar
        extras = ucs_novas - ucs_anteriores
        perdidas = ucs_anteriores - ucs_novas
        
        if extras:
            docs_com_ucs_extras += 1
            total_ucs_extras += len(extras)
            print(f"[{i}] UCs EXTRAS: {doc['file'][:40]}...")
            print(f"     Antes: {len(ucs_anteriores)} | Agora: {len(ucs_novas)} | Extras: {extras}")
        elif perdidas:
            docs_menos_ucs += 1
            # Geralmente não deve acontecer
        else:
            docs_iguais += 1
        
        # Progresso
        if i % 20 == 0:
            print(f"... processados {i}/{len(sample)}")
    
    print()
    print("=" * 60)
    print("RESULTADO DA AMOSTRAGEM:")
    print(f"  Documentos analisados: {len(sample)}")
    print(f"  Documentos iguais: {docs_iguais}")
    print(f"  Documentos com UCs EXTRAS: {docs_com_ucs_extras}")
    print(f"  Total de UCs extras encontradas: {total_ucs_extras}")
    print(f"  Documentos com menos UCs (regressão): {docs_menos_ucs}")
    print()
    
    if docs_com_ucs_extras > 0:
        pct_impacto = (docs_com_ucs_extras / len(sample)) * 100
        print(f"IMPACTO ESTIMADO: {pct_impacto:.1f}% dos documentos teriam UCs adicionais")
        print(f"Estimativa para todos os {len(success_docs)} docs: ~{int(len(success_docs) * pct_impacto / 100)} documentos afetados")
        print(f"UCs adicionais estimadas: ~{int(total_ucs_extras * len(success_docs) / len(sample))}")
        print()
        print("RECOMENDAÇÃO: Re-executar a extração completa")
    else:
        print("IMPACTO: Nenhum - Os documentos existentes não têm UCs curtas adicionais")
        print("RECOMENDAÇÃO: Manter o dataset atual")

if __name__ == "__main__":
    main()
