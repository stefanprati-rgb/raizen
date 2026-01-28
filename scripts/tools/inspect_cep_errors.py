
import pandas as pd
from pathlib import Path
import os
import unicodedata
import re

ERROR_FILE = Path("C:/Projetos/Raizen/docs/ERROS cadastros RAIZEN.xlsx")
OUTPUT_DIR = Path("C:/Projetos/Raizen/output")

def sanitize(text):
    if not isinstance(text, str): return ""
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    return re.sub(r'[^A-Z0-9]', '', text.upper())

def cross_reference():
    if not ERROR_FILE.exists():
        print("Error file missing.")
        return

    df_err = pd.read_excel(ERROR_FILE, dtype=str)
    df_err['uc_clean'] = df_err['Unidade Consumidora'].str.replace(r'\D', '', regex=True)
    df_err['cnpj_clean'] = df_err['CNPJ/CPF'].str.replace(r'\D', '', regex=True)
    df_err['name_clean'] = df_err['NOME'].apply(sanitize)

    print(f"Total errors in report: {len(df_err)}")

    if Path("C:/Projetos/Raizen/output/cep_errors_resolved_paths.csv").exists():
        os.remove("C:/Projetos/Raizen/output/cep_errors_resolved_paths.csv")

    print("Starting Global Search (Filename contains UC or CNPJ)...")
    ROOT_DIR = Path("C:/Projetos/Raizen")
    
    # Dynamic resolve for secondary workspace
    base_docs = Path("C:/Users/Stefan_Pratti/GRUPO GERA/Gestão GDC - Documentos")
    second_ws = None
    if base_docs.exists():
        for d in os.listdir(base_docs):
            if "RA" in d and "ZEN" in d: 
                pot_path = base_docs / d / "02 - Base Clientes" / "TERMO DE ADESÃO"
                if pot_path.exists():
                    second_ws = pot_path
                    break
    
    # Third workspace provided by user
    third_ws = Path("C:/Projetos/Raizen/output/termos_renomeados")

    pdf_files = []
    scan_paths = [ROOT_DIR]
    if second_ws: scan_paths.append(second_ws)
    if third_ws.exists(): scan_paths.append(third_ws)

    for base_path in scan_paths:
        if not base_path.exists(): 
            print(f"Path does not exist: {base_path}")
            continue
        print(f"Scanning: {base_path}")
        count_files = 0
        for root, _, files in os.walk(base_path):
            if ".git" in root or ".venv" in root: continue
            if "output" in root and "renamed_pdfs" not in root and "termos_renomeados" not in root: continue
            for f in files:
                if f.lower().endswith(".pdf"):
                    pdf_files.append((f, os.path.join(root, f)))
                    count_files += 1
        print(f"Found {count_files} PDFs in {base_path}")

    # Load mapping
    uc_map = {}
    map_file = Path("C:/Projetos/Raizen/output/missing_uc_to_conta_map.csv")
    if map_file.exists():
        df_map = pd.read_csv(map_file, dtype=str)
        # Assuming the second column is the account ID
        acc_col = df_map.columns[1] 
        uc_map = dict(zip(df_map['Unidade Consumidora'], df_map[acc_col]))

    extra_matches = []
    
    for idx, row in df_err.iterrows():
        uc = str(row['uc_clean']).strip()
        cnpj = str(row['cnpj_clean']).strip()
        alt_id = str(uc_map.get(row['Unidade Consumidora'], '')).strip()
        
        found = False
        for f_name, f_path in pdf_files:
            f_name_upper = f_name.upper()
            
            # Check UC (contains)
            uc_match = (len(uc) > 4 and uc in f_name_upper)
            # Check CNPJ (contains)
            cnpj_match = (len(cnpj) > 6 and cnpj in f_name_upper)
            # Check Alt ID
            alt_match = (len(alt_id) > 5 and alt_id in f_name_upper)
            
            if uc_match or cnpj_match or alt_match:
                m_row = row.copy()
                m_row['arquivo_origem'] = f_name
                m_row['caminho_completo'] = f_path
                if uc_match: m_row['match_type'] = 'UC'
                elif cnpj_match: m_row['match_type'] = 'CNPJ'
                else: m_row['match_type'] = 'ALT_ID'
                
                extra_matches.append(m_row)
                found = True
                break
        
        if not found:
            print(f"MISSING: {uc} | {cnpj} | ID: {alt_id}")

    if extra_matches:

        print(f"Global matches found: {len(extra_matches)}")
        final_ds = pd.DataFrame(extra_matches)
        
        print(f"Total Matches: {len(final_ds)}/48")
        final_ds.to_csv("C:/Projetos/Raizen/output/cep_errors_resolved_paths.csv", index=False)
    else:
        print("Global search found NO matches.")


if __name__ == "__main__":
    cross_reference()
