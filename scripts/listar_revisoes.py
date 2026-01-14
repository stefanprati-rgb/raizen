import glob
from pathlib import Path
import pandas as pd

print("ARQUIVOS PARA REVISÃO/FALHA:")
print("=" * 60)

for f in sorted(Path('output').rglob('*_revisao.csv')):
    try:
        # Assuming CSV format, likely delimiter ; or ,
        # Try finding delimiter by sniffing line 1
        with open(f, 'r', encoding='utf-8') as fs:
            header = fs.readline()
            sep = ';' if ';' in header else ','
            
        df = pd.read_csv(f, encoding='utf-8', sep=sep)
        
        # Look for file column and reason column
        file_col = next((c for c in df.columns if 'arquivo' in c.lower() or 'caminho' in c.lower()), None)
        reason_col = next((c for c in df.columns if 'motivo' in c.lower() or 'erro' in c.lower()), None)
        
        if file_col:
            model_name = f.name.replace('_revisao.csv', '')
            print(f"\nMODELO: {model_name}")
            for idx, row in df.iterrows():
                fname = row[file_col]
                reason = row[reason_col] if reason_col else "Sem motivo especificado"
                print(f"  - {fname}")
                print(f"    Erro: {reason}")
                
    except Exception as e:
        print(f"Erro lendo {f}: {e}")
