import pandas as pd
df = pd.read_excel(r'c:\Projetos\Raizen\output\enrichment\ERROS_CADASTRO_FULL_2.xlsx')
print("Columns in ERROS_CADASTRO_FULL_2.xlsx:")
for c in df.columns:
    print(c)
