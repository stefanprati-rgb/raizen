import json
from pathlib import Path
from collections import defaultdict

def analyze_partial_cases(json_path: str):
    path = Path(json_path)
    if not path.exists():
        print(f"File not found: {json_path}")
        return

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data.get("results", [])
    partial_cases = [r for r in results if r.get("fields_extracted", 0) < 5]
    
    print(f"Total Partial Cases: {len(partial_cases)}")
    
    # Analyze by combo (Distributor + Pages)
    combos = defaultdict(list)
    for r in partial_cases:
        dist = r.get("distributor", "UNKNOWN")
        pages = r.get("pages", 0)
        combo = f"{dist}_{pages}p"
        combos[combo].append(r)
    
    # Sort combos by count
    sorted_combos = sorted(combos.items(), key=lambda x: len(x[1]), reverse=True)
    
    print("\nTop 15 Combos (Distributor + Pages) for Partial Extractions:")
    print("-" * 60)
    for combo, examples in sorted_combos[:15]:
        print(f"{combo:30}: {len(examples)} cases")
        # Show first 2 examples
        for ex in examples[:2]:
            print(f"  - {ex['file']}")

if __name__ == "__main__":
    analyze_partial_cases("output/extraction_full_results.json")
