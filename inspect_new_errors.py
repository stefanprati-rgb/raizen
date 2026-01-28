import pandas as pd
from scripts.runners.enrich_errors_full import find_header_row

FILE_NEW = r"c:\Projetos\Raizen\docs\ERROS cadastros RAIZEN 1.xlsx"

try:
    df = pd.read_excel(FILE_NEW, nrows=5)
    print("Columns:", df.columns.tolist())
    print("Sample:\n", df.head(2))
except Exception as e:
    print("Error reading file:", e)
