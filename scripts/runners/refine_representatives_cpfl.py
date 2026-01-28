#!/usr/bin/env python3
"""
Script de Refinamento de Representantes (CPFL) - Gemini Turbo
Foca APENAS em recuperar o nome do representante em contratos onde está vazio.
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
MAX_WORKERS = 50 # Aumentado para 50 a pedido do usuário (Modo Turbo Boost)

PROMPT_REPRESENTANTE = """
ATENÇÃO: Sua única missão é extrair o NOME DO REPRESENTANTE LEGAL que assinou este contrato pela empresa Cliente/Consumidor.

1. Vá direto para as últimas páginas (assinaturas) ou logs de Clicksign/Docusign.
2. Procure por: "Assinado por", "Representante", "Procurador", "Signatário".
3. Se encontrar um nome de PESSOA FÍSICA, extraia apenas o nome (ex: "JOÃO DA SILVA").
4. Se for assinado apenas por certificado digital de PESSOA JURÍDICA (e-CNPJ) sem nome de pessoa fisica, retorne "e-CNPJ".
5. Se não encontrar nada ou for ilegível, retorne null.

Retorne JSON: {"representante_nome": "Valor aqui"}
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
    if not pdf_path or not os.path.exists(pdf_path): return (idx, None, "PDF404")

    try:
        sample_file = genai.upload_file(path=str(pdf_path))
        
        # Esperar processamento
        limit = 60
        while sample_file.state.name == "PROCESSING":
            time.sleep(1)
            limit -= 1
            if limit < 0: return (idx, None, "Timeout")
            sample_file = genai.get_file(sample_file.name)
            
        if sample_file.state.name == "FAILED": return (idx, None, "Failed")

        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(
            [sample_file, PROMPT_REPRESENTANTE],
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
    print(f"REFINAMENTO DE REPRESENTANTES - {MAX_WORKERS} WORKERS")
    print("="*60)
    
    setup_gemini()
    
    df = pd.read_csv(CSV_PATH, sep=";", low_memory=False)
    
    # Filtrar apenas quem não tem representante
    mask = pd.isna(df["representante_nome"])
    df_processar = df[mask]
    
    print(f"Total na base: {len(df)}")
    print(f"Sem representante: {len(df_processar)} (Alvo)")
    
    if len(df_processar) == 0:
        print("✅ Tudo preenchido!")
        return

    tasks = []
    print("Preparando tarefas...", flush=True)
    for idx, row in df_processar.iterrows():
        tasks.append((idx, row, find_pdf_path(row["arquivo_origem"], BASE_DIR)))
    
    completed = 0
    success = 0
    
    print("Iniciando workers...", flush=True)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_single_pdf, t) for t in tasks]
        
        for future in as_completed(futures):
            idx, result, error = future.result()
            completed += 1
            
            if result and result.get("representante_nome"):
                nome = result["representante_nome"]
                if nome and nome.lower() != "null":
                    with csv_lock:
                        df.at[idx, "representante_nome"] = nome
                    success += 1
                    print(f"[{completed}/{len(tasks)}] ✨ RECUPERADO: {nome[:30]}", flush=True)
                else:
                    print(f"[{completed}/{len(tasks)}] 🔹 (Sem nome)", flush=True)
            else:
                print(f"[{completed}/{len(tasks)}] ❌ {error or 'Vazio'}", flush=True)

            if completed % 20 == 0:
                with csv_lock:
                    df.to_csv(CSV_PATH, sep=";", index=False)
                    print("💾 Checkpoint", flush=True)

    df.to_csv(CSV_PATH, sep=";", index=False)
    print(f"\n🏁 FIM! Recuperados: {success}")

if __name__ == "__main__":
    main()
