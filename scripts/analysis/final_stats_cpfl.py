import pandas as pd
from pathlib import Path

CSV_PATH = Path('C:/Projetos/Raizen/output/datasets_consolidados/CPFL_PAULISTA/CPFL_PAULISTA.csv')

def main():
    if not CSV_PATH.exists():
        print("Arquivo não encontrado.")
        return

    df = pd.read_csv(CSV_PATH, sep=';', low_memory=False)
    total = len(df)
    
    campos_criticos = [
        "num_instalacao",          # 1
        "num_cliente",             # 2
        "distribuidora",           # 3
        "razao_social",            # 4
        "cnpj",                    # 5
        "data_adesao",             # 6
        "fidelidade",              # 7 (Ausente no CSV atual?)
        "aviso_previo",            # 8 (aviso_previo_dias)
        "representante_nome",      # 9
        "representante_cpf",       # 10
        "participacao_percentual"  # 11
    ]
    
    print("### Estatísticas Finais de Extração (CPFL Paulista)")
    print(f"**Total de Documentos:** {total}\n")
    
    print("| Campo | Preenchidos | % Completo | Vazios |")
    print("|-------|-------------|------------|--------|")
    
    for campo in campos_criticos:
        if campo in df.columns:
            filled = df[campo].notna().sum()
            # Tratar strings vazias como NaN se houver
            if df[campo].dtype == object:
                filled = df[campo].replace(r'^\s*$', pd.NA, regex=True).notna().sum()
                
            pct = (filled / total) * 100
            empty = total - filled
            print(f"| `{campo}` | {filled} | **{pct:.1f}%** | {empty} |")
            
    print("\n*Dados processados via Regex + Turbo IA (Gemini 2.5 Flash Lite)*")

if __name__ == "__main__":
    main()
