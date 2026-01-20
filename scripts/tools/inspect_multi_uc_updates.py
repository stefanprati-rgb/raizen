import pandas as pd

file_path = 'output/cpfl_paulista_final/cpfl_dataset_v5_updated.xlsx'
print(f"Loading {file_path}...")

try:
    df = pd.read_excel(file_path)
    
    # Filter rows with multiple UCs (containing ';')
    # We need to handle non-string values just in case
    multi_uc_df = df[df['UC'].astype(str).str.contains(';', na=False)]
    
    print(f"Total rows: {len(df)}")
    print(f"Rows with Multi-UCs: {len(multi_uc_df)}")
    print("-" * 40)
    
    if not multi_uc_df.empty:
        print("Examples of Multi-UC updates:")
        # Select relevant columns for display
        cols = ['Arquivo', 'Numero do Cliente', 'UC', 'Status']
        # If 'Numero do Cliente' not present/empty try 'Nº Cliente'
        if 'Numero do Cliente' not in df.columns:
             cols = ['Arquivo', 'Nº Cliente', 'UC', 'Status']
             
        # Take first 5 examples
        for idx, row in multi_uc_df.head(5).iterrows():
            print(f"\nRow {idx}:")
            print(f"  Arquivo: {row.get('Arquivo')}")
            print(f"  Cliente: {row.get(cols[1])}")
            print(f"  UCs: {row.get('UC')}")
    else:
        print("No rows found with ';' separator in 'UC' column.")

except Exception as e:
    print(f"Error: {e}")
