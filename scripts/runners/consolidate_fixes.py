import json
from pathlib import Path

# Caminhos
MERGED_JSON = Path("output/cpfl_paulista_final/cpfl_full_extraction_v6_merged.json")
REFINED_JSON = Path("output/cpfl_paulista_final/cpfl_full_extraction_v6_refinado.json")
OUTPUT_JSON = Path("output/cpfl_paulista_final/cpfl_full_extraction_v6_gold.json")

def consolidate():
    print(f"Lendo {MERGED_JSON}...")
    with open(MERGED_JSON, 'r', encoding='utf-8') as f:
        merged_data = {e['path']: e for e in json.load(f)}
        
    print(f"Lendo {REFINED_JSON}...")
    with open(REFINED_JSON, 'r', encoding='utf-8') as f:
        refined_data = {e['path']: e for e in json.load(f)}
        
    consolidated_list = []
    stats = {"names_recovered": 0, "installations_preserved": 0}
    
    print("Consolidando datasets...")
    for path, merged_entry in merged_data.items():
        refined_entry = refined_data.get(path)
        
        final_entry = merged_entry.copy()
        
        if refined_entry:
            merged_data_fields = merged_entry.get('data', {}) or {}
            refined_data_fields = refined_entry.get('data', {}) or {}
            
            # 1. Prioridade para Nome do Refinado (que usou Gemini Regex)
            ref_name = refined_data_fields.get('representante_nome')
            if ref_name and not merged_data_fields.get('representante_nome'):
                if final_entry.get('data') is None: final_entry['data'] = {}
                final_entry['data']['representante_nome'] = ref_name
                stats["names_recovered"] += 1
                
            # 2. Garantir Instalação do Merged (que estava boa)
            # (Já está em final_entry pois copiamos de merged_entry)
            if merged_data_fields.get('num_instalacao'):
                stats["installations_preserved"] += 1
                
        consolidated_list.append(final_entry)
        
    print(f"Salvando {OUTPUT_JSON}...")
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(consolidated_list, f, ensure_ascii=False, indent=2)
        
    print("\n=== ESTATÍSTICAS DE CONSOLIDAÇÃO ===")
    print(f"Total de Arquivos: {len(consolidated_list)}")
    print(f"Nomes Recuperados do Refinado: {stats['names_recovered']}")
    print(f"Instalações Preservadas do Merged: {stats['installations_preserved']}")

if __name__ == "__main__":
    consolidate()
