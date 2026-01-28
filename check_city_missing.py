import pandas as pd
file_path = r"c:\Projetos\Raizen\output\enrichment\ERROS_CADASTRO_RAIZEN_1_ENRICHED.xlsx"
df = pd.read_excel(file_path)

mask_missing_cep = df['FINAL_CEP'].isna()
missing_cep_df = df[mask_missing_cep]

print(f"Total Missing CEP: {len(missing_cep_df)}")
print("Missing City Count:", missing_cep_df['FINAL_CIDADE'].isna().sum())

print("\nSample records with Missing CEP:")
print(missing_cep_df[['UC', 'FINAL_LOGRADOURO', 'FINAL_CIDADE', 'FINAL_UF']].head(10).to_string())
