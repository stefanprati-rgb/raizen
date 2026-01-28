"""
Aplicar patch de UCs recuperadas ao dataset explodido.
"""
import pandas as pd
import json
from pathlib import Path

DATASET_PATH = Path('output/cpfl_paulista_final/cpfl_dataset_v5_exploded.xlsx')
PATCH_PATH = Path('output/cpfl_paulista_final/patch_ucs_curtas.json')
OUTPUT_PATH = Path('output/cpfl_paulista_final/cpfl_dataset_v5_final.xlsx')

def main():
    print("Carregando dataset...")
    df = pd.read_excel(DATASET_PATH)
    print(f"Linhas originais: {len(df)}")
    
    print("Carregando patch...")
    with open(PATCH_PATH, 'r', encoding='utf-8') as f:
        patch = json.load(f)
    
    print(f"Registros no patch: {len(patch)}")
    
    # Criar índice por arquivo
    df_index = df.set_index('Arquivo', drop=False) if 'Arquivo' in df.columns else None
    
    new_rows = []
    updated = 0
    added = 0
    
    for p in patch:
        filename = p['file']
        ucs = p['ucs']
        
        # Verificar se já existe no dataset
        if 'Arquivo' in df.columns:
            mask = df['Arquivo'] == filename
            existing = df[mask]
        else:
            existing = pd.DataFrame()
        
        if len(existing) > 0:
            # Atualizar registros existentes
            # Para cada UC no patch, verificar se já existe
            for uc in ucs:
                uc_exists = ((df['Arquivo'] == filename) & (df['UC'].astype(str) == str(uc))).any()
                if not uc_exists:
                    # Clonar primeira linha existente e atualizar UC
                    new_row = existing.iloc[0].copy()
                    new_row['UC'] = uc
                    new_row['Status'] = 'RECUPERADO_V5'
                    if 'Nº Instalação' in df.columns:
                        new_row['Nº Instalação'] = uc
                    if 'Nº Conta Contrato (UC)' in df.columns:
                        new_row['Nº Conta Contrato (UC)'] = uc
                    new_rows.append(new_row)
                    added += 1
        else:
            # Não existe - criar novos registros
            for uc in ucs:
                new_row = {
                    'Arquivo': filename,
                    'UC': uc,
                    'Tipo': p.get('type', ''),
                    'Pasta': p.get('folder', ''),
                    'Status': 'NOVO_V5',
                    'Distribuidora': 'CPFL PAULISTA'
                }
                new_rows.append(pd.Series(new_row))
                added += 1
    
    print(f"Novas linhas a adicionar: {added}")
    
    # Adicionar novas linhas
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        df = pd.concat([df, new_df], ignore_index=True)
    
    print(f"Linhas finais: {len(df)}")
    
    # Salvar
    print(f"Salvando em {OUTPUT_PATH}...")
    df.to_excel(OUTPUT_PATH, index=False)
    print("Concluído!")
    
    # Estatísticas finais
    print()
    print("=" * 50)
    print("ESTATÍSTICAS FINAIS:")
    print(f"  Total de linhas: {len(df)}")
    print(f"  UCs únicas: {df['UC'].nunique()}")
    print(f"  Arquivos únicos: {df['Arquivo'].nunique() if 'Arquivo' in df.columns else 'N/A'}")

if __name__ == "__main__":
    main()
