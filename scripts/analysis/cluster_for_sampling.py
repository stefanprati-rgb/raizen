import json
import shutil
import os
from pathlib import Path
from collections import defaultdict
import logging

# Configuração
INPUT_JSON = Path("output/cache/extraction_full_results.json")
OUTPUT_BASE = Path("output/clusters_amostragem")
PROCESSED_DIR = Path("data/processed")

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

def index_files(directory):
    """Indexa todos os PDFs por nome para busca rápida."""
    logger.info(f"Indexando arquivos em {directory}...")
    file_map = {}
    count = 0
    for path in directory.rglob("*.pdf"):
        file_map[path.name] = path
        count += 1
    logger.info(f"Indexados {count} arquivos.")
    return file_map

def main():
    if not INPUT_JSON.exists():
        logger.error(f"Arquivo {INPUT_JSON} não encontrado!")
        return

    # 1. Indexar arquivos reais no disco
    real_files_map = index_files(PROCESSED_DIR)

    logger.info("Carregando resultados da extração...")
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    results = data.get("results", [])
    logger.info(f"Total de documentos no JSON: {len(results)}")

    # 2. Agrupar
    clusters = defaultdict(list)
    found_count = 0
    missing_count = 0
    
    for r in results:
        dist = r.get("distributor", "DESCONHECIDO")
        pages = r.get("pages", 0)
        filename = r.get("file") or Path(r.get("path", "")).name
        
        if not filename or pages == 0:
            continue
            
        # Tentar encontrar arquivo real
        real_path = real_files_map.get(filename)
        
        if not real_path:
            # Tentar encontrar ignorando sufixos que as vezes o extrator adiciona? 
            # (Ex: .pdf vs .PDF)
            # Por enquanto, contabiliza como missing
            missing_count += 1
            continue
            
        found_count += 1
        
        # Cluster Key: DISTRIBUIDORA_PAGINAS
        cluster_key = f"{dist}_{pages:02d}p"
        
        clusters[cluster_key].append({
            "original_record": r,
            "real_path": real_path
        })

    logger.info(f"Docs encontrados no disco: {found_count}")
    logger.info(f"Docs não encontrados: {missing_count}")
    logger.info(f"Clusters identificados: {len(clusters)}")

    # 3. Criar Amostras
    if OUTPUT_BASE.exists():
        shutil.rmtree(OUTPUT_BASE)
    OUTPUT_BASE.mkdir(parents=True)

    summary = []
    
    # Ordenar clusters por tamanho
    sorted_keys = sorted(clusters.keys(), key=lambda k: len(clusters[k]), reverse=True)
    
    for key in sorted_keys:
        items = clusters[key]
        count = len(items)
        
        # Pegar amostra (primeiro arquivo que existe - todos existem aqui)
        sample = items[0]
        
        # Copiar PDF
        clean_key = key.replace(" ", "_").replace("/", "-")
        dest_folder = OUTPUT_BASE / clean_key
        dest_folder.mkdir()
        
        src = sample["real_path"]
        dst = dest_folder / f"AMOSTRA_{clean_key}.pdf"
        
        try:
            shutil.copy2(src, dst)
            
            # Criar info.txt
            with open(dest_folder / "info.txt", "w", encoding="utf-8") as f:
                f.write(f"Cluster: {key}\n")
                f.write(f"Total Arquivos: {count}\n")
                f.write(f"Amostra Original: {src}\n")
                
                # Listar nomes de alguns arquivos do grupo
                f.write("\n--- Arquivos no Grupo (Top 10) ---\n")
                for item in items[:10]:
                    f.write(f"- {item['real_path'].name}\n")

            summary.append({
                "cluster": key,
                "count": count,
                "sample_path": str(dst)
            })
            # logger.info(f"✅ {key}: {count} docs -> Salvo.")
            
        except Exception as e:
            logger.error(f"Erro ao copiar {src}: {e}")

    # Salvar resumo geral
    with open(OUTPUT_BASE / "cluster_report.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        
    logger.info(f"\nProcesso concluído! {len(summary)} amostras geradas em: {OUTPUT_BASE}")

if __name__ == "__main__":
    main()
