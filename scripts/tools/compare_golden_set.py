import json
import argparse
from typing import Dict, Any, List
from collections import defaultdict
import pandas as pd

def normalize_value(val: Any) -> str:
    """Normaliza valores para comparação."""
    if val is None:
        return ""
    return str(val).strip().upper()

def compare_samples(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    stats = defaultdict(lambda: {"total": 0, "match": 0, "empty_real": 0, "empty_extracted": 0})
    errors = []

    for sample in samples:
        real = sample.get("real", {})
        extracted = sample.get("extraido", {})
        
        # Ignorar samples sem dados reais (erro no Document AI ou não processado)
        if not real or all(v is None for v in real.values()):
            continue

        for field in real.keys():
            stats[field]["total"] += 1
            
            val_real = normalize_value(real.get(field))
            val_ext = normalize_value(extracted.get(field))
            
            if not val_real:
                stats[field]["empty_real"] += 1
                # Se real é vazio, consideramos match se extraído também for vazio (ou ignoramos?)
                # Vamos considerar match se ambos vazios
                if not val_ext:
                     stats[field]["match"] += 1
                continue
            
            if not val_ext:
                stats[field]["empty_extracted"] += 1
            
            # Comparação flexível para alguns campos
            match = False
            if val_real == val_ext:
                match = True
            elif field == "cnpj" and val_real.replace(".", "").replace("/", "").replace("-", "") in val_ext.replace(".", "").replace("/", "").replace("-", ""):
                 match = True # CNPJ parcial ou formatação
            elif field in ["participacao_percentual", "duracao_meses", "aviso_previo"]:
                try:
                    # Tentar comparar como número
                    num_real = float(val_real.replace(",", "."))
                    num_ext = float(val_ext.replace(",", "."))
                    if abs(num_real - num_ext) < 0.01:
                        match = True
                except:
                    pass
            
            if match:
                stats[field]["match"] += 1
            else:
                errors.append({
                    "arquivo": sample.get("arquivo"),
                    "campo": field,
                    "esperado": val_real,
                    "encontrado": val_ext
                })

    return stats, errors

def main():
    parser = argparse.ArgumentParser(description="Comparar Extração vs Golden Set (Document AI)")
    parser.add_argument("--input", default="output/golden_set_100_docai.json", help="Arquivo Golden Set preenchido")
    parser.add_argument("--output", default="output/comparison_report.md", help="Relatório de saída")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    samples = data.get("amostras", [])
    stats, errors = compare_samples(samples)
    
    # Gerar Relatório
    report = "# Relatório de Comparação: Extrator Local vs Document AI\n\n"
    
    # Tabela de Resumo
    report += "## Resumo por Campo\n\n"
    report += "| Campo | Acurácia | Total Amostras | Falhas Extrator | Real Vazio |\n"
    report += "|-------|----------|----------------|-----------------|------------|\n"
    
    for field, metrics in stats.items():
        total_valid = metrics["total"] - metrics["empty_real"]
        if total_valid > 0:
            acc = (metrics["match"] / metrics["total"]) * 100 # Acurácia geral (incluindo vazios)
            # Acurácia sobre dados existentes
            matches_on_valid = metrics["match"] - (metrics["empty_real"] if metrics["empty_real"] == metrics["match"] else 0) # Simplificação
            
            # Vamos usar a contagem direta de matches
            acc = (metrics["match"] / metrics["total"]) * 100
            
            report += f"| {field} | {acc:.1f}% | {metrics['total']} | {metrics['empty_extracted']} | {metrics['empty_real']} |\n"
    
    # Detalhe dos Erros (Top 20)
    report += "\n## Amostra de Erros (Top 20)\n\n"
    for err in errors[:20]:
        report += f"- **{err['campo']}** em `{err['arquivo']}`\n"
        report += f"  - Esperado: `{err['esperado']}`\n"
        report += f"  - Encontrado: `{err['encontrado']}`\n"

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report)
        
    print(f"Relatório gerado em: {args.output}")

if __name__ == "__main__":
    main()
