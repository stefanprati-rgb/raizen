"""
Detector de Modelos de Contrato - Fingerprinting
Versão: 1.0

Analisa contratos dentro de uma pasta e identifica diferentes "modelos"
baseado em fingerprints textuais (palavras-chave, estrutura, formato).

Uso:
    python scripts/detect_models.py contratos_por_paginas/05_paginas
    python scripts/detect_models.py contratos_por_paginas/09_paginas/CPFL_PAULISTA
"""
import sys
import re
import json
import hashlib
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extrator_contratos.table_extractor import open_pdf, extract_all_text_from_pdf

# Indicadores de layout/modelo
LAYOUT_INDICATORS = {
    'MODELO_SOLAR_RAIZEN': [
        'CONSÓRCIO RZ',
        'CONSORCIADA (VOCÊ)',
        'SOLAR',
        'ANEXO I',
        'DADOS DA CONSORCIADA',
    ],
    'MODELO_SMARTFIT': [
        'DA QUALIFICAÇÃO DA CONSORCIADA',
        'SmartFit',
        'Consórcio SmartFit',
    ],
    'MODELO_GUARDA_CHUVA': [
        'CONTRATO GUARDA-CHUVA',
        'múltiplas instalações',
        'unidades consumidoras listadas',
    ],
    'MODELO_CEMIG': [
        'CEMIG',
        'Cemig Distribuição',
        'CEMIG-D',
    ],
    'MODELO_CPFL': [
        'CPFL',
        'CPFL Paulista',
        'CPFL Piratininga',
    ],
    'MODELO_ENEL': [
        'ENEL',
        'Enel Distribuição',
    ],
}


def extract_fingerprint(text: str) -> Dict:
    """
    Extrai fingerprint de um contrato baseado em características do texto.
    """
    fingerprint = {
        'indicadores': [],
        'distribuidora': None,
        'tem_anexo': False,
        'tem_tabela_instalacoes': False,
        'primeiras_palavras': '',
        'hash_estrutura': '',
    }
    
    # Detectar indicadores de layout
    for modelo, indicators in LAYOUT_INDICATORS.items():
        matches = sum(1 for ind in indicators if ind.upper() in text.upper())
        if matches >= 2:
            fingerprint['indicadores'].append(modelo)
    
    # Detectar distribuidora
    distribuidoras = [
        'CEMIG', 'CPFL', 'ENEL', 'LIGHT', 'ELEKTRO', 'ENERGISA',
        'NEOENERGIA', 'EQUATORIAL', 'COELBA', 'CELPE', 'COSERN',
        'EDP', 'CELESC', 'COPEL', 'CEEE', 'RGE', 'CELG'
    ]
    for dist in distribuidoras:
        if dist.upper() in text.upper():
            fingerprint['distribuidora'] = dist
            break
    
    # Detectar Anexo I
    if re.search(r'ANEXO\s*I', text, re.IGNORECASE):
        fingerprint['tem_anexo'] = True
    
    # Detectar tabela de instalações
    if re.search(r'Unidade\s+Consumidora|Instalação|N[º°]\s*UC', text, re.IGNORECASE):
        fingerprint['tem_tabela_instalacoes'] = True
    
    # Primeiras palavras significativas (ignorar cabeçalhos genéricos)
    lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 10][:10]
    fingerprint['primeiras_palavras'] = ' | '.join(lines[:3])[:200]
    
    # Hash da estrutura (baseado em palavras-chave ordenadas)
    keywords = re.findall(r'\b(CONTRATO|TERMO|ADESÃO|CONSÓRCIO|ANEXO|CLÁUSULA)\b', text.upper())
    fingerprint['hash_estrutura'] = hashlib.md5('_'.join(keywords[:20]).encode()).hexdigest()[:8]
    
    return fingerprint


def analyze_folder(folder_path: Path, sample_size: int = None) -> Dict:
    """
    Analisa todos os PDFs em uma pasta e agrupa por modelo detectado.
    """
    pdf_files = list(folder_path.rglob('*.pdf'))
    
    if sample_size and len(pdf_files) > sample_size:
        import random
        pdf_files = random.sample(pdf_files, sample_size)
    
    print(f"\n📁 Analisando: {folder_path}")
    print(f"   PDFs encontrados: {len(pdf_files)}")
    print("-" * 60)
    
    # Agrupar por fingerprint
    models = defaultdict(list)
    
    for i, pdf_path in enumerate(pdf_files):
        try:
            with open_pdf(str(pdf_path)) as pdf:
                text = extract_all_text_from_pdf(pdf, max_pages=3, use_ocr_fallback=False)
            
            fp = extract_fingerprint(text)
            
            # Criar chave única para o modelo
            model_key = '_'.join(sorted(fp['indicadores'])) if fp['indicadores'] else 'DESCONHECIDO'
            if fp['distribuidora']:
                model_key += f"_{fp['distribuidora']}"
            
            models[model_key].append({
                'arquivo': pdf_path.name,
                'fingerprint': fp
            })
            
            # Progresso
            if (i + 1) % 20 == 0:
                print(f"   Processados: {i + 1}/{len(pdf_files)}")
                
        except Exception as e:
            models['ERRO_LEITURA'].append({
                'arquivo': pdf_path.name,
                'erro': str(e)
            })
    
    return dict(models)


def print_analysis(models: Dict):
    """Exibe análise de modelos detectados."""
    print("\n" + "=" * 70)
    print("MODELOS DETECTADOS")
    print("=" * 70)
    
    total = sum(len(files) for files in models.values())
    
    # Ordenar por quantidade
    sorted_models = sorted(models.items(), key=lambda x: len(x[1]), reverse=True)
    
    for model_key, files in sorted_models:
        count = len(files)
        pct = count / total * 100
        print(f"\n📋 {model_key}")
        print(f"   Quantidade: {count} ({pct:.1f}%)")
        
        # Mostrar exemplos
        if files and 'fingerprint' in files[0]:
            fp = files[0]['fingerprint']
            print(f"   Distribuidora: {fp.get('distribuidora', 'N/A')}")
            print(f"   Tem Anexo: {'Sim' if fp.get('tem_anexo') else 'Não'}")
            print(f"   Hash Estrutura: {fp.get('hash_estrutura', 'N/A')}")
            print(f"   Exemplo: {files[0]['arquivo'][:50]}...")
    
    print("\n" + "=" * 70)
    print(f"TOTAL: {total} PDFs em {len(models)} modelos diferentes")
    print("=" * 70)


def export_for_gemini(models: Dict, output_dir: Path):
    """
    Exporta textos de amostra para usar no Gemini Web.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for model_key, files in models.items():
        if model_key == 'ERRO_LEITURA' or not files:
            continue
        
        # Pegar primeiro arquivo como amostra
        sample_file = files[0]['arquivo']
        
        # Criar arquivo de texto para copiar no Gemini
        output_file = output_dir / f"{model_key}_amostra.txt"
        
        try:
            # Encontrar PDF original
            sample_path = None
            for f in Path('.').rglob(sample_file):
                sample_path = f
                break
            
            if sample_path:
                with open_pdf(str(sample_path)) as pdf:
                    text = extract_all_text_from_pdf(pdf, max_pages=5)
                
                # Criar prompt para Gemini
                prompt = f"""
ANALISE ESTE CONTRATO E GERE UM MAPA DE EXTRAÇÃO

MODELO: {model_key}
ARQUIVO: {sample_file}

CAMPOS A EXTRAIR:
1. cnpj
2. razao_social
3. num_instalacao (UC)
4. num_cliente
5. distribuidora
6. data_adesao
7. duracao_meses (fidelidade)
8. aviso_previo (dias)
9. representante_nome
10. representante_cpf
11. participacao_percentual

RETORNE JSON COM:
- "ancora": texto antes do campo
- "regex": padrão para capturar
- "valor_amostra": valor encontrado

TEXTO DO CONTRATO:
---
{text[:30000]}
---
"""
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(prompt)
                
                print(f"✅ Exportado: {output_file.name}")
        
        except Exception as e:
            print(f"❌ Erro ao exportar {model_key}: {e}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Detector de Modelos de Contrato")
    parser.add_argument("folder", type=Path, help="Pasta com PDFs para analisar")
    parser.add_argument("--sample", "-s", type=int, default=None, help="Analisar apenas N PDFs")
    parser.add_argument("--export", "-e", action="store_true", help="Exportar amostras para Gemini Web")
    
    args = parser.parse_args()
    
    if not args.folder.exists():
        print(f"❌ Pasta não encontrada: {args.folder}")
        return
    
    # Analisar
    models = analyze_folder(args.folder, args.sample)
    
    # Exibir resultados
    print_analysis(models)
    
    # Exportar se solicitado
    if args.export:
        export_dir = Path("output/gemini_samples")
        export_for_gemini(models, export_dir)
        print(f"\n📁 Amostras exportadas em: {export_dir}")
        print("   Copie o conteúdo dos arquivos .txt no Gemini Web")
    
    # Salvar análise
    analysis_file = Path("output") / f"analysis_{args.folder.name}.json"
    analysis_file.parent.mkdir(exist_ok=True)
    
    # Converter para JSON serializable
    export_data = {}
    for model, files in models.items():
        export_data[model] = {
            'count': len(files),
            'samples': [f['arquivo'] for f in files[:5]]
        }
    
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Análise salva em: {analysis_file}")


if __name__ == "__main__":
    main()
