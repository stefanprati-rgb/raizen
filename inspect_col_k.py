import pandas as pd
from pathlib import Path
from scripts.runners.enrich_errors_full import find_header_row, clean_uc_key_vectorized

FILE_BASE = r"c:\Projetos\Raizen\docs\BASE DE CLIENTES - Raizen.xlsx"
p = Path(FILE_BASE)

# Find header
header_row = find_header_row(p, hints=['NUMERO UC', 'id_uc_negociada'])
print(f"Loading Base from row {header_row}...")

# Load without header initially to check absolute position "K" (index 10)
# actually, better to load with header and check if K corresponds to what we think
df = pd.read_excel(FILE_BASE, skiprows=header_row)

print("Total columns:", len(df.columns))
print("Column Names:", df.columns.tolist())

# Check Column K (Index 10)
if len(df.columns) > 10:
    col_k_name = df.columns[10]
    print(f"\nColumn K (Index 10) Name: '{col_k_name}'")
    print("Sample values from Column K:")
    print(df.iloc[:5, 10].tolist())
    
    # Check if this column resembles CNPJ
    sample = df.iloc[0, 10]
    print(f"First value type: {type(sample)}")
else:
    print("\nFile has fewer than 11 columns!")
