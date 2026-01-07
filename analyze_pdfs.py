"""
Script para analisar a estrutura dos PDFs (versão rápida com amostragem).
"""
import pdfplumber
import os
from pathlib import Path
import re
import warnings
warnings.filterwarnings('ignore')

PDF_DIR = r"c:\Projetos\Raizen\OneDrive_2026-01-06\TERMO DE ADESÃO"

def extract_text_from_pdf(pdf_path, max_pages=2):
    """Extrai texto de um PDF."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for i, page in enumerate(pdf.pages[:max_pages]):
                page_text = page.extract_text() or ""
                text += f"\n--- PÁGINA {i+1} ---\n{page_text}"
            return text, len(pdf.pages)
    except Exception as e:
        return f"ERRO: {e}", 0

def analyze_sample():
    """Analisa amostras específicas dos PDFs."""
    pdf_files = list(Path(PDF_DIR).glob("*.pdf"))
    
    output = []
    output.append("="*80)
    output.append(f"ANÁLISE DE AMOSTRA - Total: {len(pdf_files)} arquivos")
    output.append("="*80)
    
    # Buscar exemplos específicos
    samples_to_find = [
        # Termos de Adesão GD
        ("GD TERMO ADESAO", lambda f: f.name.startswith("GD") and "DISTRATO" not in f.name.upper() and "ADITIVO" not in f.name.upper() and "CONFISS" not in f.name.upper()),
        # Termos de Adesão SOLAR  
        ("SOLAR TERMO ADESAO", lambda f: f.name.startswith("SOLAR") and "DISTRATO" not in f.name.upper() and "ADITIVO" not in f.name.upper() and "CONFISS" not in f.name.upper() and "CONDICOES" not in f.name.upper()),
        # Termos de Adesão TERMO ADESAO
        ("TERMO ADESAO", lambda f: f.name.upper().startswith("TERMO ADESAO")),
        # Outros formatos
        ("CORPOREOS", lambda f: "CORPOREOS" in f.name.upper()),
        ("FORTBRAS", lambda f: "FORTBRAS" in f.name.upper()),
    ]
    
    for sample_name, filter_func in samples_to_find:
        matching = [f for f in pdf_files if filter_func(f)]
        output.append(f"\n\n{'='*80}")
        output.append(f"TIPO: {sample_name} - {len(matching)} arquivos encontrados")
        output.append("="*80)
        
        if matching:
            sample_file = matching[0]
            output.append(f"\nArquivo: {sample_file.name}")
            output.append(f"Tamanho: {sample_file.stat().st_size / 1024:.1f} KB")
            
            text, num_pages = extract_text_from_pdf(sample_file, max_pages=3)
            output.append(f"Páginas: {num_pages}")
            output.append("\n" + "-"*60)
            output.append(text[:6000])
            output.append("-"*60)
    
    with open("pdf_analysis_sample.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    
    print("Análise salva em pdf_analysis_sample.txt")

if __name__ == "__main__":
    analyze_sample()
