import json
import sys
sys.path.insert(0, 'scripts')
from uc_extractor_robust_v3 import process_single_pdf

# Carregar dados de validacao
with open('output/validacao_gemini/validacao_dados.json', 'r', encoding='utf-8') as f:
    validation = json.load(f)

print('=== RE-TESTE V4 (com filtro Nr Cliente) ===')
print()

for v in validation[:10]:  # Rodada 1
    result = process_single_pdf(v['path_original'])
    
    old_ucs = set(v['ucs_extraidas'])
    new_ucs = set(result['ucs'])
    
    removed = old_ucs - new_ucs
    added = new_ucs - old_ucs
    
    print(f"{v['id']:02d}. {v['arquivo'][:40]}...")
    print(f"   V3: {len(old_ucs)} UCs -> V4: {len(new_ucs)} UCs")
    if removed:
        print(f"   Removidos: {removed}")
    if added:
        print(f"   Adicionados: {added}")
    print()
