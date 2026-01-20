"""
Analisar preenchimento dos campos no dataset final e identificar lacunas.
"""
import pandas as pd
from pathlib import Path

# Usar o dataset padronizado
DATASET_PATH = Path('output/cpfl_paulista_final/cpfl_dataset_final_padronizado.xlsx')

def main():
    print("Carregando dataset final...")
    df = pd.read_excel(DATASET_PATH)
    
    total = len(df)
    print(f"Total de registros: {total}")
    print()
    
    print("=" * 60)
    print("ANÁLISE DE PREENCHIMENTO POR CAMPO")
    print("=" * 60)
    print(f"{'Campo':<30} {'Preenchidos':<10} {'%':<8} {'Vazios'}")
    print("-" * 60)
    
    stats = []
    
    for col in df.columns:
        # Considerar vazio: NaN, None, string vazia, ou string com apenas espaços
        filled_mask = df[col].notna() & (df[col].astype(str).str.strip() != '')
        count = filled_mask.sum()
        pct = (count / total) * 100
        missing = total - count
        
        print(f"{col:<30} {count:<10} {pct:<7.1f}% {missing}")
        stats.append({'campo': col, 'pct': pct, 'missing': missing})
        
    print("-" * 60)
    print()
    
    # Identificar piores campos
    worst_fields = sorted([s for s in stats if s['pct'] < 80], key=lambda x: x['pct'])
    
    print("=" * 60)
    print("ÁREAS PRIORITÁRIAS PARA MELHORIA (<80% preenchimento)")
    print("=" * 60)
    
    if not worst_fields:
        print("Nenhum campo crítico identificado! Todos acima de 80%.")
    else:
        for item in worst_fields:
            if item['campo'] in ['nome_arquivo_origem', 'pasta_origem']:
                continue # Ignorar campos de metadados
                
            print(f"❌ {item['campo'].upper()}: apenas {item['pct']:.1f}% preenchido")
            print(f"   - Faltam dados em {item['missing']} registros")
            
            # Sugestão de melhoria baseada no campo
            sugestao = ""
            if 'data' in item['campo']:
                sugestao = "Melhorar regex de data (DD/MM/AAAA, extenso, espaços)"
            elif 'representante' in item['campo']:
                sugestao = "Buscar em páginas de assinatura (final do doc) ou preâmbulo"
            elif 'fidelidade' in item['campo']:
                sugestao = "Buscar termos como 'Prazo de Vigência', 'Meses', 'Anos'"
            elif 'aviso' in item['campo']:
                sugestao = "Buscar cláusulas de 'Rescisão' ou 'Denúncia'"
            elif 'participacao' in item['campo']:
                sugestao = "Buscar tabelas de 'Rateio', 'Percentual', 'Cotas'"
            
            if sugestao:
                print(f"   -> Sugestão: {sugestao}")
            print()

if __name__ == "__main__":
    main()
