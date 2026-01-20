import pandas as pd
import os
import sys
import re

# Caminhos dos arquivos
FILE_TERMOS = r"C:\Projetos\Raizen\extracao-termos.xlsx"
FILE_DATASET = r"C:\Projetos\Raizen\output\cpfl_paulista_final\cpfl_dataset_final_compiled.xlsx"
OUTPUT_FILE = r"C:\Projetos\Raizen\output\cpfl_paulista_final\cpfl_dataset_consolidated_filtered.xlsx"

def normalize_filename(path):
    if pd.isna(path):
        return ""
    return os.path.basename(str(path)).strip()

def unify_ucs(row):
    """
    Unifica UCs das colunas especificas, tratando string splits e set union.
    """
    ucs_set = set()
    
    # Colunas de origem das UCs (pós merge, algumas podem ter sufixo se conflitaram, mas aqui acessamos pelo nome esperado)
    # No merge, sufixo _termos vai para o df_termos. O df_dataset fica sem sufixo (conforme script anterior).
    # Colunas de interesse:
    # 1. 'UC' (vinda do extracao-termos -> provavelmente virou 'UC' ou 'UC_termos')
    # 2. 'Nº Instalação' (vinda do cpfl_dataset)
    # 3. 'Nº Conta Contrato (UC)' (vinda do cpfl_dataset)
    
    # Mapear possíveis nomes de colunas que contenham dados de UC
    target_cols = ['UC', 'UC_termos', 'Nº Instalação', 'Nº Conta Contrato (UC)']
    
    for col in target_cols:
        if col in row.index and pd.notna(row[col]):
            val = str(row[col])
            # Separar por ; , ou \n ou espaço
            parts = re.split(r'[;,\n\s]+', val)
            for part in parts:
                clean_part = part.strip()
                # Filtrar apenas numeros ou codigos relevantes (opcional, aqui vou pegar tudo que não for vazio)
                if clean_part and len(clean_part) > 2: # >2 para evitar lixo
                    ucs_set.add(clean_part)
                    
    return "; ".join(sorted(ucs_set))

def main():
    print("Carregando arquivos...")
    try:
        df_termos = pd.read_excel(FILE_TERMOS)
        df_dataset = pd.read_excel(FILE_DATASET)
        
        print(f"Total Termos Orig: {df_termos.shape}")
        print(f"Total Dataset Orig: {df_dataset.shape}")
        
        # NORMALIZACAO DE DISTRIBUIDORAS
        def normalize_distribuidora(val):
            if pd.isna(val): return val
            val = str(val).upper().strip()
            # Remover prefixos comuns e sujeira
            val = re.sub(r'^(SP|MG|RJ|BA|PR|SC|RS|MT|MS|GO|DF|ES|PE|CE|RN|PB|AL|SE|TO|PI|MA|AM|PA|AC|RR|RO|AP)\s*[-–]\s*', '', val)
            val = re.sub(r'DE\s+ENERGIA\s*', '', val)
            val = val.replace('de\nenergia', '')
            val = val.replace('\n', ' ')
            # Fix typos especificos CPFL
            val = re.sub(r'C\s*P\s*F\s*L', 'CPFL', val)
            val = re.sub(r'P\s*A\s*U\s*L\s*I\s*S\s*T\s*A', 'PAULISTA', val)
            val = re.sub(r'P\s*I\s*R\s*A\s*T\s*I\s*N\s*I\s*N\s*G\s*A', 'PIRATININGA', val)
            
            # Limpeza final
            val = re.sub(r'\s+', ' ', val).strip()
            
            # Mapping direto para padronizacao final
            if 'CPFL PAULISTA' in val: return 'CPFL PAULISTA'
            if 'CPFL PIRATININGA' in val: return 'CPFL PIRATININGA'
            if 'CPFL SANTA CRUZ' in val: return 'CPFL SANTA CRUZ'
            
            return val

        print("Normalizando nomes das distribuidoras...")
        if 'Distribuidora' in df_termos.columns:
            df_termos['Distribuidora'] = df_termos['Distribuidora'].apply(normalize_distribuidora)
            
        if 'Distribuidora' in df_dataset.columns:
            df_dataset['Distribuidora'] = df_dataset['Distribuidora'].apply(normalize_distribuidora)

        # 1. FILTRAR APENAS CPFL
        # Tentar identificar coluna de distribuidora e filtrar
        print("Filtrando distribuidoras CPFL...")
        
        def is_cpfl(val):
            if pd.isna(val): return False
            return 'CPFL' in str(val).upper()

        # Filtrar df_termos
        if 'Distribuidora' in df_termos.columns:
            df_termos = df_termos[df_termos['Distribuidora'].apply(is_cpfl)]
        
        # Filtrar df_dataset
        if 'Distribuidora' in df_dataset.columns:
            df_dataset = df_dataset[df_dataset['Distribuidora'].apply(is_cpfl)]
            
        print(f"Total Termos (CPFL): {df_termos.shape}")
        print(f"Total Dataset (CPFL): {df_dataset.shape}")
        
        # Identificar chaves e Normalizar
        key_col_termos = df_termos.columns[0]
        key_col_dataset = df_dataset.columns[0]
        
        df_termos['merge_key'] = df_termos[key_col_termos].apply(normalize_filename)
        df_dataset['merge_key'] = df_dataset[key_col_dataset].apply(normalize_filename)
        
        # Merge Outer
        print("Realizando merge (Outer)...")
        # suffixes: _termos para o que vem da primeira base, vazio para a segunda (prioridade visual)
        df_merged = pd.merge(df_termos, df_dataset, on='merge_key', how='outer', suffixes=('_termos', ''))
        
        # 2. UNIFICAR UCs
        print("Unificando UCs...")
        df_merged['UC_Final_Consolidada'] = df_merged.apply(unify_ucs, axis=1)
        
        # 3. TRATAR COLUNAS DUPLICADAS E PREENCHER DADOS
        cols_to_drop = []
        for col in df_merged.columns:
            if col.endswith('_termos'):
                original_col = col.replace('_termos', '')
                # Se existe a coluna original (sem sufixo, vinda do df_dataset)
                if original_col in df_merged.columns:
                    # Preencher vazios do original com dados do _termos
                    df_merged[original_col] = df_merged[original_col].fillna(df_merged[col])
                    cols_to_drop.append(col)
        
        # Remover auxiliares
        if cols_to_drop:
            print(f"Removendo colunas auxiliares mescladas: {len(cols_to_drop)}")
            df_merged.drop(columns=cols_to_drop, inplace=True)
            
        if 'merge_key' in df_merged.columns:
            df_merged.drop(columns=['merge_key'], inplace=True)
            
        print(f"Salvando {len(df_merged)} contratos filtrados e consolidados...")
        df_merged.to_excel(OUTPUT_FILE, index=False)
        print(f"Arquivo salvo: {OUTPUT_FILE}")
        print("Sucesso.")
        
    except Exception as e:
        print(f"ERRO CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
