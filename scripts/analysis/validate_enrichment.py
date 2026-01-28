import pandas as pd
try:
    df = pd.read_excel(r'c:\Projetos\Raizen\output\enrichment\ERROS_CADASTRO_ENRICHED_FULL.xlsx')
    stats = df['STATUS_ENRIQUECIMENTO'].value_counts().to_string()
    
    with open('enrichment_stats.txt', 'w') as f:
        f.write(f"Total Rows: {len(df)}\n")
        f.write("Status Counts:\n")
        f.write(stats + "\n")
        f.write(f"Columns: {df.columns.tolist()}\n")
        f.write(f"Sample Row: {df.iloc[0].to_dict()}\n")
except Exception as e:
    with open('enrichment_stats.txt', 'w') as f:
        f.write(f"Error: {e}")
