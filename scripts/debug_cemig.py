import json
from pathlib import Path

f_path = Path(r"output\05_paginas\CEMIG\Termo de Adesão ao Consórcio - CEMIG (05 páginas)_relatorio.json")
try:
    data = json.load(open(f_path, encoding='utf-8', errors='ignore'))
    print("Keys:", data.keys())
    print("Validos:", data.get('validos'))
    print("Total:", data.get('total_pdfs'))
    print("Revisao Count:", len(data.get('revisao', [])))
    print("Erros Count:", len(data.get('erros', [])))
    
    if data.get('revisao'):
        print("\n--- REVISAO SAMPLE ---")
        print(data['revisao'][:2])
        
    if data.get('erros'):
        print("\n--- ERROS SAMPLE ---")
        print(data['erros'][:2])
        
except Exception as e:
    print(f"Error: {e}")
