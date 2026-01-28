
import pandas as pd
from pathlib import Path

BASE_FILE = Path("C:/Projetos/Raizen/docs/BASE DE CLIENTES - Raizen.xlsx")
ERROR_FILE = Path("C:/Projetos/Raizen/docs/ERROS cadastros RAIZEN.xlsx")
RESOLVED_FILE = Path("C:/Projetos/Raizen/output/cep_errors_resolved_paths.csv")

def check_base_for_matches():
    # Load Base
    df_base = pd.read_excel(BASE_FILE, header=2, dtype=str)
    print("Columns in Base:", df_base.columns.tolist())
    
    # Load Missing
    df_err = pd.read_excel(ERROR_FILE, dtype=str)
    resolved_ucs = set()
    if RESOLVED_FILE.exists():
        df_res = pd.read_csv(RESOLVED_FILE, dtype=str)
        resolved_ucs = set(df_res['Unidade Consumidora'])
    
    missing = df_err[~df_err['Unidade Consumidora'].isin(resolved_ucs)].copy()
    
    # Clean UCs
    df_base['uc_clean'] = df_base['NUMERO UC'].astype(str).str.replace(r'\D', '', regex=True)
    missing['uc_clean'] = missing['Unidade Consumidora'].astype(str).str.replace(r'\D', '', regex=True)
    
    # Check overlap
    matches = pd.merge(missing, df_base, on='uc_clean', how='inner')
    
    print(f"\nMissing UCs found in Base: {len(matches)} / {len(missing)}")
    
    if not matches.empty:
        print("Merged Columns:", matches.columns.tolist())
        
        # Try to dynamically identify the account column
        acc_col = 'NUMERO CONTA' if 'NUMERO CONTA' in matches.columns else 'NUMERO CONTA_y'
        if acc_col not in matches.columns:
             # Fallback: look for likely candidates
             candidates = [c for c in matches.columns if 'CONTA' in c.upper()]
             acc_col = candidates[0] if candidates else None

        name_col = 'NOME' if 'NOME' in matches.columns else 'NOME_x'
        
        cols_to_show = ['Unidade Consumidora', name_col]
        if acc_col: cols_to_show.append(acc_col)

        print("\nPotential Alternative IDs found:")
        print(matches[cols_to_show].to_string(index=False))
        
        # Save mapping for use in inspection
        if acc_col:
            matches[['Unidade Consumidora', acc_col]].to_csv("C:/Projetos/Raizen/output/missing_uc_to_conta_map.csv", index=False)
            print("\nMapping saved to output/missing_uc_to_conta_map.csv")


if __name__ == "__main__":
    check_base_for_matches()
