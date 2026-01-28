import json
import argparse
from collections import Counter

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="output/golden_set_100_docai.json")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("=== Validação de Distribuidoras ===\n")
    
    comparativo = []
    
    for sample in data.get("amostras", []):
        ext = str(sample.get("extraido", {}).get("distribuidora") or "N/A")
        real = str(sample.get("real", {}).get("distribuidora") or "N/A")
        arquivo = sample.get("arquivo")
        
        # Simplificação para comparação visual
        comparativo.append(f"{ext:<20} | {real:<20} | {arquivo[:30]}...")

    print(f"{'EXTRATOR (Local)':<20} | {'DOC AI (Regex Poor)':<20} | ARQUIVO")
    print("-" * 70)
    
    # Mostrar primeiros 20 divergentes
    count = 0
    for line in comparativo:
        parts = line.split("|")
        local = parts[0].strip()
        docai = parts[1].strip()
        
        if local != docai:
            print(line)
            count += 1
            if count >= 30:
                break
    
    print("-" * 70)
    print(f"\nTotal amostras: {len(comparativo)}")
    print(f"Divergências exibidas: {count}")

if __name__ == "__main__":
    main()
