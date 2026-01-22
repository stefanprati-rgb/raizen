import pandas as pd

file_path = "data/reference/PAINEL DE DESEMPENHO DAS DISTRIBUIDORAS POR MUNICÍPIO.xlsx"

try:
    df = pd.read_excel(file_path, nrows=20)
    print("Colunas encontradas:")
    for col in df.columns:
        print(f"- {col}")
    print("\nPrimeiras 5 linhas:")
    print(df.head())
except Exception as e:
    print(f"Erro ao ler Excel: {e}")
