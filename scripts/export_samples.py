"""
Exporta um PDF de amostra para cada modelo detectado.
Copia os PDFs para uma pasta separada para facilitar upload no Gemini Web.
"""
import sys
import shutil
import json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extrator_contratos.table_extractor import open_pdf, extract_all_text_from_pdf

def extract_fingerprint(text):
    import re
    import hashlib
    
    LAYOUT_INDICATORS = {
        'SOLAR_RAIZEN': ['CONSÓRCIO RZ', 'CONSORCIADA (VOCÊ)', 'SOLAR', 'ANEXO I'],
        'SMARTFIT': ['DA QUALIFICAÇÃO DA CONSORCIADA', 'SmartFit'],
        'GUARDA_CHUVA': ['CONTRATO GUARDA-CHUVA', 'múltiplas instalações'],
    }
    
    DISTRIBUIDORAS = ['CEMIG', 'CPFL', 'ENEL', 'LIGHT', 'ELEKTRO', 'ENERGISA', 
                      'NEOENERGIA', 'EQUATORIAL', 'COELBA', 'CELPE', 'COSERN',
                      'EDP', 'CELESC', 'COPEL', 'CEEE', 'RGE', 'CELG']
    
    modelo = 'DESCONHECIDO'
    for m, indicators in LAYOUT_INDICATORS.items():
        if sum(1 for i in indicators if i.upper() in text.upper()) >= 2:
            modelo = m
            break
    
    distribuidora = 'OUTRAS'
    for d in DISTRIBUIDORAS:
        if d.upper() in text.upper():
            distribuidora = d
            break
    
    return f"{modelo}_{distribuidora}"


def main():
    source_folder = Path("contratos_por_paginas/05_paginas")
    output_folder = Path("output/pdfs_para_gemini_05p")
    output_folder.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("EXPORTANDO PDFs DE AMOSTRA PARA GEMINI WEB")
    print("=" * 70)
    
    pdf_files = list(source_folder.rglob('*.pdf'))
    print(f"\n📁 Pasta: {source_folder}")
    print(f"   Total PDFs: {len(pdf_files)}")
    
    # Agrupar por modelo
    models = defaultdict(list)
    
    for i, pdf_path in enumerate(pdf_files):
        try:
            with open_pdf(str(pdf_path)) as pdf:
                text = extract_all_text_from_pdf(pdf, max_pages=2, use_ocr_fallback=False)
            
            model_key = extract_fingerprint(text)
            models[model_key].append(pdf_path)
            
            if (i + 1) % 50 == 0:
                print(f"   Analisados: {i + 1}/{len(pdf_files)}")
                
        except Exception as e:
            continue
    
    print(f"\n📊 Modelos detectados: {len(models)}")
    print("-" * 70)
    
    # Copiar um PDF de cada modelo
    copied = []
    for model_key, files in sorted(models.items(), key=lambda x: -len(x[1])):
        sample = files[0]
        
        # Nome do arquivo de destino
        safe_name = model_key.replace('/', '_').replace('\\', '_')
        dest_name = f"{safe_name}_AMOSTRA.pdf"
        dest_path = output_folder / dest_name
        
        shutil.copy2(sample, dest_path)
        
        print(f"✅ {model_key}")
        print(f"   Quantidade: {len(files)} PDFs")
        print(f"   Amostra: {sample.name[:50]}...")
        print(f"   Copiado: {dest_name}")
        print()
        
        copied.append({
            'modelo': model_key,
            'quantidade': len(files),
            'arquivo_amostra': str(dest_path),
            'original': str(sample)
        })
    
    # Salvar resumo
    summary_file = output_folder / "resumo_modelos.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(copied, f, ensure_ascii=False, indent=2)
    
    print("=" * 70)
    print(f"📁 PDFs copiados para: {output_folder}")
    print(f"   Total modelos: {len(copied)}")
    print("\n🚀 PRÓXIMO PASSO:")
    print("   1. Abra https://gemini.google.com")
    print(f"   2. Faça upload de cada PDF em {output_folder}")
    print("   3. Use o prompt abaixo para cada PDF:")
    print()
    print('-' * 70)
    print("""
Analise o PDF anexo. Para cada campo abaixo, forneça:
1. O valor exato encontrado no texto.
2. A "âncora" (texto fixo que precede o valor).
3. Um REGEX Python robusto para capturar este valor.

Campos obrigatórios:
- sic_ec_cliente (código SIC/EC do cliente)
- razao_social (nome da empresa consorciada)
- cnpj (CNPJ da consorciada, formato XX.XXX.XXX/XXXX-XX)
- num_instalacao (número da UC/instalação)
- num_cliente (conta contrato)
- distribuidora (CEMIG, CPFL, ENEL, ELEKTRO, etc)
- participacao_percentual (% rateio, formato brasileiro com vírgula)
- duracao_meses (vigência em meses)
- data_adesao (data de assinatura)
- representante_nome (representante legal)
- email (e-mail de contato)

Retorne APENAS um JSON neste formato:
{
  "modelo_identificado": "Nome do layout/modelo",
  "distribuidora_principal": "CEMIG/CPFL/etc",
  "campos": {
    "razao_social": {
      "valor_encontrado": "EMPRESA X LTDA",
      "ancora": "Razão Social:",
      "regex": "Raz[ãa]o\\\\s*Social[:\\\\s]*([A-Z][A-Z0-9\\\\s\\\\.\\\\-]+)",
      "pagina": 1,
      "confianca": "alta"
    }
  },
  "campos_nao_encontrados": []
}
""")
    print('-' * 70)


if __name__ == "__main__":
    main()
