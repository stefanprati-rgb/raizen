import pandas as pd
import sys
from pathlib import Path

# Adicionar src ao path para reusar a função de limpeza
project_root = Path(r"c:\Projetos\Raizen")
sys.path.append(str(project_root))

from scripts.runners.enrich_errors_full import clean_uc_key_vectorized, find_header_row

FILE_ERROS = project_root / "docs" / "ERROS CADASTRO RZ 1.xlsx"
FILE_BASE = project_root / "docs" / "BASE DE CLIENTES - Raizen.xlsx"

print(">>> Debugging Keys <<<")

# Carregar Erros
df_erros = pd.read_excel(FILE_ERROS)
df_erros['UC_RAW'] = df_erros['UC']
df_erros['UC_KEY'] = clean_uc_key_vectorized(df_erros['UC'])
print("\n[ERROS] Sample Keys:")
print(df_erros[['UC_RAW', 'UC_KEY']].head(5))

# Carregar Base
header_row = find_header_row(FILE_BASE, hints=['NUMERO UC', 'id_uc_negociada'])
df_base = pd.read_excel(FILE_BASE, skiprows=header_row)

# Identificar coluna UC
col_uc_base = 'NUMERO UC'
if col_uc_base not in df_base.columns:
    print(f"\nColuna {col_uc_base} não encontrada diretamente. Colunas disponíveis:")
    print(df_base.columns.tolist()[:10])
    # Tentar achar
    candidates = [c for c in df_base.columns if 'UC' in str(c).upper()]
    if candidates:
        col_uc_base = candidates[0]
        print(f"Usando coluna candidata: {col_uc_base}")

print(f"\n[BASE] Using Column: {col_uc_base}")
uc_series = df_base[col_uc_base]
if isinstance(uc_series, pd.DataFrame):
    uc_series = uc_series.iloc[:, 0]

df_base['UC_RAW'] = uc_series
df_base['UC_KEY'] = clean_uc_key_vectorized(uc_series)

print("\n[BASE] Sample Keys:")
print(df_base[['UC_RAW', 'UC_KEY']].head(5))

# Tentar interseção manual
common = set(df_erros['UC_KEY']).intersection(set(df_base['UC_KEY']))
print(f"\nTotal Common Keys: {len(common)}")
if len(common) == 0:
    print("No matches found!")
    print(f"Erros Example: '{df_erros['UC_KEY'].iloc[0]}' (len={len(df_erros['UC_KEY'].iloc[0])})")
    print(f"Base Example: '{df_base['UC_KEY'].iloc[0]}' (len={len(df_base['UC_KEY'].iloc[0])})")
else:
    print(f"Found {len(common)} matches. Join should work.")
