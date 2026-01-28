import json
from pathlib import Path

total_validos = 0
total_pdfs = 0

print("RELATÓRIO DE EXTRAÇÕES CONCLUÍDAS")
print("=" * 70)

for f in sorted(Path('output').rglob('*_relatorio.json')):
    data = json.load(open(f, encoding='utf-8'))
    modelo = data['modelo'][:45]
    validos = data['validos']
    total = data['total_pdfs']
    taxa = data['taxa_sucesso']
    print(f"{modelo:45s} | {validos:3d}/{total:3d} | {taxa}")
    total_validos += validos
    total_pdfs += total

print("=" * 70)
print(f"TOTAL EXTRAÍDO: {total_validos} contratos de {total_pdfs} PDFs processados")
