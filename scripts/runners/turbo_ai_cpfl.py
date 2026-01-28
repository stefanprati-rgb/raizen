#!/usr/bin/env python3
"""
Script TURBO de Finalização com IA (Gemini) - Multithreaded.
Processa Múltiplos PDFs simultaneamente para máxima velocidade.

Requisitos:
- Arquivo .env com GEMINI_API_KEY configurada.
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
CSV_PATH = Path("C:/Projetos/Raizen/output/datasets_consolidados/CPFL_PAULISTA/CPFL_PAULISTA.csv")
MODEL_NAME = "gemini-2.5-flash-lite"
MAX_WORKERS = 10  # Número de threads simultâneas

SCHEMA_PROMPT = """
Atue como um especialista em contratos de energia (CPFL). Analise o documento PDF.
Extraia os seguintes campos. Retorne JSON.

Campos:
1. "data_adesao": (string DD/MM/AAAA) Data de assinatura. Procure LOGS DE ASSINATURA (fim do arquivo). Se houver várias datas, pegue a mais recente de assinatura do cliente.
2. "participacao_percentual": (number) Percentual de participação/rateio (ex: 12.5).
3. "representante_nome": (string) Nome do representante legal.
4. "aviso_previo": (number) Dias de aviso prévio.
5. "num_instalacao": (string) UC principal.

Regras:
- Priorize logs de assinatura digital (Clicksign, Qualisign).
- Normalizar datas para DD/MM/AAAA.
"""

# Lock para escrita no CSV (thread safety)
csv_lock = Lock()

def setup_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Erro: GEMINI_API_KEY não encontrada.")
        sys.exit(1)
    genai.configure(api_key=api_key)

def process_single_pdf(args):
    """Processa um único PDF (função worker)"""
    idx, row, pdf_path = args
    
    if not pdf_path or not os.path.exists(pdf_path):
        return (idx, None, "PDF não encontrado")

    try:
        # Upload
        sample_file = genai.upload_file(path=str(pdf_path))
        
        # Wait for processing
        timeout = 60
        start_time = time.time()
        while sample_file.state.name == "PROCESSING":
            if time.time() - start_time > timeout:
                return (idx, None, "Timeout no processamento")
            time.sleep(1)
            sample_file = genai.get_file(sample_file.name)
            
        if sample_file.state.name == "FAILED":
            return (idx, None, "Falha no processamento pelo Gemini")

        # Generate
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(
            [sample_file, SCHEMA_PROMPT],
            generation_config={"response_mime_type": "application/json"}
        )
        
        # Cleanup
        try:
            genai.delete_file(sample_file.name)
        except: pass
            
        return (idx, json.loads(response.text), None)

    except Exception as e:
        return (idx, None, str(e))

def find_pdf_path(filename, base_dir):
    # Lógica de busca rápida
    candidate = base_dir / "16_paginas/CPFL_PAULISTA" / filename
    if candidate.exists(): return candidate
    
    for subdir in ["05_paginas", "11_paginas", "02_paginas"]:
        candidate = base_dir / subdir / "CPFL_PAULISTA" / filename
        if candidate.exists(): return candidate

    results = list(base_dir.rglob(filename))
    if results: return results[0]
    return None

def main():
    print("=" * 70)
    print(f"TURBO IA (GEMINI) - {MAX_WORKERS} WORKERS SIMULTÂNEOS")
    print("=" * 70)
    
    setup_gemini()
    
    df = pd.read_csv(CSV_PATH, sep=";", low_memory=False)
    
    # Filtrar incompletos
    mask_incompleto = (
        pd.isna(df["data_adesao"]) | 
        pd.isna(df["participacao_percentual"]) |
        pd.isna(df["representante_nome"])
    )
    df_processar = df[mask_incompleto]
    
    print(f"Total: {len(df)}")
    print(f"Pendentes: {len(df_processar)}")
    
    if len(df_processar) == 0:
        print("✅ Tudo pronto!")
        return

    print(f"Iniciando {MAX_WORKERS} threads...", flush=True)
    
    # Preparar tarefas
    tasks = []
    for idx, row in df_processar.iterrows():
        arquivo = row.get("arquivo_origem")
        pdf_path = find_pdf_path(arquivo, BASE_DIR)
        tasks.append((idx, row, pdf_path))
    
    completed = 0
    success = 0
    errors = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        futures = [executor.submit(process_single_pdf, task) for task in tasks]
        
        for future in as_completed(futures):
            idx, result, error = future.result()
            completed += 1
            
            if result:
                success += 1
                # Atualizar DataFrame (Thread Safe com Lock)
                with csv_lock:
                    if result.get("data_adesao"):
                        df.at[idx, "data_adesao"] = result["data_adesao"]
                    if result.get("participacao_percentual"):
                        val = result["participacao_percentual"]
                        if isinstance(val, (int, float)) or (isinstance(val, str) and val.replace('.','').isdigit()):
                             df.at[idx, "participacao_percentual"] = val
                    if result.get("representante_nome"):
                        df.at[idx, "representante_nome"] = result["representante_nome"]
                    if result.get("aviso_previo"):
                        df.at[idx, "aviso_previo"] = result["aviso_previo"]
                        
                print(f"[{completed}/{len(tasks)}] ✅ {df.at[idx, 'arquivo_origem'][:30]}... Data: {result.get('data_adesao')}", flush=True)
            else:
                errors += 1
                print(f"[{completed}/{len(tasks)}] ❌ {df.at[idx, 'arquivo_origem'][:30]}... Erro: {error}", flush=True)
            
            # Save checkpoint every 20 completed
            if completed % 20 == 0:
                with csv_lock:
                    df.to_csv(CSV_PATH, sep=";", index=False)
                    print(f"💾 Checkpoint salvo ({completed}/{len(tasks)})", flush=True)

    # Final save
    df.to_csv(CSV_PATH, sep=";", index=False)
    
    # Excel
    excel_path = Path("C:/Projetos/Raizen/output/datasets/cpfl/dataset_CPFL_PAULISTA_final_TURBO.xlsx")
    df.to_excel(excel_path, index=False)
    
    print("=" * 70)
    print(f"🏁 Concluído! Sucesso: {success}, Erros: {errors}")
    print(f"Excel: {excel_path}")

if __name__ == "__main__":
    main()
