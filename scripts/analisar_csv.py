import glob
import os
import pandas as pd

# Find the latest CSV
csv_files = glob.glob('output/CONSOLIDADO_EXTRACOES_*.csv')
latest_csv = max(csv_files, key=os.path.getctime)
print(f"Reading {latest_csv}...")

try:
    df = pd.read_csv(latest_csv, encoding='utf-8', on_bad_lines='skip', quotechar='"')
    print("Columns found:", list(df.columns))
    
    # Try to identify status column
    status_col = next((c for c in df.columns if 'status' in c.lower()), None)
    
    if status_col:
        failures = df[df[status_col] != 'OK']
        print(f"Total failures: {len(failures)}")
        if not failures.empty:
            print(failures[[status_col, 'arquivo', 'erros'] if 'erros' in df.columns else [status_col]].head(20).to_string())
    else:
        print("Status column not found. First row:")
        print(df.iloc[0])

except Exception as e:
    print(e)
