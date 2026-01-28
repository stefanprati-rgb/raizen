import pandas as pd
import os
import sys

# Configura saída UTF-8 para Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

FILES = {
    "ORIGINAL": r"C:\Projetos\Raizen\docs\ERROS cadastros RAIZEN.xlsx",
    "SCRIPT_V4": r"C:\Projetos\Raizen\docs\ERROS_COM_ENDERECO_FINAL_V4.xlsx",
    "SCRIPT_V5": r"C:\Projetos\Raizen\docs\ERROS_COM_ENDERECO_FINAL_V5.xlsx",
    "CEP_OUTPUT": r"C:\Projetos\Raizen\output\CEP.xlsx"
}

def analyze_file(name, path):
    if not os.path.exists(path):
        print(f"❌ {name}: Arquivo não encontrado em {path}")
        return None
    
    try:
        df = pd.read_excel(path)
    except Exception as e:
        print(f"❌ {name}: Erro ao ler ({e})")
        return None

    total = len(df)
    
    # Colunas de interesse para verificar preenchimento
    cols_check = ['FOUND_CEP', 'FOUND_LOGRADOURO', 'FOUND_CIDADE', 'FOUND_UF']
    
    # Adiciona colunas que não existem como 100% missing
    for col in cols_check:
        if col not in df.columns:
            df[col] = None
            
    stats = {'Total': total}
    
    # Conta nulos (Missing)
    for col in cols_check:
        missing = df[col].isnull().sum()
        stats[f"Sem {col}"] = missing
        
    # Critério: Sem Endereço Completo (CEP ou Logradouro faltando)
    sem_endereco = df[df['FOUND_CEP'].isnull() & df['FOUND_LOGRADOURO'].isnull()].shape[0]
    stats['Sem CEP E Logradouro'] = sem_endereco
    
    return stats

results = []
for name, path in FILES.items():
    stats = analyze_file(name, path)
    if stats:
        stats['Arquivo'] = name
        results.append(stats)

if results:
    df_res = pd.DataFrame(results)
    # Reordena colunas
    cols = ['Arquivo', 'Total', 'Sem FOUND_CEP', 'Sem FOUND_LOGRADOURO', 'Sem CEP E Logradouro']
    # Adiciona colunas extras se existirem
    cols += [c for c in df_res.columns if c not in cols]
    
    print("\n📊 RELATÓRIO DE PREENCHIMENTO:\n")
    print(df_res[cols].to_markdown(index=False))
else:
    print("Nenhum arquivo analisado com sucesso.")
