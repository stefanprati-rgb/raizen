"""
Pipeline de Extracao Inteligente
Classifica documentos e aplica o mapa correto para cada tipo.
"""
import sys
import json
import csv
import re
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.extrator_contratos.table_extractor import open_pdf, extract_all_text_from_pdf
from src.extrator_contratos.normalizers import normalize_all


# Mapeamento: (distribuidora, tipo_doc, num_paginas) -> mapa
MAPA_DOCUMENTOS = {
    # CEMIG
    ('CEMIG', 'ADESAO', 5): 'maps/CEMIG_05p_v1.json',
    ('CEMIG', 'ADESAO', 2): 'maps/CEMIG_02p_v1.json',
    ('CEMIG', 'ADITIVO', 5): 'maps/CEMIG_Aditivo_Condicoes_v1.json',
    ('CEMIG', 'DISTRATO', 5): 'maps/DISTRATO_RGE_v1.json',
    
    # CPFL
    ('CPFL', 'ADESAO', 5): 'maps/CPFL_05p_v1.json',
    ('CPFL', 'ADESAO', 2): 'maps/CPFL_02p_v1.json',
    ('CPFL', 'ADITIVO', 5): 'maps/CEMIG_Aditivo_Condicoes_v1.json',
    ('CPFL', 'DISTRATO', 5): 'maps/DISTRATO_RGE_v1.json',
    
    # ENEL
    ('ENEL', 'ADESAO', 5): 'maps/ENEL_05p_v1.json',
    ('ENEL', 'ADITIVO', 5): 'maps/CEMIG_Aditivo_Condicoes_v1.json',
    ('ENEL', 'DISTRATO', 5): 'maps/DISTRATO_RGE_v1.json',
    
    # ELEKTRO
    ('ELEKTRO', 'ADESAO', 5): 'maps/ELEKTRO_05p_v1.json',
    ('ELEKTRO', 'ADITIVO', 5): 'maps/CEMIG_Aditivo_Condicoes_v1.json',
    
    # ENERGISA
    ('ENERGISA', 'ADESAO', 5): 'maps/ENERGISA_MT_05p_v1.json',
    ('ENERGISA', 'ADITIVO', 5): 'maps/ENERGISA_MT_Aditivo_v1.json',
    
    # CELPE
    ('CELPE', 'ADESAO', 5): 'maps/CELPE_05p_v1.json',
    ('CELPE', 'ADITIVO', 5): 'maps/CEMIG_Aditivo_Condicoes_v1.json',
    
    # EDP
    ('EDP', 'ADESAO', 5): 'maps/CPFL_05p_v1.json',
    ('EDP', 'ADITIVO', 5): 'maps/CEMIG_Aditivo_Condicoes_v1.json',
    
    # RGE
    ('RGE', 'ADESAO', 5): 'maps/CPFL_05p_v1.json',
    ('RGE', 'DISTRATO', 5): 'maps/DISTRATO_RGE_v1.json',
    
    # Fallback
    ('DESCONHECIDA', 'ADESAO', 5): 'maps/CPFL_05p_v1.json',
    ('DESCONHECIDA', 'ADITIVO', 5): 'maps/CEMIG_Aditivo_Condicoes_v1.json',
    ('DESCONHECIDA', 'DISTRATO', 5): 'maps/DISTRATO_RGE_v1.json',
}



def classificar_documento(text: str, filename: str) -> str:
    """Classifica o tipo de documento."""
    text_upper = text.upper()
    filename_upper = filename.upper()
    
    if 'DISTRATO' in text_upper or 'DISTRATO' in filename_upper:
        return 'DISTRATO'
    
    if any(termo in text_upper for termo in ['ADITIVO CONTRATUAL', 'TERMO DE ADITIVO', 'ADT CONDICOES']):
        return 'ADITIVO'
    if 'ADT' in filename_upper and 'CONDICOES' in filename_upper:
        return 'ADITIVO'
    
    return 'ADESAO'


def detectar_distribuidora(text: str, filename: str, parent_folder: str = '') -> str:
    """Detecta a distribuidora do documento."""
    # Primeiro tenta pelo nome do arquivo
    distribuidoras = ['CEMIG', 'CPFL', 'ENEL', 'ELEKTRO', 'ENERGISA', 'CELPE', 'LIGHT', 'EDP', 'COPEL']
    
    filename_upper = filename.upper()
    for dist in distribuidoras:
        if dist in filename_upper:
            return dist
    
    # Tenta pelo conteudo
    text_upper = text.upper()
    for dist in distribuidoras:
        if dist in text_upper:
            return dist
    
    # Fallback: pasta pai
    if parent_folder:
        parent_upper = parent_folder.upper()
        for dist in distribuidoras:
            if dist in parent_upper:
                return dist
    
    return 'DESCONHECIDA'


def extract_with_map(text: str, mapa: dict) -> dict:
    """Extrai campos usando o mapa."""
    resultado = {}
    campos = mapa.get('campos', {})
    
    for campo, config in campos.items():
        if not config or not config.get('encontrado', True):
            resultado[campo] = None
            continue
        
        regex = config.get('regex', '')
        if not regex:
            resultado[campo] = None
            continue
        
        try:
            pattern = re.compile(regex, re.IGNORECASE | re.MULTILINE)
            match = pattern.search(text)
            
            if match:
                valor = match.group(1) if match.groups() else match.group(0)
                resultado[campo] = valor.strip()
            else:
                resultado[campo] = None
                
        except Exception:
            resultado[campo] = None
    
    return resultado


def processar_pdf(pdf_path: str, base_dir: str) -> dict:
    """Processa um PDF com classificacao automatica."""
    try:
        path = Path(pdf_path)
        
        with open_pdf(pdf_path) as pdf:
            num_paginas = len(pdf.pages)
            text = extract_all_text_from_pdf(pdf, max_pages=10, use_ocr_fallback=False)
        
        # Classificar
        tipo_doc = classificar_documento(text, path.name)
        distribuidora = detectar_distribuidora(text, path.name, path.parent.name)
        
        # Buscar mapa apropriado
        chave = (distribuidora, tipo_doc, num_paginas)
        mapa_path = MAPA_DOCUMENTOS.get(chave)
        
        # Fallback: tentar sem num_paginas
        if not mapa_path:
            for (d, t, p), mp in MAPA_DOCUMENTOS.items():
                if d == distribuidora and t == tipo_doc:
                    mapa_path = mp
                    break
        
        if not mapa_path:
            return {
                'status': 'sem_mapa',
                'dados': {
                    'arquivo_origem': path.name,
                    'distribuidora': distribuidora,
                    'tipo_documento': tipo_doc,
                    'num_paginas': num_paginas,
                    'erro': f'Sem mapa para {chave}'
                }
            }
        
        # Carregar mapa e extrair
        mapa_full_path = Path(base_dir) / mapa_path
        with open(mapa_full_path, 'r', encoding='utf-8') as f:
            mapa = json.load(f)
        
        dados = extract_with_map(text, mapa)
        dados['arquivo_origem'] = path.name
        dados['caminho_completo'] = str(path.resolve())
        dados['data_extracao'] = datetime.now().isoformat()
        dados['modelo_usado'] = mapa.get('modelo_identificado', 'N/A')
        dados['tipo_documento'] = tipo_doc
        dados['distribuidora_detectada'] = distribuidora
        
        # Normalizar
        dados = normalize_all(dados)
        
        # Calcular confianca
        campos_preenchidos = sum(1 for v in dados.values() if v and v not in ['N/A', None])
        total_campos = len(mapa.get('campos', {}))
        confianca = int((campos_preenchidos / total_campos) * 100) if total_campos > 0 else 0
        dados['confianca_score'] = confianca
        
        return {'status': 'sucesso', 'dados': dados}
        
    except Exception as e:
        return {
            'status': 'erro',
            'dados': {
                'arquivo_origem': Path(pdf_path).name,
                'erro': str(e),
                'confianca_score': 0
            }
        }


def executar_extracao(pasta_pdfs: str, output_dir: str, workers: int = 4):
    """Executa extracao em todos os PDFs da pasta."""
    pasta = Path(pasta_pdfs)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    
    base_dir = Path(__file__).parent.parent
    
    print("=" * 70)
    print("PIPELINE DE EXTRACAO INTELIGENTE")
    print("=" * 70)
    print(f"Pasta: {pasta}")
    
    pdfs = list(pasta.rglob('*.pdf'))
    print(f"PDFs encontrados: {len(pdfs)}")
    
    resultados = []
    sem_mapa = []
    erros = []
    
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(processar_pdf, str(pdf), str(base_dir)): pdf
            for pdf in pdfs
        }
        
        for i, future in enumerate(as_completed(futures), 1):
            resultado = future.result()
            
            if resultado['status'] == 'sucesso':
                resultados.append(resultado['dados'])
            elif resultado['status'] == 'sem_mapa':
                sem_mapa.append(resultado['dados'])
            else:
                erros.append(resultado['dados'])
            
            if i % 50 == 0:
                print(f"  Processados: {i}/{len(pdfs)}")
    
    # Separar por confianca
    validos = [r for r in resultados if r.get('confianca_score', 0) >= 70]
    revisao = [r for r in resultados if r.get('confianca_score', 0) < 70]
    
    print(f"\nResultados:")
    print(f"  Validos (>=70%): {len(validos)}")
    print(f"  Revisao (<70%): {len(revisao)}")
    print(f"  Sem mapa: {len(sem_mapa)}")
    print(f"  Erros: {len(erros)}")
    
    # Salvar CSVs
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    
    if validos:
        csv_path = output / f"extraidos_{timestamp}.csv"
        campos = list(validos[0].keys())
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=campos, delimiter=';')
            writer.writeheader()
            writer.writerows(validos)
        print(f"\nSalvo: {csv_path}")
    
    if sem_mapa:
        csv_sem_mapa = output / f"sem_mapa_{timestamp}.csv"
        campos = list(sem_mapa[0].keys())
        with open(csv_sem_mapa, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=campos, delimiter=';')
            writer.writeheader()
            writer.writerows(sem_mapa)
        print(f"Salvo: {csv_sem_mapa}")
    
    return {
        'validos': len(validos),
        'revisao': len(revisao),
        'sem_mapa': len(sem_mapa),
        'erros': len(erros)
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Pipeline de Extracao Inteligente")
    parser.add_argument("pasta", type=Path, help="Pasta com PDFs")
    parser.add_argument("-o", "--output", type=Path, default=Path("output/extracao_inteligente"))
    parser.add_argument("-w", "--workers", type=int, default=4)
    args = parser.parse_args()
    
    executar_extracao(str(args.pasta), str(args.output), args.workers)
