import pandas as pd
from pathlib import Path
import re

INPUT_CSV = Path("C:/Projetos/Raizen/output/GOLDEN_DATASET_REFINED.csv")
OUTPUT_EXCEL = Path("C:/Projetos/Raizen/output/DATASET_FINAL_GOLDEN_RAIZEN_EXPLODED.xlsx")

def clean_val(val):
    if pd.isna(val) or str(val).lower() in ['nan', 'none', 'null']:
        return ""
    return str(val).strip()

def split_vals(val):
    # Split by semicolon, comma or newline
    # But usually semicolon based on prompts
    if not val:
        return []
    # Replace common separators with unique one then split
    cleaned = str(val).replace('\n', ';').replace(',', ';')
    parts = [p.strip() for p in cleaned.split(';') if p.strip()]
    return parts

def main():
    print("="*60)
    print("EXPLODING DATASET (Separating Multi-UC rows)")
    print("="*60)

    if not INPUT_CSV.exists():
        print(f"❌ Input not found: {INPUT_CSV}")
        return

    df = pd.read_csv(INPUT_CSV, sep=";", dtype=str)
    print(f"Original Rows: {len(df)}")

    new_rows = []

    for idx, row in df.iterrows():
        # Get raw values
        raw_inst = clean_val(row.get('num_instalacao'))
        raw_cli = clean_val(row.get('num_cliente'))
        
        # Split
        inst_list = split_vals(raw_inst)
        cli_list = split_vals(raw_cli)
        
        # Calculate max expansion needed
        n_inst = len(inst_list)
        n_cli = len(cli_list)
        max_len = max(n_inst, n_cli, 1) # At least 1 row
        
        base_row = row.to_dict()
        
        for i in range(max_len):
            new_row = base_row.copy()
            
            # Resolve Installation
            if i < n_inst:
                new_row['num_instalacao'] = inst_list[i]
            else:
                # If we ran out of UCs but have more clients, what to do?
                # Usually repeat the last one OR empty?
                # Case: 1 Inst, 3 Clients -> Repeat Inst? Unlikely.
                # Case: 3 Inst, 1 Client -> Repeat Client.
                # Let's assume Repeat Logic for the "Single" side
                if n_inst == 1:
                    new_row['num_instalacao'] = inst_list[0]
                else:
                    new_row['num_instalacao'] = "" # Or keep empty
            
            # Resolve Client
            if i < n_cli:
                new_row['num_cliente'] = cli_list[i]
            else:
                if n_cli == 1:
                    new_row['num_cliente'] = cli_list[0]
                else:
                    new_row['num_cliente'] = ""

            new_rows.append(new_row)

    df_exploded = pd.DataFrame(new_rows)
    print(f"Exploded Rows: {len(df_exploded)} (Added {len(df_exploded) - len(df)})")
    
    # Schema Final Cleaning
    col_map = {
        "num_instalacao": "UC / Instalação",
        "num_cliente": "Número do Cliente",
        "distribuidora": "Distribuidora",
        "razao_social": "Razão Social",
        "cnpj": "CNPJ",
        "data_adesao": "Data de Adesão",
        "fidelidade": "Fidelidade",
        "aviso_previo": "Aviso Prévio (Dias)",
        "representante_nome": "Representante Legal",
        "representante_cpf": "CPF Representante",
        "participacao_percentual": "Participação Contratada"
    }
    
    # Rename
    df_final = df_exploded.rename(columns=col_map)
    
    # Select Cols
    meta_cols = ["arquivo_origem", "status_proc", "score_confianca", "tipo_erro", "erro_detalhe"]
    final_ordered_cols = list(col_map.values()) + [c for c in meta_cols if c in df_final.columns]
    final_ordered_cols = [c for c in final_ordered_cols if c in df_final.columns]

    # Save
    df_final[final_ordered_cols].to_excel(OUTPUT_EXCEL, index=False)
    print(f"✅ Saved to: {OUTPUT_EXCEL}")

if __name__ == "__main__":
    main()
