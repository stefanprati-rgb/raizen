import pandas as pd
import sys
from pathlib import Path

# Adicionar src ao path
project_root = Path(r"c:\Projetos\Raizen")
sys.path.append(str(project_root))

from scripts.runners.enrich_errors_full import clean_uc_key_vectorized

FILE_ERROS = project_root / "docs" / "ERROS CADASTRO RZ 1.xlsx"
FILE_BASE = project_root / "docs" / "BASE DE CLIENTES - Raizen.xlsx"

# Carregar Erros
df_erros = pd.read_excel(FILE_ERROS, nrows=5)
df_erros['UC_KEY'] = clean_uc_key_vectorized(df_erros['UC'])
df_erros.set_index('UC_KEY', inplace=True)
print("Columns in Erros:", df_erros.columns.tolist())

# Carregar Base Real
print(f"Loading Base from {FILE_BASE}...")
# Encontrar header
from scripts.runners.enrich_errors_full import find_header_row
header_row = find_header_row(FILE_BASE, hints=['NUMERO UC', 'id_uc_negociada'])
df_base = pd.read_excel(FILE_BASE, skiprows=header_row, nrows=5)
print("ALL Columns in Base:", df_base.columns.tolist())
