"""
Validador de Mapas de Extração
Testa os regex gerados pelo Gemini contra o PDF original.

Uso:
    python scripts/validate_map.py maps/MODELO_v1.json
    python scripts/validate_map.py maps/MODELO_v1.json --pdf contratos/amostra.pdf
"""
import sys
import json
import re
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extrator_contratos.table_extractor import open_pdf, extract_all_text_from_pdf


def validate_map(map_path: Path, pdf_path: Path = None):
    """Valida um mapa de extração contra um PDF."""
    
    print("=" * 70)
    print("VALIDAÇÃO DE MAPA DE EXTRAÇÃO")
    print("=" * 70)
    
    # Carregar mapa
    with open(map_path, 'r', encoding='utf-8') as f:
        mapa = json.load(f)
    
    print(f"\n📄 Mapa: {map_path.name}")
    print(f"   Modelo: {mapa.get('modelo_identificado', 'N/A')}")
    print(f"   Distribuidora: {mapa.get('distribuidora_principal', 'N/A')}")
    
    # Encontrar PDF se não especificado
    if pdf_path is None:
        # Tentar encontrar pelo nome do modelo
        modelo = map_path.stem.replace('_v1', '').replace('_v2', '')
        pdf_candidates = list(Path('output/pdfs_para_gemini').glob(f'{modelo}*.pdf'))
        
        if pdf_candidates:
            pdf_path = pdf_candidates[0]
        else:
            print("\n❌ Nenhum PDF encontrado para validação!")
            print("   Use: --pdf <caminho_do_pdf>")
            return False
    
    print(f"\n📑 PDF: {pdf_path.name}")
    
    # Extrair texto do PDF
    with open_pdf(str(pdf_path)) as pdf:
        text = extract_all_text_from_pdf(pdf, max_pages=10, use_ocr_fallback=False)
    
    print(f"   Caracteres extraídos: {len(text):,}")
    
    # Validar cada campo
    print("\n" + "-" * 70)
    print("RESULTADOS DA VALIDAÇÃO")
    print("-" * 70)
    
    campos = mapa.get('campos', {})
    resultados = {
        'sucesso': [],
        'falha': [],
        'nao_encontrado': []
    }
    
    for campo, config in campos.items():
        if not config or not config.get('encontrado', False):
            resultados['nao_encontrado'].append(campo)
            continue
        
        regex = config.get('regex', '')
        valor_esperado = config.get('valor_extraido', '')
        ancora = config.get('ancora', '')
        
        if not regex:
            resultados['nao_encontrado'].append(campo)
            continue
        
        try:
            # Compilar e executar regex
            pattern = re.compile(regex, re.IGNORECASE | re.MULTILINE)
            match = pattern.search(text)
            
            if match:
                # Extrair valor
                valor_extraido = match.group(1) if match.groups() else match.group(0)
                valor_extraido = valor_extraido.strip()
                
                # Comparar com esperado
                norm_extraido = re.sub(r'\s+', '', valor_extraido.upper())
                norm_esperado = re.sub(r'\s+', '', valor_esperado.upper())
                
                if norm_extraido == norm_esperado:
                    status = "✅ OK"
                    resultados['sucesso'].append(campo)
                else:
                    status = "⚠️  DIFERENTE"
                    resultados['falha'].append(campo)
                
                print(f"\n{status} {campo}")
                print(f"   Esperado: {valor_esperado[:50]}")
                print(f"   Extraído: {valor_extraido[:50]}")
            else:
                print(f"\n❌ FALHA {campo}")
                print(f"   Regex não encontrou match")
                print(f"   Regex: {regex[:60]}...")
                resultados['falha'].append(campo)
                
        except re.error as e:
            print(f"\n❌ ERRO {campo}")
            print(f"   Regex inválido: {e}")
            resultados['falha'].append(campo)
    
    # Resumo
    print("\n" + "=" * 70)
    print("RESUMO")
    print("=" * 70)
    
    total = len(campos)
    sucesso = len(resultados['sucesso'])
    falha = len(resultados['falha'])
    nao_encontrado = len(resultados['nao_encontrado'])
    
    print(f"\n✅ Sucesso: {sucesso}/{total} ({sucesso/total*100:.0f}%)")
    print(f"❌ Falha: {falha}/{total}")
    print(f"⚪ Não encontrado: {nao_encontrado}/{total}")
    
    if resultados['falha']:
        print(f"\n⚠️  Campos com problema:")
        for campo in resultados['falha']:
            print(f"   - {campo}")
    
    # Veredicto
    if sucesso >= total * 0.8:
        print("\n🎉 MAPA APROVADO - Taxa de sucesso >= 80%")
        return True
    else:
        print("\n❌ MAPA REPROVADO - Necessário ajustar regex")
        return False


def main():
    parser = argparse.ArgumentParser(description="Validador de Mapas de Extração")
    parser.add_argument("map_file", type=Path, help="Arquivo JSON do mapa")
    parser.add_argument("--pdf", type=Path, help="PDF para validação (opcional)")
    
    args = parser.parse_args()
    
    if not args.map_file.exists():
        print(f"❌ Arquivo não encontrado: {args.map_file}")
        return
    
    validate_map(args.map_file, args.pdf)


if __name__ == "__main__":
    main()
