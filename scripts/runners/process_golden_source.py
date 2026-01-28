#!/usr/bin/env python3
"""
Script GOLDEN SOURCE - BASE OURO
Objetivo: Processar os 6.327 arquivos da pasta oficial do cliente.
Entrada: Pasta "../02 - Base Clientes/TERMO DE ADESÃO"
Saída: Dataset Oficial Limpo.
"""

import os
import sys
import json
import time
import random
import re
import pandas as pd
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Carregar variáveis de ambiente
load_dotenv()

# Configurações
# Caminho OTIMIZADO (Snapshot Local)
GOLDEN_DIR = Path("C:/Projetos/Raizen/data/golden_source")
OUTPUT_CSV = Path("C:/Projetos/Raizen/output/GOLDEN_DATASET_RAW.csv")
OUTPUT_XLSX = Path("C:/Projetos/Raizen/output/DATASET_OFICIAL_GOLDEN.xlsx")

MODEL_NAME = "gemini-2.5-flash-lite"
MAX_WORKERS = 60 # Aumentado para 60 (Quota: 4.000 RPM / Ilimitado RPD) 🚀 

# Garantir diretórios
OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

PROMPT_FULL = """
Atue como especialista em contratos de energia (Mercado Livre/GD).
Dados principais para extrair:

1. num_instalacao: UC / Número da Instalação (Crucial). Se houver lista, pegue a principal ou liste separadas por ponto-e-vírgula.
2. num_cliente: Número do Cliente / Parceiro.
3. distribuidora: Identifique a distribuidora (CPFL, CEMIG, ELEKTRO, LIGHT, ENEL, etc) pelo cabeçalho ou logo.
4. razao_social: Nome da empresa/cliente.
5. cnpj: CNPJ do cliente.
6. data_adesao: Data de assinatura.
7. fidelidade: Prazo de fidelidade (meses).
8. aviso_previo: Prazo de cancelamento (dias).
9. representante_nome: Nome do signatário.
10. representante_cpf: CPF do signatário.
11. participacao_percentual: Percentual de desconto/cota.

Retorne exclusivamente um JSON com as chaves abaixo. Se não encontrar o valor, retorne null. Não invente dados.

{
  "num_instalacao": "string ou null",
  "num_cliente": "string ou null",
  "distribuidora": "string ou null",
  "razao_social": "string ou null",
  "cnpj": "string ou null",
  "data_adesao": "DD/MM/AAAA ou null",
  "fidelidade": "string ou null",
  "aviso_previo": "string ou null",
  "representante_nome": "string ou null",
  "representante_cpf": "string ou null",
  "participacao_percentual": "string ou null"
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
    sample_file = None
    try:
        # Rate Limit aleatório
        time.sleep(random.uniform(0.1, 0.3))
        
        # Tentar upload
        try:
            sample_file = genai.upload_file(path=str(pdf_path))
        except Exception as e_upload:
            # Log de arquivos corrompidos/protegidos para auditoria (Sugestão User)
            try:
                with open("corrupted_files_log.txt", "a", encoding="utf-8") as bad_log:
                     bad_log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {pdf_path.name} | {str(e_upload)}\n")
            except: pass
            raise e_upload # Repassa erro para o fluxo normal (CSV)
        
        start = time.time()
        while sample_file.state.name == "PROCESSING":
            if time.time() - start > 90: 
                # Cleanup será feito no finally
                return None, "Timeout Upload", "ERRO_TIMEOUT"
            time.sleep(1)
            sample_file = genai.get_file(sample_file.name)
            
        if sample_file.state.name == "FAILED": return None, "Falha Upload", "ERRO_UPLOAD_FAILED"

        model = genai.GenerativeModel(MODEL_NAME)
        
        # Retry com Backoff Exponencial
        response = None
        last_error = None
        for attempt in range(1, 4):
            try:
                response = model.generate_content(
                    [sample_file, PROMPT_FULL],
                    generation_config={"response_mime_type": "application/json"}
                )
                break # Sucesso
            except Exception as e:
                last_error = e
                # Se for erro de cota (429), espera um pouco mais
                if "429" in str(e) or "Resource has been exhausted" in str(e):
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"⚠️ Rate Limit (429). Tentativa {attempt}/3. Esperando {wait_time:.1f}s...", flush=True)
                    # Log detalhado
                    try:
                        with open("rate_limit_log.txt", "a", encoding="utf-8") as log:
                            log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {pdf_path.name} | Attempt {attempt}\n")
                    except: pass
                    
                    time.sleep(wait_time)
                else:
                    raise e # Outros erros falham direto
        
        if not response:
             raise last_error
        
        # Limpeza de Markdown (Bug do Gemini) - Regex mais robusto
        text_content = re.sub(r'```(?:json)?', '', response.text).strip()
        
        if not text_content or text_content == "null":
            return None, "Resposta vazia da IA", "ERRO_IA_VAZIA"
            
        try:
            data = json.loads(text_content, strict=False) # strict=False ajuda com controle chars
        except json.JSONDecodeError as je:
             return None, f"JSON inválido: {text_content[:100]}", "ERRO_JSON"
        # Tratamento de lista (IA às vezes retorna [{}])
        if isinstance(data, list):
             data = data[0] if len(data) > 0 else {}
             
        # Validação Pós-IA: Chaves Padrão (Sugestão Colega)
        expected_keys = [
            "num_instalacao", "num_cliente", "distribuidora", "razao_social", 
            "cnpj", "data_adesao", "fidelidade", "aviso_previo", 
            "representante_nome", "representante_cpf", "participacao_percentual"
        ]
        for k in expected_keys:
            data.setdefault(k, None)

        # Score de Confiança (Campos não nulos) - Apenas chaves de negócio
        filled = sum(1 for k, v in data.items() if k in expected_keys and v)
        data["score_confianca"] = f"{filled}/{len(expected_keys)}"
        
        # Qualidade mínima
        status_final = "OK"
        if filled < 3:
            status_final = "BAIXA_QUALIDADE"

        # Sanitização
        if data.get('cnpj'):
            data['cnpj'] = ''.join(filter(str.isdigit, str(data['cnpj'])))
        if data.get('representante_cpf'):
            data['representante_cpf'] = ''.join(filter(str.isdigit, str(data['representante_cpf'])))
             
        return data, None, status_final
    except Exception as e:
        return None, str(e), "ERRO_TECNICO"
    finally:
        # Garantir limpeza na nuvem (Feedback: Evitar vazamento)
        if sample_file:
            try: genai.delete_file(sample_file.name)
            except: pass

def main():
    print("="*60)
    print(f"PROCESSAMENTO BASE OURO (GOLDEN SOURCE) - {MAX_WORKERS} THREADS")
    print(f"Pasta: {GOLDEN_DIR}")
    print("="*60)
    
    setup_gemini()
    
    if not GOLDEN_DIR.exists():
        print(f"❌ Pasta não encontrada: {GOLDEN_DIR}")
        return

    # Listar recursivamente
    print("Mapeando arquivos...")
    files = []
    for root, dirs, f_names in os.walk(GOLDEN_DIR):
        for f in f_names:
            if f.lower().endswith(".pdf"):
                files.append(Path(root) / f)
                
    print(f"Total Base Ouro: {len(files)} arquivos.")
    
    if not files:
        print("Nenhum arquivo encontrado.")
        return

    # Checkpoint
    if OUTPUT_CSV.exists():
        try:
            # Ler tudo como string para não perder zeros à esquerda
            df = pd.read_csv(OUTPUT_CSV, sep=";", dtype=str)
            # Verificar se já processamos este caminho exato
            if "caminho_completo" in df.columns and not df.empty:
                processed_set = set(df["caminho_completo"].dropna())
                files = [f for f in files if str(f) not in processed_set]
                print(f"Restantes após checkpoint (Path Check): {len(files)}")
            # Fallback para nome do arquivo se caminho não existir (compatibilidade)
            elif "arquivo_origem" in df.columns and not df.empty:
                processed_set = set(df["arquivo_origem"].dropna())
                files = [f for f in files if f.name not in processed_set]
                print(f"Restantes após checkpoint: {len(files)}")
        except:
            pass
    else:
        df = pd.DataFrame(columns=[
            "arquivo_origem", "caminho_completo", "status_proc", "tipo_erro", "erro_detalhe", "score_confianca",
            "num_instalacao", "num_cliente", "distribuidora", "razao_social", "cnpj",
            "data_adesao", "fidelidade", "aviso_previo", 
            "representante_nome", "representante_cpf", "participacao_percentual"
        ])

    write_header = not OUTPUT_CSV.exists()
    
    if files:
        completed = 0
        batch_rows = [] # Buffer para performance (Feedback: Evitar concat loop)
        print(f"Iniciando tarefas...", flush=True)
        
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_map = {executor.submit(process_pdf, f): f for f in files}
            
            for future in as_completed(future_map):
                pdf_path = future_map[future]
                data, error_msg, status_code = future.result()
                completed += 1
                
                new_row = {
                    "arquivo_origem": pdf_path.name,
                    "caminho_completo": str(pdf_path)
                }
                
                if data:
                    new_row["status_proc"] = status_code
                    new_row["tipo_erro"] = None # Schema Estável
                    new_row["erro_detalhe"] = None
                    new_row.update(data)
                    dist = str(data.get('distribuidora', 'N/A'))
                    score = str(data.get('score_confianca', 'N/A'))
                    print(f"[{completed}/{len(files)}] ✅ {dist} | Score: {score}", flush=True)
                else:
                    new_row["status_proc"] = "ERRO"
                    new_row["tipo_erro"] = status_code
                    new_row["erro_detalhe"] = str(error_msg)
                    print(f"[{completed}/{len(files)}] ❌ {status_code}: {error_msg} ({pdf_path.name})", flush=True)

                # ETA a cada 50 arquivos
                if completed % 50 == 0:
                    elapsed = time.time() - start_time
                    rate = completed / elapsed
                    remaining = len(files) - completed
                    eta_seconds = remaining / rate if rate > 0 else 0
                    print(f"⏱️ Taxa: {rate:.1f} docs/s | ETA: {eta_seconds/60:.1f} min", flush=True)
                
                # Acumular no buffer
                batch_rows.append(new_row)
                
                # Checkpoint Otimizado (Append Mode - O(1))
                if len(batch_rows) >= 20:
                    with csv_lock:
                        df_batch = pd.DataFrame(batch_rows)
                        df_batch.to_csv(OUTPUT_CSV, sep=";", index=False, mode='a', header=write_header)
                        # Da próxima vez, não escreve header
                        write_header = False
                        
                        print("💾 Checkpoint (Batch Appended)", flush=True)
                        batch_rows = [] # Limpar buffer

        # Processar buffer restante
        if batch_rows:
            pd.DataFrame(batch_rows).to_csv(OUTPUT_CSV, sep=";", index=False, mode='a', header=write_header)
        
        # Reload para Relatório e Excel (Pois usamos Append)
        print("\nRecarregando CSV para Relatório Final...", flush=True)
        try:
            df_final = pd.read_csv(OUTPUT_CSV, sep=";", dtype=str)
        except:
            df_final = pd.DataFrame()
        
        # Resumo de Erros Seguro
        if not df_final.empty:
            erros = df_final[df_final["status_proc"] == "ERRO"]
            total = len(df_final)
            print(f"\n📊 Resumo: {total} processados | {len(erros)} erros ({len(erros)/total*100:.1f}%)")
        else:
            print("\n📊 Nenhum arquivo processado ou erro de leitura.")
    else:
        print("Todos os arquivos já processados.")
    
    # Generate Excel Final
    print("\nGerando Excel Oficial Ouro...")
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
        
        # Usar o DF recarregado
        if 'df_final' in locals() and not df_final.empty:
            df_clean = df_final.copy()
        else:
            # Fallback se não entrou no if files
             if OUTPUT_CSV.exists():
                 df_clean = pd.read_csv(OUTPUT_CSV, sep=";", dtype=str)
             else:
                 return

        df_clean.rename(columns=col_map, inplace=True)
        # Filtrar colunas finais (Incluindo Diagnóstico)
        cols_final = list(col_map.values()) + ["arquivo_origem", "status_proc", "score_confianca", "tipo_erro", "erro_detalhe"]
        # Manter apenas as que existem
        cols_final = [c for c in cols_final if c in df_clean.columns]
        
        # Forçar string nas colunas numéricas para o Excel não comer o zero
        for col_str in ["CNPJ", "CPF Representante", "Número do Cliente"]:
            if col_str in df_clean.columns:
                df_clean[col_str] = df_clean[col_str].astype(str).str.replace(r'\.0$', '', regex=True)

        df_clean[cols_final].to_excel(OUTPUT_XLSX, index=False)
        print(f"👑 DATASET OURO GERADO: {OUTPUT_XLSX}")
    except Exception as e:
        print(f"Erro Excel: {e}")

if __name__ == "__main__":
    main()
