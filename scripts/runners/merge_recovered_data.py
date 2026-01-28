import pandas as pd
from pathlib import Path

def merge_recovered_data():
    project_root = Path(r"c:\Projetos\Raizen")
    dataset_path = project_root / "output" / "DATASET_FINAL_.xlsx"
    recovered_path = project_root / "output" / "recovery" / "recovered_data_final.xlsx"
    output_path = project_root / "output" / "DATASET_FINAL_RECUPERADO.xlsx"

    if not dataset_path.exists() or not recovered_path.exists():
        print("Arquivos necessários não encontrados.")
        return

    print("Carregando datasets...")
    df_main = pd.read_excel(dataset_path)
    df_rec = pd.read_excel(recovered_path)

    # Filtrar apenas sucessos
    df_rec_success = df_rec[df_rec['status'] == 'Sucesso'].copy()
    
    print(f"Total para atualizar: {len(df_rec_success)}")

    # Garantir que UC seja string para o merge
    df_main['UC_STR'] = df_main['UC / Instalação'].astype(str).str.strip()
    df_rec_success['UC_STR'] = df_rec_success['UC'].astype(str).str.strip()

    # Criar um dicionário de atualizações
    # Chave: UC_STR, Valor: dict com novos valores
    updates = {}
    for _, row in df_rec_success.iterrows():
        uc = row['UC_STR']
        updates[uc] = {
            'CNPJ': row.get('documento_corrigido'),
            'CEP': row.get('cep'),
            'Endereco': row.get('endereco_encontrado'),
            'Cidade': row.get('cidade'),
            'UF': row.get('uf')
        }

    count = 0
    for idx, row in df_main.iterrows():
        uc = row['UC_STR']
        if uc in updates:
            upd = updates[uc]
            
            # Atualizar CNPJ se estiver presente no update e não nulo
            if pd.notna(upd['CNPJ']):
                df_main.at[idx, 'CNPJ'] = upd['CNPJ']
            
            # Nota: O dataset original não parece ter colunas CEP, Cidade, UF separadas no schema padrão Raizen
            # (O schema Raizen pede: UC, Num Cliente, Distribuidora, Razao Social, CNPJ, Data Adesao, Fidelidade, Aviso Previo, Repres, CPF Reapres, Participacao)
            # Mas podemos adicionar essas informações se houver interesse ou atualizar a Razao Social se mudou.
            # O plano falava em "atualizar campos vazios".
            
            count += 1

    # Remover coluna auxiliar
    df_main = df_main.drop(columns=['UC_STR'])

    print(f"Total de linhas atualizadas: {count}")
    df_main.to_excel(output_path, index=False)
    print(f"Novo dataset salvo em: {output_path}")

if __name__ == "__main__":
    merge_recovered_data()
