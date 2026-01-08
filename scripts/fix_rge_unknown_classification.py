import shutil
from pathlib import Path
import sys

# Adicionar diretório scripts ao path para importar do super_organizer_v4
sys.path.append(str(Path(__file__).parent))

from super_organizer_v4 import identify_distributor, load_databases

# Configuração
BASE_DIR = Path(r"C:\Projetos\Raizen\contratos_por_paginas")
TARGET_DIRECTORIES = ["RGE", "OUTRAS_DESCONHECIDAS", "ERRO_LEITURA"]

def process_targeted():
    """
    Processa APENAS pastas específicas (RGE, Desconhecidas) aplicando a nova lógica de classificação.
    """
    print("🚀 Iniciando reclassificação FOCADA (RGE + Desconhecidas)...")
    load_databases()
    
    page_dirs = sorted([d for d in BASE_DIR.iterdir() if d.is_dir() and "paginas" in d.name])
    
    total_moved = 0
    total_processed = 0
    
    for p_dir in page_dirs:
        print(f"\n📂 Verificando: {p_dir.name}")
        
        # Listar arquivos APENAS nas pastas alvo
        files_to_process = []
        for target_name in TARGET_DIRECTORIES:
            target_path = p_dir / target_name
            if target_path.exists() and target_path.is_dir():
                found = list(target_path.glob("*.pdf"))
                if found:
                    print(f"   found {len(found)} contracts in '{target_name}'")
                    files_to_process.extend(found)
        
        if not files_to_process:
            continue
            
        print(f"   🔍 Reclassificando {len(files_to_process)} arquivos...")
        
        for i, pdf_path in enumerate(files_to_process):
            # Identificar nova distribuidora
            new_dist = identify_distributor(pdf_path)
            
            # Limpar nome (remover sufixos antigos se houver, mas aqui estamos pegando do super_organizer que retorna limpo)
            # O identify_distributor retorna ex: "CEMIG", "CPFL_PAULISTA"
            
            # Pasta de destino
            dest_dir = p_dir / new_dist[:50]
            dest_dir.mkdir(exist_ok=True)
            
            # Caminho final
            dest_path = dest_dir / pdf_path.name
            
            # Se o destino for diferente da pasta atual, mover
            # .parent.name dá o nome da pasta onde o arquivo está (ex: "RGE")
            current_folder = pdf_path.parent.name
            
            if new_dist != current_folder:
                print(f"      🔄 Movendo: {pdf_path.name}")
                print(f"         De: {current_folder} -> Para: {new_dist}")
                
                try:
                    shutil.move(str(pdf_path), str(dest_path))
                    total_moved += 1
                except Exception as e:
                    print(f"         ❌ Erro ao mover: {e}")
            
            total_processed += 1
            
            if (i+1) % 50 == 0:
                print(f"    Progresso: {i+1}/{len(files_to_process)}...")

    print(f"\n{'='*50}")
    print(f"RESUMO DA RECLASSIFICAÇÃO")
    print(f"{'='*50}")
    print(f"Total analisado: {total_processed}")
    print(f"Total movido/corrigido: {total_moved}")

if __name__ == "__main__":
    process_targeted()
