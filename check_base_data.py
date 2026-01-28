import pandas as pd
from scripts.runners.enrich_errors_full import find_header_row

FILE_BASE = r"c:\Projetos\Raizen\docs\BASE DE CLIENTES - Raizen.xlsx"
from pathlib import Path
p = Path(FILE_BASE)
header_row = find_header_row(p, hints=['NUMERO UC', 'id_uc_negociada'])

print(f"Reading Base from row {header_row}...")
df = pd.read_excel(FILE_BASE, skiprows=header_row)

print("Columns:", df.columns.tolist())
if 'CNPJ' in df.columns:
    print("CNPJ Non-Null Count:", df['CNPJ'].count())
    print("CNPJ First 5 values:", df['CNPJ'].head().tolist())
else:
    print("CNPJ column NOT FOUND!")
    
# Check UC 4458837 (known from earlier logs to be in Error file)
target_uc = '4458837'
print(f"\nChecking for UC {target_uc}...")

# Normalize UC in Base for search
if 'NUMERO UC' in df.columns:
    df['UC_STR'] = df['NUMERO UC'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    row = df[df['UC_STR'] == target_uc]
    
    if not row.empty:
        print("Row Found!")
        print(row[['NUMERO UC', 'CNPJ']].to_dict('records'))
    else:
        print("UC NOT FOUND in clean search (try fuzzy?)")
        # Fuzzy
        match = df[df['UC_STR'].str.contains(target_uc, na=False)]
        if not match.empty:
            print("Fuzzy Match Found:")
            print(match[['NUMERO UC', 'CNPJ']].head().to_dict('records'))
        else:
            print("Definitely not found.")
else:
    print("Column 'NUMERO UC' missing.")
