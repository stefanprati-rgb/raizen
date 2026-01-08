"""Debug Fresh4Pet - investigar EDP_SP"""
import pdfplumber
import unicodedata
import re
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

def normalize(t):
    if not isinstance(t, str): return ''
    return unicodedata.normalize('NFKD', t).encode('ASCII', 'ignore').decode('ASCII').upper().strip()

# Carregar mapa de cidades
df = pd.read_excel(r'C:\Projetos\Raizen\PAINEL DE DESEMPENHO DAS DISTRIBUIDORAS POR MUNICÍPIO.xlsx')
city_to_dist = {}
for _, row in df.iterrows():
    city = normalize(str(row['Município']))
    dist = str(row['Distribuidora']).strip()
    if city and len(city) >= 3:
        city_to_dist[city] = dist

# Lista de cidades atendidas por EDP
edp_cities = [city for city, dist in city_to_dist.items() if 'EDP' in dist.upper()]
print(f'Total de cidades EDP: {len(edp_cities)}')

# Ler PDF
pdf_path = r'C:\Projetos\Raizen\contratos_por_paginas\10_paginas\RGE\GD Fresh4Pet.pdf'
with pdfplumber.open(pdf_path) as pdf:
    text = ''
    for page in pdf.pages[:4]:
        t = page.extract_text()
        if t: text += t + '\n'
    
    text_norm = normalize(text)
    
    # Verificar se alguma cidade EDP está no texto
    print('\nCidades EDP encontradas no texto:')
    found = []
    for city in edp_cities:
        if len(city) >= 5 and city in text_norm:
            print(f'  {city} -> {city_to_dist[city]}')
            found.append(city)
    
    if not found:
        print('  Nenhuma cidade EDP encontrada!')
    
    # Verificar se EDP_SP como string existe no texto
    print('\nBusca direta por EDP:')
    if 'EDP' in text_norm:
        # Encontrar contexto
        idx = text_norm.find('EDP')
        print(f'  EDP encontrado na posicao {idx}')
        print(f'  Contexto: ...{text_norm[max(0,idx-30):idx+30]}...')
    else:
        print('  EDP NAO encontrado no texto!')
