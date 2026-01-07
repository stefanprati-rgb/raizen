"""Verificar instalações do contrato OI."""
import pdfplumber
import sys
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, 'src')
from extrator_contratos.table_extractor import (
    find_anexo_i_page_from_pdf, 
    extract_installations_from_pdf,
    extract_tables_from_page_pdf,
    parse_installation_table
)

pdf_path = r'C:\Projetos\Raizen\OneDrive_2026-01-06\TERMO DE ADESÃO\GD - TERMO DE ADESÃO - SOLAR 17486 - OI SA EM RECUPERACAO JUDICIAL - 76535764032932.pdf.pdf'

with pdfplumber.open(pdf_path) as pdf:
    print(f'Total páginas: {len(pdf.pages)}')
    
    anexo_page = find_anexo_i_page_from_pdf(pdf)
    print(f'Página do Anexo I: {anexo_page}')
    
    # Verificar página 1 (tem tabelas)
    print('\n--- Tabelas na página 1 ---')
    tables = extract_tables_from_page_pdf(pdf, 0)
    print(f'Número de tabelas: {len(tables)}')
    
    for i, table in enumerate(tables):
        print(f'\nTabela {i+1} ({len(table)} linhas):')
        for row in table[:3]:
            print(f'  {row}')
        if len(table) > 3:
            print(f'  ... mais {len(table)-3} linhas')
    
    # Tentar extrair instalações
    installations = extract_installations_from_pdf(pdf)
    print(f'\n\nInstalações extraídas: {len(installations)}')
    
    if installations:
        for i, inst in enumerate(installations[:5]):
            print(f'  {i+1}. {inst}')
