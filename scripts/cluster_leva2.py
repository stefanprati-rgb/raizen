"""
Script para criar clusters adicionais (12-21) para Gemini Web
"""
import json
import shutil
import random
from pathlib import Path
from collections import defaultdict

# Configurações
DATASET_FILE = Path("output/cpfl_paulista_final/cpfl_dataset_final_compiled.json")
OUTPUT_DIR = Path("output/gemini_clusters")

CAMPOS_CRITICOS = ['num_instalacao', 'num_cliente', 'fidelidade', 'aviso_previo_dias']
NOMES_CAMPOS = {
    'num_instalacao': 'Número da Instalação (UC)',
    'num_cliente': 'Número do Cliente',
    'fidelidade': 'Período de Fidelidade',
    'aviso_previo_dias': 'Aviso Prévio (dias)'
}

def get_gap_key(gaps):
    abrev = {'num_instalacao': 'numin', 'num_cliente': 'numcl', 'fidelidade': 'fidel', 'aviso_previo_dias': 'aviso'}
    return '_'.join(sorted([abrev.get(g, g[:5]) for g in gaps])) if gaps else 'COMPLETO'

def create_prompt_txt(gaps, output_path):
    gaps_descricao = '\n'.join([f'- **{g}**: {NOMES_CAMPOS.get(g, g)}' for g in gaps])
    
    prompt = f'''Você é um engenheiro de dados especialista em extração de informações de contratos de energia. 
Analise os PDFs anexados (contratos da CPFL Paulista/Raízen Power) e me ajude a criar regex para extrair os campos faltantes.

## CAMPOS FALTANTES (que precisam de regex)
{gaps_descricao}

## INSTRUÇÕES
Para cada campo faltante:
1. Localize onde o campo aparece nos PDFs
2. Copie o trecho exato onde aparece
3. Crie uma regex Python para capturar o valor

## FORMATO DE RESPOSTA
Retorne JSON:
{{
    "campos": {{
        "nome_campo": {{
            "encontrado": true,
            "pagina": "número",
            "trecho_original": "texto do PDF",
            "regex": "expressão Python",
            "exemplo_valor": "valor extraído"
        }}
    }}
}}

Analise os PDFs anexados.'''

    conteudo = f'''===============================================
INSTRUÇÕES - COPIE E COLE NO GEMINI
===============================================

1. Acesse https://gemini.google.com
2. Faça upload dos PDFs desta pasta
3. Copie o texto abaixo e cole no chat

===============================================
{prompt}
===============================================

4. Cole a resposta no arquivo RESPOSTA.txt
===============================================
'''
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(conteudo)

def create_resposta_txt(output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('[Cole a resposta do Gemini aqui]')

def main():
    print("=== CRIANDO CLUSTERS 12-21 ===")
    
    # Carregar dataset
    with open(DATASET_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Agrupar
    clusters = defaultdict(list)
    for r in data:
        tipo = r.get('type', 'UNKNOWN')
        pasta = r.get('folder', 'UNKNOWN').replace('_paginas', 'p')
        gaps = [c for c in CAMPOS_CRITICOS if not r.get('data', {}).get(c)]
        gap_key = get_gap_key(gaps)
        cluster_key = f'{tipo}|{pasta}|{gap_key}'
        clusters[cluster_key].append({'file': r.get('file'), 'path': r.get('path'), 'gaps': gaps})
    
    sorted_clusters = sorted(clusters.items(), key=lambda x: -len(x[1]))
    
    # Dividir: Barbara (12-16), Natalia (17-21)
    barbara_new = sorted_clusters[11:16]
    natalia_new = sorted_clusters[16:21]
    
    barbara_dir = OUTPUT_DIR / 'barbara'
    natalia_dir = OUTPUT_DIR / 'natalia'
    
    def process_clusters(clusters_list, base_dir, start_num):
        for i, (cluster_key, files) in enumerate(clusters_list, start_num):
            parts = cluster_key.split('|')
            tipo, paginas, gaps_str = parts[0], parts[1], parts[2]
            folder_name = f'{i:02d}_{tipo}_{paginas}_{gaps_str}'
            cluster_dir = base_dir / folder_name
            cluster_dir.mkdir(exist_ok=True)
            
            random.seed(42 + i)
            samples = random.sample(files, min(2, len(files)))
            
            for j, sample in enumerate(samples, 1):
                src_path = Path(sample['path'])
                if src_path.exists():
                    dst_path = cluster_dir / f'amostra_{j:02d}.pdf'
                    shutil.copy2(src_path, dst_path)
            
            gaps = samples[0]['gaps'] if samples else []
            create_prompt_txt(gaps, cluster_dir / 'PROMPT.txt')
            create_resposta_txt(cluster_dir / 'RESPOSTA.txt')
            print(f'📁 {folder_name}: {len(files)} PDFs')
    
    print("\n👩 BARBARA (12-16):")
    process_clusters(barbara_new, barbara_dir, 12)
    
    print("\n👩 NATALIA (17-21):")
    process_clusters(natalia_new, natalia_dir, 17)
    
    print("\n✅ 10 novos clusters criados!")

if __name__ == "__main__":
    main()
