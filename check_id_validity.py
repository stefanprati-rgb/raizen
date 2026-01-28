import pandas as pd
import sys
import os
import re

# Add src to path to import TextSanitizer/NoiseFilter
sys.path.append(os.path.abspath(r"c:\Projetos\Raizen\src"))
from raizen_power.utils.text_sanitizer import NoiseFilter

files = [
    r"c:\Projetos\Raizen\output\enrichment\ERROS_CADASTRO_ENRICHED_FULL.xlsx",
    r"c:\Projetos\Raizen\output\enrichment\ERROS_CADASTRO_RAIZEN_1.xlsx"
]

all_invalid = []

def check_validity(val):
    if pd.isna(val): return "VAZIO"
    clean = re.sub(r'\D', '', str(val))
    if len(clean) == 11:
        return "VALIDO" if NoiseFilter.is_valid_cpf(clean) else "INVALIDO_CPF"
    elif len(clean) == 14:
        return "VALIDO" if NoiseFilter.is_valid_cnpj(clean) else "INVALIDO_CNPJ"
    elif len(clean) == 0:
        return "VAZIO"
    else:
        return f"TAMANHO_INVALIDO ({len(clean)})"

for f in files:
    try:
        df = pd.read_excel(f)
        df['VALIDACAO_ID'] = df['CNPJ'].apply(check_validity)
        
        invalid = df[df['VALIDACAO_ID'].str.contains("INVALIDO")]
        if not invalid.empty:
            for _, row in invalid.iterrows():
                all_invalid.append({
                    "Arquivo": f.split('\\')[-1],
                    "UC": row.get('UC'),
                    "ID_ORIGINAL": row.get('CNPJ'),
                    "ERRO": row['VALIDACAO_ID']
                })
    except Exception as e:
        print(f"Erro ao ler {f}: {e}")

report = pd.DataFrame(all_invalid)
if not report.empty:
    report.to_csv("invalid_ids_report.csv", index=False)
    print("IDs INVÁLIDOS ENCONTRADOS:")
    print(report.to_string())
else:
    print("Todos os CPFs/CNPJs verificados são VÁLIDOS (Checksum OK).")
