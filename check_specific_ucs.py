import pandas as pd
import numpy as np

ucs_to_check = [
    11133155, 33215340, 37135120, 33771383, 2055880, 13604325, 11133163, 
    10350306, 30862108, 742341, 742350, 83973605, 411290256, 414496590, 
    58319271, 411305830, 410229456, 412446273, 413526465, 420297039, 
    1793501, 3176151, 3002037796, 3007304806, 3000939808
]

files = [
    r"c:\Projetos\Raizen\output\enrichment\ERROS_CADASTRO_ENRICHED_FULL.xlsx",
    r"c:\Projetos\Raizen\output\enrichment\ERROS_CADASTRO_RAIZEN_1.xlsx"
]

results = []

def clean_uc(val):
    try:
        return str(int(float(val))).strip()
    except:
        return str(val).strip()

ucs_to_check_str = [clean_uc(u) for u in ucs_to_check]

for f in files:
    try:
        df = pd.read_excel(f)
        df['UC_CLEAN'] = df['UC'].apply(clean_uc)
        
        found = df[df['UC_CLEAN'].isin(ucs_to_check_str)]
        if not found.empty:
            for _, row in found.iterrows():
                # Check completeness
                addr_cols = ['FINAL_LOGRADOURO', 'FINAL_CIDADE', 'FINAL_UF', 'FINAL_CEP']
                is_complete = all(pd.notna(row.get(c)) for c in addr_cols)
                
                results.append({
                    "UC": row['UC'],
                    "Arquivo": f.split('\\')[-1],
                    "Status": row.get('STATUS_ENRIQUECIMENTO', 'N/A'),
                    "Completo": "SIM" if is_complete else "NÃO",
                    "Faltando": [c for c in addr_cols if pd.isna(row.get(c))]
                })
    except Exception as e:
        print(f"Erro ao ler {f}: {e}")

report = pd.DataFrame(results)
report.to_csv("uc_check_results.csv", index=False)
with open("uc_check_full.txt", "w") as f_out:
    f_out.write(report.to_string())
print("Results saved to uc_check_full.txt")
