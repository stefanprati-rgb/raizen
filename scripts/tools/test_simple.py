"""Teste simples do Gemini"""
import sys
from pathlib import Path
sys.path.insert(0, '.')

from src.extrator_contratos.gemini_client import GeminiClient
from src.extrator_contratos.table_extractor import extract_all_text_from_pdf, open_pdf

# Encontrar PDF
pdf_files = list(Path('contratos_por_paginas').rglob('*.pdf'))[:1]
if pdf_files:
    pdf_path = pdf_files[0]
    print(f'PDF: {pdf_path.name}')
    
    # Extrair texto usando context manager
    with open_pdf(str(pdf_path)) as pdf:
        text = extract_all_text_from_pdf(pdf, max_pages=3)
    print(f'Texto: {len(text)} chars')
    
    # Testar Gemini
    client = GeminiClient()
    print('Conectado ao Gemini!')
    
    print('Gerando mapeamento...')
    mapa = client.generate_mapping(text[:20000], grupo='TESTE')
    
    print('Campos encontrados:')
    for campo, config in mapa.get('campos', {}).items():
        if config:
            valor = config.get('valor_amostra', 'N/A')
            print(f'  - {campo}: {valor}')
    
    # Salvar resultado
    import json
    Path('maps').mkdir(exist_ok=True)
    with open('maps/teste_result.json', 'w', encoding='utf-8') as f:
        json.dump(mapa, f, ensure_ascii=False, indent=2)
    print('Mapa salvo em maps/teste_result.json')
else:
    print('Nenhum PDF encontrado')
