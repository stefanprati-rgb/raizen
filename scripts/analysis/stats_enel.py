import pandas as pd
from pathlib import Path

CSV_PATH = Path("C:/Projetos/Raizen/output/datasets_consolidados/ENEL/ENEL_FULL.csv")

def main():
    if not CSV_PATH.exists(): return
    df = pd.read_csv(CSV_PATH, sep=";", low_memory=False)
    
    # Remover duplicatas se houver (baseado no nome do arquivo)
    df = df.drop_duplicates(subset=["arquivo_origem"])
    
    print(f"Total Único: {len(df)}")
    cols = ["num_instalacao", "cnpj", "data_adesao", "fidelidade", "representante_nome", "distribuidora"]
    for c in cols:
        if c in df.columns:
            filled = df[c].notna().sum()
            print(f"{c}: {filled} ({filled/len(df):.1%})")
            
    # Breakdown por distribuidora (SP, RJ, etc)
    if "distribuidora" in df.columns:
        print("\nPor Distribuidora:")
        print(df["distribuidora"].value_counts())

if __name__ == "__main__":
    main()
