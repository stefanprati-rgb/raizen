import pandas as pd
from pathlib import Path

# Load dataset
FILE = Path("C:/Projetos/Raizen/output/DATASET_FINAL_GOLDEN_RAIZEN_EXPLODED.xlsx")

def main():
    if not FILE.exists():
        print(f"Arquivo não encontrado: {FILE}")
        print("Conteúdo da pasta output:")
        for f in FILE.parent.glob("*"):
            print(f" - {f.name}")
        return

    try:
        df = pd.read_excel(FILE)
        
        # Columns of interest
        cols = [
            'UC / Instalação', 'Número do Cliente', 'Distribuidora', 'Razão Social', 
            'CNPJ', 'Data de Adesão', 'Fidelidade', 'Aviso Prévio (Dias)', 
            'Representante Legal', 'CPF Representante', 'Participação Contratada'
        ]
        
        # Calculate completeness
        stats = {}
        for c in cols:
            if c in df.columns:
                non_null = df[c].notna() & (df[c].astype(str).str.strip() != "")
                pct = non_null.mean() * 100
                stats[c] = pct
        
        # Sort and print
        print("="*40)
        print("📊 COMPLETUDE DOS DADOS (%)")
        print("="*40)
        for k, v in sorted(stats.items(), key=lambda item: item[1]):
            print(f"{k}: {v:.2f}%")
            
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
