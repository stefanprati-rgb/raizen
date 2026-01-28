import os
from pathlib import Path
from collections import Counter

BASE_DIR = Path("C:/Projetos/Raizen/data/processed")

def get_distributor_counts():
    counts = Counter()
    
    print(f"Varrendo {BASE_DIR}...")
    
    # Varre recursivamente
    for root, dirs, files in os.walk(BASE_DIR):
        # Ignorar pastas ocultas ou de sistema
        if ".git" in root or "__pycache__" in root:
            continue
            
        path = Path(root)
        # Assumindo estrutura: data/processed/{SUBDIR}/{DISTRIBUIDORA}/*.pdf
        # Vamos contar arquivos PDF dentro de pastas que parecem ser distribuidoras
        
        # Heuristica: Se tem PDF, o nome da pasta pai é a distribuidora?
        # Ou avo?
        # Estrutura observada: .../16_paginas/CPFL_PAULISTA/arquivo.pdf
        
        pdfs = [f for f in files if f.lower().endswith('.pdf')]
        if not pdfs:
            continue
            
        distribuidora = path.name
        
        # Normalização básica (opcional, só para agrupar visualmente agora)
        counts[distribuidora] += len(pdfs)

    return counts

def main():
    counts = get_distributor_counts()
    
    print("\nRanking de Distribuidoras (Top 20):")
    print("-" * 40)
    print(f"{'Distribuidora':<30} | {'Qtd':>5}")
    print("-" * 40)
    
    sorted_counts = counts.most_common()
    
    for dist, count in sorted_counts[:20]:
        print(f"{dist:<30} | {count:>5}")
        
    print("-" * 40)
    print(f"Total Arquivos PDF: {sum(counts.values())}")

if __name__ == "__main__":
    main()
