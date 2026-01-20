
import pandas as pd
import sys

def get_headers(file_path):
    try:
        df = pd.read_excel(file_path, nrows=0)
        return df.columns.tolist()
    except Exception as e:
        return str(e)

file1 = r"C:\Projetos\Raizen\extracao-termos.xlsx"
file2 = r"C:\Projetos\Raizen\output\cpfl_paulista_final\cpfl_dataset_final_compiled.xlsx"

with open("headers_info.txt", "w", encoding="utf-8") as f:
    f.write(f"File 1 ({file1}):\n")
    f.write(str(get_headers(file1)) + "\n\n")
    f.write(f"File 2 ({file2}):\n")
    f.write(str(get_headers(file2)) + "\n")
