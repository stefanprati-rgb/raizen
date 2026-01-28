"""
Re-processar os 85 arquivos vazios com V5 atualizado e gerar patch.
"""
import sys
sys.path.insert(0, 'scripts')

import json
from pathlib import Path
from uc_extractor_v5 import UCExtractorV5

V5_RESULTS_PATH = Path('output/cpfl_paulista_final/cpfl_v5_full_results.json')
OUTPUT_PATCH = Path('output/cpfl_paulista_final/patch_ucs_curtas.json')

def main():
    print("Carregando resultados V5...")
    with open(V5_RESULTS_PATH, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    # Filtrar vazios
    empty_docs = [r for r in results if r['status'] == 'VAZIO']
    print(f"Total vazios: {len(empty_docs)}")
    
    extractor = UCExtractorV5(use_dynamic_blacklist=False)
    
    patch = []
    success = 0
    still_empty = 0
    
    for i, doc in enumerate(empty_docs, 1):
        path = doc['path']
        
        if not Path(path).exists():
            print(f"[{i}/{len(empty_docs)}] Arquivo não encontrado: {path}")
            continue
        
        # Re-extrair com V5 atualizado
        result = extractor.extract_from_pdf(path)
        
        if result.uc_count > 0:
            patch.append({
                'path': path,
                'file': result.file,
                'type': doc['type'],
                'folder': doc['folder'],
                'ucs': result.ucs,
                'uc_count': result.uc_count,
                'method': result.method
            })
            success += 1
            print(f"[{i}/{len(empty_docs)}] RECUPERADO: {result.file[:40]}... ({result.uc_count} UCs)")
        else:
            still_empty += 1
    
    print()
    print("=" * 60)
    print(f"RESULTADO:")
    print(f"  Recuperados: {success}")
    print(f"  Ainda vazios: {still_empty}")
    print(f"  Total processado: {success + still_empty}")
    
    # Salvar patch
    with open(OUTPUT_PATCH, 'w', encoding='utf-8') as f:
        json.dump(patch, f, ensure_ascii=False, indent=2)
    
    print(f"\nPatch salvo em: {OUTPUT_PATCH}")
    
    if patch:
        print(f"\nExemplos de UCs recuperadas:")
        for p in patch[:5]:
            print(f"  - {p['file'][:40]}: {p['ucs']}")

if __name__ == "__main__":
    main()
