"""
Análise de Distribuição de Contratos para AI Mapping.
Identifica grupos prioritários para mapeamento com Gemini.

Saída:
- Contagem de PDFs por pasta (distribuidora + páginas)
- Ranking por volume (Pareto: 80/20)
- Estimativa de requisições necessárias
"""
import os
from pathlib import Path
from collections import defaultdict
import json

# Configuração
BASE_DIR = Path("contratos_por_paginas")
PDFS_PER_REQUEST = 3  # Quantos PDFs agregamos por requisição Gemini
MAX_REQUESTS_DAY = 20  # Limite do plano gratuito

def analyze_distribution():
    """Analisa a distribuição de PDFs por pasta."""
    
    distribution = defaultdict(lambda: {"count": 0, "sample_files": []})
    total_pdfs = 0
    
    # Percorrer todas as pastas
    for root, dirs, files in os.walk(BASE_DIR):
        pdf_files = [f for f in files if f.lower().endswith('.pdf')]
        
        if pdf_files:
            # Extrair informações do caminho
            rel_path = Path(root).relative_to(BASE_DIR)
            parts = str(rel_path).split(os.sep)
            
            if len(parts) >= 1:
                # Formato: "05_paginas" ou "05_paginas/CEMIG"
                pages_folder = parts[0]
                distributor = parts[1] if len(parts) > 1 else "ROOT"
                
                key = f"{pages_folder}/{distributor}"
                distribution[key]["count"] += len(pdf_files)
                distribution[key]["pages"] = pages_folder
                distribution[key]["distributor"] = distributor
                distribution[key]["path"] = str(root)
                
                # Guardar alguns exemplos
                if len(distribution[key]["sample_files"]) < 5:
                    distribution[key]["sample_files"].extend(pdf_files[:5])
                
                total_pdfs += len(pdf_files)
    
    return dict(distribution), total_pdfs

def calculate_priorities(distribution: dict, total_pdfs: int):
    """Calcula prioridades de mapeamento (Pareto 80/20)."""
    
    # Ordenar por volume
    sorted_groups = sorted(
        distribution.items(), 
        key=lambda x: x[1]["count"], 
        reverse=True
    )
    
    # Calcular acumulado para Pareto
    cumulative = 0
    pareto_80 = []
    
    for group, data in sorted_groups:
        cumulative += data["count"]
        pareto_80.append({
            "group": group,
            "count": data["count"],
            "percentage": round(data["count"] / total_pdfs * 100, 2),
            "cumulative_pct": round(cumulative / total_pdfs * 100, 2),
            "path": data["path"],
            "sample_files": data["sample_files"][:3]
        })
        
        if cumulative >= total_pdfs * 0.80:
            break
    
    return sorted_groups, pareto_80

def estimate_requests(total_groups: int, pdfs_per_req: int = 3):
    """Estima quantas requisições Gemini serão necessárias."""
    
    # 1 requisição por grupo (com PDFs agregados)
    requests_needed = total_groups
    days_needed = (requests_needed + MAX_REQUESTS_DAY - 1) // MAX_REQUESTS_DAY
    
    return requests_needed, days_needed

def main():
    print("=" * 70)
    print("ANÁLISE DE DISTRIBUIÇÃO PARA AI MAPPING")
    print("=" * 70)
    
    # Analisar distribuição
    distribution, total_pdfs = analyze_distribution()
    
    print(f"\n📊 ESTATÍSTICAS GERAIS")
    print("-" * 50)
    print(f"   Total de PDFs: {total_pdfs:,}")
    print(f"   Total de Grupos: {len(distribution)}")
    
    # Calcular prioridades
    sorted_groups, pareto_80 = calculate_priorities(distribution, total_pdfs)
    
    print(f"\n🎯 ANÁLISE PARETO (80/20)")
    print("-" * 50)
    print(f"   Grupos para cobrir 80%: {len(pareto_80)}")
    print(f"   PDFs nesses grupos: {sum(g['count'] for g in pareto_80):,}")
    
    # Top 15 grupos
    print(f"\n📈 TOP 15 GRUPOS (por volume)")
    print("-" * 70)
    print(f"{'#':<3} {'Grupo':<35} {'PDFs':>8} {'%':>6} {'Acum%':>7}")
    print("-" * 70)
    
    for i, (group, data) in enumerate(sorted_groups[:15], 1):
        pct = data["count"] / total_pdfs * 100
        print(f"{i:<3} {group:<35} {data['count']:>8,} {pct:>5.1f}% ")
    
    # Estimar requisições
    requests_needed, days_needed = estimate_requests(len(distribution))
    
    print(f"\n⏱️  ESTIMATIVA DE MAPEAMENTO GEMINI")
    print("-" * 50)
    print(f"   Requisições necessárias: {requests_needed}")
    print(f"   Dias para mapear tudo: {days_needed}")
    print(f"   Se mapear só Pareto 80%: {len(pareto_80)} reqs ({(len(pareto_80) + 19) // 20} dia(s))")
    
    # Salvar relatório JSON
    report = {
        "total_pdfs": total_pdfs,
        "total_groups": len(distribution),
        "pareto_80_groups": len(pareto_80),
        "requests_needed": requests_needed,
        "days_needed": days_needed,
        "top_groups": [
            {
                "group": g,
                "count": d["count"],
                "path": d["path"],
                "samples": d["sample_files"][:3]
            }
            for g, d in sorted_groups[:20]
        ],
        "pareto_80": pareto_80
    }
    
    output_path = Path("scripts/distribution_analysis.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Relatório salvo em: {output_path}")
    
    # Recomendações
    print(f"\n🚀 RECOMENDAÇÕES")
    print("-" * 50)
    if len(pareto_80) <= MAX_REQUESTS_DAY:
        print(f"   ✅ Mapear grupos Pareto 80% em 1 dia ({len(pareto_80)} reqs)")
    else:
        print(f"   ⚠️  Dividir em {(len(pareto_80) + 19) // 20} dias")
    
    print(f"   💡 Começar pelos grupos com mais PDFs para maior impacto")

if __name__ == "__main__":
    main()
