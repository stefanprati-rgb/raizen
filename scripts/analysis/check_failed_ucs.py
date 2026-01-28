import pandas as pd
import os
from pathlib import Path

path = r"c:\Projetos\Raizen\output\recovery\recovered_data_final.xlsx"
df = pd.read_excel(path)
failed = df[df['status'] == 'Falha (PDF não encontrado)'].head(10)

renamed_dir = Path(r"c:\Projetos\Raizen\output\termos_renomeados")
all_files = list(renamed_dir.glob("*.pdf"))
file_names = [f.name for f in all_files]

print("Verificando 10 UCs que falharam:")
for uc in failed['UC']:
    uc_str = str(uc).strip()
    found = [f for f in file_names if uc_str in f]
    print(f"UC: {uc_str} | Encontrado no diretório: {found[:1]}")
