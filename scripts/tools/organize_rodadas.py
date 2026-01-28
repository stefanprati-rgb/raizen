import shutil
from pathlib import Path

base = Path('output/validacao_gemini')

# Criar subpastas
rodada1 = base / 'rodada_1'
rodada2 = base / 'rodada_2'
rodada1.mkdir(exist_ok=True)
rodada2.mkdir(exist_ok=True)

# Mover PDFs
pdfs = sorted([f for f in base.glob('*.pdf')])
for i, pdf in enumerate(pdfs):
    if i < 10:
        shutil.move(str(pdf), rodada1 / pdf.name)
    else:
        shutil.move(str(pdf), rodada2 / pdf.name)

print(f'Rodada 1: {len(list(rodada1.glob("*.pdf")))} PDFs')
print(f'Rodada 2: {len(list(rodada2.glob("*.pdf")))} PDFs')

# Copiar prompt para cada rodada
shutil.copy(base / 'PROMPT_VALIDACAO.md', rodada1 / 'PROMPT.md')
shutil.copy(base / 'PROMPT_VALIDACAO.md', rodada2 / 'PROMPT.md')
print('Prompts copiados para cada rodada')
