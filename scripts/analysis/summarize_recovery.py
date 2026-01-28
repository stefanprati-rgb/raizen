import pandas as pd
import os

path = r"c:\Projetos\Raizen\output\recovery\recovered_data_final.xlsx"
if os.path.exists(path):
    df = pd.read_excel(path)
    print(f"Total registros: {len(df)}")
    print("\nResumo por Status:")
    print(df['status'].value_counts())
    print("\nResumo por Método de Recuperação:")
    print(df['recuperado_por'].value_counts())
    
    # Mostrar alguns exemplos de sucesso
    sucesso = df[df['status'] == 'Sucesso']
    if not sucesso.empty:
        print("\nExemplos de Sucesso (primeiros 5):")
        cols = [c for c in ['UC', 'documento_corrigido', 'cep', 'cidade', 'recuperado_por'] if c in sucesso.columns]
        print(sucesso[cols].head(5))
else:
    print("Arquivo recovered_data_final.xlsx não encontrado.")
