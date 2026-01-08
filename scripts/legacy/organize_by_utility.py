"""
Script para sub-organizar os PDFs por Distribuidora usando base oficial em Excel.
Caminho final: contratos_por_paginas/XX_paginas/NOME_DISTRIBUIDORA/arquivo.pdf
"""
import pdfplumber
import shutil
import re
import pandas as pd
from pathlib import Path
import logging

# Configuração
BASE_DIR = Path(r"C:\Projetos\Raizen\contratos_por_paginas")
EXCEL_PATH = Path(r"C:\Projetos\Raizen\AreaatuadistbaseBI.xlsx")

def load_distribuidoras():
    """Carrega distribuidoras do Excel e gera lista de nomes para busca."""
    try:
        df = pd.read_excel(EXCEL_PATH)
        # Pegar Siglas e Razões Sociais
        siglas = df['SIGLA'].dropna().unique().tolist()
        razoes = df['Razão Social'].dropna().unique().tolist()
        
        # Criar uma lista de busca (nomes em maiúsculo)
        search_list = []
        for s in siglas:
            if len(str(s)) > 1:
                search_list.append(str(s).upper())
        for r in razoes:
            if len(str(r)) > 3:
                # Pegar o primeiro nome da razão social (ex: "CPFL" de "CPFL PAULISTA")
                # e também o nome completo
                search_list.append(str(r).upper())
                first_part = str(r).split(' ')[0].upper()
                if len(first_part) > 3:
                    search_list.append(first_part)
        
        # Adicionar casos manuais/comuns que podem estar em formatos diferentes
        especiais = ["CPFL PAULISTA", "CPFL PIRATININGA", "ENEL SP", "ENEL RJ", "ENEL CE", "EQUATORIAL", "COELBA", "COELCE", "CELPE", "ENERGISA"]
        search_list.extend(especiais)
        
        return sorted(list(set(search_list)), key=len, reverse=True)
    except Exception as e:
        print(f"Erro ao carregar Excel: {e}")
        return ["CPFL PAULISTA", "CEMIG", "ENERGISA", "EQUATORIAL"]

SEARCH_LIST = load_distribuidoras()

def get_distribuidora_v2(pdf_path: Path) -> str:
    """Identifica distribuidora usando base oficial."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Varrer primeiras páginas
            total_text = ""
            for page in pdf.pages[:3]:
                page_text = page.extract_text()
                if page_text:
                    total_text += page_text.upper() + "\n"
            
            if not total_text:
                return "TEXTO_NAO_EXTRAIDO"

            # 1. Tentar encontrar o nome perto da palavra "DISTRIBUIDORA"
            lines = total_text.split('\n')
            for i, line in enumerate(lines):
                if "DISTRIBUIDORA" in line:
                    # Olhar essa linha e a próxima
                    context = line + " " + (lines[i+1] if i+1 < len(lines) else "")
                    for dist in SEARCH_LIST:
                        if dist in context:
                            return dist.replace(" ", "_")

            # 2. Busca global no texto (se não achou perto da palavra âncora)
            for dist in SEARCH_LIST:
                if dist in total_text:
                    return dist.replace(" ", "_")
                        
        return "OUTRAS_DESCONHECIDAS"
    except Exception as e:
        return f"ERRO_LEITURA"

def cleanup_and_reorganize():
    """Move arquivos de subpastas erradas para a pasta pai e re-organiza."""
    page_dirs = [d for d in BASE_DIR.iterdir() if d.is_dir() and "paginas" in d.name]
    
    for p_dir in page_dirs:
        print(f"\n📂 Limpando e re-organizando: {p_dir.name}")
        
        # 1. Mover tudo que está em subpastas de volta para a p_dir
        for sub_dir in [d for d in p_dir.iterdir() if d.is_dir()]:
            for file in sub_dir.glob("*.pdf"):
                shutil.move(file, p_dir / file.name)
            # Remover subpasta vazia
            try:
                sub_dir.rmdir()
            except:
                pass
        
        # 2. Agora processar os arquivos na p_dir
        pdfs = list(p_dir.glob("*.pdf"))
        print(f"  🔍 Analisando {len(pdfs)} arquivos...")
        
        for i, pdf_path in enumerate(pdfs):
            dist = get_distribuidora_v2(pdf_path)
            
            # Criar subpasta limpa
            # Limitar tamanho do nome da pasta para evitar caminhos muito longos
            folder_name = dist[:50]
            dist_dir = p_dir / folder_name
            dist_dir.mkdir(exist_ok=True)
            
            # Mover arquivo
            try:
                shutil.move(pdf_path, dist_dir / pdf_path.name)
            except:
                pass
                
            if (i+1) % 100 == 0:
                print(f"    Progresso: {i+1}/{len(pdfs)}...")

if __name__ == "__main__":
    cleanup_and_reorganize()
