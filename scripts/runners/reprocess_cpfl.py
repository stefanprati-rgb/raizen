import json
import time
from pathlib import Path
from multiprocessing import cpu_count
from concurrent.futures import ProcessPoolExecutor, as_completed

# Ajustar path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extrator_contratos.table_extractor import open_pdf, extract_all_text_from_pdf
from scripts.apply_map import extract_with_map

# Config
ORIGINAL_JSON = Path("output/cpfl_paulista_final/cpfl_full_extraction_v6_gold.json")
MAP_V6 = Path("maps/CPFL_PAULISTA_completo_v6.json")
OUTPUT_JSON = Path("output/cpfl_paulista_final/cpfl_full_extraction_v6_final.json")

def needs_reprocessing(entry):
    """V6.4: Foco em TERMO_ADESAO sem identificação de ativo"""
    if entry.get('type') != 'TERMO_ADESAO':
        return False  # Só reprocessa Termos de Adesão
        
    data = entry.get('data', {}) or {}
    
    # Se não tem instalação NEM conta contrato NEM cliente, reprocessa
    has_id = data.get('num_instalacao') or data.get('num_conta_contrato') or data.get('num_cliente')
    if not has_id:
        return True
        
    return False


def reprocess_file(file_path, mapa, original_entry):
    """Roda extração v6 no arquivo"""
    try:
        with open_pdf(str(file_path)) as doc:
            # Aumentar range de páginas para pegar logs de assinatura no final
            text = extract_all_text_from_pdf(doc, max_pages=15, use_ocr_fallback=False)
            
        new_data = extract_with_map(text, mapa)
        
        # Merge inteligente: Manter campos antigos se novos forem vazios?
        # A V6 é superior, vamos confiar na V6.
        
        # Contar campos preenchidos
        filled = len([v for v in new_data.values() if v])
        
        return {
            "status": "SUCCESS_FIXED",
            "file": original_entry['file'],
            "path": original_entry['path'],
            "folder": original_entry['folder'],
            "type": original_entry['type'],
            "fields_count": filled,
            "data": new_data,
            "fixed": True
        }
    except Exception as e:
        return original_entry # Retorna o original se der erro

def main():
    print(f"Lendo dados originais: {ORIGINAL_JSON}")
    with open(ORIGINAL_JSON, 'r', encoding='utf-8') as f:
        original_data = json.load(f)
        
    print(f"Carregando Mapa V6: {MAP_V6}")
    with open(MAP_V6, 'r', encoding='utf-8') as f:
        mapa_v6 = json.load(f)
        
    # Identificar candidatos
    to_reprocess = []
    skipped = []
    
    for entry in original_data:
        if needs_reprocessing(entry):
            to_reprocess.append(entry)
        else:
            skipped.append(entry)
            
    print(f"\n📊 Análise de Reprocessamento:")
    print(f"   Total Original: {len(original_data)}")
    print(f"   A Reprocessar: {len(to_reprocess)} (arquivos com falha em Data, Rep ou Inst)")
    print(f"   Ignorados (OK): {len(skipped)}")
    
    if not to_reprocess:
        print("Nada a reprocessar.")
        return

    # Executar reprocessamento
    print(f"\n🚀 Iniciando Reprocessamento com {min(4, cpu_count())} workers...")
    
    fixed_results = []
    
    # Carregar dados parciais se existirem (para resume)
    # Por simplicidade, vamos começar do zero, mas com safety save
    
    with ProcessPoolExecutor(max_workers=min(4, cpu_count())) as executor:
        future_to_entry = {
            executor.submit(reprocess_file, Path(entry['path']), mapa_v6, entry): entry 
            for entry in to_reprocess
        }
        
        for i, future in enumerate(as_completed(future_to_entry), 1):
            try:
                result = future.result()
                fixed_results.append(result)
            except Exception as e:
                print(f"❌ Erro crítico no worker: {e}")
            
            if i % 50 == 0 or i == len(to_reprocess):
                print(f"   Processado: {i}/{len(to_reprocess)}")
                
                # Salvamento Incremental (Safety Save)
                if i % 200 == 0:
                     print(f"   💾 Salvando checkpoint parcial ({i} processados)...")
                     partial_dataset = skipped + fixed_results
                     with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
                        json.dump(partial_dataset, f, ensure_ascii=False, indent=2)

                
    # Merge Final
    final_dataset = skipped + fixed_results
    
    # Salvar
    print(f"\n💾 Salvando Merge Final: {OUTPUT_JSON}")
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(final_dataset, f, ensure_ascii=False, indent=2)
        
    print(f"✅ Concluído. Total Final: {len(final_dataset)}")

if __name__ == "__main__":
    main()
