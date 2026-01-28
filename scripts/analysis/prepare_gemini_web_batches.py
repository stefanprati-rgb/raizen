import shutil
import os
from pathlib import Path

SOURCE_DIR = Path("output/clusters_amostragem")
OUTPUT_DIR = Path("output/lotes_gemini_web")

def main():
    if not SOURCE_DIR.exists():
        print("❌ Pasta de amostras não encontrada.")
        return

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    # Coletar todos os PDFs de amostra
    all_pdfs = list(SOURCE_DIR.glob("*/*.pdf"))
    total_pdfs = len(all_pdfs)
    
    print(f"📦 Organizando {total_pdfs} amostras para o Gemini Web...")

    batch_size = 10
    
    for i in range(0, total_pdfs, batch_size):
        batch_num = (i // batch_size) + 1
        batch_folder = OUTPUT_DIR / f"lote_{batch_num:02d}"
        batch_folder.mkdir()
        
        batch_files = all_pdfs[i : i + batch_size]
        
        for file in batch_files:
            # Manter nome original + info do cluster no nome para facilitar
            cluster_name = file.parent.name
            new_name = f"[{cluster_name}] {file.name}"
            shutil.copy2(file, batch_folder / new_name)
            
        print(f"   ✅ Lote {batch_num:02d}: {len(batch_files)} arquivos")

    print(f"\n✨ Tudo pronto em: {OUTPUT_DIR}")
    print("Agora você pode arrastar cada pasta inteira para o chat do Gemini!")

if __name__ == "__main__":
    main()
