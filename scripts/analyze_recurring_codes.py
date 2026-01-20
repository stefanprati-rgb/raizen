"""
Analisar códigos recorrentes para decidir se são UCs válidas ou blacklist.
"""
import json
from pathlib import Path
from collections import Counter

V5_RESULTS_PATH = Path('output/cpfl_paulista_final/cpfl_v5_full_results.json')

def main():
    print("Carregando resultados V5...")
    with open(V5_RESULTS_PATH, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    # Contar frequência de cada UC
    all_ucs = []
    uc_to_docs = {}  # UC -> lista de documentos onde aparece
    
    for r in results:
        if r['ucs']:
            for uc in r['ucs']:
                all_ucs.append(uc)
                if uc not in uc_to_docs:
                    uc_to_docs[uc] = []
                uc_to_docs[uc].append(r['file'][:50])
    
    # Contar frequências
    freq = Counter(all_ucs)
    total_docs = len([r for r in results if r['status'] == 'SUCCESS'])
    
    print(f"Total de documentos com sucesso: {total_docs}")
    print(f"Total de UCs (com repetição): {len(all_ucs)}")
    print(f"UCs únicas: {len(freq)}")
    print()
    
    # Identificar códigos suspeitos (aparecem em muitos documentos)
    print("=" * 70)
    print("CÓDIGOS MAIS FREQUENTES (possível blacklist)")
    print("=" * 70)
    print(f"{'UC':<15} {'Freq':<8} {'%':<8} {'Padrão':<15} {'Risco'}")
    print("-" * 70)
    
    suspicious = []
    
    for uc, count in freq.most_common(50):
        pct = (count / total_docs) * 100
        
        # Classificar padrão
        if len(uc) == 5 and uc.startswith('1'):
            pattern = "5dig_1XXXX"
            risk = "ALTO" if pct > 5 else "MÉDIO"
        elif len(uc) == 5 and uc.startswith('9'):
            pattern = "5dig_9XXXX"
            risk = "ALTO" if pct > 5 else "MÉDIO"
        elif len(uc) == 5:
            pattern = "5dig_outro"
            risk = "MÉDIO" if pct > 3 else "BAIXO"
        elif len(uc) == 6:
            pattern = "6dig"
            risk = "MÉDIO" if pct > 3 else "BAIXO"
        else:
            pattern = f"{len(uc)}dig"
            risk = "BAIXO"
        
        # Marcar suspeitos
        if pct > 5:
            suspicious.append(uc)
            risk = "⚠️ " + risk
        
        print(f"{uc:<15} {count:<8} {pct:<7.1f}% {pattern:<15} {risk}")
        
        if count < 20:  # Parar quando frequência cair
            break
    
    print()
    print("=" * 70)
    print("ANÁLISE DOS CÓDIGOS 1341X")
    print("=" * 70)
    
    # Focar nos códigos 1341x
    codes_1341x = [uc for uc in freq if uc.startswith('1341')]
    
    for uc in sorted(codes_1341x):
        count = freq[uc]
        pct = (count / total_docs) * 100
        docs_sample = uc_to_docs[uc][:5]
        
        print(f"\n{uc}: aparece em {count} docs ({pct:.1f}%)")
        print(f"  Exemplos de documentos:")
        for doc in docs_sample:
            print(f"    - {doc}")
    
    print()
    print("=" * 70)
    print("RECOMENDAÇÃO")
    print("=" * 70)
    
    # Códigos que aparecem em >10% dos docs são claramente sistema
    system_codes = [uc for uc, count in freq.items() if count / total_docs > 0.10]
    
    print(f"\nCódigos de SISTEMA (>10% dos docs) - BLACKLIST RECOMENDADA:")
    for uc in system_codes:
        print(f"  - {uc}: {freq[uc]} ocorrências ({(freq[uc]/total_docs)*100:.1f}%)")
    
    # Códigos que aparecem em 5-10% são duvidosos
    doubtful_codes = [uc for uc, count in freq.items() if 0.05 <= count / total_docs <= 0.10]
    
    if doubtful_codes:
        print(f"\nCódigos DUVIDOSOS (5-10% dos docs) - VERIFICAR MANUALMENTE:")
        for uc in doubtful_codes:
            print(f"  - {uc}: {freq[uc]} ocorrências ({(freq[uc]/total_docs)*100:.1f}%)")
    
    # Salvar análise
    analysis = {
        'system_codes': system_codes,
        'doubtful_codes': doubtful_codes,
        'frequency': dict(freq.most_common(100))
    }
    
    output_file = Path('output/cpfl_paulista_final/analise_codigos_recorrentes.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    
    print(f"\nAnálise salva em: {output_file}")

if __name__ == "__main__":
    main()
