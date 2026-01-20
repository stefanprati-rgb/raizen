"""
Padronizar colunas do dataset final CPFL conforme schema obrigatório.
"""
import pandas as pd
from pathlib import Path

INPUT_PATH = Path('output/cpfl_paulista_final/cpfl_dataset_v5_exploded.xlsx')
OUTPUT_PATH = Path('output/cpfl_paulista_final/cpfl_dataset_final_padronizado.xlsx')

# Mapeamento: Nome Atual -> Nome Schema Obrigatório
COLUMN_MAPPING = {
    'UC': 'num_instalacao',
    'Numero do Cliente': 'num_cliente',
    'Distribuidora': 'distribuidora',
    'Razao Social': 'razao_social',
    'CNPJ': 'cnpj',
    'Data de Adesao': 'data_adesao',
    'Data Adesão': 'data_adesao',  # Fallback
    'Fidelidade': 'fidelidade',
    'Aviso previo': 'aviso_previo_dias',
    'Representante Legal': 'representante_nome',
    'Nome Representante': 'representante_nome', # Fallback
    'CPF Representante': 'representante_cpf',
    'Participacao Contratada': 'participacao_percentual',
    'Arquivo Original': 'nome_arquivo_origem',
    'Pasta': 'pasta_origem'
}

def main():
    print("Carregando dataset...")
    df = pd.read_excel(INPUT_PATH)
    print(f"Colunas originais: {df.columns.tolist()}")
    
    # Normalizar nomes atuais (remover espaços extras, acentos se necessário)
    # Por enquanto vamos usar o mapping direto
    
    # Renomear colunas
    df_renamed = df.rename(columns=COLUMN_MAPPING)
    
    # Manter apenas colunas do schema + úteis
    cols_to_keep = [
        'num_instalacao', 'num_cliente', 'distribuidora', 'razao_social', 'cnpj',
        'data_adesao', 'fidelidade', 'aviso_previo_dias', 'representante_nome', 
        'representante_cpf', 'participacao_percentual', 'nome_arquivo_origem', 'pasta_origem'
    ]
    
    # Garantir que todas existam (mesmo vazias)
    for col in cols_to_keep:
        if col not in df_renamed.columns:
            print(f"Criando coluna vazia faltante: {col}")
            df_renamed[col] = None
            
    # Reordenar
    df_final = df_renamed[cols_to_keep]
    
    print(f"\nColunas finais: {df_final.columns.tolist()}")
    
    print(f"Salvando em {OUTPUT_PATH}...")
    df_final.to_excel(OUTPUT_PATH, index=False)
    print("Dataset padronizado concluído!")

if __name__ == "__main__":
    main()
