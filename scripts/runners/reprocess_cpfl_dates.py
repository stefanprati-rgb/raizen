#!/usr/bin/env python3
"""
Script pontual para extrair APENAS a Data de Adesão dos contratos da CPFL PAULISTA.
Usa o novo regex descoberto para assinaturas digitais (Clicksign/Qualisign).
Atualiza o CSV consolidado existente.
"""

import re
import pandas as pd
from pathlib import Path
import pdfplumber
import logging

# Configurações
BASE_DIR = Path("C:/Projetos/Raizen/data/processed")
CSV_PATH = Path("C:/Projetos/Raizen/output/datasets_consolidados/CPFL_PAULISTA/CPFL_PAULISTA.csv")

# Regexes ajustados para Logs de Assinatura
DATA_PATTERNS = [
    r'(?:Assinou\s+como\s+contratante\s+em|Assinado\s+em)\s+(\d{1,2}\s+[a-zç]+\s+\d{4})',
    r'Data\s+limite\s+para\s+assinatura.*?:?\s*(\d{1,2}\s+de\s+[a-zç]+\s+de\s+\d{4})',
    r'(\d{1,2}\s+[a-zç]+\s+\d{4}),?\s+\d{2}:\d{2}:\d{2}.*?Operador', # 06 set 2022, 08:36...
]

# Mapa de meses para converter extenso -> numérico
MESES = {
    'jan': '01', 'janeiro': '01',
    'fev': '02', 'fevereiro': '02',
    'mar': '03', 'março': '03',
    'abr': '04', 'abril': '04',
    'mai': '05', 'maio': '05',
    'jun': '06', 'junho': '06',
    'jul': '07', 'julho': '07',
    'ago': '08', 'agosto': '08',
    'set': '09', 'setembro': '09',
    'out': '10', 'outubro': '10',
    'nov': '11', 'novembro': '11',
    'dez': '12', 'dezembro': '12'
}

def parse_data_extenso(data_str):
    """Converte '14 set 2022' ou '04 de dezembro de 2022' para '14/09/2022'"""
    parts = data_str.lower().replace(' de ', ' ').split()
    if len(parts) < 3:
        return None
    
    dia, mes_ext, ano = parts[0], parts[1], parts[-1]
    
    # Normalizar mês (remover acentos se necessário, já tratado no regex [a-zç])
    for chave, valor in MESES.items():
        if mes_ext.startswith(chave):
            return f"{dia.zfill(2)}/{valor}/{ano}"
            
    return None

def extract_date_from_text(text):
    """Busca data nos padrões definidos"""
    for pattern in DATA_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw_date = match.group(1)
            parsed = parse_data_extenso(raw_date)
            if parsed:
                return parsed
    return None

def find_pdf_path(filename, base_dir):
    """Encontra o PDF correspondente ao nome do arquivo"""
    # Tenta achar em qualquer subpasta de páginas da CPFL_PAULISTA
    # Otimização: buscar direto pelo nome se possível, ou iterar
    # Como são 3 mil arquivos, iterar tudo pode ser lento
    # Vamos assumir que filename é algo como "SOLAR...pdf"
    
    # Procurar primeiro em 16_paginas (onde tem mais)
    candidate = base_dir / "16_paginas/CPFL_PAULISTA" / filename
    if candidate.exists():
        return candidate
        
    # Fallback: buscar em todas
    results = list(base_dir.rglob(filename))
    if results:
        return results[0]
    return None

def main():
    print("=" * 60)
    print("REPROCESSAMENTO DE DATAS - CPFL PAULISTA")
    print("=" * 60)
    
    logging.getLogger("pdfminer").setLevel(logging.ERROR)
    
    if not CSV_PATH.exists():
        print(f"Erro: CSV não encontrado: {CSV_PATH}")
        return
        
    print(f"Lendo dataset: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, sep=";", low_memory=False)
    
    # Verificar colunas
    if "data_adesao" not in df.columns:
        df["data_adesao"] = None
        
    # Filtrar registros sem data
    sem_data = df[pd.isna(df["data_adesao"]) | (df["data_adesao"] == "")]
    print(f"Registros totais: {len(df)}")
    print(f"Sem data adesão: {len(sem_data)}")
    
    if len(sem_data) == 0:
        print("Todos os registros já possuem data!")
        return

    # Processar
    print("\nIniciando extração (pode demorar)...")
    atualizados = 0
    erros = 0
    nao_encontrados = 0
    
    # Processar apenas os primeiros 50 como teste inicial (comente a linha abaixo para rodar completo)
    # subset = sem_data.head(50) 
    subset = sem_data # Rodar em todos
    
    for idx, row in subset.iterrows():
        arquivo = row.get("arquivo_origem")
        if not arquivo:
            continue
            
        pdf_path = find_pdf_path(arquivo, BASE_DIR)
        
        if not pdf_path:
            # print(f"PDF não encontrado: {arquivo}")
            continue
            
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Pegar texto das últimas 3 páginas (onde costuma estar o log) e da primeira
                num_pages = len(pdf.pages)
                
                # Texto para busca
                text_content = ""
                
                # Primeira página (às vezes tem data no cabeçalho)
                if num_pages > 0:
                     text_content += pdf.pages[0].extract_text() or ""
                
                # Últimas 3 páginas (logs)
                start_page = max(1, num_pages - 3)
                for i in range(start_page, num_pages):
                    text_content += "\n" + (pdf.pages[i].extract_text() or "")
            
            nova_data = extract_date_from_text(text_content)
            
            if nova_data:
                df.at[idx, "data_adesao"] = nova_data
                atualizados += 1
                print(f"✓ {arquivo[:40]}... -> {nova_data}")
            else:
                nao_encontrados += 1
                
        except Exception as e:
            erros += 1
            print(f"Erro em {arquivo}: {e}")
            
        if (idx + 1) % 100 == 0:
            print(f"Processados: {idx+1}/{len(subset)} (Atualizados: {atualizados})")

    # Salvar resultado
    print("-" * 60)
    print(f"RESUMO:")
    print(f"Atualizados: {atualizados}")
    print(f"Não encontrados: {nao_encontrados}")
    print(f"Erros: {erros}")
    
    df.to_csv(CSV_PATH, sep=";", index=False)
    print(f"\nCSV atualizado salvo em: {CSV_PATH}")
    
    # Salvar Excel atualizado também
    excel_path = Path("C:/Projetos/Raizen/output/datasets/cpfl/dataset_CPFL_PAULISTA_final.xlsx")
    if excel_path.exists():
        print(f"Atualizando Excel: {excel_path}")
        with pd.ExcelWriter(excel_path, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="CPFL_PAULISTA", index=False)
            
    print("Concluído!")

if __name__ == "__main__":
    main()
