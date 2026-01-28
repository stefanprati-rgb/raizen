"""
Módulo de Indexação para localização de arquivos PDF no projeto.
Permite encontrar documentos por nome original ou por UC (em arquivos renomeados).
"""
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

def build_file_index() -> Tuple[Dict[str, str], List[Path]]:
    """
    Cria mapa de arquivos para busca rápida.
    Retorna: (dict_by_name, list_renamed_paths)
    """
    # Caminhos base conforme estrutura do projeto Raizen
    paths = {
        "golden": Path("C:/Projetos/Raizen/data/golden_source"),
        "renamed": Path("C:/Projetos/Raizen/output/termos_renomeados")
    }
    
    index_name = {}
    renamed_files = []

    # Indexar Golden (Busca pelo nome original preservado)
    if paths["golden"].exists():
        for p in paths["golden"].rglob("*.pdf"):
            index_name[p.name] = str(p)

    # Indexar Renomeados (Busca por UC contida no nome)
    if paths["renamed"].exists():
        for p in paths["renamed"].rglob("*.pdf"):
            renamed_files.append(p)
            
    return index_name, renamed_files

def find_pdf_path(uc: Optional[str], original_filename: Optional[str], index_name: Dict[str, str], renamed_files: List[Path]) -> Optional[str]:
    """
    Tenta localizar o caminho físico do PDF.
    1. Busca por nome original exato.
    2. Busca por UC no nome de arquivos já renomeados.
    """
    # 1. Tenta nome exato (Golden Source)
    if original_filename and original_filename in index_name:
        return index_name[original_filename]
    
    # 2. Tenta buscar UC dentro dos arquivos renomeados
    if uc:
        uc_str = str(uc).strip()
        # Evitar buscar UCs muito curtas que podem dar falso positivo
        if len(uc_str) >= 5:
            for p in renamed_files:
                if uc_str in p.name:
                    return str(p)
            
    return None
