"""
Script para organizar PDFs em pastas pelo número de páginas.
Cria pastas como: 5_paginas, 8_paginas, etc.
"""
import pdfplumber
import shutil
from pathlib import Path
from collections import Counter
import warnings

warnings.filterwarnings('ignore')

# Configuração
PDF_DIR = Path(r"C:\Projetos\Raizen\data\raw\OneDrive_2026-01-06\TERMO DE ADESÃO")
OUTPUT_BASE = Path(r"C:\Projetos\Raizen\contratos_por_paginas")

def get_page_count(pdf_path: Path) -> int:
    """Retorna o número de páginas de um PDF."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            return len(pdf.pages)
    except Exception as e:
        print(f"Erro ao ler {pdf_path.name}: {e}")
        return -1  # Erro

def organize_pdfs():
    """Organiza PDFs em pastas por número de páginas."""
    
    # Criar pasta base
    OUTPUT_BASE.mkdir(exist_ok=True)
    
    # Listar PDFs
    pdf_files = list(PDF_DIR.glob("*.pdf"))
    total = len(pdf_files)
    
    print(f"Total de PDFs: {total}")
    print(f"Pasta de destino: {OUTPUT_BASE}")
    print()
    print("Analisando...")
    
    # Contadores
    page_counts = Counter()
    errors = []
    
    for i, pdf_path in enumerate(pdf_files):
        # Progresso
        if (i + 1) % 500 == 0:
            print(f"  {i+1}/{total}...")
        
        # Obter número de páginas
        pages = get_page_count(pdf_path)
        
        if pages == -1:
            errors.append(pdf_path.name)
            # Criar pasta de erros
            error_dir = OUTPUT_BASE / "ERRO_LEITURA"
            error_dir.mkdir(exist_ok=True)
            shutil.copy2(pdf_path, error_dir / pdf_path.name)
            continue
        
        page_counts[pages] += 1
        
        # Criar pasta para esse número de páginas
        folder_name = f"{pages:02d}_paginas"
        dest_dir = OUTPUT_BASE / folder_name
        dest_dir.mkdir(exist_ok=True)
        
        # Copiar arquivo (não mover, para segurança)
        dest_path = dest_dir / pdf_path.name
        if not dest_path.exists():
            shutil.copy2(pdf_path, dest_path)
    
    # Estatísticas
    print()
    print("=" * 50)
    print("RESULTADO")
    print("=" * 50)
    print()
    print("DISTRIBUIÇÃO POR NÚMERO DE PÁGINAS:")
    print("-" * 40)
    
    for pages, count in sorted(page_counts.items()):
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        print(f"{pages:3d} págs: {count:5d} ({pct:5.1f}%) {bar}")
    
    print()
    print(f"Total processado: {sum(page_counts.values())}")
    print(f"Erros: {len(errors)}")
    
    if errors:
        print()
        print("Arquivos com erro:")
        for e in errors[:10]:
            print(f"  - {e}")
        if len(errors) > 10:
            print(f"  ... e mais {len(errors) - 10}")
    
    print()
    print(f"Pastas criadas em: {OUTPUT_BASE}")

if __name__ == "__main__":
    organize_pdfs()
