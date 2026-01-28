import json
from pathlib import Path
from collections import Counter, defaultdict
import re

# Caminho do JSON
JSON_FILE = Path("output/cpfl_paulista_final/cpfl_full_extraction_v6_gold.json")

def audit_data():
    if not JSON_FILE.exists():
        print(f"Erro: Arquivo {JSON_FILE} não encontrado.")
        return

    print(f"Lendo {JSON_FILE}...")
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    total_files = len(data)
    print(f"Total de arquivos analisados: {total_files}")
    
    # 1. Análise de Campos Vazios
    missing_fields = Counter()
    missing_by_type = defaultdict(Counter)
    type_counts = Counter()
    
    # Camopos esperados (baseado no mapa v5)
    expected_fields = [
        "razao_social", "cnpj", "distribuidora", "data_adesao", "duracao_meses", 
        "fidelidade", "aviso_previo_dias", "vencimento_dia", "performance_alvo", 
        "representante_nome", "representante_cpf", "plataforma_assinatura",
        "num_instalacao", "num_cliente", "email"
    ]
    
    # 2. Análise de Formato de Data
    date_samples = []
    
    for entry in data:
        extracted = entry.get('data', {})
        doc_type = entry.get('type', 'DESCONHECIDO')
        type_counts[doc_type] += 1
        
        # Verificar campos vazios
        for field in expected_fields:
            value = extracted.get(field)
            if not value or value == "":
                missing_fields[field] += 1
                missing_by_type[doc_type][field] += 1
        
        # Verificar formato de data
        if extracted.get('data_adesao'):
            date_samples.append(extracted['data_adesao'])

    print("\n=== RELATÓRIO DE FALHAS POR CAMPO ===")
    print(f"{'CAMPO':<25} | {'FALHAS':<10} | {'% FALHA':<10}")
    print("-" * 50)
    for field, count in missing_fields.most_common():
        pct = (count / total_files) * 100
        print(f"{field:<25} | {count:<10} | {pct:.1f}%")

    print("\n=== FALHAS CRÍTICAS POR TIPO DE DOCUMENTO ===")
    for doc_type, failures in missing_by_type.items():
        total_type = type_counts[doc_type]
        print(f"\nTipo: {doc_type} (Total: {total_type})")
        for field, count in failures.most_common(5):
            pct = (count / total_type) * 100
            print(f"  - {field}: {count} falhas ({pct:.1f}%)")

    print("\n=== AMOSTRAGEM DE DATAS (Verificação de Formato) ===")
    print("Últimas 10 datas extraídas:")
    for d in date_samples[-10:]:
        print(f"  '{d}'")
        
    # Validar se as datas parecem completas (DD/MM/AAAA)
    # Procurar por datas que tenham pelo menos 8 caracteres (ex: 2022-12-01 ou 01/12/2022)
    complete_dates = [d for d in date_samples if len(str(d).strip()) >= 8]
    incomplete_dates = [d for d in date_samples if d not in complete_dates]
    
    print(f"\nDatas Aparentemente Corretas: {len(complete_dates)}")
    print(f"Datas Incompletas/Texto: {len(incomplete_dates)}")
    if incomplete_dates:
        print(f"Exemplos de incompletas: {incomplete_dates[:10]}")

if __name__ == "__main__":
    audit_data()
