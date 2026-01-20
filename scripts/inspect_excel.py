import pandas as pd
import json

file_path = 'output/cpfl_paulista_final/cpfl_dataset.xlsx'
try:
    df = pd.read_excel(file_path)
    print(f"File: {file_path}")
    print(f"Shape: {df.shape}")
    print("Columns:")
    for col in df.columns:
        print(f"  - {col}")
    
    print("\nFirst row sample:")
    print(df.iloc[0].to_dict())
except Exception as e:
    print(f"Error reading file: {e}")
