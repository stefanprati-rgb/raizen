#!/usr/bin/env python3
"""
Script de Preenchimento de GAPS (Combo) - CPFL
Alvos:
1. Fidelidade (Prioridade Maxima - Base toda)
2. Aviso Prévio (Melhoria - Quem estiver vazio)
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

PROMPT_COMBO = """
Analise o contrato de energia (CPFL) e extraia:

1. "fidelidade": Prazo de vigência/fidelidade do contrato. (Ex: "12 meses", "24 meses").
   - Procure por: "Prazo de Vigência", "Fidelidade", "Vigência de X meses".
   - Se for indeterminado, retorne "Indeterminado".

2. "aviso_previo": Prazo de aviso prévio para denúncia/rescisão imotivada. (Ex: "30 dias", "60 dias", "90 dias").
   - Procure por: "Denúncia", "Rescisão", "Aviso Prévio".

Retorne JSON: {"fidelidade": "...", "aviso_previo": "..."}
Se não encontrar, retorne null.
"""

csv_lock = Lock()

def setup_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Erro: GEMINI_API_KEY não encontrada.")
        sys.exit(1)
    genai.configure(api_key=api_key)

def process_single_pdf(args):
    idx, row, pdf_path = args
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

        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(
            [sample_file, PROMPT_COMBO],
            generation_config={"response_mime_type": "application/json"}
        )
        
        try: genai.delete_file(sample_file.name)
        except: pass
            
        return (idx, json.loads(response.text), None)
    except Exception as e:
        return (idx, None, str(e))

def find_pdf_path(filename, base_dir):
    # Otimização: Busca direta primeiro
    candidate = base_dir / "16_paginas/CPFL_PAULISTA" / filename
    if candidate.exists(): return candidate
    for subdir in ["05_paginas", "11_paginas", "02_paginas"]:
        candidate = base_dir / subdir / "CPFL_PAULISTA" / filename
        if candidate.exists(): return candidate
    # Fallback lento
    results = list(base_dir.rglob(filename))
    if results: return results[0]
    return None

def main():
    print("="*60)
    print(f"COMBO GAPS: FIDELIDADE + AVISO PRÉVIO ({MAX_WORKERS} threads)")
    print("="*60)
    
    setup_gemini()
    
    df = pd.read_csv(CSV_PATH, sep=";", low_memory=False)
    
    # Adicionar colunas se não existirem
    if "fidelidade" not in df.columns:
        df["fidelidade"] = None
        print("Created column: fidelidade")
    
    # Filtrar quem precisa
    # Regra: Fidelidade vazia OU Aviso Prévio vazio
    # Mas como fidelidade é 0%, vai pegar todo mundo.
    mask = pd.isna(df["fidelidade"]) | pd.isna(df["aviso_previo"])
    df_processar = df[mask]
    
    print(f"Total na base: {len(df)}")
    print(f"Alvos (Gaps): {len(df_processar)}")
    
    if len(df_processar) == 0:
        print("✅ Tudo preenchido!")
        return

    tasks = []
    print("Preparando tarefas...", flush=True)
    # Cache find_pdf_path?? Não, vou deixar rolar.
    for idx, row in df_processar.iterrows():
        tasks.append((idx, row, find_pdf_path(row["arquivo_origem"], BASE_DIR)))
    
    completed = 0
    success_fid = 0
    success_av = 0
    
    print("Iniciando workers...", flush=True)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_single_pdf, t) for t in tasks]
        
        for future in as_completed(futures):
            idx, result, error = future.result()
            completed += 1
            
            if result:
                fid = result.get("fidelidade")
                av = result.get("aviso_previo")
                
                with csv_lock:
                    if fid: 
                        df.at[idx, "fidelidade"] = fid
                        success_fid += 1
                    if av: 
                        df.at[idx, "aviso_previo"] = av
                        success_av += 1
                
                log_fid = f"Fid:{fid}" if fid else ""
                log_av = f"Av:{av}" if av else ""
                print(f"[{completed}/{len(tasks)}] ✅ {log_fid} {log_av}", flush=True)
            else:
                print(f"[{completed}/{len(tasks)}] ❌ {error or 'Vazio'}", flush=True)

            if completed % 50 == 0:
                with csv_lock:
                    df.to_csv(CSV_PATH, sep=";", index=False)
                    print("💾 Checkpoint", flush=True)

    df.to_csv(CSV_PATH, sep=";", index=False)
    print(f"\n🏁 FIM! Fidelidade: {success_fid}, Aviso: {success_av}")

if __name__ == "__main__":
    main()
