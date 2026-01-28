import pandas as pd
path = r"c:\Projetos\Raizen\docs\BASE DE CLIENTES - Raizen.xlsx"
df = pd.read_excel(path, nrows=5)
print(df.columns.tolist())
print(df.head())
