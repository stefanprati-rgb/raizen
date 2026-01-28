import os
import pandas as pd
from pathlib import Path

BASE_DIR = Path("C:/Projetos/Raizen/data/processed")
IGNORE_CSVS = [
    Path("C:/Projetos/Raizen/output/datasets_consolidados/CPFL_PAULISTA/CPFL_PAULISTA.csv"),
    Path("C:/Projetos/Raizen/output/datasets_consolidados/CEMIG/CEMIG_FULL.csv"),
    Path("C:/Projetos/Raizen/output/datasets_consolidados/ELEKTRO/ELEKTRO_FULL.csv"),
    Path("C:/Projetos/Raizen/output/datasets_consolidados/LIGHT/LIGHT_FULL.csv"),
    Path("C:/Projetos/Raizen/output/datasets_consolidados/ENEL/ENEL_FULL.csv")
]

def main():
    processed_set = set()
    for csv_path in IGNORE_CSVS:
        if csv_path.exists():
            try:
                df = pd.read_csv(csv_path, sep=";", low_memory=False)
                if "arquivo_origem" in df.columns:
                    processed_set.update(df["arquivo_origem"].astype(str))
            except: pass
            
    print(f"Total Processado (Ignorar): {len(processed_set)}")
    
    count = 0
    examples = []
    
    for root, dirs, files in os.walk(BASE_DIR):
        if "output" in root or ".git" in root: continue
        
        for f in files:
            if f.lower().endswith(".pdf"):
                if f not in processed_set:
                    count += 1
                    if len(examples) < 5:
                        examples.append(str(Path(root)/f))
                        
    print(f"Arquivos Restantes: {count}")
    if examples:
        print("Exemplos:")
        for e in examples:
            print(f" - {e}")

if __name__ == "__main__":
    main()
