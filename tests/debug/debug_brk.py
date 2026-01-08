"""Debug BRK - encontrar origem de EQUATORIAL_PA"""
import pdfplumber
import unicodedata
import re
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

def normalize(t):
    return unicodedata.normalize('NFKD', t).encode('ASCII', 'ignore').decode('ASCII').upper() if t else ''

# Carregar base de cidades
df = pd.read_excel(r'C:\Projetos\Raizen\PAINEL DE DESEMPENHO DAS DISTRIBUIDORAS POR MUNICÍPIO.xlsx')
city_to_dist = {}
for _, row in df.iterrows():
    city = normalize(str(row['Município']))
    dist = str(row['Distribuidora']).strip()
    if city and len(city) >= 3:
        city_to_dist[city] = dist

# Cidades atendidas por Equatorial PA
equatorial_cities = [c for c, d in city_to_dist.items() if 'EQUATORIAL' in d.upper() and 'PA' in d.upper()]
print(f'Total cidades Equatorial PA: {len(equatorial_cities)}')

pdf_path = r'C:\Projetos\Raizen\contratos_por_paginas\17_paginas\RGE\SOLAR 47366 - BRK AMBIENTAL ARAGUAIA SANEAMENTO S A - 16876276000178 - Clicksign.pdf'
with pdfplumber.open(pdf_path) as pdf:
    text = ''
    for page in pdf.pages[:4]:
        t = page.extract_text()
        if t: text += t + '\n'
    
    text_norm = normalize(text)
    
    # Verificar cidades da Equatorial PA no texto
    print('\nCidades Equatorial PA encontradas no texto:')
    found = []
    for city in equatorial_cities:
        if len(city) >= 5 and city in text_norm:
            print(f'  {city} -> Equatorial PA')
            found.append(city)
    
    if not found:
        print('  Nenhuma encontrada diretamente')
        
    # Verificar ARAGUAIA (nome do cliente tem Araguaia)
    if 'ARAGUAIA' in text_norm:
        print('\nARAGUAIA encontrado no texto')
        # Ver se Araguaia é uma cidade
        araguaia_cities = [c for c in city_to_dist.keys() if 'ARAGUAIA' in c]
        for ac in araguaia_cities:
            print(f'  Cidade: {ac} -> {city_to_dist[ac]}')
