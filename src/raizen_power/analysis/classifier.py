import re
import unicodedata
import pandas as pd
import fitz  # PyMuPDF
from pathlib import Path
from enum import Enum, auto
from typing import Optional, List, Dict, Tuple, Set, Any
from dataclasses import dataclass

# Caminhos para arquivos de referência
# Ajustar conforme necessário ou mover para arquivo de configuração
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
EXCEL_BI = PROJECT_ROOT / "data/reference/AreaatuadistbaseBI.xlsx"
EXCEL_MUNICIPIO = PROJECT_ROOT / "data/reference/PAINEL DE DESEMPENHO DAS DISTRIBUIDORAS POR MUNICÍPIO.xlsx"

class ContractCategory(Enum):
    SIMPLES = auto()      # <= 7 paginas
    PADRAO = auto()       # 8-16 paginas
    GUARDA_CHUVA = auto() # > 16 paginas

@dataclass
class ContractClassification:
    category: ContractCategory
    distributor: str
    pages: int
    confidence: float = 0.0

# Endereços da Raízen para ignorar
RAIZEN_ADDRESSES = [
    "CEZIRA GIOVANONI MORETTI", "ROD SP-308", "SP-308",
    "FAZENDA COSTA PINTO", "13411-900", "28.986.143/0001-33",
    "RAIZEN GD LTDA"
]

PALAVRAS_GENERICAS = {
    'EMPRESA', 'COOPERATIVA', 'CENTRAIS', 'COMPANHIA', 'DISTRIBUIDORA',
    'SOCIEDADE', 'ELETRICA', 'ENERGIA', 'FORCA', 'SERVICOS', 'LTDA',
    'NOVA', 'SISTEMA', 'GRUPO', 'REGIONAL', 'MUNICIPAL'
}

# Cache das bases de dados
_SORTED_DISTS = None
_CITY_TO_DIST = None

def normalize_text(text: Any) -> str:
    if not isinstance(text, str): return ""
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    return text.upper().strip()

def is_raizen_address(text: str) -> bool:
    text_norm = normalize_text(text)
    return any(addr in text_norm for addr in RAIZEN_ADDRESSES)

def load_databases() -> Tuple[List[str], Dict[str, str]]:
    global _SORTED_DISTS, _CITY_TO_DIST
    if _SORTED_DISTS is not None and _CITY_TO_DIST is not None:
        return _SORTED_DISTS, _CITY_TO_DIST

    try:
        if not EXCEL_MUNICIPIO.exists() or not EXCEL_BI.exists():
            print(f"Bases de dados não encontradas em {PROJECT_ROOT}/data/reference/")
            return [], {}

        # 1. Base Municípios
        df_mun = pd.read_excel(EXCEL_MUNICIPIO)
        city_to_dist = {}
        for _, row in df_mun.iterrows():
            city = normalize_text(str(row['Município']))
            dist = str(row['Distribuidora']).strip()
            if city and len(city) >= 3:
                city_to_dist[city] = dist
        
        # 2. Base Distribuidoras
        df_bi = pd.read_excel(EXCEL_BI)
        dist_names = set()
        for _, row in df_bi.iterrows():
            sigla = normalize_text(str(row['SIGLA']))
            razao = normalize_text(str(row['Razão Social']))
            if len(sigla) > 2: dist_names.add(sigla)
            if len(razao) > 3: 
                dist_names.add(razao)
                first = razao.split()[0] if razao.split() else ""
                if len(first) > 3 and first not in PALAVRAS_GENERICAS:
                    dist_names.add(first)
        
        # Casos especiais
        dist_names.update([
            "CPFL PAULISTA", "CPFL PIRATININGA", "CPFL", 
            "ENERGISA MT", "ENERGISA MS", "ENERGISA",
            "EQUATORIAL", "ENEL SP", "ENEL RJ", "ENEL CE", "ENEL GO", "ENEL",
            "COELBA", "COELCE", "CELESC", "CELPE", "COPEL", "CEMIG", 
            "RGE", "EDP", "LIGHT", "ELEKTRO", "NEOENERGIA"
        ])
        
        sorted_dists = sorted(list(dist_names), key=len, reverse=True)
        
        _SORTED_DISTS = sorted_dists
        _CITY_TO_DIST = city_to_dist
        return sorted_dists, city_to_dist
    except Exception as e:
        print(f"Erro ao carregar bases: {e}")
        return [], {}

def extract_client_city(text_norm: str) -> Optional[str]:
    if is_raizen_address(text_norm): return None
    
    ESTADOS_BR = (
        "ACRE|ALAGOAS|AMAPA|AMAZONAS|BAHIA|CEARA|DISTRITO FEDERAL|ESPIRITO SANTO|"
        "GOIAS|MARANHAO|MATO GROSSO DO SUL|MATO GROSSO|MINAS GERAIS|PARA|PARAIBA|"
        "PARANA|PERNAMBUCO|PIAUI|RIO DE JANEIRO|RIO GRANDE DO NORTE|RIO GRANDE DO SUL|"
        "RONDONIA|RORAIMA|SANTA CATARINA|SAO PAULO|SERGIPE|TOCANTINS"
    )
    
    patterns = [
        rf'([A-Z][A-Z\s]{{2,30}})\s*[-/,]\s*({ESTADOS_BR})',
        r'([A-Z][A-Z\s]{2,30})\s*[-/,]\s*([A-Z]{2})\b',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text_norm)
        for city, uf in matches:
            city = city.strip()
            if any(addr in city for addr in RAIZEN_ADDRESSES): continue
            if len(city) >= 3: return city
    return None

def identify_distributor_from_text(text: str) -> str:
    """Identifica distribuidora a partir do texto extraído (otimizado)."""
    sorted_dists, city_to_dist = load_databases()
    if not sorted_dists: return "DESCONHECIDO"

    try:
        if not text: return "ERRO_OCR"
        text_norm = normalize_text(text)
        lines = text_norm.split('\n')
        
        # 1. Nome explícito
        for i, line in enumerate(lines):
            if "DISTRIBUIDORA" in line:
                context = line + " " + (lines[i+1] if i+1 < len(lines) else "")
                for d in sorted_dists:
                    if len(d) <= 4:
                        if re.search(rf'\b{re.escape(d)}\b', context):
                            return d.replace(" ", "_")
                    else:
                        if d in context:
                            return d.replace(" ", "_")
        
        # 2. Cidade do Cliente
        # Tentar bloco de endereço primeiro
        endereco_match = re.search(r'ENDERECO[:\s]*([^\n]+(?:\n[^\n]+){0,2})', text_norm)
        if endereco_match:
            block = endereco_match.group(1)
            if not is_raizen_address(block):
                city = extract_client_city(block)
                if city and city in city_to_dist:
                    return normalize_text(city_to_dist[city]).replace(" ", "_")
        
        # Tentar linhas avulsas
        for line in lines:
            if is_raizen_address(line): continue
            city = extract_client_city(line)
            if city and city in city_to_dist:
                return normalize_text(city_to_dist[city]).replace(" ", "_")
        
        # 3. Busca Global
        for d in sorted_dists:
            if len(d) <= 4:
                if re.search(rf'\b{re.escape(d)}\b', text_norm):
                    return d.replace(" ", "_")
            else:
                if d in text_norm:
                    return d.replace(" ", "_")
                    
        return "OUTRAS_DESCONHECIDAS"
    except Exception as e:
        print(f"Erro ao identificar distribuidora: {e}")
        return "ERRO_LEITURA"

def identify_distributor(pdf_path: str) -> str:
    """Identifica distribuidora abrindo o PDF (método legado/conveniente)."""
    try:
        with fitz.open(pdf_path) as pdf:
            text = ""
            for i in range(min(4, len(pdf))):
                t = pdf[i].get_text()
                if t: text += t + "\n"
        return identify_distributor_from_text(text)
    except Exception as e:
        print(f"Erro ao ler PDF {pdf_path}: {e}")
        return "ERRO_LEITURA"

def classify_contract(pdf_path: str) -> ContractClassification:
    """Classifica contrato por categoria (páginas) e distribuidora."""
    try:
        with fitz.open(pdf_path) as pdf:
            pages = len(pdf)
            text = ""
            for i in range(min(4, pages)):
                t = pdf[i].get_text()
                if t: text += t + "\n"
    except:
        pages = 0
        text = ""

    distributor = identify_distributor_from_text(text)
    
    category = ContractCategory.PADRAO
    if pages <= 7:
        category = ContractCategory.SIMPLES
    elif pages > 16:
        category = ContractCategory.GUARDA_CHUVA
        
    return ContractClassification(
        category=category,
        distributor=distributor,
        pages=pages,
        confidence=1.0 if distributor not in ["OUTRAS_DESCONHECIDAS", "ERRO_LEITURA", "ERRO_OCR"] else 0.0
    )
