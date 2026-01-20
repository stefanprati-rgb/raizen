"""
Análise simplificada das divergências.
"""
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.extrator_contratos.table_extractor import open_pdf, extract_all_text_from_pdf

# Carregar dados
df_val = pd.read_excel('output/relatorio_validacao_automatica.xlsx')
df_am = pd.read_excel('output/amostra_validacao_50.xlsx')

divergencias = df_val[df_val['status'] == 'DIVERGENCIA']
print(f'Total divergencias: {len(divergencias)}')
print()

# Analisar 3 casos
casos_analisados = 0
erros_reais = 0
falsos_negativos = 0

for idx in divergencias.index[:3]:
    arquivo = divergencias.loc[idx, 'arquivo']
    print(f'=== CASO {casos_analisados+1}: {arquivo[:40]} ===')
    
    # Buscar dados da amostra
    matches = df_am[df_am['Arquivo Original'].str.contains(arquivo[:25], na=False, regex=False)]
    if matches.empty:
        print('  Arquivo não encontrado na amostra')
        continue
    
    row = matches.iloc[0]
    uc_excel = str(row['UC']) if pd.notna(row['UC']) else ''
    cnpj_excel = str(row['CNPJ']) if pd.notna(row['CNPJ']) else ''
    
    print(f'  UC Excel: {uc_excel}')
    print(f'  CNPJ Excel: {cnpj_excel}')
    
    # Buscar PDF
    pdf_path = None
    for pdf in Path('output/validacao_amostra_50').glob('*.pdf'):
        if arquivo[:25] in pdf.name:
            pdf_path = pdf
            break
    
    if not pdf_path:
        print('  PDF não encontrado')
        continue
    
    # Extrair texto
    with open_pdf(str(pdf_path)) as pdf:
        texto = extract_all_text_from_pdf(pdf, max_pages=3, use_ocr_fallback=False)
    
    # Verificar UC
    uc_encontrada = uc_excel in texto if uc_excel else False
    cnpj_encontrado = cnpj_excel in texto if cnpj_excel else False
    
    # Verificar CNPJ sem formatação
    if not cnpj_encontrado and cnpj_excel:
        cnpj_limpo = ''.join(c for c in cnpj_excel if c.isdigit())
        if cnpj_limpo in texto:
            cnpj_encontrado = True
            print('  CNPJ encontrado (sem formatação)')
    
    if uc_encontrada:
        falsos_negativos += 1
        print('  UC: ENCONTRADA (falso negativo do validador)')
    else:
        erros_reais += 1
        print('  UC: NAO ENCONTRADA (possível erro real)')
    
    if cnpj_encontrado:
        print('  CNPJ: ENCONTRADO')
    else:
        print('  CNPJ: NAO ENCONTRADO')
    
    casos_analisados += 1
    print()

print('=' * 50)
print(f'RESUMO: De {casos_analisados} casos analisados:')
print(f'  - Falsos negativos (script não encontrou mas existe): {falsos_negativos}')
print(f'  - Possíveis erros reais: {erros_reais}')
