import google.generativeai as genai
import os
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import json

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

BASE_DIR = Path("C:/Projetos/Raizen/data/processed")
CSV_PATH = Path("C:/Projetos/Raizen/output/datasets_consolidados/CPFL_PAULISTA/CPFL_PAULISTA.csv")

def find_pdf_path(filename, base_dir):
    candidate = base_dir / "16_paginas/CPFL_PAULISTA" / filename
    if candidate.exists(): return candidate
    for subdir in ["05_paginas", "11_paginas", "02_paginas"]:
        candidate = base_dir / subdir / "CPFL_PAULISTA" / filename
        if candidate.exists(): return candidate
    results = list(base_dir.rglob(filename))
    if results: return results[0]
    return None

def investigate():
    df = pd.read_csv(CSV_PATH, sep=';', low_memory=False)
    # Pegar 3 casos sem representante mas COM data (para garantir que o doc é legível)
    amostras = df[pd.isna(df["representante_nome"]) & df["data_adesao"].notna()].head(3)
    
    print(f"Analisando {len(amostras)} casos sem representante...")
    
    model = genai.GenerativeModel("gemini-2.5-flash-lite")
    
    for idx, row in amostras.iterrows():
        arquivo = row["arquivo_origem"]
        pdf_path = find_pdf_path(arquivo, BASE_DIR)
        
        if not pdf_path: continue
        
        print("\n" + "="*50)
        print(f"Arquivo: {arquivo}")
        
        # Upload
        sample_file = genai.upload_file(path=str(pdf_path))
        
        prompt = """
        Analise a seção de assinaturas deste contrato (geralmente no final ou em anexos de log Clicksign/Docusign).
        1. Existe algum nome de PESSOA FÍSICA listado como signatário da empresa CONTRATANTE?
        2. Se sim, qual é?
        3. Se não, explique o porquê (ex: "Assinado apenas com e-CNPJ", "Assinatura ilegível", "Campo em branco").
        """
        
        response = model.generate_content([sample_file, prompt])
        print(f"Diagnóstico Gemini:\n{response.text}")
        
if __name__ == "__main__":
    investigate()
