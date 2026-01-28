"""
Script para criar clusters de PDFs para processamento via Gemini Web
Divide trabalho entre Barbara e Natalia com prompts técnicos completos
"""
import json
import shutil
import random
from pathlib import Path
from collections import defaultdict

# Configurações
SOURCE_DIR = Path("cpfl_paulista_por_tipo")
DATASET_FILE = Path("output/cpfl_paulista_final/cpfl_dataset_final_compiled.json")
OUTPUT_DIR = Path("output/gemini_clusters")

# Campos críticos para identificar gaps
CAMPOS_CRITICOS = ['num_instalacao', 'num_cliente', 'fidelidade', 'aviso_previo_dias']

# Mapeamento dos nomes amigáveis
NOMES_CAMPOS = {
    'num_instalacao': 'Número da Instalação (UC)',
    'num_cliente': 'Número do Cliente',
    'fidelidade': 'Período de Fidelidade',
    'aviso_previo_dias': 'Aviso Prévio (dias)',
    'razao_social': 'Razão Social da Empresa',
    'cnpj': 'CNPJ',
    'data_adesao': 'Data de Adesão',
    'representante_nome': 'Nome do Representante',
    'representante_cpf': 'CPF do Representante',
    'participacao_percentual': 'Participação/Cotas (%)'
}

def get_gap_key(gaps):
    """Gera chave abreviada para os gaps"""
    abrev = {
        'num_instalacao': 'numin',
        'num_cliente': 'numcl', 
        'fidelidade': 'fidel',
        'aviso_previo_dias': 'aviso'
    }
    return '_'.join(sorted([abrev.get(g, g[:5]) for g in gaps])) if gaps else 'COMPLETO'

def create_prompt_txt(cluster_info, gaps, output_path):
    """Cria arquivo PROMPT.txt com prompt técnico completo para Gemini"""
    
    # Criar lista de campos faltantes com nomes técnicos
    gaps_json_keys = ', '.join([f'"{g}"' for g in gaps])
    gaps_descricao = '\n'.join([f"- **{g}**: {NOMES_CAMPOS.get(g, g)}" for g in gaps])
    
    # Prompt técnico e completo para o Gemini
    gemini_prompt = f'''Você é um engenheiro de dados especialista em extração de informações de contratos de energia. 
Analise os PDFs anexados (contratos da CPFL Paulista/Raízen Power) e me ajude a criar regex para extrair os campos que estão faltando.

## CONTEXTO
Estou construindo um pipeline de extração de dados de contratos de energia usando Python + regex. 
Alguns campos não estão sendo extraídos corretamente. Preciso que você:
1. Localize onde cada campo aparece nos PDFs
2. Identifique o padrão textual ao redor do dado
3. Crie uma expressão regular (regex) Python para capturar o valor

## CAMPOS FALTANTES (que precisam de regex)
{gaps_descricao}

## SCHEMA DE DADOS ESPERADO
```json
{{
    "num_instalacao": "string (6-12 dígitos, ex: 17113911)",
    "num_cliente": "string (5-12 dígitos, código do cliente)",
    "fidelidade": "string (ex: 'ISENTO', '12 meses', 'SEM FIDELIDADE')",
    "aviso_previo_dias": "string (número de dias, ex: '180', '90')",
    "razao_social": "string (nome da empresa)",
    "cnpj": "string (formato XX.XXX.XXX/XXXX-XX)",
    "data_adesao": "string (DD/MM/AAAA ou 'DD de Mês de AAAA')",
    "representante_nome": "string (nome completo)",
    "representante_cpf": "string (XXX.XXX.XXX-XX)",
    "participacao_percentual": "string (valor numérico ou percentual)"
}}
```

## INSTRUÇÕES
Para cada campo faltante [{gaps_json_keys}]:

1. **LOCALIZE** o campo nos PDFs anexados
2. **COPIE** o trecho exato onde aparece (com contexto de 50 caracteres antes e depois)
3. **CRIE** uma regex Python que capture o valor

## FORMATO DE RESPOSTA OBRIGATÓRIO
Retorne um JSON válido no seguinte formato:

```json
{{
    "campos": {{
        "nome_do_campo": {{
            "encontrado": true,
            "pagina": "número ou 'Anexo I'",
            "trecho_original": "texto copiado do PDF",
            "regex": "expressão regular Python",
            "grupo_captura": 1,
            "exemplo_valor": "valor extraído do PDF",
            "observacoes": "notas sobre variações encontradas"
        }}
    }},
    "meta": {{
        "total_paginas": "número",
        "tipo_contrato": "TERMO_ADESAO/SOLAR/ADITIVO/etc",
        "observacoes_gerais": "qualquer nota relevante"
    }}
}}
```

## DICAS PARA REGEX
- Use `(?i)` para case-insensitive
- Use grupos de captura `()` para extrair o valor
- Considere variações de formatação OCR (espaços extras, quebras de linha)
- Escape caracteres especiais: `.` `(` `)` `[` `]`

Analise os PDFs e retorne o JSON completo.'''

    # Arquivo com instruções simples para as meninas + prompt técnico
    conteudo = f"""===============================================
INSTRUÇÕES - COPIE E COLE NO GEMINI
===============================================

PASSO 1: Acesse https://gemini.google.com

PASSO 2: Clique no + e faça upload dos PDFs desta pasta

PASSO 3: Copie TODO o texto abaixo (de === até ===) e cole no chat

===============================================
{gemini_prompt}
===============================================

PASSO 4: Aguarde a resposta

PASSO 5: Copie TODA a resposta e cole no arquivo RESPOSTA.txt

===============================================
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(conteudo)

def create_resposta_txt(output_path):
    """Cria arquivo RESPOSTA.txt vazio para a pessoa preencher"""
    template = """===============================================
COLE AQUI A RESPOSTA DO GEMINI
===============================================

[Apague este texto e cole a resposta do Gemini aqui]





===============================================
"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(template)

def main():
    print("=== CRIANDO CLUSTERS PARA GEMINI WEB ===")
    
    # Carregar dataset
    with open(DATASET_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Dataset carregado: {len(data)} registros")
    
    # Agrupar por TIPO + PÁGINAS + GAPS
    clusters = defaultdict(list)
    
    for r in data:
        tipo = r.get('type', 'UNKNOWN')
        pasta = r.get('folder', 'UNKNOWN').replace('_paginas', 'p')
        file_path = r.get('path', '')
        
        # Identificar gaps
        gaps = []
        for campo in CAMPOS_CRITICOS:
            if not r.get('data', {}).get(campo):
                gaps.append(campo)
        
        gap_key = get_gap_key(gaps)
        cluster_key = f"{tipo}|{pasta}|{gap_key}"
        
        clusters[cluster_key].append({
            'file': r.get('file'),
            'path': file_path,
            'gaps': gaps
        })
    
    # Ordenar por quantidade (maiores primeiro)
    sorted_clusters = sorted(clusters.items(), key=lambda x: -len(x[1]))
    
    print(f"Total de clusters: {len(clusters)}")
    
    # Definir divisão (Barbara = primeiros 4, Natalia = próximos 7)
    barbara_clusters = sorted_clusters[:4]
    natalia_clusters = sorted_clusters[4:11]
    
    # Criar estrutura de pastas
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    barbara_dir = OUTPUT_DIR / "barbara"
    natalia_dir = OUTPUT_DIR / "natalia"
    barbara_dir.mkdir(exist_ok=True)
    natalia_dir.mkdir(exist_ok=True)
    
    def process_clusters(clusters_list, base_dir, start_num):
        for i, (cluster_key, files) in enumerate(clusters_list, start_num):
            parts = cluster_key.split('|')
            tipo, paginas, gaps_str = parts[0], parts[1], parts[2]
            
            # Nome da pasta
            folder_name = f"{i:02d}_{tipo}_{paginas}_{gaps_str}"
            cluster_dir = base_dir / folder_name
            cluster_dir.mkdir(exist_ok=True)
            
            # Selecionar 2 amostras aleatórias
            random.seed(42)
            samples = random.sample(files, min(2, len(files)))
            
            # Copiar PDFs
            for j, sample in enumerate(samples, 1):
                src_path = Path(sample['path'])
                if src_path.exists():
                    dst_path = cluster_dir / f"amostra_{j:02d}.pdf"
                    shutil.copy2(src_path, dst_path)
                    print(f"  ✅ Copiado: {dst_path.name}")
            
            # Extrair gaps do primeiro arquivo
            gaps = samples[0]['gaps'] if samples else []
            
            # Criar PROMPT.txt
            create_prompt_txt(cluster_key, gaps, cluster_dir / "PROMPT.txt")
            
            # Criar RESPOSTA.txt vazio
            create_resposta_txt(cluster_dir / "RESPOSTA.txt")
            
            print(f"📁 {folder_name}: {len(files)} PDFs, {len(samples)} amostras")
    
    print("\n👩 Processando clusters para BARBARA...")
    process_clusters(barbara_clusters, barbara_dir, 1)
    
    print("\n👩 Processando clusters para NATALIA...")
    process_clusters(natalia_clusters, natalia_dir, 5)
    
    # Criar README geral
    readme_content = f"""===============================================
INSTRUÇÕES GERAIS - PROJETO RAÍZEN
===============================================

Este trabalho foi dividido entre duas pessoas:

📁 barbara/ - Contém 4 pastas (clusters maiores)
📁 natalia/ - Contém 7 pastas (clusters menores)

COMO FAZER:

1. Entre na sua pasta (barbara ou natalia)
2. Abra cada subpasta (01_..., 02_..., etc)
3. Leia o arquivo PROMPT.txt com as instruções
4. Siga os passos para usar o Gemini
5. Cole a resposta no arquivo RESPOSTA.txt
6. Repita para todas as pastas

Gerado em: {__import__('datetime').datetime.now().strftime('%d/%m/%Y %H:%M')}
===============================================
"""
    
    with open(OUTPUT_DIR / "README.txt", 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"\n✅ Concluído! Pastas criadas em: {OUTPUT_DIR}")
    print(f"   - barbara/: {len(barbara_clusters)} clusters")
    print(f"   - natalia/: {len(natalia_clusters)} clusters")

if __name__ == "__main__":
    main()
