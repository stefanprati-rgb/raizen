import pandas as pd
from pathlib import Path

INPUT_PATH = Path('output/cpfl_paulista_final/cpfl_dataset_v5_updated.xlsx')
OUTPUT_PATH = Path('output/cpfl_paulista_final/cpfl_dataset_v5_exploded.xlsx')

def main():
    print(f"Loading {INPUT_PATH}...")
    try:
        df = pd.read_excel(INPUT_PATH)
    except Exception as e:
        print(f"Error loading file: {e}")
        return

    print(f"Original shape: {df.shape}")
    
    new_rows = []
    
    for index, row in df.iterrows():
        uc_val = str(row.get('UC', ''))
        
        # Check if we have multiple UCs
        if ';' in uc_val:
            ucs = [u.strip() for u in uc_val.split(';') if u.strip()]
            for uc in ucs:
                new_row = row.copy()
                new_row['UC'] = uc
                # Also ensure duplicate columns are synced if they exist
                if 'Nº Instalação' in df.columns:
                     new_row['Nº Instalação'] = uc
                if 'Nº Conta Contrato (UC)' in df.columns:
                     new_row['Nº Conta Contrato (UC)'] = uc
                     
                new_rows.append(new_row)
        else:
            new_rows.append(row)
            
    # Create new DataFrame
    df_exploded = pd.DataFrame(new_rows)
    
    print("-" * 30)
    print(f"New shape: {df_exploded.shape}")
    print(f"Rows added: {len(df_exploded) - len(df)}")
    print("-" * 30)
    
    print(f"Saving to {OUTPUT_PATH}...")
    df_exploded.to_excel(OUTPUT_PATH, index=False)
    print("Done!")

if __name__ == "__main__":
    main()
