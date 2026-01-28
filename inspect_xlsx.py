import pandas as pd
import os

files = [
    r"c:\Projetos\Raizen\docs\ERROS CADASTRO RZ 1.xlsx",
    r"c:\Projetos\Raizen\output\DATASET_FINAL_.xlsx"
]

for f in files:
    if os.path.exists(f):
        print(f"\n--- {f} ---")
        try:
            df = pd.read_excel(f, nrows=2)
            print("Columns:", df.columns.tolist())
            print("Sample Head (1 row):")
            print(df.head(1).to_dict(orient='records'))
        except Exception as e:
            print(f"Error reading {f}: {e}")
    else:
        print(f"\nFile not found: {f}")
