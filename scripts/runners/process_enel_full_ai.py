#!/usr/bin/env python3
"""
Script FULL IA - ENEL (Grupo Unificado)
Estratégia: Full IA (Gemini) nas pastas ENEL_CE, ENEL_RJ, ENEL_GO, ENEL_SP.
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
OUTPUT_CSV = Path("C:/Projetos/Raizen/output/datasets_consolidados/ENEL/ENEL_FULL.csv")
OUTPUT_XLSX = Path("C:/Projetos/Raizen/output/datasets/enel/dataset_ENEL_ENTREGA_OFICIAL.xlsx")
MODEL_NAME = "gemini-2.5-flash-lite"
MAX_WORKERS = 50 

# Garantir diretórios
OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_XLSX.parent.mkdir(parents=True, exist_ok=True)

PROMPT_FULL = """
Atue como especialista em contratos da ENEL.
Extraia os dados com precisão.

CAMPOS OBRIGATÓRIOS:
1. num_instalacao: Número da Instalação/UC.
2. num_cliente: Número do Cliente.
3. distribuidora: Identifique qual ENEL é (SP, RJ, CE, GO) baseado no cabeçalho ou endereço.
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
    if not api_key:
        print("❌ Erro: GEMINI_API_KEY não encontrada.")
        sys.exit(1)
    genai.configure(api_key=api_key)

def get_enel_files():
    targets = ["ENEL_CE", "ENEL_RJ", "ENEL_GO", "ENEL_SP"]
    files = []
    for t in targets:
        d = BASE_DIR / t
        if d.exists():
            found = list(d.glob("*.pdf"))
            print(f"  > {t}: {len(found)} arquivos")
            files.extend(found)
    return files

def process_pdf(pdf_path):
    try:
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
            
        data = json.loads(response.text)
        if isinstance(data, list):
             data = data[0] if len(data) > 0 else {}

        return data, None
    except Exception as e:
        return None, str(e)

def main():
    print("="*60)
    print(f"ENEL FULL IA - {MAX_WORKERS} THREADS")
    print("="*60)
    
    setup_gemini()
    
    files = get_enel_files()
    print(f"Total ENEL: {len(files)} arquivos")
    
    if not files:
        print("Nenhum arquivo encontrado.")
        return

    # Checkpoint
    if OUTPUT_CSV.exists():
        df = pd.read_csv(OUTPUT_CSV, sep=";", low_memory=False)
        processed_set = set(df["arquivo_origem"])
        files = [f for f in files if f.name not in processed_set]
        print(f"Restantes após checkpoint: {len(files)}")
    else:
        df = pd.DataFrame(columns=[
            "arquivo_origem", "status_proc", "erro",
            "num_instalacao", "num_cliente", "distribuidora", "razao_social", "cnpj",
            "data_adesao", "fidelidade", "aviso_previo", 
            "representante_nome", "representante_cpf", "participacao_percentual"
        ])

    if files:
        completed = 0
        print(f"Iniciando {len(files)} tarefas...", flush=True)
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_map = {executor.submit(process_pdf, f): f for f in files}
            
            for future in as_completed(future_map):
                pdf_path = future_map[future]
                data, error = future.result()
                completed += 1
                
                new_row = {"arquivo_origem": pdf_path.name}
                
                if data:
                    new_row["status_proc"] = "OK"
                    new_row.update(data)
                    print(f"[{completed}/{len(files)}] ✅ {str(data.get('razao_social',''))[:15]}...", flush=True)
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
    else:
        print("Todos os arquivos já processados. Indo para Excel...")
    
    # Generate Excel
    print("\nGerando Excel Oficial...")
    try:
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
        print(f"🏁 Concluído! Excel em: {OUTPUT_XLSX}")
    except Exception as e:
        print(f"Erro ao gerar Excel: {e}")

if __name__ == "__main__":
    main()
