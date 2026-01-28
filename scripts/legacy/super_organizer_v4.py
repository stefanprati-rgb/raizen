"""
Super Organizer V4 - Identificação por Nome Distribuidora + Cidade do Cliente
Usa dois Excels para máxima precisão:
1. AreaatuadistbaseBI.xlsx (Nomes oficiais e Siglas)
2. PAINEL DE DESEMPENHO DAS DISTRIBUIDORAS POR MUNICÍPIO.xlsx (Mapeamento por Cidade)

IGNORA endereços da Raízen para evitar falsos positivos.
"""
import pdfplumber
import shutil
import re
import pandas as pd
from pathlib import Path
import unicodedata

# Configuração
BASE_DIR = Path(r"C:\Projetos\Raizen\contratos_por_paginas")
EXCEL_BI = Path(r"C:\Projetos\Raizen\data\reference\AreaatuadistbaseBI.xlsx")
EXCEL_MUNICIPIO = Path(r"C:\Projetos\Raizen\data\reference\PAINEL DE DESEMPENHO DAS DISTRIBUIDORAS POR MUNICÍPIO.xlsx")

# Endereços ESPECÍFICOS da sede Raízen para IGNORAR
# NOTA: NÃO incluir "PIRACICABA" pois clientes podem ser de Piracicaba!
RAIZEN_ADDRESSES = [
    "CEZIRA GIOVANONI MORETTI",   # Endereço sede 1
    "ROD SP-308",                  # Rodovia da sede
    "SP-308",                      # Variação
    "FAZENDA COSTA PINTO",         # Endereço sede 2
    "13411-900",                   # CEP sede Piracicaba
    "28.986.143/0001-33",          # CNPJ Raízen GD
    "RAIZEN GD LTDA",              # Nome da empresa
]

def normalize_text(text):
    """Remove acentos e deixa em maiúsculo."""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    return text.upper().strip()

def is_raizen_address(text):
    """Verifica se o texto contém endereço da Raízen."""
    text_norm = normalize_text(text)
    for addr in RAIZEN_ADDRESSES:
        if addr in text_norm:
            return True
    return False

def load_databases():
    """Carrega as duas bases e cria mapas de busca."""
    print("Carregando bases de dados...")
    
    # 1. Base por Município -> Distribuidora
    df_mun = pd.read_excel(EXCEL_MUNICIPIO)
    city_to_dist = {}
    for _, row in df_mun.iterrows():
        city = normalize_text(str(row['Município']))
        dist = str(row['Distribuidora']).strip()
        if city and len(city) >= 3:
            city_to_dist[city] = dist
    
    print(f"  → {len(city_to_dist)} municípios carregados")
            
    # 2. Base de Nomes e Siglas de Distribuidoras
    df_bi = pd.read_excel(EXCEL_BI)
    dist_names = set()
    
    # Palavras genéricas a IGNORAR (causam falsos positivos)
    PALAVRAS_GENERICAS = {
        'EMPRESA', 'COOPERATIVA', 'CENTRAIS', 'COMPANHIA', 'DISTRIBUIDORA',
        'SOCIEDADE', 'ELETRICA', 'ENERGIA', 'FORCA', 'SERVICOS', 'LTDA',
        'NOVA', 'SISTEMA', 'GRUPO', 'REGIONAL', 'MUNICIPAL'
    }
    
    for _, row in df_bi.iterrows():
        sigla = normalize_text(str(row['SIGLA']))
        razao = normalize_text(str(row['Razão Social']))
        if len(sigla) > 2: 
            dist_names.add(sigla)
        if len(razao) > 3: 
            dist_names.add(razao)
            first = razao.split()[0] if razao.split() else ""
            # Só adicionar primeira palavra se não for genérica
            if len(first) > 3 and first not in PALAVRAS_GENERICAS: 
                dist_names.add(first)
            
    # Casos especiais conhecidos
    dist_names.update([
        "CPFL PAULISTA", "CPFL PIRATININGA", "CPFL", 
        "ENERGISA MT", "ENERGISA MS", "ENERGISA",
        "EQUATORIAL", "ENEL SP", "ENEL RJ", "ENEL CE", "ENEL GO", "ENEL",
        "COELBA", "COELCE", "CELESC", "CELPE", "COPEL", "CEMIG", 
        "RGE", "EDP", "LIGHT", "ELEKTRO", "NEOENERGIA"
    ])
    
    # Lista ordenada por tamanho (maiores primeiro)
    sorted_dists = sorted(list(dist_names), key=len, reverse=True)
    
    print(f"  → {len(sorted_dists)} nomes de distribuidoras carregados")
    
    return sorted_dists, city_to_dist

SORTED_DISTS, CITY_TO_DIST = load_databases()

def extract_client_city(text):
    """
    Extrai a cidade do endereço do CLIENTE.
    Procura padrão: Cidade - UF ou Cidade/UF ou Cidade, UF
    IGNORA endereços da Raízen.
    """
    text_norm = normalize_text(text)
    
    # Se contém endereço da Raízen, não usar essa parte
    if is_raizen_address(text_norm):
        return None
    
    # Padrões comuns de cidade/UF no Brasil
    # Ex: "SAO PAULO - SP", "CAMPINAS/SP", "CURITIBA, PR", "BELO HORIZONTE-MINAS GERAIS"
    
    # Todos os 27 estados brasileiros por extenso
    ESTADOS_BR = (
        "ACRE|ALAGOAS|AMAPA|AMAZONAS|BAHIA|CEARA|DISTRITO FEDERAL|ESPIRITO SANTO|"
        "GOIAS|MARANHAO|MATO GROSSO DO SUL|MATO GROSSO|MINAS GERAIS|PARA|PARAIBA|"
        "PARANA|PERNAMBUCO|PIAUI|RIO DE JANEIRO|RIO GRANDE DO NORTE|RIO GRANDE DO SUL|"
        "RONDONIA|RORAIMA|SANTA CATARINA|SAO PAULO|SERGIPE|TOCANTINS"
    )
    
    patterns = [
        rf'([A-Z][A-Z\s]{{2,30}})\s*[-/,]\s*({ESTADOS_BR})',  # Cidade - Estado por extenso
        r'([A-Z][A-Z\s]{2,30})\s*[-/,]\s*([A-Z]{2})\b',  # Cidade - UF (2 letras)
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text_norm)
        for city, uf in matches:
            city = city.strip()
            # Ignorar se for parte do endereço Raízen
            if any(addr in city for addr in RAIZEN_ADDRESSES):
                continue
            if len(city) >= 3:
                return city
    
    return None

def identify_distributor(pdf_path):
    """
    Estratégia de 3 camadas:
    1. Nome explícito perto de 'DISTRIBUIDORA'
    2. Cidade do endereço do CLIENTE → cruzar com base
    3. Nome em qualquer lugar do texto
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages[:4]:  # Primeiras 4 páginas
                t = page.extract_text()
                if t: 
                    text += t + "\n"
            
            if not text: 
                return "ERRO_OCR"
            
            text_norm = normalize_text(text)
            
            # ========== ESTRATÉGIA 1: Nome próximo à palavra "DISTRIBUIDORA" ==========
            lines = text_norm.split('\n')
            for i, line in enumerate(lines):
                if "DISTRIBUIDORA" in line:
                    # Contexto: linha atual + próxima
                    context = line + " " + (lines[i+1] if i+1 < len(lines) else "")
                    for d in SORTED_DISTS:
                        # Para siglas curtas, usar word boundary
                        if len(d) <= 4:
                            pattern = rf'\b{re.escape(d)}\b'
                            if re.search(pattern, context):
                                return d.replace(" ", "_")
                        else:
                            if d in context:
                                return d.replace(" ", "_")

            # ========== ESTRATÉGIA 2: Cidade do Cliente → Base de Municípios ==========
            # Procurar bloco de endereço do cliente (geralmente após "Endereço" ou "CONSORCIADA")
            address_block = ""
            
            # Tentar extrair bloco de endereço
            endereco_match = re.search(r'ENDERECO[:\s]*([^\n]+(?:\n[^\n]+){0,2})', text_norm)
            if endereco_match:
                address_block = endereco_match.group(1)
            
            # Se não é endereço Raízen, tentar extrair cidade
            if address_block and not is_raizen_address(address_block):
                city = extract_client_city(address_block)
                if city and city in CITY_TO_DIST:
                    dist = CITY_TO_DIST[city]
                    return normalize_text(dist).replace(" ", "_")
            
            # Busca alternativa: procurar padrões de cidade/UF em todo o texto
            # mas fora de contextos Raízen
            for line in lines:
                if is_raizen_address(line):
                    continue
                city = extract_client_city(line)
                if city and city in CITY_TO_DIST:
                    dist = CITY_TO_DIST[city]
                    return normalize_text(dist).replace(" ", "_")

            # ========== ESTRATÉGIA 3: Busca global por nome de distribuidora ==========
            # IMPORTANTE: Usar word boundary para evitar match dentro de outras palavras
            # Ex: "RGE" não deve dar match em "ENERGETICA"
            for d in SORTED_DISTS:
                # Para siglas curtas (<=4 chars), usar regex com word boundary
                if len(d) <= 4:
                    pattern = rf'\b{re.escape(d)}\b'
                    if re.search(pattern, text_norm):
                        return d.replace(" ", "_")
                else:
                    # Para nomes longos, substring é OK
                    if d in text_norm:
                        return d.replace(" ", "_")
                    
        return "OUTRAS_DESCONHECIDAS"
    except Exception as e:
        return "ERRO_LEITURA"

def process():
    """Processa todas as pastas de páginas."""
    page_dirs = sorted([d for d in BASE_DIR.iterdir() if d.is_dir() and "paginas" in d.name])
    
    total_processed = 0
    total_identified = 0
    
    for p_dir in page_dirs:
        print(f"\n📂 Processando: {p_dir.name}")
        
        # 1. Limpeza: Trazer arquivos de subpastas para o nível p_dir
        for sub in [d for d in p_dir.iterdir() if d.is_dir()]:
            for f in sub.glob("*.pdf"):
                try:
                    shutil.move(f, p_dir / f.name)
                except:
                    pass
            try: 
                sub.rmdir() 
            except: 
                pass
            
        # 2. Organização
        pdfs = list(p_dir.glob("*.pdf"))
        print(f"  🔍 Analisando {len(pdfs)} arquivos...")
        
        identified_count = 0
        
        for i, pdf_path in enumerate(pdfs):
            dist = identify_distributor(pdf_path)
            
            if dist != "OUTRAS_DESCONHECIDAS" and dist != "ERRO_LEITURA" and dist != "ERRO_OCR":
                identified_count += 1
            
            # Pasta de destino (limitar nome a 50 chars)
            dest_dir = p_dir / dist[:50]
            dest_dir.mkdir(exist_ok=True)
            
            try:
                shutil.move(pdf_path, dest_dir / pdf_path.name)
            except:
                pass
                
            if (i+1) % 200 == 0:
                print(f"    Progresso: {i+1}/{len(pdfs)}...")
        
        total_processed += len(pdfs)
        total_identified += identified_count
        print(f"  ✅ Identificados: {identified_count}/{len(pdfs)} ({100*identified_count/max(1,len(pdfs)):.1f}%)")
    
    print(f"\n{'='*50}")
    print(f"RESUMO FINAL")
    print(f"{'='*50}")
    print(f"Total processado: {total_processed}")
    print(f"Total identificado: {total_identified} ({100*total_identified/max(1,total_processed):.1f}%)")

if __name__ == "__main__":
    process()
