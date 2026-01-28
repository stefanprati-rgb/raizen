import pandas as pd
import shutil
from pathlib import Path

SOURCE = Path('C:/Projetos/Raizen/output/datasets_consolidados/CPFL_PAULISTA/CPFL_PAULISTA.csv')
TARGET = Path('C:/Projetos/Raizen/output/datasets/cpfl/dataset_CPFL_PAULISTA_ENTREGA_IA.xlsx')

print("="*50)
print("GERANDO ENTREGAVEL FINAL")
print("="*50)

if not SOURCE.exists():
    print(f"Erro: CSV nao encontrado: {SOURCE}")
    exit(1)

# Copiar CSV para temp evitar lock
TEMP_CSV = SOURCE.parent / "temp_process.csv"
shutil.copy(SOURCE, TEMP_CSV)

try:
    df = pd.read_csv(TEMP_CSV, sep=';', low_memory=False)
    
    total = len(df)
    datas = df['data_adesao'].notna().sum()
    part = df['participacao_percentual'].notna().sum()
    rep = df['representante_nome'].notna().sum()
    fid = df['fidelidade'].notna().sum() if 'fidelidade' in df.columns else 0
    aviso = df['aviso_previo'].notna().sum()
    
    print(f"Total Registros: {total}")
    print(f"Datas: {datas} ({datas/total:.1%})")
    print(f"Participacao: {part} ({part/total:.1%})")
    print(f"Representante: {rep} ({rep/total:.1%})")
    print(f"Fidelidade: {fid} ({fid/total:.1%})")
    print(f"Aviso Previo: {aviso} ({aviso/total:.1%})")
    
    print(f"\nSalvando Excel: {TARGET}")
    df.to_excel(TARGET, index=False)
    print("Sucesso!")

finally:
    if TEMP_CSV.exists():
        try:
            os.remove(TEMP_CSV)
        except: pass
