import os
import sys
import json
import time
import argparse
from pathlib import Path

# Adicionar raiz ao path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Importar função de análise do script existente
try:
    from scripts.analysis.analyze_pdf_gemini import analyze_pdf_with_gemini
except ImportError:
    print("Erro ao importar analyze_pdf_gemini. Verifique se o arquivo existe.")
    sys.exit(1)

CLUSTERS_DIR = Path("output/clusters_amostragem")
MAPS_DIR = Path("maps")
MAPS_DIR.mkdir(exist_ok=True)

def get_clusters():
    """Lista todos os clusters com suas amostras."""
    clusters = []
    if not CLUSTERS_DIR.exists():
        return []
        
    for cluster_folder in CLUSTERS_DIR.iterdir():
        if cluster_folder.is_dir():
            # Buscar PDF de amostra
            pdfs = list(cluster_folder.glob("*.pdf"))
            if pdfs:
                # O nome da pasta é ex: CPFL_PAULISTA_05p
                name_parts = cluster_folder.name.rsplit("_", 1)
                dist = name_parts[0]
                pages_part = name_parts[1]
                pages = int(pages_part.replace("p", ""))
                
                clusters.append({
                    "folder": cluster_folder,
                    "pdf_path": pdfs[0], # Pega a primeira amostra
                    "dist": dist,
                    "pages": pages,
                    "key": cluster_folder.name
                })
    return clusters

def main():
    parser = argparse.ArgumentParser(description="Gera mapas automaticamente para todos os clusters identificados.")
    parser.add_argument("--api-key", help="Sua chave de API do Google Gemini (ou lista separada por vírgulas)")
    parser.add_argument("--limit", type=int, default=1000, help="Limite de mapas a gerar")
    args = parser.parse_args()
    
    api_key_input = args.api_key or os.environ.get("GEMINI_API_KEY")
    
    if not api_key_input:
        print("❌ ERRO: Necessário fornecer --api-key ou definir GEMINI_API_KEY")
        print("   Dica: Você pode passar múltiplas chaves separadas por vírgula para aumentar a cota!")
        print("   Ex: --api-key KEY1,KEY2,KEY3")
        return

    # Lista de chaves para rotação
    api_keys = [k.strip() for k in api_key_input.split(",") if k.strip()]
    print(f"🔑 {len(api_keys)} chaves de API carregadas para rotação.")

    clusters = get_clusters()
    print(f"🎯 Encontrados {len(clusters)} clusters para processar.")
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    current_key_idx = 0
    
    for i, cluster in enumerate(clusters[:args.limit]):
        print(f"\n[{i+1}/{len(clusters)}] Processando: {cluster['key']}")
        
        # Verificar se mapa já existe
        map_name = f"{cluster['key']}_v1.json"
        map_path = MAPS_DIR / map_name
        
        if map_path.exists():
            print(f"   ⏭️  Mapa já existe: {map_name} (Pulando)")
            skip_count += 1
            continue
            
        # Tentar com rotação de chaves em caso de erro de cota
        attempts = 0
        max_attempts = len(api_keys) # Tentar todas as chaves se necessário
        
        while attempts < max_attempts:
            # Selecionar chave (Round Robin)
            current_key = api_keys[current_key_idx % len(api_keys)]
            
            try:
                # Chamar Gemini
                map_data = analyze_pdf_with_gemini(
                    pdf_path=cluster['pdf_path'],
                    distributor=cluster['dist'],
                    pages=cluster['pages'],
                    api_key=current_key,
                    model_name="gemini-2.5-flash-lite"
                )
                
                if map_data:
                    with open(map_path, "w", encoding="utf-8") as f:
                        json.dump(map_data, f, indent=4, ensure_ascii=False)
                    print(f"   ✅ Salvo em: {map_name}")
                    success_count += 1
                    
                    # Avançar para próxima chave para distribuir carga
                    current_key_idx += 1
                    time.sleep(2) # Delay menor pois estamos rotacionando
                    break # Sucesso, sair do loop de tentativas
                else:
                    # Falha não relacionada a cota (erro de lógica/modelo)
                    print("   ❌ Falha ao gerar mapa (resposta vazia)")
                    error_count += 1
                    break
                    
            except Exception as e:
                # Se for erro de cota (429), tentar próxima chave
                if "429" in str(e) or "Resource exhausted" in str(e):
                    print(f"   ⚠️ Cota excedida na chave {current_key_idx % len(api_keys) + 1}. Trocando chave...")
                    current_key_idx += 1
                    attempts += 1
                    time.sleep(1)
                else:
                    print(f"   ❌ Erro na API: {e}")
                    error_count += 1
                    break
            
    print(f"\n{'='*40}")
    print(f"🏁 Concluído!")
    print(f"   Criados: {success_count}")
    print(f"   Pulados (já existiam): {skip_count}")
    print(f"   Erros: {error_count}")
    
    if success_count > 0:
        print("\n🚀 Agora você pode rodar a extração completa novamente para usar os novos mapas!")

if __name__ == "__main__":
    main()
