#!/usr/bin/env python3
"""
Script de Varredura Final (Catando Milho) - CPFL
Objetivo: Preencher QUALQUER campo critico que ainda esteja vazio.
Prompt dinâmico por arquivo.
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

# Configurações Turbo
BASE_DIR = Path("C:/Projetos/Raizen/data/processed")
CSV_PATH = Path("C:/Projetos/Raizen/output/datasets_consolidados/CPFL_PAULISTA/CPFL_PAULISTA.csv")
MODEL_NAME = "gemini-2.5-flash-lite"
MAX_WORKERS = 50 

# Campos alvo para verificação
TARGET_FIELDS = [
    "data_adesao",
    "participacao_percentual",
    "num_instalacao",
    "num_cliente",
    "aviso_previo",
    "fidelidade",
    "razao_social",
    "cnpj"
]

csv_lock = Lock()

def setup_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Erro: GEMINI_API_KEY não encontrada.")
        sys.exit(1)
    genai.configure(api_key=api_key)

def process_single_pdf(args):
    idx, row, pdf_path, missing_fields = args
    if not pdf_path or not os.path.exists(pdf_path): return (idx, None, "PDF não encontrado")

    try:
        sample_file = genai.upload_file(path=str(pdf_path))
        
        # Timeout loop
        start = time.time()
        while sample_file.state.name == "PROCESSING":
            if time.time() - start > 60: return (idx, None, "Timeout")
            time.sleep(1)
            sample_file = genai.get_file(sample_file.name)
            
        if sample_file.state.name == "FAILED": return (idx, None, "Failed")

        # Prompt Dinâmico
        prompt = f"""
        Analise este contrato de energia (CPFL) com extrema atenção.
        Precisamos encontrar os seguintes valores que estão faltando: {', '.join(missing_fields)}.
        
        Regras de Extração:
        - data_adesao: Procure em logs de assinatura, cabeçalho ou rodapé. Formato DD/MM/AAAA.
        - num_cliente: Código do cliente na distribuidora (Geralmente no cabeçalho da conta ou contrato).
        - num_instalacao: Código da Instalação/UC.
        - participacao_percentual: Procure por "Rateio", "Cota", "Participação", "Alocação".
        
        Retorne um JSON APENAS com os campos encontrados:
        {{
            "campo_encontrado": "valor"
        }}
        Se não encontrar, não inclua no JSON ou use null.
        """

        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(
            [sample_file, prompt],
            generation_config={"response_mime_type": "application/json"}
        )
        
        try: genai.delete_file(sample_file.name)
        except: pass
            
        return (idx, json.loads(response.text), None)
    except Exception as e:
        return (idx, None, str(e))

def find_pdf_path(filename, base_dir):
    candidate = base_dir / "16_paginas/CPFL_PAULISTA" / filename
    if candidate.exists(): return candidate
    for subdir in ["05_paginas", "11_paginas", "02_paginas"]:
        candidate = base_dir / subdir / "CPFL_PAULISTA" / filename
        if candidate.exists(): return candidate
    results = list(base_dir.rglob(filename))
    if results: return results[0]
    return None

def main():
    print("="*60)
    print(f"VARREDURA FINAL (CATANDO MILHO) - {MAX_WORKERS} threads")
    print("="*60)
    
    setup_gemini()
    
    df = pd.read_csv(CSV_PATH, sep=";", low_memory=False)
    
    tasks = []
    print("Identificando gaps...", flush=True)
    
    for idx, row in df.iterrows():
        missing = []
        for field in TARGET_FIELDS:
            if field not in df.columns or pd.isna(row[field]) or str(row[field]).strip() == "":
                missing.append(field)
        
        if missing:
            pdf_path = find_pdf_path(row["arquivo_origem"], BASE_DIR)
            tasks.append((idx, row, pdf_path, missing))
            
    print(f"Total na base: {len(df)}")
    print(f"Contratos com gaps: {len(tasks)}")
    
    if len(tasks) == 0:
        print("✅ Tudo 100% preenchido! Nada para catar.")
        return

    completed = 0
    recuperados = 0
    
    print("Iniciando workers...", flush=True)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_single_pdf, t) for t in tasks]
        
        for future in as_completed(futures):
            idx, result, error = future.result()
            completed += 1
            
            if result:
                changes = []
                with csv_lock:
                    for k, v in result.items():
                        if k in TARGET_FIELDS and v and str(v).lower() != "null":
                             df.at[idx, k] = v
                             changes.append(f"{k}={v}")
                
                if changes:
                    recuperados += 1
                    print(f"[{completed}/{len(tasks)}] 🌽 RECUPERADO: {', '.join(changes)}", flush=True)
                else:
                    print(f"[{completed}/{len(tasks)}] 🔹 (Não encontrado)", flush=True)
            else:
                print(f"[{completed}/{len(tasks)}] ❌ {error or 'Vazio'}", flush=True)

            if completed % 50 == 0:
                with csv_lock:
                    df.to_csv(CSV_PATH, sep=";", index=False)
                    print("💾 Checkpoint", flush=True)

    df.to_csv(CSV_PATH, sep=";", index=False)
    print(f"\n🏁 FIM! Registros melhorados: {recuperados}")

if __name__ == "__main__":
    main()
