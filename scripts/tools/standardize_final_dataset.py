import pandas as pd
from pathlib import Path

CSV_PATH = Path("C:/Projetos/Raizen/output/datasets_consolidados/CPFL_PAULISTA/CPFL_PAULISTA.csv")
TARGET_XLSX = Path("C:/Projetos/Raizen/output/datasets/cpfl/dataset_CPFL_PAULISTA_ENTREGA_OFICIAL.xlsx")

# Mapeamento: Nome no CSV -> Nome no Entregável Oficial
COLUNAS_OFICIAIS = {
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

def main():
    print(f"Lendo {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH, sep=";", low_memory=False)
    
    # Criar colunas faltantes se não existirem (para não quebrar)
    for col in COLUNAS_OFICIAIS.keys():
        if col not in df.columns:
            print(f"Aviso: Coluna '{col}' não encontrada, criando vazia.")
            df[col] = None

    # Selecionar e Reordenar
    df_final = df[list(COLUNAS_OFICIAIS.keys())].copy()
    
    # Renomear
    df_final.rename(columns=COLUNAS_OFICIAIS, inplace=True)
    
    print("Colunas finais:")
    print(df_final.columns.tolist())
    
    print(f"Salvando Excel oficial em {TARGET_XLSX}...")
    df_final.to_excel(TARGET_XLSX, index=False)
    print("Sucesso!")

if __name__ == "__main__":
    main()
