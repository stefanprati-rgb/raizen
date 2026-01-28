import os
import shutil
import re
import pdfplumber
from pathlib import Path
from collections import Counter
import logging

# Silenciar warnings chatos
logging.getLogger("pdfminer").setLevel(logging.ERROR)
logging.getLogger("pdfplumber").setLevel(logging.ERROR)

BASE_DIR = Path("C:/Projetos/Raizen/data/processed")

# Mapa de Regex para Identificação Rápida
PATTERNS = {
    "CPFL_PAULISTA": r"(CPFL\s*PAULISTA|COMPANHIA\s*PAULISTA\s*DE\s*FORCA)",
    "CPFL_PIRATININGA": r"(CPFL\s*PIRATININGA|COMPANHIA\s*PIRATININGA)",
    "CPFL_SANTA_CRUZ": r"(CPFL\s*SANTA\s*CRUZ)",
    "CEMIG": r"(CEMIG\s*DISTRIBUICAO|CEMIG\s*D)",
    "LIGHT": r"(LIGHT\s*SERVICOS|LIGHT\s*S\.A)",
    "ELEKTRO": r"(ELEKTRO\s*ELETRICIDADE|NEOENERGIA\s*ELEKTRO)",
    "ENEL_SP": r"(ELETROPAULO|ENEL\s*DISTRIBUICAO\s*SAO\s*PAULO)",
    "ENEL_RJ": r"(AMPLA|ENEL\s*DISTRIBUICAO\s*RIO)",
    "ENEL_CE": r"(COELCE|ENEL\s*DISTRIBUICAO\s*CEARA)",
    "COELBA": r"(COELBA|NEOENERGIA\s*COELBA)",
    "COPEL": r"(COPEL\s*DISTRIBUICAO)",
    "EDP": r"(EDP\s*SAO\s*PAULO|EDP\s*ESPIRITO\s*SANTO)"
}

def identify_distributor(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Ler apenas a primeira página (cabeçalho)
            if not pdf.pages: return None
            text = pdf.pages[0].extract_text().upper()
            
            for dist, pattern in PATTERNS.items():
                if re.search(pattern, text):
                    return dist
            return None
    except:
        return None  # Arquivo corrompido ou imagem pura sem OCR

def main():
    print("="*60)
    print("AUDITORIA DE PASTAS (CROSS-CHECK)")
    print("="*60)
    
    moves = [] # (src, dst)
    errors = 0
    correct = 0
    unknown = 0
    
    # 1. Caminhar por todas as pastas de distribuidoras
    # Assumindo que organize_folders.py já limpou a estrutura para processed/NOME_DA_PASTA/arquivo.pdf
    
    for root, dirs, files in os.walk(BASE_DIR):
        if "output" in root: continue
        
        current_folder = Path(root).name.upper()
        if current_folder == "PROCESSED": continue # Raiz
        
        print(f"Auditando pasta: {current_folder} ({len(files)} arquivos)...")
        
        for f in files:
            if not f.lower().endswith(".pdf"): continue
            
            pdf_path = Path(root) / f
            detected = identify_distributor(pdf_path)
            
            if detected:
                # Normalizar nomes para comparação
                # Ex: Se detectou 'CPFL_PAULISTA' e a pasta é 'CPFL_PAULISTA', ok.
                # Se detectou 'CEMIG' e a pasta é 'CEMIG', ok.
                
                # Regras de equivalência simples
                match = False
                if detected in current_folder: match = True # CEMIG in CEMIG ok
                if current_folder in detected: match = True # CPFL in CPFL_PAULISTA ok? Não necessariamente.
                
                # Refinamento:
                # Se pasta é CEMIG e arquivo é LIGHT -> Erro.
                # Se pasta é CPFL_PAULISTA e arquivo é CPFL_PIRATININGA -> Erro.
                
                if detected != current_folder:
                    # Caso Especial: "CPFL" genérico vs Paulista
                    if detected == "CPFL_PAULISTA" and current_folder == "CPFL": match = True # Aceitável se existir pasta CPFL
                    # Caso Especial: EDP SP na pasta EDP
                    if "EDP" in detected and "EDP" in current_folder: match = True
                    
                    if not match:
                        # Mover!
                        target_folder = BASE_DIR / detected
                        target_file = target_folder / f
                        print(f"⚠️  INTRUSO: {f} (É {detected}, está em {current_folder}) -> Movendo...")
                        moves.append((pdf_path, target_file))
                    else:
                        correct += 1
                else:
                    correct += 1
            else:
                unknown += 1 # Não conseguiu ler (OCR ou imagem)
                
    print(f"\nResumo da Auditoria:")
    print(f"✅ Certos: {correct}")
    print(f"❓ Desconhecidos (OCR/Img): {unknown}")
    print(f"🚀 Movimentos (Correções): {len(moves)}")
    
    if moves:
        print("Aplicando correções...")
        for src, dst in moves:
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                # Evitar overwrite
                if dst.exists():
                    dst = dst.with_name(f"{dst.stem}_moved{dst.suffix}")
                shutil.move(src, dst)
            except Exception as e:
                print(f"Erro move {src}: {e}")
                
    print("Auditoria Concluída.")

if __name__ == "__main__":
    main()
