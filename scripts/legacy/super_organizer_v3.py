"""
Super Organizer V3 - Distribuidora + Município
Usa dois Excels para máxima precisão:
1. AreaatuadistbaseBI.xlsx (Nomes oficiais e Siglas)
2. PAINEL DE DESEMPENHO DAS DISTRIBUIDORAS POR MUNICÍPIO.xlsx (Mapeamento por Cidade)
"""
import pdfplumber
import shutil
import re
import pandas as pd
from pathlib import Path
import unicodedata

# Configuração
BASE_DIR = Path(r"C:\Projetos\Raizen\contratos_por_paginas")
EXCEL_BI = Path(r"C:\Projetos\Raizen\AreaatuadistbaseBI.xlsx")
EXCEL_MUNICIPIO = Path(r"C:\Projetos\Raizen\PAINEL DE DESEMPENHO DAS DISTRIBUIDORAS POR MUNICÍPIO.xlsx")

def normalize_text(text):
    """Remove acentos e deixa em maiúsculo."""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    return text.upper().strip()

def load_databases():
    """Carrega as duas bases e cria mapas de busca."""
    print("Carregando bases de dados...")
    
    # 1. Base por Município
    df_mun = pd.read_excel(EXCEL_MUNICIPIO)
    # Criar mapa Cidade -> Distribuidora
    city_map = {}
    for _, row in df_mun.iterrows():
        city = normalize_text(str(row['Município']))
        dist = str(row['Distribuidora'])
        if city:
            if city not in city_map:
                city_map[city] = []
            city_map[city].append(dist)
            
    # 2. Base de Nomes e Siglas
    df_bi = pd.read_excel(EXCEL_BI)
    dist_names = set()
    for _, row in df_bi.iterrows():
        sigla = normalize_text(str(row['SIGLA']))
        razao = normalize_text(str(row['Razão Social']))
        if len(sigla) > 1: dist_names.add(sigla)
        if len(razao) > 3: 
            dist_names.add(razao)
            # Adicionar primeira palavra se for relevante
            first = razao.split(' ')[0]
            if len(first) > 3: dist_names.add(first)
            
    # Casos especiais conhecidos
    dist_names.update(["CPFL", "ENERGISA", "EQUATORIAL", "ENEL", "COELBA", "CELESC", "COPEL", "CEMIG", "RGE", "EDP", "LIGHT"])
    
    # Lista ordenada por tamanho (maiores primeiro para evitar match parcial)
    sorted_dists = sorted(list(dist_names), key=len, reverse=True)
    sorted_cities = sorted(list(city_map.keys()), key=len, reverse=True)
    
    return sorted_dists, city_map, sorted_cities

SORTED_DISTS, CITY_MAP, SORTED_CITIES = load_databases()

def identify_distributor(pdf_path):
    """
    Tenta identificar a distribuidora por:
    1. Nome direto no contexto da palavra 'DISTRIBUIDORA'
    2. Município encontrado no texto
    3. Nome direto em qualquer parte do texto
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages[:3]: # Primeiras 3 páginas
                t = page.extract_text()
                if t: text += t.upper() + "\n"
            
            if not text: return "ERRO_OCR"
            
            text_norm = normalize_text(text)
            
            # ESTRATÉGIA 1: Nome próximo à palavra "DISTRIBUIDORA"
            lines = text_norm.split('\n')
            for i, line in enumerate(lines):
                if "DISTRIBUIDORA" in line:
                    context = line + " " + (lines[i+1] if i+1 < len(lines) else "")
                    for d in SORTED_DISTS:
                        if d in context:
                            return d.replace(" ", "_")

            # ESTRATÉGIA 2: Buscar por Município
            # Vamos procurar por nomes de cidades da base
            # Para evitar falsos positivos (como nomes comuns), focamos em cidades grandes ou 
            # cidades encontradas no contexto de endereço
            for city in SORTED_CITIES:
                if len(city) < 5: continue # Pular cidades com nomes muito curtos para evitar lixo
                if city in text_norm:
                    # Se achou a cidade, pega a distribuidora correspondente
                    dists = CITY_MAP[city]
                    return dists[0].replace(" ", "_") # Pega a primeira que atende a cidade

            # ESTRATÉGIA 3: Busca global por nome de distribuidora
            for d in SORTED_DISTS:
                if d in text_norm:
                    return d.replace(" ", "_")
                    
        return "OUTRAS_DESCONHECIDAS"
    except:
        return "ERRO_LEITURA"

def process():
    # Listar pastas de páginas
    page_dirs = [d for d in BASE_DIR.iterdir() if d.is_dir() and "paginas" in d.name]
    
    for p_dir in page_dirs:
        print(f"\n📂 Processando: {p_dir.name}")
        
        # 1. Limpeza: Trazer arquivos de subpastas para o nível p_dir
        for sub in [d for d in p_dir.iterdir() if d.is_dir()]:
            for f in sub.glob("*.pdf"):
                try:
                    shutil.move(f, p_dir / f.name)
                except:
                    # Se já existe no destino, apenas deleta o da subpasta ou ignora
                    pass
            try: sub.rmdir() 
            except: pass
            
        # 2. Organização
        pdfs = list(p_dir.glob("*.pdf"))
        print(f"  Analizando {len(pdfs)} arquivos...")
        
        for i, pdf_path in enumerate(pdfs):
            dist = identify_distributor(pdf_path)
            
            # Pasta de destino
            dest_dir = p_dir / dist[:50]
            dest_dir.mkdir(exist_ok=True)
            
            try:
                shutil.move(pdf_path, dest_dir / pdf_path.name)
            except:
                pass
                
            if (i+1) % 100 == 0:
                print(f"    {i+1}/{len(pdfs)}...")

if __name__ == "__main__":
    process()
