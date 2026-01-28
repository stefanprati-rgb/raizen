import google.generativeai as genai
import os
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import json

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print(f"Key: {api_key[:5]}...")
genai.configure(api_key=api_key)

BASE_DIR = Path("C:/Projetos/Raizen/data/processed")
CSV_PATH = Path("C:/Projetos/Raizen/output/datasets_consolidados/CPFL_PAULISTA/CPFL_PAULISTA.csv")

def find_pdf_path(filename, base_dir):
    candidate = base_dir / "16_paginas/CPFL_PAULISTA" / filename
    if candidate.exists(): return candidate
    results = list(base_dir.rglob(filename))
    if results: return results[0]
    return None

df = pd.read_csv(CSV_PATH, sep=";", low_memory=False)
sem_data = df[pd.isna(df["data_adesao"])].head(1)

if sem_data.empty:
    print("Nenhum arquivo sem data!")
    exit()

row = sem_data.iloc[0]
arquivo = row["arquivo_origem"]
print(f"Testando arquivo: {arquivo}")

pdf_path = find_pdf_path(arquivo, BASE_DIR)
if not pdf_path:
    print("PDF não encontrado")
    exit()

print("Enviando para Gemini...")
try:
    sample_file = genai.upload_file(path=str(pdf_path))
    print("Upload OK. Processando...")
    
    model = genai.GenerativeModel("gemini-2.5-flash-lite")
    prompt = "Extraia JSON: {data_adesao, participacao_percentual, representante_nome}. Data no formato DD/MM/AAAA."
    
    response = model.generate_content([sample_file, prompt], generation_config={"response_mime_type": "application/json"})
    print("Resposta:")
    print(response.text)
    
except Exception as e:
    print(f"ERRO: {e}")
