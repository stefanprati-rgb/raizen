import pandas as pd
from pathlib import Path

MASTER_PATH = "C:/Projetos/Raizen/output/DATASET_MESTRE_RAIZEN_POWER_V3.xlsx"
CLEAN_PATH = "C:/Projetos/Raizen/output/DATASET_MESTRE_RAIZEN_POWER_V3_LIMPO.xlsx"

def main():
    print("="*60)
    print("DEDUPLICAÇÃO INTELIGENTE - DATASET MESTRE")
    print("="*60)
    
    if not Path(MASTER_PATH).exists():
        print("Arquivo Mestre não encontrado.")
        return

    df = pd.read_excel(MASTER_PATH)
    print(f"Total Bruto: {len(df)}")
    
    # 1. Normalizar nome do arquivo (remover caminhos)
    # Assumindo coluna 'arquivo_origem' ou similar. No mestre consolidado, as colunas podem variar.
    # Vamos achar a coluna do nome do arquivo.
    file_col = None
    possible_names = ["arquivo_origem", "Arquivo", "FILENAME"]
    for c in df.columns:
        if c in possible_names:
            file_col = c
            break
            
    if not file_col:
        # Tentar achar a primeira coluna que parece nome de arquivo (.pdf)
        for c in df.columns:
            if df[c].astype(str).str.contains(".pdf", case=False, na=False).any():
                file_col = c
                break
    
    if not file_col:
        print("❌ Não encontrei coluna de nome de arquivo. Deduplicação impossível.")
        return
        
    print(f"Usando coluna de arquivo: {file_col}")
    
    # Criar coluna auxiliar apenas com o basename
    df["_BASENAME"] = df[file_col].apply(lambda x: Path(str(x)).name if pd.notna(x) else str(x))
    
    # 2. Definir ordem de prioridade para manter
    # Se temos duplicata, qual sobra?
    # Preferência: CPFL > CEMIG > ELEKTRO > LIGHT > ENEL > OUTRAS
    # Assumindo coluna ORIGEM_DATASET criada no consolidate_all_datasets
    
    if "ORIGEM_DATASET" in df.columns:
        priority = {"CPFL": 1, "CEMIG": 2, "ELEKTRO": 3, "LIGHT": 4, "ENEL": 5, "OUTRAS": 6}
        df["_PRIORITY"] = df["ORIGEM_DATASET"].map(priority).fillna(99)
        
        # Ordenar por prioridade
        df = df.sort_values(by=["_BASENAME", "_PRIORITY"])
    else:
        print("⚠️ Coluna ORIGEM_DATASET não encontrada. Usando ordem aleatória.")
        
    # 3. Remover Duplicatas (mantendo o primeiro/melhor prioridade)
    before_count = len(df)
    df_clean = df.drop_duplicates(subset=["_BASENAME"], keep="first")
    duplicates_removed = before_count - len(df_clean)
    
    print(f"Duplicatas Removidas: {duplicates_removed}")
    print(f"Total Final Limpo: {len(df_clean)}")
    
    # Remover colunas auxiliares
    df_clean = df_clean.drop(columns=["_BASENAME", "_PRIORITY"], errors="ignore")
    
    # Salvar
    df_clean.to_excel(CLEAN_PATH, index=False)
    print(f"✅ Arquivo Limpo Gerado: {CLEAN_PATH}")

if __name__ == "__main__":
    main()
