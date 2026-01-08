"""Debug - encontrar EMPRESA na lista"""
import pandas as pd
import unicodedata

def normalize(t):
    if not isinstance(t, str): return ''
    return unicodedata.normalize('NFKD', t).encode('ASCII', 'ignore').decode('ASCII').upper().strip()

df = pd.read_excel(r'C:\Projetos\Raizen\AreaatuadistbaseBI.xlsx')

# Mostrar todas as razoes sociais
print('Razões Sociais (primeiros 20):')
for i, (_, row) in enumerate(df.iterrows()):
    if i >= 20: break
    sigla = normalize(str(row['SIGLA']))
    razao = normalize(str(row['Razão Social']))
    first = razao.split()[0] if razao.split() else ''
    print(f'{sigla:15} | {first:15} | {razao[:40]}')

# Verificar se há "EMPRESA" como primeira palavra
print()
print('Razões que começam com "EMPRESA":')
for _, row in df.iterrows():
    razao = normalize(str(row['Razão Social']))
    if razao.startswith('EMPRESA'):
        print(f'  {razao[:60]}')
