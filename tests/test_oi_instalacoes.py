"""Verificar instalações do contrato OI."""
import fitz  # PyMuPDF
import sys
import warnings
warnings.filterwarnings('ignore')

# Import do módulo raizen_power
from raizen_power.extraction.table_extractor import (
    find_anexo_i_page_from_pdf, 
    extract_installations_from_pdf,
)

pdf_path = r'C:\Projetos\Raizen\data\processed\34_paginas\ENERGISA_MT\GD - TERMO DE ADESÃO - SOLAR 17486 - OI SA EM RECUPERACAO JUDICIAL - 76535764032932.pdf.pdf'

with fitz.open(pdf_path) as pdf:
    print(f'Total páginas: {len(pdf)}')
    
    anexo_page = find_anexo_i_page_from_pdf(pdf)
    print(f'Página do Anexo I: {anexo_page}')
    
    # Tentar extrair instalações
    installations = extract_installations_from_pdf(pdf)
    print(f'\n\nInstalações extraídas: {len(installations)}')
    
    if installations:
        for i, inst in enumerate(installations[:5]):
            print(f'  {i+1}. {inst}')
