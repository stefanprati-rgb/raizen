import os
import shutil
from pathlib import Path

BASE_DIR = Path("C:/Projetos/Raizen/data/processed")

# Mapa de Consolidação (De -> Para)
# Se o destino for o mesmo, apenas move das subpastas internas
MAPA_DISTRIBUIDORAS = {
    # CEMIG
    "CEMIG_D": "CEMIG",
    "CEMIG D": "CEMIG", 
    "MG_-_CEMIG": "CEMIG",
    "MG-CEMIG": "CEMIG",
    "CEMIG": "CEMIG",
    
    # CPFL
    "CPFL": "CPFL_PAULISTA", # Assumindo genérico como Paulista
    "CPFL_PAULISTA": "CPFL_PAULISTA",
    "SP_-_CPFL_PAULISTA": "CPFL_PAULISTA",
    "CPFL_PIRATININGA": "CPFL_PIRATININGA",
    "CPFL_SANTA_CRUZ": "CPFL_SANTA_CRUZ",
    
    # LIGHT
    "LIGHT": "LIGHT",
    "LIGHT_RJ": "LIGHT",
    "RJ_-_LIGHT": "LIGHT",
    
    # ELEKTRO
    "ELEKTRO": "ELEKTRO",
    "NEOENERGIA_ELEKTRO": "ELEKTRO",
    "SP_-_ELEKTRO": "ELEKTRO",
    
    # ENEL
    "ENEL_SP": "ENEL_SP",
    "ENEL_RJ": "ENEL_RJ",
    "ENEL_CE": "ENEL_CE",
    "ENEL_GO": "ENEL_GO",
    
    # Outros
    "NEOENERGIA_COELBA": "NEOENERGIA_COELBA",
    "COELBA": "NEOENERGIA_COELBA",
    "NEOENERGIA_PERNAMBUCO": "NEOENERGIA_PE",
    "CELPE": "NEOENERGIA_PE"
}

def clean_empty_dirs(path):
    for root, dirs, files in os.walk(path, topdown=False):
        for name in dirs:
            d = os.path.join(root, name)
            try:
                if not os.listdir(d):
                    os.rmdir(d)
                    print(f"🗑️ Removido vazio: {d}")
            except: pass

def main():
    print("="*60)
    print("ORGANIZADOR DE PASTAS (FLATTENING)")
    print("="*60)
    
    # 1. Identificar pastas de origem (ignorar raiz e output)
    # Procurar recursivamente por arquivos PDF
    
    moves = []
    
    for root, dirs, files in os.walk(BASE_DIR):
        if "output" in root or ".git" in root: continue
        
        path = Path(root)
        
        # Tentar identificar qual distribuidora essa pasta representa
        # Heuristica: Nome da pasta bate com alguma chave do mapa?
        # Ou nome da pasta pai?
        
        target_dist = None
        
        # Checar nome da pasta atual
        if path.name.upper() in MAPA_DISTRIBUIDORAS:
            target_dist = MAPA_DISTRIBUIDORAS[path.name.upper()]
        
        # Se não, checar pai (ex: 16_paginas/CEMIG)
        elif path.parent.name.upper() in MAPA_DISTRIBUIDORAS:
            target_dist = MAPA_DISTRIBUIDORAS[path.parent.name.upper()]
            
        if target_dist:
            target_dir = BASE_DIR / target_dist
            
            for f in files:
                if f.lower().endswith(".pdf"):
                    src = path / f
                    dst = target_dir / f
                    
                    # Evitar mover para si mesmo
                    if src.parent == target_dir:
                        continue
                        
                    # Tratar colisão de nomes
                    if dst.exists():
                        stem = dst.stem
                        suffix = dst.suffix
                        counter = 1
                        while dst.exists():
                            dst = target_dir / f"{stem}_{counter}{suffix}"
                            counter += 1
                    
                    moves.append((src, dst))

    print(f"Arquivos para mover: {len(moves)}")
    if len(moves) == 0:
        print("Nada a organizar.")
    else:
        # Confirmar? Não, o usuário já autorizou.
        print("Iniciando movimentação...")
        count = 0
        for src, dst in moves:
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(src, dst)
                count += 1
                if count % 100 == 0: print(f"Movidos: {count}")
            except Exception as e:
                print(f"Erro ao mover {src}: {e}")
                
        print(f"✅ Concluído! {count} arquivos reorganizados.")
    
    print("Limpando pastas vazias...")
    clean_empty_dirs(BASE_DIR)

if __name__ == "__main__":
    main()
