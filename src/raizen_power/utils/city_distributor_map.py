import pandas as pd
from typing import Dict, List, Optional
import logging
from pathlib import Path
from raizen_power.utils.distributor_rules import _normalize_key

logger = logging.getLogger(__name__)

# Cache do mapeamento
_CITY_MAP: Dict[str, List[str]] = {}

# Caminho do Excel
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
EXCEL_PATH = PROJECT_ROOT / "data/reference/PAINEL DE DESEMPENHO DAS DISTRIBUIDORAS POR MUNICÍPIO.xlsx"

# Mapeamento auxiliar de Distribuidora -> UFs de atuação
# Baseado nas principais concessionárias do Brasil
DISTRIBUTOR_STATES = {
    # CPFL
    "CPFL PAULISTA": ["SP"],
    "CPFL PIRATININGA": ["SP"],
    "CPFL SANTA CRUZ": ["SP", "PR", "MG"],
    "RGE": ["RS"],
    # NEOENERGIA
    "NEOENERGIA ELEKTRO": ["SP", "MS"],
    "NEOENERGIA COELBA": ["BA"],
    "NEOENERGIA PERNAMBUCO": ["PE"],
    "NEOENERGIA COSERN": ["RN"],
    "NEOENERGIA BRASILIA": ["DF"],
    # ENEL
    "ENEL SP": ["SP"],
    "ENEL RJ": ["RJ"],
    "ENEL CE": ["CE"],
    "ENEL GO": ["GO"],
    # CEMIG
    "CEMIG D": ["MG"],
    "CEMIG": ["MG"],
    # EQUATORIAL
    "EQUATORIAL MA": ["MA"],
    "EQUATORIAL PA": ["PA"],
    "EQUATORIAL PI": ["PI"],
    "EQUATORIAL AL": ["AL"],
    "EQUATORIAL GO": ["GO"],
    "EQUATORIAL RS": ["RS"],
    # OUTRAS
    "LIGHT": ["RJ"],
    "COPEL": ["PR"],
    "CELESC": ["SC"],
    "EDP SP": ["SP"],
    "EDP ES": ["ES"],
    "ENERGISA": ["MT", "MS", "TO", "PB", "SE", "AC", "RO", "RJ", "SP", "MG", "PR"],
}

def load_mapping():
    """Carrega o mapeamento do Excel para memória."""
    global _CITY_MAP
    if _CITY_MAP:
        return

    if not EXCEL_PATH.exists():
        logger.warning(f"Arquivo de referência não encontrado: {EXCEL_PATH}")
        return

    try:
        df = pd.read_excel(EXCEL_PATH, usecols=["Distribuidora", "Município"])
        
        # Normalizar e criar índice
        for _, row in df.iterrows():
            dist = str(row["Distribuidora"]).strip()
            city = str(row["Município"]).strip().upper()
            
            # Normalizar nome da distribuidora para formato padrão do projeto
            dist_norm = _normalize_dist_name(dist)
            
            if city not in _CITY_MAP:
                _CITY_MAP[city] = []
            if dist_norm not in _CITY_MAP[city]:
                _CITY_MAP[city].append(dist_norm)
                
        logger.info(f"Mapeamento de cidades carregado: {len(_CITY_MAP)} municípios")
        
    except Exception as e:
        logger.error(f"Erro ao carregar mapa de cidades: {e}")

def _normalize_dist_name(raw_name: str) -> str:
    """Converte nomes do Excel para o padrão do projeto."""
    name = raw_name.upper()
    
    # Mapeamentos diretos
    if "CEMIG" in name: return "CEMIG" # O projeto usa CEMIG genérico ou CEMIG D? O excel tem "Cemig-D"
    if "CPFL-PAULISTA" in name or "CPFL PAULISTA" in name: return "CPFL PAULISTA"
    if "PIRATININGA" in name: return "CPFL PIRATININGA"
    if "SANTA CRUZ" in name: return "CPFL SANTA CRUZ"
    if "ELEKTRO" in name: return "NEOENERGIA ELEKTRO"
    if "COELBA" in name: return "NEOENERGIA COELBA"
    if "CELPE" in name or "PERNAMBUCO" in name: return "NEOENERGIA PERNAMBUCO"
    if "COSERN" in name: return "NEOENERGIA COSERN"
    if "RGE" in name: return "RGE"
    if "ENEL" in name and "CEARA" in name: return "ENEL CE"
    if "ENEL" in name and "RIO" in name: return "ENEL RJ"
    if "ENEL" in name and "GOIAS" in name: return "ENEL GO"
    if "ENEL" in name and "SAO PAULO" in name: return "ENEL SP"
    if "LIGHT" in name: return "LIGHT"
    if "COPEL" in name: return "COPEL"
    if "CELESC" in name: return "CELESC"
    
    return name

def get_distributor_by_city(city: str, uf: str) -> Optional[str]:
    """
    Busca a distribuidora correta baseada na Cidade e UF.
    """
    if not city:
        return None
        
    load_mapping()
    
    city_upper = city.upper().strip()
    candidates = _CITY_MAP.get(city_upper)
    
    if not candidates:
        return None
        
    # Se só tem uma opção, retorna ela (confiando no Excel)
    if len(candidates) == 1:
        return candidates[0]
        
    # Se tem UF, tentar filtrar
    if uf:
        uf_upper = uf.upper().strip()
        valid_candidates = []
        
        for dist in candidates:
            # Verificar se a distribuidora atua nessa UF
            # Busca heurística: se UF está no nome ou na lista de estados
            allowed_states = DISTRIBUTOR_STATES.get(dist) or []
            
            # Se não temos cadastro de estados para essa dist, aceitamos (permissivo)
            if not allowed_states: 
                valid_candidates.append(dist)
                continue
                
            if uf_upper in allowed_states:
                valid_candidates.append(dist)
                
        if len(valid_candidates) == 1:
            return valid_candidates[0]
            
        # Se ainda temos ambiguidade, retornar a primeira ou None?
        # Ex: Campinas -> CPFL Paulista, CPFL Santa Cruz?
        # Retorna a primeira válida filtered
        if valid_candidates:
            return valid_candidates[0]
            
    # Fallback: retorna o primeiro candidato original
    return candidates[0]
