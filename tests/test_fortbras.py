"""Teste do organizer V4 com arquivos Fortbras"""
import importlib.util
spec = importlib.util.spec_from_file_location('organizer', 'scripts/legacy/super_organizer_v4.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

pdfs = [
    r"C:\Projetos\Raizen\data\processed\19_paginas\ELEKTRO\TERMO_ADESAO_0011962 - FORTBRAS AUTOPECAS SA - 22761584010547 - Docusign.pdf",
    r"C:\Projetos\Raizen\data\processed\19_paginas\ELEKTRO\SOLAR 11962 -  FORTBRAS AUTOPECAS S.A. -  22761584010547.pdf",
]

print("="*60)
print("TESTE FORTBRAS")
print("="*60)

for pdf in pdfs:
    result = mod.identify_distributor(pdf)
    filename = pdf.split('\\')[-1][:50]
    print(f"\nArquivo: {filename}...")
    print(f"  Resultado: {result}")
