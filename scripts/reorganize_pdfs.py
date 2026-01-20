"""
Reorganiza PDFs em pastas corretas baseado nos dados da extração.
Usa: páginas REAIS do PDF + distribuidora detectada no texto.
"""
import json
import shutil
from pathlib import Path
from collections import Counter
import argparse

# Paths
SOURCE_DIR = Path("OneDrive_2026-01-06/TERMO DE ADESÃO")
TARGET_DIR = Path("contratos_organizados")  # Nova pasta organizada
RESULTS_FILE = Path("output/extraction_full_results.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Apenas simular, não mover arquivos")
    parser.add_argument("--copy", action="store_true", help="Copiar ao invés de mover")
    args = parser.parse_args()
    
    print("=" * 60)
    print("REORGANIZADOR DE PDFs")
    print("=" * 60)
    
    # Carregar resultados da extração
    print("\nCarregando resultados da extração...")
    with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data['results']
    print(f"  {len(results)} arquivos com dados")
    
    # Criar estrutura de destino
    if not args.dry_run:
        TARGET_DIR.mkdir(exist_ok=True)
    
    # Estatísticas
    stats = {
        'total': 0,
        'moved': 0,
        'skipped': 0,
        'errors': 0
    }
    
    # Agrupar por combo para mostrar preview
    by_combo = Counter()
    for r in results:
        pages = r.get('pages', 0)
        dist = r.get('distributor', 'DESCONHECIDA')
        # Normalizar nome da distribuidora
        dist = dist.upper().replace(' ', '_').replace('-', '_')
        combo = f"{pages:02d}_paginas/{dist}"
        by_combo[combo] += 1
    
    print(f"\nDistribuição detectada:")
    for combo, count in by_combo.most_common(15):
        print(f"  {combo}: {count}")
    
    if args.dry_run:
        print(f"\n[DRY RUN] Simulação apenas, nenhum arquivo será movido.")
        print(f"Para executar de verdade, remova --dry-run")
        return
    
    # Processar cada arquivo
    print(f"\n{'Copiando' if args.copy else 'Movendo'} arquivos...")
    
    for i, r in enumerate(results, 1):
        stats['total'] += 1
        
        # Dados do arquivo
        file_name = r.get('file', '')
        source_path = SOURCE_DIR / file_name
        pages = r.get('pages', 0)
        dist = r.get('distributor', 'DESCONHECIDA')
        
        # Normalizar
        dist = dist.upper().replace(' ', '_').replace('-', '_')
        
        # Criar pasta destino
        dest_folder = TARGET_DIR / f"{pages:02d}_paginas" / dist
        dest_folder.mkdir(parents=True, exist_ok=True)
        
        dest_path = dest_folder / file_name
        
        try:
            if not source_path.exists():
                # Tentar caminho original do resultado
                source_path = Path(r.get('path', ''))
            
            if source_path.exists():
                if args.copy:
                    shutil.copy2(source_path, dest_path)
                else:
                    shutil.move(source_path, dest_path)
                stats['moved'] += 1
            else:
                stats['skipped'] += 1
                
        except Exception as e:
            stats['errors'] += 1
            if stats['errors'] <= 5:
                print(f"  Erro: {file_name}: {e}")
        
        if i % 500 == 0:
            print(f"  [{i}/{len(results)}] {stats['moved']} processados")
    
    # Resumo
    print(f"\n{'=' * 60}")
    print("RESUMO")
    print(f"{'=' * 60}")
    print(f"Total: {stats['total']}")
    print(f"{'Copiados' if args.copy else 'Movidos'}: {stats['moved']}")
    print(f"Ignorados: {stats['skipped']}")
    print(f"Erros: {stats['errors']}")
    print(f"\n📁 Estrutura criada em: {TARGET_DIR}")


if __name__ == "__main__":
    main()
