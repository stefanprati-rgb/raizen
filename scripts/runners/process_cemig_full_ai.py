#!/usr/bin/env python3
"""
Script FULL IA - CEMIG
Estratégia: Zero Regex. Processamento direto dos 11 campos via Gemini Flash Lite.
Threads: 50
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
OUTPUT_CSV = Path("C:/Projetos/Raizen/output/datasets_consolidados/CEMIG/CEMIG_FULL.csv")
OUTPUT_XLSX = Path("C:/Projetos/Raizen/output/datasets/cemig/dataset_CEMIG_ENTREGA_OFICIAL.xlsx")
MODEL_NAME = "gemini-2.5-flash-lite"
MAX_WORKERS = 50

# Garantir diretórios
OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_XLSX.parent.mkdir(parents=True, exist_ok=True)

PROMPT_FULL = """
Atue como especialista em contratos de energia da CEMIG.
Extraia os seguintes dados do documento PDF com máxima precisão.

CAMPOS OBRIGATÓRIOS:
1. num_instalacao: Número da Instalação (ou UC). Se houver lista, extraia a principal.
2. num_cliente: Número do Cliente ou Parceiro de Negócio.
3. distribuidora: "CEMIG".
4. razao_social: Nome da empresa cliente.
5. cnpj: CNPJ da empresa cliente.
6. data_adesao: Data de assinatura do contrato (DD/MM/AAAA). Procure em logs de assinatura e rodapés.
7. fidelidade: Prazo de fidelidade/vigência em meses (ex: "12 meses"). Se não explícito, procure datas de início e fim.
8. aviso_previo: Prazo de aviso prévio (dias) para rescisão (ex: "30 dias").
9. representante_nome: Nome de quem assinou. Priorize nomes de PESSOA FÍSICA nos logs de assinatura. Se apenas e-CNPJ, retorne "e-CNPJ".
10. representante_cpf: CPF do signatário (se houver).
11. participacao_percentual: Percentual de participação, rateio ou cota (ex: "10%", "50%").

Retorne JSON puro:
{
    "num_instalacao": "...",
    "num_cliente": "...",
    "distribuidora": "CEMIG",
    "razao_social": "...",
    "cnpj": "...",
    "data_adesao": "...",
    "fidelidade": "...",
    "aviso_previo": "...",
    "representante_nome": "...",
    "representante_cpf": "...",
    "participacao_percentual": "..."
}
"""

csv_lock = Lock()

def setup_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Erro: GEMINI_API_KEY não encontrada.")
        sys.exit(1)
    genai.configure(api_key=api_key)

def process_pdf(pdf_path):
    try:
        sample_file = genai.upload_file(path=str(pdf_path))
        
        # Timeout loop
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

def find_cemig_files():
    print("Mapeando arquivos CEMIG no disco...")
    files = []
    # Varre tudo mas filtra por nome de pasta
    # Otimização: Olhar pastas conhecidas
    targets = ["CEMIG", "CEMIG_D", "CEMIG D", "MG_-_CEMIG", "MG-CEMIG"]
    
    print(f"Varrendo recursivamente em {BASE_DIR} por pastas {targets}...")
    
    for root, dirs, f_names in os.walk(BASE_DIR):
        path = Path(root)
        # Se o nome da pasta (ou pai) tem CEMIG
        if any(t in str(path).upper() for t in targets):
            for f in f_names:
                if f.lower().endswith(".pdf"):
                    files.append(path / f)
    
    # Remove duplicatas
    files = list(set(files))
    print(f"Encontrados: {len(files)} arquivos (Varredura Profunda).")
    return files

def main():
    print("="*60)
    print(f"CEMIG FULL IA - {MAX_WORKERS} THREADS")
    print("="*60)
    
    setup_gemini()
    
    files = find_cemig_files()
    if not files:
        print("Nenhum arquivo encontrado.")
        return

    # Preparar DataFrame ou carregar checkpont
    if OUTPUT_CSV.exists():
        df = pd.read_csv(OUTPUT_CSV, sep=";", low_memory=False)
        print(f"Retomando checkpoint: {len(df)} processados.")
        processed_files = set(df["arquivo_origem"])
        files_to_process = [f for f in files if f.name not in processed_files]
    else:
        df = pd.DataFrame(columns=[
            "arquivo_origem", "status_proc", "erro",
            "num_instalacao", "num_cliente", "distribuidora", "razao_social", "cnpj",
            "data_adesao", "fidelidade", "aviso_previo", 
            "representante_nome", "representante_cpf", "participacao_percentual"
        ])
        files_to_process = files

    print(f"Pendentes: {len(files_to_process)}")
    if not files_to_process:
        print("Tudo pronto!")
        return

    completed = 0
    success_count = 0
    
    print("Disparando threads...", flush=True)
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Map futures to file path
        future_map = {executor.submit(process_pdf, f): f for f in files_to_process}
        
        for future in as_completed(future_map):
            pdf_path = future_map[future]
            data, error = future.result()
            completed += 1
            
            new_row = {"arquivo_origem": pdf_path.name}
            
            if data:
                new_row["status_proc"] = "OK"
                new_row.update(data)
                success_count += 1
                log_msg = f"✅ {data.get('razao_social', '')[:20]}"
            else:
                new_row["status_proc"] = "ERRO"
                new_row["erro"] = str(error)
                log_msg = f"❌ {error}"
            
            # Append to DF (thread safe logic via lock not strictly needed for append if we concat, but let's use list buffer or lock)
            with csv_lock:
                # Append row
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                
                # Checkpoint
                if completed % 20 == 0:
                    df.to_csv(OUTPUT_CSV, sep=";", index=False)
                    print(f"[{completed}/{len(files_to_process)}] 💾 Checkpoint", flush=True)
            
            print(f"[{completed}/{len(files_to_process)}] {log_msg}", flush=True)

    # Final Save
    df.to_csv(OUTPUT_CSV, sep=";", index=False)
    
    # Generate Clean Excel
    print("\nGerando Excel Oficial...")
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

if __name__ == "__main__":
    main()
