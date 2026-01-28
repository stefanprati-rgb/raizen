
import os
import sys
import json
import time
import pandas as pd
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# Carregar variáveis de ambiente
load_dotenv()

# Configurações
INPUT_CSV = Path("C:/Projetos/Raizen/output/cep_errors_resolved_paths.csv")
OUTPUT_XLSX = Path("C:/Projetos/Raizen/output/CEP_CORRIGIDO_FINAL.xlsx")
MODEL_NAME = "gemini-2.0-flash-lite"

PROMPT_CEP = """
Atue como especialista em análise de faturas e contratos de energia.
O objetivo é extrair o endereço COMPLETO de instalação da Unidade Consumidora citada no documento.

Extraia os campos:
1. endereco_rua: Nome da rua/logradouro
2. endereco_numero: Número do imóvel
3. endereco_bairro: Bairro
4. endereco_cidade: Cidade
5. endereco_estado: Estado (UF)
6. cep: CEP (apenas números, 8 dígitos)

Retorne exclusivamente um JSON. Se não encontrar, retorne null.
{
  "endereco_rua": "string",
  "endereco_numero": "string",
  "endereco_bairro": "string",
  "endereco_cidade": "string",
  "endereco_estado": "string",
  "cep": "string"
}
"""

def setup_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Erro: GEMINI_API_KEY não encontrada.")
        sys.exit(1)
    genai.configure(api_key=api_key)

def process_file(file_info):
    pdf_path = file_info.get('caminho_completo')
    
    # Se path for NaN ou vazio
    if pd.isna(pdf_path) or str(pdf_path).strip() == "":
        filename = file_info.get('arquivo_origem')
        if pd.isna(filename):
             return {"UC": file_info['Unidade Consumidora'], "status": "NO_PATH_OR_NAME"}
        # Tenta achar na pasta golden
        potential = Path("C:/Projetos/Raizen/data/golden_source") / str(filename)
        if potential.exists():
            pdf_path = str(potential)
        else:
             return {"UC": file_info['Unidade Consumidora'], "status": "FILE_NOT_FOUND_ON_DISK"}

    # Garantir que path existe
    if not Path(str(pdf_path)).exists():
         return {"UC": file_info['Unidade Consumidora'], "status": "PATH_DOES_NOT_EXIST"}


    sample_file = None
    try:
        sample_file = genai.upload_file(path=pdf_path)
        while sample_file.state.name == "PROCESSING":
            time.sleep(1)
            sample_file = genai.get_file(sample_file.name)
        
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content([sample_file, PROMPT_CEP], generation_config={"response_mime_type": "application/json"})
        
        data = json.loads(response.text)
        data['UC'] = file_info['Unidade Consumidora']
        data['NOME_ORIGINAL'] = file_info['NOME']
        data['status'] = "OK"
        return data
    except Exception as e:
        return {"UC": file_info['Unidade Consumidora'], "status": f"ERROR: {str(e)}"}
    finally:
        if sample_file:
            try: genai.delete_file(sample_file.name)
            except: pass

def main():
    setup_gemini()
    
    if not INPUT_CSV.exists():
        print(f"Arquivo {INPUT_CSV} não encontrado.")
        return

    df = pd.read_csv(INPUT_CSV)
    print(f"Processando {len(df)} arquivos para correção de CEP...")

    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_file, row) for _, row in df.iterrows()]
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            print(f"UC {res.get('UC')}: {res.get('status')}")

    df_final = pd.DataFrame(results)
    df_final.to_excel(OUTPUT_XLSX, index=False)
    print(f"[OK] Resultado salvo em: {OUTPUT_XLSX}")

if __name__ == "__main__":
    main()
