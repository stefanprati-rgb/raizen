
import pandas as pd
from pathlib import Path
import datetime

GOLDEN_PATH = Path("C:/Projetos/Raizen/output/DATASET_FINAL_GOLDEN_RAIZEN_EXPLODED.xlsx")
CORRECTED_PATH = Path("C:/Projetos/Raizen/output/CEP_CORRIGIDO_FINAL.xlsx")
ERROR_PATH = Path("C:/Projetos/Raizen/docs/ERROS cadastros RAIZEN.xlsx")
OUTPUT_PATH = Path("C:/Projetos/Raizen/output/DATASET_FINAL_GOLDEN_RAIZEN_V2.xlsx")

def finalize_merge():
    print("Loading datasets...")
    df_gold = pd.read_excel(GOLDEN_PATH, dtype=str)
    df_corr = pd.read_excel(CORRECTED_PATH, dtype=str)
    df_err = pd.read_excel(ERROR_PATH, dtype=str)
    
    print(f"Original Golden Size: {len(df_gold)}")
    
    # 1. Prepare correction map
    # Clean UCs for matching
    df_gold['uc_clean'] = df_gold['UC / Instalação'].str.replace(r'\D', '', regex=True)
    df_corr['uc_clean'] = df_corr['UC'].str.replace(r'\D', '', regex=True)
    
    # Create dicts for updates
    correction_dict = df_corr.set_index('uc_clean').to_dict('index')
    
    updates_count = 0

    # Ensure columns exist
    for col in ['CEP', 'Endereço', 'Cidade', 'Estado', 'DATA_QUALITY_NOTE']:
        if col not in df_gold.columns:
            df_gold[col] = ''
    
    # Iterar e atualizar

    for idx, row in df_gold.iterrows():
        uc = str(row['uc_clean'])
        if uc in correction_dict:
            data = correction_dict[uc]
            
            # Formatar endereço completo
            rua = str(data.get('endereco_rua', '')).replace('nan', '')
            num = str(data.get('endereco_numero', '')).replace('nan', '')
            bairro = str(data.get('endereco_bairro', '')).replace('nan', '')
            
            full_addr = f"{rua}, {num}, {bairro}".strip(', ')
            
            # Update fields
            df_gold.at[idx, 'CEP'] = data.get('cep', row['CEP'])
            df_gold.at[idx, 'Endereço'] = full_addr if len(full_addr) > 5 else row['Endereço']
            df_gold.at[idx, 'Cidade'] = data.get('endereco_cidade', row['Cidade'])
            df_gold.at[idx, 'Estado'] = data.get('endereco_estado', row['Estado'])
            
            # Mark as corrected
            df_gold.at[idx, 'DATA_QUALITY_NOTE'] = "CEP_CORRECTED_BY_AI"
            updates_count += 1

    print(f"Updated {updates_count} records with AI corrections.")

    # 2. Flag missing files
    # Identify UCs that were in error list but NOT in correction list
    corrected_ucs = set(df_corr['uc_clean'])
    df_err['uc_clean'] = df_err['Unidade Consumidora'].str.replace(r'\D', '', regex=True)
    
    missing_ucs = set(df_err[~df_err['uc_clean'].isin(corrected_ucs)]['uc_clean'])
    
    missing_count = 0
    for idx, row in df_gold.iterrows():
        uc = str(row['uc_clean'])
        if uc in missing_ucs:
            # Only tag if not already tagged/corrected? 
            # Or force tag.
            df_gold.at[idx, 'DATA_QUALITY_NOTE'] = "MANUAL_CHECK_REQ_PDF_MISSING"
            missing_count += 1
            
    print(f"Flagged {missing_count} records as PDF_MISSING.")

    # Drop temp column
    if 'uc_clean' in df_gold.columns:
        df_gold = df_gold.drop(columns=['uc_clean'])
    
    # Save
    print(f"Saving to {OUTPUT_PATH}...")
    df_gold.to_excel(OUTPUT_PATH, index=False)
    print("Done.")

if __name__ == "__main__":
    finalize_merge()
