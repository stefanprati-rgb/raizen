import json
import shutil
from pathlib import Path
from collections import defaultdict

V5_RESULTS_PATH = Path('output/cpfl_paulista_final/cpfl_v5_full_results.json')
INVESTIGATION_DIR = Path('output/investigar_vazios')

def main():
    print("Loading V5 results...")
    with open(V5_RESULTS_PATH, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    # Filter empty results
    empty_docs = [r for r in results if r['status'] == 'VAZIO']
    
    print(f"Total empty: {len(empty_docs)}")
    print("=" * 50)
    
    # Group by type
    by_type = defaultdict(list)
    for r in empty_docs:
        by_type[r['type']].append(r)
    
    # Create investigation folders and copy samples
    INVESTIGATION_DIR.mkdir(parents=True, exist_ok=True)
    
    for doc_type, docs in sorted(by_type.items(), key=lambda x: -len(x[1])):
        print(f"\n{doc_type}: {len(docs)} files")
        
        # Create subfolder
        type_dir = INVESTIGATION_DIR / doc_type
        type_dir.mkdir(exist_ok=True)
        
        # Copy up to 3 samples for each type
        samples = docs[:3]
        for i, doc in enumerate(samples, 1):
            src = Path(doc['path'])
            if src.exists():
                dst = type_dir / f"sample_{i:02d}_{src.name}"
                try:
                    shutil.copy2(src, dst)
                    print(f"  - Copied: {src.name[:60]}...")
                except Exception as e:
                    print(f"  - Error copying {src.name}: {e}")
            else:
                print(f"  - NOT FOUND: {src}")
        
        # Create list file
        list_file = type_dir / "ALL_FILES.txt"
        with open(list_file, 'w', encoding='utf-8') as f:
            for doc in docs:
                f.write(f"{doc['file']}\n")
        print(f"  - Created list: {list_file.name}")
    
    print("\n" + "=" * 50)
    print(f"Investigation folder: {INVESTIGATION_DIR.absolute()}")
    print("Samples copied for each type. Review them manually or with Gemini.")

if __name__ == "__main__":
    main()
