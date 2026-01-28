import pandas as pd
import json
from pathlib import Path
import os

# Configs
DATASET_PATH = Path('output/cpfl_paulista_final/cpfl_dataset.xlsx')
V5_RESULTS_PATH = Path('output/cpfl_paulista_final/cpfl_v5_full_results.json')
OUTPUT_PATH = Path('output/cpfl_paulista_final/cpfl_dataset_v5_updated.xlsx')

def normalize_filename(fname):
    """Normalize filename for matching."""
    return str(fname).strip().lower()

def main():
    print("Loading data...")
    
    # Load V5 Results
    with open(V5_RESULTS_PATH, 'r', encoding='utf-8') as f:
        v5_data = json.load(f)
    
    # Index V5 data by normalized filename
    v5_map = {}
    for r in v5_data:
        fname = normalize_filename(r['file'])
        v5_map[fname] = r
    
    print(f"Loaded {len(v5_data)} V5 records.")

    # Load Excel Dataset
    try:
        df = pd.read_excel(DATASET_PATH)
        print(f"Loaded Excel dataset with {len(df)} rows.")
    except Exception as e:
        print(f"Error loading Excel: {e}")
        return

    # Tracking stats
    updates_uc = 0
    updates_client = 0
    matches_found = 0
    
    # Iterate and Update
    # We will prioritize 'Arquivo Original' for matching, fallback to 'Arquivo'
    
    for index, row in df.iterrows():
        # Try to match
        match_key = None
        if pd.notna(row.get('Arquivo Original')):
            match_key = normalize_filename(row['Arquivo Original'])
        elif pd.notna(row.get('Arquivo')):
            match_key = normalize_filename(row['Arquivo'])
            
        if not match_key:
            continue
            
        # Try finding exact match or match contained in key
        v5_result = v5_map.get(match_key)
        
        # If not exact match, try fuzzy (sometimes excel has full path or slightly different name)
        if not v5_result:
            # Simple heuristic: is the key inside one of v5 keys?
            # This is slow O(N^2), maybe optimize if needed. For 4k rows it's okay.
             for k, v in v5_map.items():
                 if k in match_key or match_key in k:
                     v5_result = v
                     break
        
        if v5_result:
            matches_found += 1
            
            # --- UPDATE LOGIC ---
            
            # 1. Update UCs
            # Check if we have new UCs to add
            new_ucs = v5_result.get('ucs', [])
            if new_ucs:
                # Format strings
                new_ucs_str = "; ".join([str(u) for u in new_ucs])
                
                # If current UC is empty or just has less info, update it
                current_uc = str(row.get('UC', '')) if pd.notna(row.get('UC')) else ''
                current_inst = str(row.get('Nº Instalação', '')) if pd.notna(row.get('Nº Instalação')) else ''
                
                # Update logic: Always overwrite if we found something Valid in V5, 
                # assuming V5 is the latest and greatest truth.
                # But let's be careful not to overwrite valid data with empty if V5 failed (V5 empty is handled by if new_ucs check)
                
                df.at[index, 'UC'] = new_ucs_str
                # Also update other UC columns if they exist to keep consistency
                if 'Nº Instalação' in df.columns:
                     df.at[index, 'Nº Instalação'] = new_ucs_str
                if 'Nº Conta Contrato (UC)' in df.columns:
                     df.at[index, 'Nº Conta Contrato (UC)'] = new_ucs_str
                
                if current_uc != new_ucs_str:
                    updates_uc += 1

            # 2. Update Client Number
            # V5 doesn't explicitly extract separate client number in 'ucs' usually, 
            # unless we improved the logic to separate them.
            # Looking at V5 script, it extracts UCs. 
            # If the user rules say 'num_cliente' is important, we should check if V5 result has it.
            # The V5 result object stored in JSON has keys: "ucs", "uc_count", etc.
            # It DOES NOT seem to have a specific 'client_number' field in the root of the result dict in the snippet I read.
            # Wait, let's check the JSON content sample or script.
            # Script Line 29: returns "ucs", "uc_count". No explicit "client_number" in the return dict unless it's in ucs list?
            # AH, in the new V5 logic (DualExtractor), we might distinguish them?
            # Line 3037 in Agent.md mentions 'is_numero_cliente' logic.
            # But the OUTPUT dict in process_file_v5 only maps 'ucs'.
            
            # So V5 might actually be mixing UCs and Client Numbers if the regex caught them?
            # Or V5 is strictly UCs now.
            # If V5 is strictly UCs, we should NOT update Client Number with UCs.
            # However, looking at previous steps (Step 3442), Gemini analysis showed:
            # "numeros_cliente_ignorados": [],
            # The V5 extractor specifically TRIES to blacklist client numbers (70/71...).
            # So V5 results are purely UCs (Installations).
            # We should NOT overwrite Client Number with V5 UCs.
            # We should only update UC columns.
            
            # 3. Update Status and Info
            df.at[index, 'Status'] = v5_result['status']
            df.at[index, 'Tipo'] = v5_result['type']
            df.at[index, 'Pasta'] = v5_result['folder']
            
            # Update Distribuidora to CPFL PAULISTA if success
            if v5_result['status'] == 'SUCCESS':
                df.at[index, 'Distribuidora'] = 'CPFL PAULISTA'
            
    print("-" * 30)
    print(f"Matches found: {matches_found}/{len(df)}")
    print(f"UC Updates: {updates_uc}")
    print("-" * 30)
    
    # Save
    print(f"Saving to {OUTPUT_PATH}...")
    df.to_excel(OUTPUT_PATH, index=False)
    print("Done!")

if __name__ == "__main__":
    main()
