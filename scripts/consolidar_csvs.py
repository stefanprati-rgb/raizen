"""
Consolida todos os CSVs extraídos em um único arquivo para análise.
"""
import pandas as pd
from pathlib import Path
from datetime import datetime

def consolidar_csvs():
    output_dir = Path('output')
    
    print("=" * 70)
    print("CONSOLIDANDO CSVs EXTRAÍDOS")
    print("=" * 70)
    
    # Encontrar todos os CSVs de extração
    csv_files = list(output_dir.rglob('*_extraidos.csv'))
    print(f"\n📁 Encontrados {len(csv_files)} arquivos CSV")
    
    all_dfs = []
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file, sep=';', encoding='utf-8-sig')
            
            # Adicionar coluna de origem (pasta)
            df['pasta_origem'] = csv_file.parent.name
            df['arquivo_csv'] = csv_file.name
            
            all_dfs.append(df)
            print(f"   ✅ {csv_file.parent.name}: {len(df)} registros")
            
        except Exception as e:
            print(f"   ❌ Erro ao ler {csv_file}: {e}")
    
    if not all_dfs:
        print("\n❌ Nenhum CSV encontrado para consolidar.")
        return
    
    # Concatenar todos os DataFrames
    df_consolidado = pd.concat(all_dfs, ignore_index=True)
    
    # Reordenar colunas (colocar as mais importantes primeiro)
    colunas_prioritarias = [
        'razao_social', 'cnpj', 'num_instalacao', 'num_cliente',
        'distribuidora', 'participacao_percentual', 'duracao_meses',
        'data_adesao', 'representante_nome', 'email',
        'sic_ec_cliente', 'pasta_origem', 'caminho_completo'
    ]
    
    colunas_existentes = [c for c in colunas_prioritarias if c in df_consolidado.columns]
    outras_colunas = [c for c in df_consolidado.columns if c not in colunas_prioritarias]
    
    df_consolidado = df_consolidado[colunas_existentes + outras_colunas]
    
    # Salvar arquivo consolidado
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    output_file = output_dir / f'CONSOLIDADO_EXTRACOES_{timestamp}.csv'
    
    df_consolidado.to_csv(output_file, sep=';', index=False, encoding='utf-8-sig')
    
    print("\n" + "=" * 70)
    print(f"✅ CONSOLIDAÇÃO CONCLUÍDA!")
    print(f"   Arquivo: {output_file}")
    print(f"   Total de registros: {len(df_consolidado)}")
    print(f"   Colunas: {len(df_consolidado.columns)}")
    print("=" * 70)
    
    # Mostrar resumo por distribuidora
    print("\n📊 RESUMO POR DISTRIBUIDORA:")
    if 'distribuidora' in df_consolidado.columns:
        resumo = df_consolidado['distribuidora'].value_counts()
        for dist, count in resumo.items():
            print(f"   - {dist}: {count}")
    
    return output_file

if __name__ == "__main__":
    consolidar_csvs()
