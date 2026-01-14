"""
Script para Organização de PDFs por Distribuidora
Identifica a distribuidora no texto e move o arquivo para a subpasta correta.
"""
import os
import shutil
import sys
from pathlib import Path

# Adicionar path para importar módulos do projeto
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extrator_contratos.table_extractor import open_pdf, extract_all_text_from_pdf

DISTRIBUIDORAS_KEYWORDS = {
    'CEMIG': ['CEMIG', 'CEMIG-D', 'MINAS GERAIS'],
    'CPFL': ['CPFL', 'PAULISTA', 'PIRATININGA', 'SANTA CRUZ'],
    'ENEL': ['ENEL', 'ELETROPAULO', 'COELCE', 'AMPLA'],
    'ENERGISA': ['ENERGISA'],
    'ELEKTRO': ['ELEKTRO'],
    'LIGHT': ['LIGHT'],
    'COELBA': ['COELBA', 'NEOENERGIA'],
    'CELPE': ['CELPE'],
    'EQUATORIAL': ['EQUATORIAL', 'CELPA', 'CEMAR'],
    'CELESC': ['CELESC'],
    'COPEL': ['COPEL'],
    'EDP': ['EDP', 'ESC'],
    'RGE': ['RGE', 'SUL'],
}

def identify_distributor(text):
    text_upper = text.upper()
    for dist, keywords in DISTRIBUIDORAS_KEYWORDS.items():
        for kw in keywords:
            if kw in text_upper:
                return dist
    return 'DIVERSOS'

def organize_folder(folder_path):
    working_dir = Path(folder_path)
    print(f"📂 Organizando pasta: {working_dir}")
    
    # Listar apenas arquivos na raiz (pdfs soltos)
    files = [f for f in working_dir.iterdir() if f.is_file() and f.suffix.lower() == '.pdf']
    print(f"📄 Encontrados {len(files)} PDFs soltos.")
    
    stats = {}
    
    for pdf_file in files:
        try:
            # Extrair texto das primeiras 3 páginas para ser mais rápido
            with open_pdf(str(pdf_file)) as pdf:
                text = extract_all_text_from_pdf(pdf, max_pages=3, use_ocr_fallback=False)
            
            dist = identify_distributor(text)
            
            # Criar pasta se não existir
            dist_folder = working_dir / dist
            dist_folder.mkdir(exist_ok=True)
            
            # Mover arquivo
            dest_path = dist_folder / pdf_file.name
            
            # Se já existir arquivo com mesmo nome, renomear para evitar conflito
            if dest_path.exists():
                name_stem = pdf_file.stem
                counter = 1
                while (dist_folder / f"{name_stem}_{counter}.pdf").exists():
                    counter += 1
                dest_path = dist_folder / f"{name_stem}_{counter}.pdf"
            
            shutil.move(str(pdf_file), str(dest_path))
            
            stats[dist] = stats.get(dist, 0) + 1
            
        except Exception as e:
            print(f"❌ Erro ao processar {pdf_file.name}: {e}")
            # Mover para ERRO se não conseguir ler
            error_folder = working_dir / "ERRO_LEITURA"
            error_folder.mkdir(exist_ok=True)
            try:
                shutil.move(str(pdf_file), str(error_folder / pdf_file.name))
                stats['ERRO'] = stats.get('ERRO', 0) + 1
            except:
                pass

    print("\n✅ Concluído! Resumo da organização:")
    for dist, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        print(f"   - {dist}: {count}")

if __name__ == "__main__":
    organize_folder("contratos_por_paginas/09_paginas")
