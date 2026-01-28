
import pandas as pd
from pathlib import Path
import os
from fuzzywuzzy import process, fuzz

ERROR_FILE = Path("C:/Projetos/Raizen/docs/ERROS cadastros RAIZEN.xlsx")
RESOLVED_FILE = Path("C:/Projetos/Raizen/output/cep_errors_resolved_paths.csv")

def fuzzy_search():
    df_err = pd.read_excel(ERROR_FILE, dtype=str)
    
    resolved_ucs = set()
    if RESOLVED_FILE.exists():
        df_res = pd.read_csv(RESOLVED_FILE, dtype=str)
        resolved_ucs = set(df_res['Unidade Consumidora'])
    
    missing = df_err[~df_err['Unidade Consumidora'].isin(resolved_ucs)].copy()
    print(f"Searching for {len(missing)} remaining missing cases by NAME...")

    # Load all filenames
    all_files = []
    roots = [
        Path("C:/Projetos/Raizen"),
        Path("C:/Projetos/Raizen/output/termos_renomeados"),
        Path("C:/Users/Stefan_Pratti/GRUPO GERA/Gestão GDC - Documentos/RAÍZEN/02 - Base Clientes/TERMO DE ADESÃO")
    ]
    
    for r in roots:
        if not r.exists(): continue
        for root, _, files in os.walk(r):
            if ".git" in root or ".venv" in root: continue
            for f in files:
                if f.lower().endswith('.pdf'):
                    all_files.append(f)
    
    unique_files = list(set(all_files))
    print(f"Total Unique Files to Match Against: {len(unique_files)}")

    matches = []
    for idx, row in missing.iterrows():
        name = str(row['NOME'])
        if len(name) < 5: continue
        
        # Fuzzy match
        best_match, score = process.extractOne(name, unique_files, scorer=fuzz.token_set_ratio)
        
        if score > 80:
            print(f"MATCH FOUND ({score}%): '{name}' -> '{best_match}'")
            matches.append({
                'UC': row['Unidade Consumidora'],
                'NOME_ALVO': name,
                'ARQUIVO_ENCONTRADO': best_match,
                'SCORE': score
            })
        else:
            print(f"No good match for '{name}' (Best: {score}% - {best_match})")

    if matches:
        pd.DataFrame(matches).to_excel("C:/Projetos/Raizen/output/fuzzy_name_matches.xlsx", index=False)
        print("Matches saved to fuzzy_name_matches.xlsx")

if __name__ == "__main__":
    fuzzy_search()
