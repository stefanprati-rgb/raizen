import pandas as pd
f = r"c:\Projetos\Raizen\output\DATASET_FINAL_.xlsx"
df = pd.read_excel(f, nrows=1)
print(df.columns.tolist())
