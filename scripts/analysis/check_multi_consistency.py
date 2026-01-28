import pandas as pd
from pathlib import Path

INPUT_CSV = Path("C:/Projetos/Raizen/output/GOLDEN_DATASET_REFINED.csv")

def split_vals(val):
    if pd.isna(val) or str(val).lower() in ['nan', 'none', 'null', '']:
        return []
    cleaned = str(val).replace('\n', ';').replace(',', ';')
    return [p.strip() for p in cleaned.split(';') if p.strip()]

def main():
    print("="*60)
    print("CONSISTENCY CHECK: MULTI-VALUE ROWS (UC vs CLIENT)")
    print("="*60)

    df = pd.read_csv(INPUT_CSV, sep=";", dtype=str)
    
    multi_rows = []
    
    for idx, row in df.iterrows():
        uc_list = split_vals(row.get('num_instalacao'))
        cli_list = split_vals(row.get('num_cliente'))
        
        if len(uc_list) > 1 or len(cli_list) > 1:
            multi_rows.append({
                'idx': idx,
                'file': row.get('arquivo_origem'),
                'uc_count': len(uc_list),
                'cli_count': len(cli_list),
                'uc_vals': uc_list,
                'cli_vals': cli_list
            })
            
    print(f"Total Multi-Value Rows: {len(multi_rows)}")
    
    matched = 0
    mismatched = 0
    one_client_many_ucs = 0
    one_uc_many_clients = 0
    
    for m in multi_rows:
        if m['uc_count'] == m['cli_count']:
            matched += 1
        else:
            mismatched += 1
            if m['cli_count'] == 1 and m['uc_count'] > 1:
                one_client_many_ucs += 1
            elif m['uc_count'] == 1 and m['cli_count'] > 1:
                one_uc_many_clients += 1
            else:
                # Ex: 3 UCs and 2 Clients
                pass

    print(f"✅ Matched Counts (1:1): {matched} rows")
    print(f"⚠️ Mismatched Counts: {mismatched} rows")
    print(f"   - 1 Client / Many UCs (Common): {one_client_many_ucs}")
    print(f"   - 1 UC / Many Clients (Rare): {one_uc_many_clients}")
    print(f"   - Other Mismatches: {mismatched - one_client_many_ucs - one_uc_many_clients}")

    if mismatched > 0:
        print("\nExamples of Mismatches:")
        for m in multi_rows:
            if m['uc_count'] != m['cli_count']:
                 print(f"Line {m['idx']} ({m['file']}): {m['uc_count']} UCs vs {m['cli_count']} Clients")
                 print(f"   UCs: {m['uc_vals']}")
                 print(f"   Clis: {m['cli_vals']}")
                 print("-" * 20)
                 if mismatched > 5: break # limit output

if __name__ == "__main__":
    main()
