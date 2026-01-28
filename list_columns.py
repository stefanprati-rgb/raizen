import pandas as pd
try:
    df = pd.read_excel(r'c:\Projetos\Raizen\output\enrichment\ERROS_CADASTRO_RAIZEN_1_ENRICHED.xlsx')
    cols = list(df.columns)
    with open('cols_dump_final.txt', 'w') as f:
        f.write(str(cols))
    print("Columns saved to cols_dump_final.txt")
except Exception as e:
    print(e)
