import pandas as pd
from pathlib import Path

MASTER_PATH = "C:/Projetos/Raizen/output/DATASET_MESTRE_RAIZEN_POWER_V3.xlsx"
SMART_PATH = "C:/Projetos/Raizen/output/DATASET_MESTRE_RAIZEN_POWER_V3_SMART.xlsx"

def main():
    print("="*60)
    print("DEDUPLICAÇÃO VIA CHAVE DE NEGÓCIO")
    print("="*60)
    
    if not Path(MASTER_PATH).exists(): return

    df = pd.read_excel(MASTER_PATH)
    print(f"Total Bruto: {len(df)}")
    
    # Normalizar chaves
    # num_instalacao e cnpj podem ser strings ou numeros. Vamos limpar.
    df["key_cnpj"] = df["cnpj"].astype(str).str.replace(r"[^0-9]", "", regex=True)
    df["key_inst"] = df["num_instalacao"].astype(str).str.replace(r"[^0-9]", "", regex=True)
    
    # Criar chave única
    # Se não tiver CNPJ ou Instalacao, a chave será o nome do arquivo (fallback)
    df["unique_id"] = df.apply(lambda row: 
                               f"{row['key_cnpj']}_{row['key_inst']}" 
                               if (len(str(row['key_cnpj'])) > 5 and len(str(row['key_inst'])) > 3) 
                               else f"FILE_{row['arquivo_origem']}", axis=1)
                               
    # Prioridade (CPFL > Outras)
    if "ORIGEM_DATASET" in df.columns:
        priority = {"CPFL": 1, "CEMIG": 2, "ELEKTRO": 3, "LIGHT": 4, "ENEL": 5, "OUTRAS": 6}
        df["_PRIORITY"] = df["ORIGEM_DATASET"].map(priority).fillna(99)
        df = df.sort_values(by=["unique_id", "_PRIORITY"])
        
    # Deduplicar
    df_clean = df.drop_duplicates(subset=["unique_id"], keep="first")
    
    print(f"Total Smart Limpo: {len(df_clean)}")
    print(f"Duplicatas Reais Removidas: {len(df) - len(df_clean)}")
    
    # Salvar
    cols_to_drop = ["key_cnpj", "key_inst", "unique_id", "_PRIORITY"]
    df_clean.drop(columns=cols_to_drop, errors="ignore").to_excel(SMART_PATH, index=False)
    print(f"✅ Arquivo: {SMART_PATH}")

if __name__ == "__main__":
    main()
