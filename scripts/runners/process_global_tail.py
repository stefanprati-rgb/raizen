#!/usr/bin/env python3
"""
Script ARRASTÃO GLOBAL (Long Tail)
Objetivo: Processar todos os arquivos que NÃO são CPFL Paulista nem CEMIG.
Estratégia: Full IA (Gemini) em tudo que sobrar.
"""

import os
import sys
import json
import time
import pandas as pd
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Carregar variáveis de ambiente
load_dotenv()

# Configurações
BASE_DIR = Path("C:/Projetos/Raizen/data/processed")
OUTPUT_CSV = Path("C:/Projetos/Raizen/output/datasets_consolidados/GERAL/DATASET_GLOBAL_OUTRAS.csv")
OUTPUT_XLSX = Path("C:/Projetos/Raizen/output/datasets/geral/dataset_GERAL_OUTRAS_ENTREGA.xlsx")

# Arquivos já processados para ignorar
IGNORE_CSVS = [
    Path("C:/Projetos/Raizen/output/datasets_consolidados/CPFL_PAULISTA/CPFL_PAULISTA.csv"),
    Path("C:/Projetos/Raizen/output/datasets_consolidados/CEMIG/CEMIG_FULL.csv"),
    Path("C:/Projetos/Raizen/output/datasets_consolidados/ELEKTRO/ELEKTRO_FULL.csv"),
    Path("C:/Projetos/Raizen/output/datasets_consolidados/LIGHT/LIGHT_FULL.csv"),
    Path("C:/Projetos/Raizen/output/datasets_consolidados/ENEL/ENEL_FULL.csv")
]

MODEL_NAME = "gemini-2.5-flash-lite"
MAX_WORKERS = 20 # Ajustado para o saldo final (lote pequeno)

# Garantir diretórios
OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_XLSX.parent.mkdir(parents=True, exist_ok=True)

PROMPT_FULL = """
Extraia os dados deste contrato de energia (Identifique a distribuidora automaticamente).

CAMPOS OBRIGATÓRIOS:
1. num_instalacao: Número da Instalação/UC.
2. num_cliente: Número do Cliente.
3. distribuidora: Nome da Distribuidora (Ex: LIGHT, ELEKTRO, ENEL SP, NEOENERGIA). Extraia do cabeçalho.
4. razao_social: Nome da empresa cliente.
5. cnpj: CNPJ da empresa cliente.
6. data_adesao: Data de assinatura (DD/MM/AAAA).
7. fidelidade: Prazo de fidelidade (ex: "12 meses").
8. aviso_previo: Prazo de aviso prévio (dias).
9. representante_nome: Nome de quem assinou. Priorize nomes de PESSOA FÍSICA. Se e-CNPJ, retorne "e-CNPJ".
10. representante_cpf: CPF do signatário.
11. participacao_percentual: Percentual de cota/rateio.

Retorne JSON puro.
"""

csv_lock = Lock()

def setup_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

def process_pdf(pdf_path):
    try:
        # Debug visual para saber que a thread esta viva
        print(f"⬆️ Up: {pdf_path.name[:15]}...", flush=True) 
        
        sample_file = genai.upload_file(path=str(pdf_path))
        
        start = time.time()
        while sample_file.state.name == "PROCESSING":
            if time.time() - start > 60: return None, "Timeout Upload"
            time.sleep(1)
            sample_file = genai.get_file(sample_file.name)
            
        if sample_file.state.name == "FAILED": return None, "Falha Upload"

        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(
            [sample_file, PROMPT_FULL],
            generation_config={"response_mime_type": "application/json"}
        )
        
        try: genai.delete_file(sample_file.name)
        except: pass
            
        return json.loads(response.text), None
    except Exception as e:
        return None, str(e)

def get_processed_files():
    processed = set()
    for csv_path in IGNORE_CSVS:
        if csv_path.exists():
            try:
                df = pd.read_csv(csv_path, sep=";", low_memory=False)
                # Assumindo coluna 'arquivo_origem'
                if "arquivo_origem" in df.columns:
                    processed.update(df["arquivo_origem"].astype(str))
            except: pass
    return processed

def audit_and_list_files():
    print("Mapeando arquivos ignorando processados...")
    processed_set = get_processed_files()
    print(f"Arquivos já processados (CPFL/CEMIG): {len(processed_set)}")
    
    files_to_do = []
    
    for root, dirs, f_names in os.walk(BASE_DIR):
        if "output" in root or ".git" in root: continue
        
        for f in f_names:
            if f.lower().endswith(".pdf"):
                if f not in processed_set:
                    files_to_do.append(Path(root) / f)
                    
    print(f"Arquivos restantes para processar: {len(files_to_do)}")
    return files_to_do

def main():
    print("="*60)
    print(f"ARRASTÃO GLOBAL (RESTO DO MUNDO) - {MAX_WORKERS} THREADS")
    print("="*60)
    
    setup_gemini()
    
    files = audit_and_list_files()
    
    if not files:
        print("Nada pendente!")
        return

    # Checkpoint logic
    if OUTPUT_CSV.exists():
        df = pd.read_csv(OUTPUT_CSV, sep=";", low_memory=False)
        processed_in_this_run = set(df["arquivo_origem"])
        files = [f for f in files if f.name not in processed_in_this_run]
        print(f"Retomando checkpoint local: {len(files)} restantes reais.")
    else:
        df = pd.DataFrame(columns=[
            "arquivo_origem", "caminho_completo", "status_proc", "erro",
            "num_instalacao", "num_cliente", "distribuidora", "razao_social", "cnpj",
            "data_adesao", "fidelidade", "aviso_previo", 
            "representante_nome", "representante_cpf", "participacao_percentual"
        ])

    print(f"Iniciando {len(files)} tarefas...")
    
    completed = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {executor.submit(process_pdf, f): f for f in files}
        
        for future in as_completed(future_map):
            pdf_path = future_map[future]
            data, error = future.result()
            completed += 1
            
            new_row = {
                "arquivo_origem": pdf_path.name,
                "caminho_completo": str(pdf_path)
            }
            
            if data:
                # Fix: Robustez contra retorno de lista [{}].
                if isinstance(data, list):
                     data = data[0] if len(data) > 0 else {}

                new_row["status_proc"] = "OK"
                new_row.update(data)
                # Garantir string segura para o print
                dist_print = str(data.get('distribuidora', 'N/A'))
                print(f"[{completed}/{len(files)}] ✅ {dist_print} | {pdf_path.name[:20]}...", flush=True)
            else:
                new_row["status_proc"] = "ERRO"
                new_row["erro"] = str(error)
                print(f"[{completed}/{len(files)}] ❌ {error}", flush=True)
            
            with csv_lock:
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                if completed % 20 == 0:
                    df.to_csv(OUTPUT_CSV, sep=";", index=False)
                    print("💾 Checkpoint", flush=True)

    df.to_csv(OUTPUT_CSV, sep=";", index=False)
    
    # Clean Excel
    print("\nGerando Excel...")
    col_map = {
        "num_instalacao": "UC / Instalação",
        "num_cliente": "Número do Cliente",
        "distribuidora": "Distribuidora",
        "razao_social": "Razão Social",
        "cnpj": "CNPJ",
        "data_adesao": "Data de Adesão",
        "fidelidade": "Fidelidade",
        "aviso_previo": "Aviso Prévio (Dias)",
        "representante_nome": "Representante Legal",
        "representante_cpf": "CPF Representante",
        "participacao_percentual": "Participação Contratada"
    }
    
    df_clean = df[list(col_map.keys())].copy()
    df_clean.rename(columns=col_map, inplace=True)
    df_clean.to_excel(OUTPUT_XLSX, index=False)
    print(f"🏁 FIM! Dataset Global: {OUTPUT_XLSX}")

if __name__ == "__main__":
    main()
