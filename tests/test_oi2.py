"""Teste OI S.A."""
import importlib.util
import pdfplumber
import warnings
warnings.filterwarnings('ignore')

spec = importlib.util.spec_from_file_location('organizer', 'scripts/legacy/super_organizer_v4.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

pdf_path = r'C:\Projetos\Raizen\data\processed\17_paginas\ENERGISA\SOLAR 16885 - OI S.A. – EM RECUPERAÇÃO JUDICIAL - 76535764032509.pdf'

result = mod.identify_distributor(pdf_path)
print(f'Resultado: {result}')
print()

# Ver conteúdo
with pdfplumber.open(pdf_path) as pdf:
    text = pdf.pages[0].extract_text()
    if text:
        print('Primeiras linhas:')
        for line in text.split('\n')[:25]:
            print(f'  {line[:70]}')
