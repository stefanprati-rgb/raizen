"""Teste Embracon"""
import importlib.util
import pdfplumber
import warnings
warnings.filterwarnings('ignore')

spec = importlib.util.spec_from_file_location('organizer', 'scripts/legacy/super_organizer_v4.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

pdf_path = r'C:\Projetos\Raizen\data\processed\18_paginas\ELEKTRO\SOLAR 41372 - EMBRACON ADM DE CONSORCIO LTDA - 58113812000123 - Clicksign.pdf'

# Testar identificação
result = mod.identify_distributor(pdf_path)
print(f'Resultado: {result}')
print()

# Ver endereço do cliente
with pdfplumber.open(pdf_path) as pdf:
    text = pdf.pages[0].extract_text()
    if text:
        print("DADOS DO CONTRATO (primeira página):")
        lines = text.split('\n')
        for line in lines[:30]:
            print(f"  {line[:80]}")
