import pandas as pd
path = r"c:\Projetos\Raizen\docs\BASE DE CLIENTES - Raizen.xlsx"
df = pd.read_excel(path)
match = df[df['NUMERO UC'].astype(str).str.contains('3176151')]
print(match)
