import pandas as pd

file_path = r"c:\Projetos\Raizen\output\enrichment\ERROS_CADASTRO_ENRICHED_FULL.xlsx"

try:
    df = pd.read_excel(file_path)
    
    # Filter for the addresses seen in the image to diagnose
    keywords = ["Ourique", "Joao Liera", "Rita Ludolf", "Washington Luiz", "AFONSO MORENO"]
    
    mask = df['FINAL_LOGRADOURO'].astype(str).str.contains('|'.join(keywords), na=False, case=False)
    
    debug_df = df[mask]
    
    print(f"Found {len(debug_df)} matching records.")
    
    cols_to_show = ['UC', 'CNPJ', 'FINAL_LOGRADOURO', 'FINAL_CIDADE', 'FINAL_UF', 'FINAL_CEP', 'BASE_CEP']
    # Filter matching cols
    cols_to_show = [c for c in cols_to_show if c in df.columns]
    
    for idx, row in debug_df[cols_to_show].iterrows():
        print(f"\nRecord {idx}:")
        print(row.to_dict())
    
except Exception as e:
    print(f"Error: {e}")
