"""
Aplicador de Mapas de Extração em Lote
Aplica um mapa gerado pelo Gemini em todos os PDFs de um modelo.

Uso:
    python scripts/apply_map.py maps/DESCONHECIDO_CEMIG_v1.json contratos_por_paginas/05_paginas
    python scripts/apply_map.py maps/MODELO_v1.json pasta_pdfs --output output/extracao_modelo
"""
import sys
import json
import re
import csv
import argparse
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extrator_contratos.table_extractor import open_pdf, extract_all_text_from_pdf
from src.extrator_contratos.normalizers import normalize_all


def extract_with_map(text: str, mapa: dict) -> dict:
    """Extrai campos de um texto usando o mapa."""
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


def process_pdf_with_map(pdf_path: str, mapa: dict) -> dict:
    """Processa um PDF usando o mapa de extração."""
    try:
        with open_pdf(pdf_path) as pdf:
            text = extract_all_text_from_pdf(pdf, max_pages=10, use_ocr_fallback=False)
        
        dados = extract_with_map(text, mapa)
        dados['arquivo_origem'] = Path(pdf_path).name
        dados['caminho_completo'] = str(Path(pdf_path).resolve())
        dados['data_extracao'] = datetime.now().isoformat()
        dados['modelo_usado'] = mapa.get('modelo_identificado', 'N/A')
        
        # Normalizar
        dados = normalize_all(dados)
        
        # Calcular confiança
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


def apply_map_batch(map_path: Path, pdfs_folder: Path, output_folder: Path, workers: int = 4):
    """Aplica um mapa em todos os PDFs de uma pasta."""
    
    print("=" * 70)
    print("APLICAÇÃO DE MAPA EM LOTE")
    print("=" * 70)
    
    # Carregar mapa
    with open(map_path, 'r', encoding='utf-8') as f:
        mapa = json.load(f)
    
    modelo = mapa.get('modelo_identificado', map_path.stem)
    distribuidora = mapa.get('distribuidora_principal', 'N/A')
    
    print(f"\n📋 Mapa: {map_path.name}")
    print(f"   Modelo: {modelo}")
    print(f"   Distribuidora: {distribuidora}")
    
    # Listar PDFs
    pdf_files = list(pdfs_folder.rglob('*.pdf'))
    print(f"\n📁 Pasta: {pdfs_folder}")
    print(f"   PDFs encontrados: {len(pdf_files)}")
    
    if not pdf_files:
        print("❌ Nenhum PDF encontrado!")
        return
    
    # Processar em paralelo
    print(f"\n🔄 Processando com {workers} workers...")
    
    resultados = []
    erros = []
    
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(process_pdf_with_map, str(pdf), mapa): pdf 
            for pdf in pdf_files
        }
        
        for i, future in enumerate(as_completed(futures), 1):
            try:
                resultado = future.result()
                if resultado['status'] == 'sucesso':
                    resultados.append(resultado['dados'])
                else:
                    erros.append(resultado['dados'])
            except Exception as e:
                erros.append({'erro': str(e)})
            
            if i % 50 == 0:
                print(f"   Processados: {i}/{len(pdf_files)}")
    
    # Separar por confiança
    validos = [r for r in resultados if r.get('confianca_score', 0) >= 70]
    revisao = [r for r in resultados if r.get('confianca_score', 0) < 70]
    
    print(f"\n✅ Concluído!")
    print(f"   Total: {len(resultados)}")
    print(f"   Válidos (>=70%): {len(validos)}")
    print(f"   Para revisão (<70%): {len(revisao)}")
    print(f"   Erros: {len(erros)}")
    
    # Salvar resultados
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # CSV de válidos
    if validos:
        csv_path = output_folder / f"{modelo}_extraidos.csv"
        campos = list(validos[0].keys())
        
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=campos, delimiter=';')
            writer.writeheader()
            writer.writerows(validos)
        
        print(f"\n💾 Salvos:")
        print(f"   - {csv_path}")
    
    # CSV de revisão
    if revisao:
        csv_revisao = output_folder / f"{modelo}_revisao.csv"
        campos = list(revisao[0].keys())
        
        with open(csv_revisao, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=campos, delimiter=';')
            writer.writeheader()
            writer.writerows(revisao)
        
        print(f"   - {csv_revisao}")
    
    # Relatório JSON
    relatorio = {
        'mapa': map_path.name,
        'modelo': modelo,
        'distribuidora': distribuidora,
        'total_pdfs': len(pdf_files),
        'validos': len(validos),
        'revisao': len(revisao),
        'erros': len(erros),
        'taxa_sucesso': f"{len(validos)/len(pdf_files)*100:.1f}%" if pdf_files else "0%",
        'data_execucao': datetime.now().isoformat()
    }
    
    relatorio_path = output_folder / f"{modelo}_relatorio.json"
    with open(relatorio_path, 'w', encoding='utf-8') as f:
        json.dump(relatorio, f, ensure_ascii=False, indent=2)
    
    print(f"   - {relatorio_path}")
    
    return relatorio


def main():
    parser = argparse.ArgumentParser(description="Aplicador de Mapas em Lote")
    parser.add_argument("map_file", type=Path, help="Arquivo JSON do mapa")
    parser.add_argument("pdfs_folder", type=Path, help="Pasta com PDFs")
    parser.add_argument("--output", "-o", type=Path, default=Path("output/mapa_aplicado"),
                       help="Pasta de saída")
    parser.add_argument("--workers", "-w", type=int, default=4, help="Número de workers")
    
    args = parser.parse_args()
    
    if not args.map_file.exists():
        print(f"❌ Mapa não encontrado: {args.map_file}")
        return
    
    if not args.pdfs_folder.exists():
        print(f"❌ Pasta não encontrada: {args.pdfs_folder}")
        return
    
    apply_map_batch(args.map_file, args.pdfs_folder, args.output, args.workers)


if __name__ == "__main__":
    main()
