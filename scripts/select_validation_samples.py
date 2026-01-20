"""
Seleciona 20 PDFs para validação com Gemini Vision:
- 10 do Grupo 1 (5 com mais UCs + 5 com menos UCs)
- 10 do Grupo 2 (5 com mais UCs + 5 com menos UCs)
"""

import json
import shutil
from pathlib import Path

# Carregar resultados
with open('output/multi_uc_robust_v3_test2.json', 'r', encoding='utf-8') as f:
    grupo1 = json.load(f)

with open('output/multi_uc_group2.json', 'r', encoding='utf-8') as f:
    grupo2 = json.load(f)

# Criar pasta de validação
output_dir = Path('output/validacao_gemini')
output_dir.mkdir(exist_ok=True)

def select_samples(data, group_name):
    """Seleciona 5 com mais UCs e 5 com menos UCs"""
    # Filtrar apenas docs com pelo menos 1 UC
    with_ucs = [d for d in data if d['uc_count'] > 0]
    
    # Ordenar por quantidade de UCs
    sorted_data = sorted(with_ucs, key=lambda x: x['uc_count'], reverse=True)
    
    # 5 com mais UCs
    top5 = sorted_data[:5]
    # 5 com menos UCs (excluindo os top5)
    bottom5 = sorted_data[-5:]
    
    return {
        f'{group_name}_top': top5,
        f'{group_name}_bottom': bottom5
    }

# Selecionar amostras
samples_g1 = select_samples(grupo1, 'g1')
samples_g2 = select_samples(grupo2, 'g2')

# Consolidar
all_samples = []
for key, samples in {**samples_g1, **samples_g2}.items():
    for s in samples:
        all_samples.append({
            'grupo': key,
            **s
        })

# Copiar PDFs para pasta de validação
print("=== SELECIONANDO 20 PDFs PARA VALIDAÇÃO ===\n")

validation_data = []
for i, sample in enumerate(all_samples, 1):
    src = Path(sample['path'])
    if src.exists():
        dst = output_dir / f"{i:02d}_{sample['file'][:60]}.pdf"
        shutil.copy2(src, dst)
        
        validation_data.append({
            'id': i,
            'arquivo': sample['file'],
            'path_original': sample['path'],
            'path_validacao': str(dst),
            'grupo': sample['grupo'],
            'ucs_extraidas': sample['ucs'],
            'uc_count': sample['uc_count'],
            'confidence': sample['confidence']
        })
        
        print(f"{i:02d}. [{sample['grupo']}] {sample['file'][:50]}...")
        print(f"    UCs extraídas ({sample['uc_count']}): {sample['ucs'][:3]}{'...' if len(sample['ucs']) > 3 else ''}")
        print()

# Salvar dados de validação
with open(output_dir / 'validacao_dados.json', 'w', encoding='utf-8') as f:
    json.dump(validation_data, f, ensure_ascii=False, indent=2)

print(f"\n✅ {len(validation_data)} PDFs copiados para: {output_dir}")
print(f"📄 Dados salvos em: {output_dir / 'validacao_dados.json'}")

# Criar resumo
print("\n=== RESUMO ===")
for grupo in ['g1_top', 'g1_bottom', 'g2_top', 'g2_bottom']:
    docs = [d for d in validation_data if d['grupo'] == grupo]
    total_ucs = sum(d['uc_count'] for d in docs)
    print(f"{grupo}: {len(docs)} docs, {total_ucs} UCs")
