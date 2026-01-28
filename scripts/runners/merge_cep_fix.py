import pandas as pd
import sys
import os

# Configura saída UTF-8 para Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

FILE_V4 = r"C:\Projetos\Raizen\docs\ERROS_COM_ENDERECO_FINAL_V4.xlsx"
FILE_CEP = r"C:\Projetos\Raizen\output\CEP.xlsx"
FILE_V5 = r"C:\Projetos\Raizen\docs\ERROS_COM_ENDERECO_FINAL_V5.xlsx"

def main():
    print(f"📂 Lendo V4: {FILE_V4}")
    df_v4 = pd.read_excel(FILE_V4)
    
    print(f"📂 Lendo CEP: {FILE_CEP}")
    df_cep = pd.read_excel(FILE_CEP)
    
    # Normalização de Chaves (UC)
    # Remove .0 decimal se existir e converte para string limpa
    def clean_uc(val):
        if pd.isna(val): return None
        s = str(val).replace('.0', '').strip()
        return s if s else None

    df_v4['KEY_UC'] = df_v4['Unidade Consumidora'].apply(clean_uc)
    df_cep['KEY_UC'] = df_cep['UC'].apply(clean_uc)
    
    # Indexar CEP por UC para busca rápida
    # Se houver duplicatas no CEP.xlsx, pegamos o primeiro válido
    cep_lookup = df_cep.dropna(subset=['KEY_UC']).set_index('KEY_UC')
    
    print(f"🔍 Registros no V4: {len(df_v4)}")
    print(f"🔍 Registros no CEP.xlsx: {len(df_cep)}")
    print(f"🔍 UCs únicas no CEP lookup: {len(cep_lookup)}")
    
    # Contadores
    updated_count = 0
    
    # Iterar sobre V4 e preencher buracos
    for idx, row in df_v4.iterrows():
        # Só preenche se estiver faltando CEP ou Logradouro
        if pd.isna(row['FOUND_CEP']):
            uc_key = row['KEY_UC']
            
            if uc_key and uc_key in cep_lookup.index:
                match = cep_lookup.loc[uc_key]
                
                # Se houver duplicidade de chave no lookup (retorna DataFrame), pegar a primeira série
                if isinstance(match, pd.DataFrame):
                    match = match.iloc[0]
                
                # Mapeamento
                # FOUND_CEP <- cep
                # FOUND_LOGRADOURO <- endereco_rua, numero, comp
                # FOUND_BAIRRO <- endereco_bairro
                # FOUND_CIDADE <- endereco_cidade
                # FOUND_UF <- endereco_estado
                
                new_cep = match.get('cep')
                rua = str(match.get('endereco_rua', ''))
                num = str(match.get('endereco_numero', ''))
                
                # Constrói logradouro
                if num and num != 'nan':
                    logradouro = f"{rua}, {num}"
                else:
                    logradouro = rua
                    
                new_bairro = match.get('endereco_bairro')
                new_cidade = match.get('endereco_cidade')
                new_uf = match.get('endereco_estado')
                
                # Aplica alterações
                if new_cep and str(new_cep) != 'nan':
                    df_v4.at[idx, 'FOUND_CEP'] = new_cep
                    df_v4.at[idx, 'FOUND_LOGRADOURO'] = logradouro.upper()
                    df_v4.at[idx, 'FOUND_BAIRRO'] = str(new_bairro).upper()
                    df_v4.at[idx, 'FOUND_CIDADE'] = str(new_cidade).upper()
                    df_v4.at[idx, 'FOUND_UF'] = str(new_uf).upper()
                    df_v4.at[idx, 'API_SOURCE'] = "CEP_XLSX_RECOVERY"
                    df_v4.at[idx, 'STATUS_API'] = "SUCESSO_RECOVERY"
                    
                    updated_count += 1

    # Remove coluna auxiliar
    df_v4.drop(columns=['KEY_UC'], inplace=True)
    
    print(f"✅ Atualizados {updated_count} registros com dados do CEP.xlsx")
    
    df_v4.to_excel(FILE_V5, index=False)
    print(f"💾 Salvo em: {FILE_V5}")

if __name__ == "__main__":
    main()
