import pandas as pd
from pathlib import Path

CSV_PATH = Path("C:/Projetos/Raizen/output/datasets_consolidados/LIGHT/LIGHT_FULL.csv")

def main():
    if not CSV_PATH.exists(): return
    df = pd.read_csv(CSV_PATH, sep=";", low_memory=False)
    
    print(f"Total: {len(df)}")
    cols = ["num_instalacao", "cnpj", "data_adesao", "fidelidade", "representante_nome"]
    for c in cols:
        if c in df.columns:
            filled = df[c].notna().sum()
            print(f"{c}: {filled} ({filled/len(df):.1%})")

if __name__ == "__main__":
    main()
