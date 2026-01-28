import pandas as pd
f = r"c:\Projetos\Raizen\output\enrichment\ERROS_CADASTRO_ENRICHED_FULL.xlsx"
df = pd.read_excel(f)

with open('verification_report.txt', 'w') as out:
    out.write(f"File: {f}\n")
    out.write(f"Total Rows: {len(df)}\n")
    out.write("\nOrigem Dado counts:\n")
    out.write(df['ORIGEM_DADO'].value_counts().to_string())
    out.write("\n\nStatus Enriquecimento counts:\n")
    out.write(df['STATUS_ENRIQUECIMENTO'].value_counts().to_string())
    out.write("\n\nManual Patches Sample:\n")
    out.write(df[df['ORIGEM_DADO'] == 'PATCH_MANUAL'][['UC', 'FINAL_LOGRADOURO', 'FINAL_CIDADE', 'FINAL_CEP']].to_string())
