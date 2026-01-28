import pandas as pd

# Correct paths based on script output
files = [
    r"c:\Projetos\Raizen\output\enrichment\ERROS_CADASTRO_ENRICHED_FULL.xlsx",
    r"c:\Projetos\Raizen\output\enrichment\ERROS_CADASTRO_RAIZEN_1_ENRICHED.xlsx"
]

for f in files:
    try:
        df = pd.read_excel(f)
        print(f"\n>>> Analyzing: {f}")
        print(f"Total Rows: {len(df)}")
        
        # Check if API_CEP exists and has data
        if 'API_CEP' in df.columns:
            filled_api = df['API_CEP'].notna().sum()
            print(f"API_CEP Populated Count: {filled_api} / {len(df)}")
            
            if filled_api > 0:
                print("Sample API_CEP:", df[df['API_CEP'].notna()]['API_CEP'].head().tolist())
        else:
            print("Column 'API_CEP' NOT FOUND!")

        # Check EFFECTIVE missing (Neither Base nor API)
        has_base = df['BASE_CEP'].notna() if 'BASE_CEP' in df.columns else False
        has_api = df['API_CEP'].notna() if 'API_CEP' in df.columns else False
        
        # If column missing, treat as all False
        if not isinstance(has_base, pd.Series): has_base = pd.Series([False]*len(df))
        if not isinstance(has_api, pd.Series): has_api = pd.Series([False]*len(df))
        
        fully_enriched = (has_base | has_api).sum()
        print(f"Effective Enriched (Base OR API): {fully_enriched} / {len(df)}")
        
    except FileNotFoundError:
        print(f"File not found: {f}")
    except Exception as e:
        print(f"Error reading {f}: {e}")
