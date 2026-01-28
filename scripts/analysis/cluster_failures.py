import json
import shutil
from pathlib import Path
from collections import defaultdict, Counter

# Configurações
JSON_FILE = Path("output/cpfl_paulista_final/cpfl_full_extraction.json")
CLUSTERS_DIR = Path("output/cpfl_clusters")

# Campos críticos para considerar na falha
CRITICAL_FIELDS = [
    "data_adesao", 
    "representante_nome", 
    "representante_cpf",
    "fidelidade",
    "num_instalacao"
]

def get_failure_signature(entry):
    """Gera uma assinatura única para o tipo de falha"""
    data = entry.get('data', {})
    failures = []
    
    for field in CRITICAL_FIELDS:
        val = data.get(field)
        if not val:
            failures.append(field)
    
    if not failures:
        return None
    
    # Assinatura: TIPO_PAGINAS_FALHAS
    # Ex: TERMO_ADESAO_11p_SemDATA_SemREP
    doc_type = entry.get('type', 'UNK')
    folder = entry.get('folder', '00p').replace('_paginas', 'p')
    
    # Simplificar nomes para assinatura
    fail_codes = []
    if "data_adesao" in failures: fail_codes.append("Data")
    if "representante_nome" in failures: fail_codes.append("Rep")
    if "fidelidade" in failures: fail_codes.append("Fid")
    if "num_instalacao" in failures: fail_codes.append("Inst")
    
    if not fail_codes:
        return "Outros"
        
    sig = f"{doc_type}_{folder}_Sem{''.join(fail_codes)}"
    return sig

def main():
    if not JSON_FILE.exists():
        print(f"Erro: {JSON_FILE} não encontrado")
        return

    # Limpar pasta anterior
    if CLUSTERS_DIR.exists():
        shutil.rmtree(CLUSTERS_DIR)
    CLUSTERS_DIR.mkdir(parents=True)

    print(f"Lendo {JSON_FILE}...")
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Agrupar
    clusters = defaultdict(list)
    
    for entry in data:
        sig = get_failure_signature(entry)
        if sig:
            clusters[sig].append(entry)

    # Analisar e salvar amostras
    print("\n=== CLUSTERS DE FALHAS IDENTIFICADOS ===")
    print(f"{'CLUSTER':<50} | {'ARQUIVOS':<10}")
    print("-" * 65)
    
    summary = []
    
    for sig, items in sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True):
        count = len(items)
        if count < 10: continue  # Ignorar clusters muito pequenos
        
        print(f"{sig:<50} | {count:<10}")
        
        # Criar pasta do cluster
        cluster_path = CLUSTERS_DIR / sig
        cluster_path.mkdir()
        
        # Copiar até 5 amostras
        samples = items[:5]
        for i, sample in enumerate(samples):
            src = Path(sample['path'])
            if src.exists():
                dest = cluster_path / f"Amostra_{i+1}_{src.name}"
                shutil.copy2(src, dest)
        
        summary.append({
            "cluster": sig,
            "count": count,
            "critical_field": "representante" if "Rep" in sig else "data" if "Data" in sig else "Outro"
        })

    # Salvar resumo para uso posterior
    with open(CLUSTERS_DIR / "clusters_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)
        
    print(f"\n✅ Amostras separadas em: {CLUSTERS_DIR}")

if __name__ == "__main__":
    main()
