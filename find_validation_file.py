import glob
import pandas as pd
import os

folder = r"c:\Projetos\Raizen\output\enrichment"
files = glob.glob(os.path.join(folder, "*.xlsx"))

for f in files:
    try:
        df = pd.read_excel(f)
        if "VALIDACAO_ID" in df.columns:
            print(f"FOUND: {f}")
            print("Columns:")
            for col in df.columns:
                print(f"  - {col}")
            print(df["VALIDACAO_ID"].value_counts())
            print("-" * 30)
    except:
        pass
