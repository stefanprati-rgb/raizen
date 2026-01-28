import pandas as pd
import sys
import os
import re

# Add src to path
sys.path.append(os.path.abspath(r"c:\Projetos\Raizen\src"))
from raizen_power.utils.text_sanitizer import NoiseFilter

file_path = r"c:\Projetos\Raizen\output\enrichment\ERROS_CADASTRO_RAIZEN_1.xlsx"

try:
    # Read carefully to avoid float issues
    df = pd.read_excel(file_path)
    id_col = 'CNPJ_CLEAN' if 'CNPJ_CLEAN' in df.columns else 'CNPJ'
    df = pd.read_excel(file_path, dtype={id_col: str})
    
    # Identificar coluna de ID
    id_col = 'CNPJ_CLEAN' if 'CNPJ_CLEAN' in df.columns else 'CNPJ'
    print(f"Usando coluna de ID: {id_col}")
    
    # Filter only those we repaired
    repaired_df = df[df['VALIDACAO_ID'].str.contains('REPARADO', na=False)].copy()
    
    print(f"Total registros reparados: {len(repaired_df)}")
    
    def verify_dv(row):
        # Convert to clean digits string
        val = str(row[id_col])
        if 'e+' in val.lower(): # scientific notation
            val = f"{float(val):.0f}"
        clean = re.sub(r'\D', '', val)
        
        status = str(row['VALIDACAO_ID'])
        
        if 'CNPJ' in status:
            return NoiseFilter.is_valid_cnpj(clean.zfill(14))
        else:
            return NoiseFilter.is_valid_cpf(clean.zfill(11))

    repaired_df['DV_VERIFICADO'] = repaired_df.apply(verify_dv, axis=1)
    
    success_count = repaired_df['DV_VERIFICADO'].sum()
    fail_count = len(repaired_df) - success_count
    
    print(f"Dígitos Verificadores CORRETOS: {success_count}")
    print(f"Dígitos Verificadores INCORRETOS: {fail_count}")
    
    if fail_count > 0:
        print("\nExemplos de falhas:")
        print(repaired_df[repaired_df['DV_VERIFICADO'] == False][['UC', id_col, 'VALIDACAO_ID']].head())
    else:
        print("\n✅ Todos os registros marcados como 'REPARADO' possuem Dígitos Verificadores 100% válidos.")

except Exception as e:
    print(f"Erro: {e}")
