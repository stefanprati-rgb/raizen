"""
Comparar colunas do dataset CPFL com o schema obrigatório do projeto.
"""
import pandas as pd
from pathlib import Path

DATASET_PATH = Path('output/cpfl_paulista_final/cpfl_dataset_v5_exploded.xlsx')

# Schema obrigatório do projeto (projeto_raizen.md)
SCHEMA_OBRIGATORIO = {
    'num_instalacao': ['UC', 'Nº Instalação', 'Nº Conta Contrato (UC)'],
    'num_cliente': ['Numero do Cliente', 'Nº Cliente'],
    'distribuidora': ['Distribuidora'],
    'razao_social': ['Razao Social', 'Razão Social'],
    'cnpj': ['CNPJ'],
    'data_adesao': ['Data de Adesão', 'Data Adesão', 'Data de Assinatura'],
    'fidelidade': ['Fidelidade', 'Período Fidelidade'],
    'aviso_previo_dias': ['Aviso Prévio', 'Aviso Previo Dias'],
    'representante_nome': ['Representante', 'Representante Legal'],
    'representante_cpf': ['CPF Representante', 'CPF'],
    'participacao_percentual': ['Participação', 'Participação Contratada', 'Desconto', 'Cotas']
}

def main():
    print("Carregando dataset CPFL...")
    df = pd.read_excel(DATASET_PATH)
    
    output_file = Path('output/schema_report.txt')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Total de linhas: {len(df)}\n")
        f.write(f"Total de colunas: {len(df.columns)}\n\n")
        
        f.write("=" * 70 + "\n")
        f.write("COLUNAS EXISTENTES NO DATASET:\n")
        f.write("=" * 70 + "\n")
        for col in df.columns:
            f.write(f"  - {col}\n")
        f.write("\n")
        
        f.write("=" * 70 + "\n")
        f.write("ANÁLISE DE COBERTURA vs SCHEMA OBRIGATÓRIO:\n")
        f.write("=" * 70 + "\n")
        
        cobertura = {}
        for campo_schema, possiveis_colunas in SCHEMA_OBRIGATORIO.items():
            encontrado = False
            coluna_usada = None
            preenchimento = 0
            
            for col_nome in possiveis_colunas:
                if col_nome in df.columns:
                    encontrado = True
                    coluna_usada = col_nome
                    preenchimento = (df[col_nome].notna() & (df[col_nome] != '')).sum() / len(df) * 100
                    break
            
            cobertura[campo_schema] = {
                'encontrado': encontrado,
                'coluna': coluna_usada,
                'preenchimento': preenchimento
            }
            
            status = "✓" if encontrado else "✗"
            if encontrado:
                f.write(f"{status} {campo_schema:<25} -> '{coluna_usada}' ({preenchimento:.1f}% preenchido)\n")
            else:
                f.write(f"{status} {campo_schema:<25} -> NÃO ENCONTRADO\n")
        
        f.write("\n")
        f.write("=" * 70 + "\n")
        f.write("RESUMO:\n")
        f.write("=" * 70 + "\n")
        
        campos_ok = sum(1 for c in cobertura.values() if c['encontrado'])
        campos_total = len(SCHEMA_OBRIGATORIO)
        f.write(f"Campos encontrados: {campos_ok}/{campos_total}\n\n")
        
        faltantes = [k for k, v in cobertura.items() if not v['encontrado']]
        if faltantes:
            f.write("CAMPOS FALTANTES (precisam ser extraídos):\n")
            for fal in faltantes:
                f.write(f"  ❌ {fal}\n")
        
        f.write("\nCAMPOS COM BAIXO PREENCHIMENTO (<50%):\n")
        for campo, info in cobertura.items():
            if info['encontrado'] and info['preenchimento'] < 50:
                f.write(f"  ⚠️ {campo}: {info['preenchimento']:.1f}%\n")
                
        f.write("\n")
        f.write("=" * 70 + "\n")
        f.write("AMOSTRA DE DADOS (primeiras 3 linhas):\n")
        f.write("=" * 70 + "\n")
        sample_cols = [info['coluna'] for info in cobertura.values() if info['coluna']]
        f.write(df[sample_cols].head(3).to_string())
        
    print(f"Relatório salvo em {output_file}")

if __name__ == "__main__":
    main()
