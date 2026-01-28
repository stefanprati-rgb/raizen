import pandas as pd
df = pd.read_excel(r"c:\Projetos\Raizen\output\DATASET_FINAL_.xlsx")
match = df[df['UC / Instalação'].astype(str).str.contains('3176151')]
print(match[['UC / Instalação', 'arquivo_origem']])
