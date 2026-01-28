import pandas as pd
from pathlib import Path

CSV_PATH = Path("C:/Projetos/Raizen/output/datasets_consolidados/CEMIG/CEMIG_FULL.csv")

def main():
    if not CSV_PATH.exists():
        print("Arquivo CSV não encontrado.")
        return

    df = pd.read_csv(CSV_PATH, sep=";", low_memory=False)
    total = len(df)
    
    campos_criticos = [
        "cnpj", "distribuidora", "num_instalacao", "num_cliente", "razao_social",
        "data_adesao", "fidelidade", "aviso_previo", 
        "representante_nome", "representante_cpf", "participacao_percentual"
    ]
    
    print("\n### Estatísticas Finais - CEMIG")
    print(f"**Total de Documentos:** {total}\n")
    print("| Campo | Preenchido | % Completo |")
    print("|-------|------------|------------|")
    
    for campo in campos_criticos:
        if campo in df.columns:
            filled = df[campo].notna().sum()
            # Tratar strings "null" ou vazias
            if df[campo].dtype == object:
                # Remove 'None', 'null' strings
                filled = df[campo].astype(str).replace(['None', 'null', 'nan'], pd.NA).notna().sum()
                
            pct = (filled / total) * 100
            print(f"| `{campo}` | {filled} | **{pct:.1f}%** |")
        else:
            print(f"| `{campo}` | 0 | 0.0% |")

if __name__ == "__main__":
    main()
