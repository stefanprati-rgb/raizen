
import pandas as pd
import sys

try:
    df1 = pd.read_excel(r'C:\Projetos\Raizen\extracao-termos.xlsx')
    df2 = pd.read_excel(r'C:\Projetos\Raizen\output\cpfl_paulista_final\cpfl_dataset_final_compiled.xlsx')
    df_merged = pd.read_excel(r'C:\Projetos\Raizen\output\cpfl_paulista_final\cpfl_dataset_consolidated.xlsx')

    with open('distribuidora_analysis.txt', 'w', encoding='utf-8') as f:
        f.write("FILE 1 (extracao-termos.xlsx):\n")
        if 'Distribuidora' in df1.columns:
            f.write(str(df1['Distribuidora'].unique()) + "\n")
            f.write(str(df1['Distribuidora'].value_counts()) + "\n")
        else:
            f.write("Column 'Distribuidora' not found.\n")
        
        f.write("\nFILE 2 (cpfl_dataset_final_compiled.xlsx):\n")
        if 'Distribuidora' in df2.columns:
            f.write(str(df2['Distribuidora'].unique()) + "\n")
            f.write(str(df2['Distribuidora'].value_counts()) + "\n")
        else:
            f.write("Column 'Distribuidora' not found.\n")

        f.write("\nMERGED FILE:\n")
        if 'Distribuidora' in df_merged.columns:
             f.write(str(df_merged['Distribuidora'].unique()) + "\n")
        else:
             f.write("Column 'Distribuidora' not found.\n")

except Exception as e:
    with open('distribuidora_analysis.txt', 'w') as f:
        f.write(str(e))
