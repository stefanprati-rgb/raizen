import json
import pandas as pd
from pathlib import Path

# Arquivos de entrada
GOLD_PATH = Path("output/cpfl_paulista_final/cpfl_full_extraction_v6_gold.json")
OCR_PATH = Path("output/cpfl_paulista_final/cpfl_full_extraction_v6_ocr.json")

# Saída
OUTPUT_JSON = Path("output/cpfl_paulista_final/cpfl_dataset_final_compiled.json")
OUTPUT_EXCEL = Path("output/cpfl_paulista_final/cpfl_dataset_final_compiled.xlsx")

def load_json(path):
    if not path.exists():
        print(f"Arquivo não encontrado: {path}")
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def clean_data(val):
    """Limpa valores nulos ou vazios"""
    if val is None:
        return ""
    return str(val).strip()

def main():
    print("🚀 Iniciando compilação do dataset final...")
    
    # 1. Carregar datasets
    gold_data = load_json(GOLD_PATH)
    ocr_data = load_json(OCR_PATH)
    
    print(f"📊 Gold original: {len(gold_data)} registros")
    print(f"📊 OCR dataset: {len(ocr_data)} registros")
    
    # 2. Criar dicionário indexado por caminho para o GOLD (base)
    # Assumindo que 'path' é único
    compiled_db = {item['path']: item for item in gold_data}
    
    # 3. Merge Inteligente: Sobrepor com dados do OCR apenas se houver novidade
    updated_count = 0
    new_records = 0
    
    for item in ocr_data:
        path = item['path']
        
        # Verificar se tem dados de OCR
        ocr_extract = item.get('data', {})
        has_ocr_id = bool(ocr_extract.get('num_instalacao') or ocr_extract.get('num_conta_contrato') or ocr_extract.get('num_cliente'))
        
        if path in compiled_db:
            # Se já existe no Gold, atualizamos apenas se o OCR trouxe dados novos que faltavam
            # ou se é um documento de 9 páginas (alvo do OCR) e o Gold estava vazio nesses campos
            current_data = compiled_db[path].get('data', {})
            
            # Condição para aplicar o OCR:
            # 1. É um 'TERMO_ADESAO' de '09_paginas' (nosso alvo principal)
            # 2. E o OCR achou algo
            is_target_doc = '09_paginas' in path
            
            if is_target_doc and has_ocr_id:
                # Merge dos campos chave
                if ocr_extract.get('num_instalacao'):
                    current_data['num_instalacao'] = ocr_extract['num_instalacao']
                if ocr_extract.get('num_conta_contrato'):
                    current_data['num_conta_contrato'] = ocr_extract['num_conta_contrato']
                if ocr_extract.get('num_cliente'):
                    current_data['num_cliente'] = ocr_extract['num_cliente']
                
                # Atualiza status
                compiled_db[path]['status'] = "SUCCESS_OCR"
                compiled_db[path]['data'] = current_data
                updated_count += 1
        else:
            # Se não existe no Gold (raro, mas possível), adiciona
            compiled_db[path] = item
            new_records += 1
            
    print(f"✅ Atualizados com OCR: {updated_count} registros")
    print(f"✅ Novos registros adicionados: {new_records} registros")
    
    # 4. Converter para Lista Final
    final_list = list(compiled_db.values())
    print(f"🏁 Dataset Final: {len(final_list)} registros")
    
    # 5. Salvar JSON Final
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(final_list, f, ensure_ascii=False, indent=2)
    print(f"💾 JSON salvo em: {OUTPUT_JSON}")
    
    # 6. Exportar para Excel (Flattening data)
    print("📊 Preparando Excel...")
    rows = []
    for entry in final_list:
        data = entry.get('data', {})
        row = {
            'Arquivo': entry.get('path', ''),
            'Tipo': entry.get('type', ''),
            'Status': entry.get('status', 'ERROR'),
            'Pasta': entry.get('folder', ''),
            
            # Campos Extraídos
            'Razão Social': clean_data(data.get('razao_social')),
            'CNPJ': clean_data(data.get('cnpj')),
            'CPF Representante': clean_data(data.get('cpf') or data.get('representante_cpf')),
            'Nome Representante': clean_data(data.get('representante_nome')),
            'Data Adesão': clean_data(data.get('data_adesao')),
            'Nº Instalação': clean_data(data.get('num_instalacao')),
            'Nº Conta Contrato (UC)': clean_data(data.get('num_conta_contrato')),
            'Nº Cliente': clean_data(data.get('num_cliente')),
            'Distribuidora': clean_data(data.get('distribuidora')),
            'Fidelidade': clean_data(data.get('fidelidade')),
        }
        rows.append(row)
        
    df = pd.DataFrame(rows)
    df.to_excel(OUTPUT_EXCEL, index=False)
    print(f"💾 Excel salvo em: {OUTPUT_EXCEL}")

if __name__ == "__main__":
    main()
