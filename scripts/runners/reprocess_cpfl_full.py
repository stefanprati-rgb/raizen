#!/usr/bin/env python3
"""
Script de Reprocessamento TOTAL para CPFL Paulista.
Objetivo: Garantir preenchimento dos 11 campos obrigatórios do schema.
Melhorias:
- Datas de adesão via logs de assinatura
- Aviso prévio com regex contextual
- Representante e Participação com regex tolerante
- Suporte a MULTI-UC (detectar múltiplas instalações no mesmo PDF)
"""

import re
import pandas as pd
from pathlib import Path
import pdfplumber
import logging
from datetime import datetime
import warnings

# Suprimir warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)

# Configurações
BASE_DIR = Path("C:/Projetos/Raizen/data/processed")
CSV_PATH = Path("C:/Projetos/Raizen/output/datasets_consolidados/CPFL_PAULISTA/CPFL_PAULISTA.csv")

# ==============================================================================
# NOVOS REGEXES APRIMORADOS
# ==============================================================================

# Data de Adesão (focados em logs de assinatura)
DATA_PATTERNS = [
    r'(?:Assinou\s+como\s+contratante\s+em|Assinado\s+em)\s+(\d{1,2}\s+[a-zç]+\s+\d{4})',
    r'Data\s+limite\s+para\s+assinatura.*?:?\s*(\d{1,2}\s+de\s+[a-zç]+\s+de\s+\d{4})',
    r'(\d{1,2}\s+[a-zç]+\s+\d{4}),?\s+\d{2}:\d{2}:\d{2}.*?Operador',
    r'Data\s+de\s+In[íi]cio.*?:?\s*(\d{2}/\d{2}/\d{4})',
]

# Aviso Prévio (contextual)
AVISO_PATTERNS = [
    r'prazo\s+de\s+(\d+)\s*(?:\(.*?\))?\s*dias.*?notifica[çc][ãa]o\s+de\s+den[úu]ncia',
    r'aviso\s+pr[ée]vio.*?(?:de\s+)?(\d+)\s*dias',
    r'anteced[êe]ncia.*?(?:de\s+)?(\d+)\s*dias',
]

# Participação (tolerante a espaços e quebras)
PARTICIPACAO_PATTERNS = [
    r'Participa.*?o\s+n[oa]\s+Cons.*?rcio.*?Rateio.*?:?\s*([\d.,]+)\s*%',
    r'Rateio\s*[:=]\s*([\d.,]+)\s*%',
]

# Representante (limpeza de CPF/Nome composto)
REP_PATTERNS = [
    r'DADOS\s+DO\s+REPRESENTANTE\s+LEGAL:.*?Nome:\s*([^\n]+)',
    r'Representante\s+Legal:?\s*([^\n]+)',
    # Log de assinatura
    r'Representante\s+CPF\s+([A-Z\s]+?)\s+\d{3}',
]

# Multi-UC
UC_PATTERN = r'(?:Instala[çc][ãa]o|Unidade\s+Consumidora).*?[:\s]*(\d{8,})'

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

MESES = {
    'jan': '01', 'janeiro': '01', 'fev': '02', 'fevereiro': '02',
    'mar': '03', 'março': '03', 'abr': '04', 'abril': '04',
    'mai': '05', 'maio': '05', 'jun': '06', 'junho': '06',
    'jul': '07', 'julho': '07', 'ago': '08', 'agosto': '08',
    'set': '09', 'setembro': '09', 'out': '10', 'outubro': '10',
    'nov': '11', 'novembro': '11', 'dez': '12', 'dezembro': '12'
}

def parse_data_extenso(data_str):
    if not data_str: return None
    try:
        parts = data_str.lower().replace(' de ', ' ').split()
        if len(parts) < 3: return None
        dia, mes_ext, ano = parts[0], parts[1], parts[-1]
        for chave, valor in MESES.items():
            if mes_ext.startswith(chave):
                return f"{dia.zfill(2)}/{valor}/{ano}"
        # Tentar dd/mm/aaaa direto
        if '/' in data_str:
             return data_str.strip()
    except:
        return None
    return None

def clean_text(text):
    return re.sub(r'\s+', ' ', text).strip()

def clean_rep_name(name):
    if not name: return None
    # Remove CPF se vier colado "Nome CPF: 123"
    name = re.sub(r'CPF.*', '', name, flags=re.IGNORECASE)
    # Remove números
    name = re.sub(r'\d+', '', name)
    return clean_text(name)

def find_pdf_path(filename, base_dir):
    # Otimização: buscar direto em 16_paginas
    candidate = base_dir / "16_paginas/CPFL_PAULISTA" / filename
    if candidate.exists(): return candidate
    
    # Fallback: buscar em todas
    results = list(base_dir.rglob(filename))
    if results: return results[0]
    return None

def main():
    print("=" * 70)
    print("REPROCESSAMENTO TOTAL - CPFL PAULISTA")
    print("=" * 70)
    
    logging.getLogger("pdfminer").setLevel(logging.ERROR)
    
    if not CSV_PATH.exists():
        print(f"Erro: CSV não encontrado: {CSV_PATH}")
        return
        
    df = pd.read_csv(CSV_PATH, sep=";", low_memory=False)
    print(f"Registros originais: {len(df)}")
    
    # Lista para novos registros (Multi-UC)
    novos_registros = []
    indices_para_remover = []
    
    print("\nIniciando reprocessamento...")
    
    for idx, row in df.iterrows():
        arquivo = row.get("arquivo_origem")
        if not arquivo: continue
            
        pdf_path = find_pdf_path(arquivo, BASE_DIR)
        if not pdf_path: continue
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Otimização: Ler apenas páginas relevantes (Início e Fim)
                # Evita processar miolo de contratos grandes (50+ págs)
                num_pages = len(pdf.pages)
                pages_to_read = set(range(min(8, num_pages))) # Primeiras 8 (Dados cadastrais)
                pages_to_read.update(range(max(0, num_pages-5), num_pages)) # Últimas 5 (Assinaturas/Anexos)
                
                text_content = ""
                # Converter set para lista ordenada para manter fluxo do texto (aprox)
                for i in sorted(list(pages_to_read)):
                    try:
                        text_content += "\n" + (pdf.pages[i].extract_text() or "")
                    except: pass
            
            # 1. Multi-UC Check
            ucs_encontradas = sorted(list(set(re.findall(UC_PATTERN, text_content))))
            
            # Se encontrou mais de 1 UC e o registro atual tem apenas uma (ou nenhuma)
            if len(ucs_encontradas) > 1:
                # Vamos criar Múltiplos registros
                indices_para_remover.append(idx)
                for uc in ucs_encontradas:
                    novo_reg = row.copy()
                    novo_reg["num_instalacao"] = uc
                    novo_reg["metodo_distribuidora"] = "MULTI_UC_REPROC"
                    
                    # Tentar extrair dados específicos (se possível)
                    # Por simplicidade, replicamos os dados do contrato para todas as UCs
                    # (geralmente data, representante, etc são iguais)
                    novos_registros.append(novo_reg)
                
                # Atualizar a row atual para ser o primeiro registro (para continuar processamento de campos)
                row["num_instalacao"] = ucs_encontradas[0] # Apenas temporário para extração de campos
            
            # 2. Extração de Campos Faltantes (Data, Aviso, Rep, Part)
            
            # Data Adesão
            if pd.isna(row.get("data_adesao")) or row.get("data_adesao") == "":
                for pat in DATA_PATTERNS:
                    match = re.search(pat, text_content, re.IGNORECASE)
                    if match:
                        data_parsed = parse_data_extenso(match.group(1))
                        if data_parsed:
                            row["data_adesao"] = data_parsed
                            break
            
            # Aviso Prévio
            for pat in AVISO_PATTERNS:
                match = re.search(pat, text_content, re.IGNORECASE | re.DOTALL)
                if match:
                    row["aviso_previo"] = match.group(1).strip()
                    break
            
            # Participação
            if pd.isna(row.get("participacao_percentual")) or row.get("participacao_percentual") == "":
                for pat in PARTICIPACAO_PATTERNS:
                    match = re.search(pat, text_content, re.IGNORECASE | re.DOTALL)
                    if match:
                        row["participacao_percentual"] = match.group(1).replace(',', '.').strip()
                        break
            
            # Representante
            if pd.isna(row.get("representante_nome")) or row.get("representante_nome") == "":
                for pat in REP_PATTERNS:
                    match = re.search(pat, text_content, re.IGNORECASE | re.DOTALL)
                    if match:
                        row["representante_nome"] = clean_rep_name(match.group(1))
                        break
            
            # Atualizar registro original (se não for multi-UC removido)
            if idx not in indices_para_remover:
                df.loc[idx] = row
            else:
                # Atualizar os novos registros criados
                for nreg in novos_registros:
                    if nreg["arquivo_origem"] == arquivo:
                        nreg["data_adesao"] = row["data_adesao"]
                        nreg["aviso_previo"] = row["aviso_previo"]
                        nreg["participacao_percentual"] = row["participacao_percentual"]
                        nreg["representante_nome"] = row["representante_nome"]
        
        except Exception as e:
            print(f"Erro {arquivo}: {e}")
            
        if (idx + 1) % 10 == 0:
            print(f"Processados: {idx+1}/{len(df)}")
            
        if (idx + 1) % 50 == 0:
            df.to_csv(CSV_PATH, sep=";", index=False)
            print(f"Checkpoint salvo: {idx+1}")
            
    # Consolidar Multi-UC
    if indices_para_remover:
        print(f"\nDetectados {len(indices_para_remover)} arquivos Multi-UC. Expandindo...")
        df = df.drop(indices_para_remover)
        df_multi = pd.DataFrame(novos_registros)
        df = pd.concat([df, df_multi], ignore_index=True)
    
    print(f"\nTotal Final de Registros: {len(df)}")
    
    # Salvar
    df.to_csv(CSV_PATH, sep=";", index=False)
    print(f"CSV atualizado: {CSV_PATH}")
    
    # Gerar Excel Final
    output_excel = Path("C:/Projetos/Raizen/output/datasets/cpfl/dataset_CPFL_PAULISTA_final_enriched.xlsx")
    df.to_excel(output_excel, index=False)
    print(f"Excel final: {output_excel}")

if __name__ == "__main__":
    main()
