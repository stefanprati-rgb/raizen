"""
Gera amostra estratificada para validação manual da extração.
"""
import pandas as pd
from pathlib import Path
import random

def gerar_amostra_validacao():
    # Carregar arquivo da outra equipe
    df = pd.read_excel('extracao-termos.xlsx')
    
    print("=" * 70)
    print("GERAÇÃO DE AMOSTRA PARA VALIDAÇÃO")
    print("=" * 70)
    print(f"\nTotal de registros disponíveis: {len(df)}")
    
    # Identificar distribuidoras principais
    dist_counts = df['Distribuidora'].value_counts()
    print(f"\nDistribuidoras encontradas: {len(dist_counts)}")
    print("\nTop 10 distribuidoras:")
    print(dist_counts.head(10).to_string())
    
    # Selecionar amostra estratificada
    amostra_registros = []
    
    # Pegar 10 registros de cada uma das 5 maiores distribuidoras
    top_distribuidoras = dist_counts.head(5).index.tolist()
    
    for dist in top_distribuidoras:
        subset = df[df['Distribuidora'] == dist]
        n_amostras = min(10, len(subset))
        amostras = subset.sample(n_amostras, random_state=42)
        amostra_registros.append(amostras)
        print(f"\n  ✓ {dist}: {n_amostras} amostras selecionadas")
    
    # Concatenar amostras
    df_amostra = pd.concat(amostra_registros, ignore_index=True)
    
    # Adicionar colunas de validação
    df_amostra['VALIDACAO_UC'] = ''
    df_amostra['VALIDACAO_CNPJ'] = ''
    df_amostra['VALIDACAO_RAZAO'] = ''
    df_amostra['VALIDACAO_DATA'] = ''
    df_amostra['OBSERVACOES'] = ''
    
    # Salvar arquivo
    output_file = Path('output/amostra_validacao_50.xlsx')
    df_amostra.to_excel(output_file, index=False)
    
    print("\n" + "=" * 70)
    print(f"✅ Amostra gerada: {output_file}")
    print(f"   Total de registros na amostra: {len(df_amostra)}")
    print("\nINSTRUÇÕES:")
    print("1. Abra o arquivo Excel gerado")
    print("2. Para cada registro, localize o PDF original (coluna 'Arquivo Original')")
    print("3. Verifique se UC, CNPJ, Razão Social e Data estão corretos")
    print("4. Preencha as colunas VALIDACAO_* com: OK, PARCIAL ou ERRO")
    print("5. Use a coluna OBSERVACOES para notas")
    print("=" * 70)
    
    return df_amostra

if __name__ == "__main__":
    gerar_amostra_validacao()
