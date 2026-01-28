import pandas as pd
from pathlib import Path

# Caminhos dos Datasets Finais
DATASETS = {
    "CPFL": "C:/Projetos/Raizen/output/datasets/cpfl/dataset_CPFL_PAULISTA_final.xlsx",
    "CEMIG": "C:/Projetos/Raizen/output/datasets/cemig/dataset_CEMIG_ENTREGA_OFICIAL.xlsx",
    "ELEKTRO": "C:/Projetos/Raizen/output/datasets/elektro/dataset_ELEKTRO_ENTREGA_OFICIAL.xlsx",
    "LIGHT": "C:/Projetos/Raizen/output/datasets/light/dataset_LIGHT_ENTREGA_OFICIAL.xlsx",
    "ENEL": "C:/Projetos/Raizen/output/datasets/enel/dataset_ENEL_ENTREGA_OFICIAL.xlsx",
    "OUTRAS": "C:/Projetos/Raizen/output/datasets/geral/dataset_GERAL_OUTRAS_ENTREGA.xlsx"
}

OUTPUT_MASTER = "C:/Projetos/Raizen/output/DATASET_MESTRE_RAIZEN_POWER_V3.xlsx"

def main():
    print("="*60)
    print("CONSOLIDAÇÃO MESTRE - RAIZEN POWER")
    print("="*60)
    
    master_df = pd.DataFrame()
    
    for name, path in DATASETS.items():
        p = Path(path)
        if p.exists():
            print(f"Lendo {name}...")
            try:
                df = pd.read_excel(p)
                df["ORIGEM_DATASET"] = name # Rastreabilidade
                master_df = pd.concat([master_df, df], ignore_index=True)
                print(f"  > +{len(df)} registros.")
            except Exception as e:
                print(f"  > Erro ao ler {name}: {e}")
        else:
            print(f"  > ⚠️ {name} não encontrado: {path}")

    # Limpeza final
    print("\nSalvando Arquivo Mestre...")
    master_df.to_excel(OUTPUT_MASTER, index=False)
    print(f"✅ SUCESSO! Arquivo Gerado: {OUTPUT_MASTER}")
    print(f"Total de Contratos Extraídos: {len(master_df)}")

if __name__ == "__main__":
    main()
