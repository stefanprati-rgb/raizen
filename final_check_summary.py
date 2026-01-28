import pandas as pd
df = pd.read_csv(r'c:\Projetos\Raizen\uc_check_results.csv')
print(f"Total UCs found: {len(df)}")
print(f"Complete: {len(df[df['Completo'] == 'SIM'])}")
print(f"Incomplete: {len(df[df['Completo'] == 'NÃO'])}")
if len(df[df['Completo'] == 'NÃO']) > 0:
    print("Incomplete list:")
    print(df[df['Completo'] == 'NÃO'][['UC', 'Faltando']])
