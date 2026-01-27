
import pandas as pd
from pathlib import Path

# Path to the latest dataset
DATASET_PATH = Path("C:/Projetos/Raizen/output/DATASET_FINAL_GOLDEN_RAIZEN_EXPLODED.xlsx")

def inspect_dataset():
    if not DATASET_PATH.exists():
        print(f"Dataset not found at {DATASET_PATH}")
        return

    try:
        df = pd.read_excel(DATASET_PATH)
        print("COLUMNS:")
        for col in df.columns:
            print(f"- {col}")
        
        cols = list(df.columns)
        print(f"Has 'caminho_completo'? {'caminho_completo' in cols}")
        print(f"Has 'arquivo_origem'? {'arquivo_origem' in cols}")
        
        if 'arquivo_origem' in cols:
             print(f"Sample Filename: {df.iloc[0]['arquivo_origem']}")
    except Exception as e:
        print(f"Error reading dataset: {e}")

if __name__ == "__main__":
    inspect_dataset()
