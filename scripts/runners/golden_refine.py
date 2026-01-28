#!/usr/bin/env python3
"""
Script DE REPESCAGEM (Refinement)
Objetivo: Ler o dataset bruto gerado pelo Flash Lite, identificar falhas/baixa qualidade
e reprocessar APENAS esses arquivos com o modelo Flash Standard (mais forte).
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
INPUT_CSV = Path("C:/Projetos/Raizen/output/GOLDEN_DATASET_RAW.csv")
OUTPUT_CSV = Path("C:/Projetos/Raizen/output/GOLDEN_DATASET_REFINED.csv")

# MUDANÇA: Modelo mais forte para a repescagem
MODEL_NAME = "gemini-2.5-flash" 
MAX_WORKERS = 30 # Aumentado para 30 (Quota: 1.000 RPM) 

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
        time.sleep(random.uniform(0.1, 0.5)) # Um pouco mais lento pro modelo heavy
        
        # Tentar upload
        try:
            sample_file = genai.upload_file(path=str(pdf_path))
        except Exception as e_upload:
            return None, f"Falha Upload: {str(e_upload)}", "ERRO_UPLOAD"
        
        start = time.time()
        while sample_file.state.name == "PROCESSING":
            if time.time() - start > 120: # Mais complacente
                return None, "Timeout Upload", "ERRO_TIMEOUT"
            time.sleep(1)
            sample_file = genai.get_file(sample_file.name)
            
        if sample_file.state.name == "FAILED": return None, "Falha Upload", "ERRO_UPLOAD_FAILED"

        model = genai.GenerativeModel(MODEL_NAME)
        
        # Retry logic
        response = None
        last_error = None
        for attempt in range(1, 4):
            try:
                response = model.generate_content(
                    [sample_file, PROMPT_FULL],
                    generation_config={"response_mime_type": "application/json"}
                )
                break
            except Exception as e:
                last_error = e
                if "429" in str(e) or "Resource has been exhausted" in str(e):
                    wait_time = (2 ** attempt) + random.uniform(1, 2)
                    time.sleep(wait_time)
                else:
                    raise e
        
        if not response:
             raise last_error
        
        # Limpeza de Markdown
        text_content = re.sub(r'```(?:json)?', '', response.text).strip()
        if not text_content or text_content == "null":
            return None, "Resposta vazia da IA", "ERRO_IA_VAZIA"
            
        try:
            data = json.loads(text_content, strict=False)
        except json.JSONDecodeError:
             return None, f"JSON inválido: {text_content[:100]}", "ERRO_JSON"

        # Tratamento de lista
        if isinstance(data, list):
             data = data[0] if len(data) > 0 else {}
             
        # Validação chaves
        expected_keys = [
            "num_instalacao", "num_cliente", "distribuidora", "razao_social", 
            "cnpj", "data_adesao", "fidelidade", "aviso_previo", 
            "representante_nome", "representante_cpf", "participacao_percentual"
        ]
        for k in expected_keys:
            data.setdefault(k, None)

        # Score
        filled = sum(1 for k, v in data.items() if k in expected_keys and v)
        data["score_confianca"] = f"{filled}/{len(expected_keys)}"
        
        # Status
        status_final = "OK_REFINED"
        if filled < 3:
            status_final = "BAIXA_QUALIDADE_REFINED"

        # Sanitização
        if data.get('cnpj'):
            data['cnpj'] = ''.join(filter(str.isdigit, str(data['cnpj'])))
        if data.get('representante_cpf'):
            data['representante_cpf'] = ''.join(filter(str.isdigit, str(data['representante_cpf'])))
             
        return data, None, status_final
    except Exception as e:
        return None, str(e), "ERRO_TECNICO_REFINED"
    finally:
        if sample_file:
            try: genai.delete_file(sample_file.name)
            except: pass

def deve_reprocessar(row):
    # 1. Erros Técnicos e de Parse
    if row['status_proc'] in ["ERRO", "ERRO_JSON", "ERRO_IA_VAZIA", "ERRO_TECNICO", "ERRO_UPLOAD", "ERRO_TIMEOUT"]:
        return True
    
    # 2. Baixa Qualidade (definida no script anterior)
    if 'BAIXA_QUALIDADE' in str(row['status_proc']):
        return True
        
    # 3. Score de Confiança Baixo
    try:
        if pd.notna(row['score_confianca']):
            score = int(str(row['score_confianca']).split('/')[0])
            if score < 5: 
                return True
    except:
        pass 
        
    return False

def main():
    print("="*60)
    print("REPESCAGEM INTELIGENTE (GOLDEN SOURCE PHASE 2)")
    print(f"Modelo: {MODEL_NAME}")
    print("="*60)
    
    setup_gemini()
    
    if not INPUT_CSV.exists():
        print(f"❌ Arquivo de entrada não encontrado: {INPUT_CSV}")
        return

    print("Carregando dataset bruto...")
    df = pd.read_csv(INPUT_CSV, sep=";", dtype=str)
    
    # Identificar candidatos
    mask = df.apply(deve_reprocessar, axis=1)
    df_to_fix = df[mask].copy()
    
    print(f"Total Arquivos: {len(df)}")
    print(f"Arquivos para Repescagem: {len(df_to_fix)} ({len(df_to_fix)/len(df)*100:.1f}%)")
    
    if df_to_fix.empty:
        print("🎉 Nenhum arquivo precisa de repescagem! Dataset já está perfeito.")
        df.to_csv(OUTPUT_CSV, sep=";", index=False)
        return
        
    # Lista de arquivos para processar
    # Criar mapa de index -> path para atualizar depois
    tasks = []
    for idx, row in df_to_fix.iterrows():
        path_str = row.get('caminho_completo')
        if pd.notna(path_str) and Path(path_str).exists():
            tasks.append((idx, Path(path_str)))
            
    print(f"Iniciando reprocessamento de {len(tasks)} arquivos...")
    
    completed = 0
    start_time = time.time()
    
    # Vamos atualizar o DF original em memória e salvar no final (volume menor)
    # ou salvar updates. Para simplificar e garantir consistencia, atualizamos o DF.
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {executor.submit(process_pdf, path): idx for idx, path in tasks}
        
        for future in as_completed(future_map):
            idx = future_map[future]
            try:
                data, error_msg, status_code = future.result()
                completed += 1
                
                if data:
                    # Atualizar colunas no DF original
                    df.at[idx, "status_proc"] = status_code
                    df.at[idx, "tipo_erro"] = None
                    df.at[idx, "erro_detalhe"] = None
                    for k, v in data.items():
                        if k in df.columns:
                            df.at[idx, k] = v
                    
                    dist = str(data.get('distribuidora', 'N/A'))
                    score = str(data.get('score_confianca', 'N/A'))
                    print(f"[{completed}/{len(tasks)}] ♻️ RECUPERADO: {dist} | Score: {score}", flush=True)
                else:
                    # Se falhou de novo, atualiza erro
                    df.at[idx, "status_proc"] = "ERRO_FATAL"
                    df.at[idx, "tipo_erro"] = status_code
                    df.at[idx, "erro_detalhe"] = str(error_msg)
                    print(f"[{completed}/{len(tasks)}] 💀 FALHOU NOVAMENTE: {status_code}", flush=True)
                    
            except Exception as e:
                print(f"Erro interno na thread: {e}")

            if completed % 10 == 0:
                # Checkpoint
                df.to_csv(OUTPUT_CSV, sep=";", index=False)
                print("💾 Checkpoint (Refined)", flush=True)

    print("\nSalvando Dataset Refinado Final...")
    df.to_csv(OUTPUT_CSV, sep=";", index=False)
    print(f"✅ Concluído: {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
