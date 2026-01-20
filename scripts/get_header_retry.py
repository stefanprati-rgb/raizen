import pandas as pd
with open("headers_retry.txt", "w", encoding='utf-8') as f:
    try:
        df1 = pd.read_excel(r'C:\Projetos\Raizen\extracao-termos.xlsx', nrows=1)
        f.write(str(df1.columns.tolist()) + "\n")
        df2 = pd.read_excel(r'C:\Projetos\Raizen\output\cpfl_paulista_final\cpfl_dataset_final_compiled.xlsx', nrows=1)
        f.write(str(df2.columns.tolist()) + "\n")
    except Exception as e:
        f.write(str(e))
