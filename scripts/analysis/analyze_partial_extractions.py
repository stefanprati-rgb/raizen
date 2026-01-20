"""
Analyzes partial extraction results to identify patterns and missing maps.
Helps prioritize which new maps to create for maximum impact.
"""

import json
from pathlib import Path
from collections import defaultdict
import sys

def load_results(results_path: Path) -> dict:
    """Load extraction results from JSON file."""
    with open(results_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze_partial_extractions(results: dict) -> dict:
    """Analyze partial extractions to identify patterns."""
    
    partial_results = []
    success_results = []
    
    for result in results.get('results', []):
        fields_extracted = result.get('fields_extracted', 0)
        if fields_extracted < 5:
            partial_results.append(result)
        else:
            success_results.append(result)
    
    # Analyze by distributor
    partial_by_distributor = defaultdict(list)
    for r in partial_results:
        dist = r.get('distributor', 'UNKNOWN')
        partial_by_distributor[dist].append(r)
    
    # Analyze by map used
    partial_by_map = defaultdict(list)
    for r in partial_results:
        map_used = r.get('map_used', 'NONE')
        partial_by_map[map_used].append(r)
    
    # Analyze by page count
    partial_by_pages = defaultdict(list)
    for r in partial_results:
        pages = r.get('pages', 0)
        partial_by_pages[pages].append(r)
    
    # Analyze by distributor + pages combination
    partial_by_combo = defaultdict(list)
    for r in partial_results:
        dist = r.get('distributor', 'UNKNOWN')
        pages = r.get('pages', 0)
        combo = f"{dist}_{pages}p"
        partial_by_combo[combo].append(r)
    
    # Identify fields commonly missing
    all_possible_fields = set()
    for r in success_results:
        all_possible_fields.update(r.get('data', {}).keys())
    
    missing_fields_count = defaultdict(int)
    for r in partial_results:
        extracted_fields = set(r.get('data', {}).keys())
        missing = all_possible_fields - extracted_fields
        for field in missing:
            missing_fields_count[field] += 1
    
    return {
        'total_partial': len(partial_results),
        'total_success': len(success_results),
        'partial_by_distributor': {k: len(v) for k, v in sorted(partial_by_distributor.items(), key=lambda x: -len(x[1]))},
        'partial_by_map': {k: len(v) for k, v in sorted(partial_by_map.items(), key=lambda x: -len(x[1]))},
        'partial_by_pages': {k: len(v) for k, v in sorted(partial_by_pages.items(), key=lambda x: -len(x[1]))},
        'partial_by_combo': {k: len(v) for k, v in sorted(partial_by_combo.items(), key=lambda x: -len(x[1]))[:30]},
        'missing_fields_count': dict(sorted(missing_fields_count.items(), key=lambda x: -x[1])),
        'sample_partials': partial_results[:20],  # First 20 for inspection
    }

def identify_priority_maps(analysis: dict, results: dict) -> list:
    """Identify which new maps would have the highest impact."""
    
    priorities = []
    
    # Group partial results by distributor+pages
    partial_results = [r for r in results.get('results', []) if r.get('fields_extracted', 0) < 5]
    
    combo_groups = defaultdict(list)
    for r in partial_results:
        dist = r.get('distributor', 'UNKNOWN')
        pages = r.get('pages', 0)
        combo = f"{dist}_{pages}p"
        combo_groups[combo].append(r)
    
    # Sort by count (highest impact first)
    for combo, items in sorted(combo_groups.items(), key=lambda x: -len(x[1])):
        if len(items) >= 10:  # Only consider if 10+ PDFs would benefit
            # Get sample files
            sample_files = [r.get('file', '') for r in items[:5]]
            
            # Analyze what maps are being used for these
            maps_used = defaultdict(int)
            for r in items:
                maps_used[r.get('map_used', 'NONE')] += 1
            
            # Analyze avg fields extracted
            avg_fields = sum(r.get('fields_extracted', 0) for r in items) / len(items)
            
            priorities.append({
                'combo': combo,
                'count': len(items),
                'avg_fields_extracted': round(avg_fields, 1),
                'current_maps_used': dict(maps_used),
                'sample_files': sample_files,
                'impact_score': len(items) * (5 - avg_fields)  # Higher = more PDFs * more missing fields
            })
    
    # Sort by impact score
    priorities.sort(key=lambda x: -x['impact_score'])
    
    return priorities[:20]  # Top 20 priorities

def print_analysis(analysis: dict, priorities: list):
    """Print analysis in a readable format."""
    
    print("\n" + "="*80)
    print("📊 ANÁLISE DE EXTRAÇÕES PARCIAIS")
    print("="*80)
    
    print(f"\n📈 RESUMO GERAL:")
    print(f"   ✅ Sucesso (5+ campos): {analysis['total_success']}")
    print(f"   ⚠️  Parcial (<5 campos): {analysis['total_partial']}")
    print(f"   Taxa de sucesso: {analysis['total_success']/(analysis['total_success']+analysis['total_partial'])*100:.1f}%")
    
    print(f"\n📍 TOP 10 DISTRIBUIDORAS COM MAIS PARCIAIS:")
    for i, (dist, count) in enumerate(list(analysis['partial_by_distributor'].items())[:10], 1):
        print(f"   {i:2}. {dist}: {count} PDFs")
    
    print(f"\n🗺️  MAPAS USADOS EM PARCIAIS:")
    for i, (map_name, count) in enumerate(list(analysis['partial_by_map'].items())[:10], 1):
        print(f"   {i:2}. {map_name}: {count} PDFs")
    
    print(f"\n📄 PARCIAIS POR Nº DE PÁGINAS:")
    for pages, count in sorted(analysis['partial_by_pages'].items()):
        print(f"   {pages} páginas: {count} PDFs")
    
    print(f"\n🎯 TOP 20 COMBOS DISTRIBUIDORA+PÁGINAS (mais prioritários):")
    for combo, count in list(analysis['partial_by_combo'].items())[:20]:
        print(f"   {combo}: {count} PDFs")
    
    print(f"\n❌ CAMPOS MAIS FREQUENTEMENTE FALTANDO:")
    for field, count in list(analysis['missing_fields_count'].items())[:10]:
        print(f"   {field}: faltando em {count} PDFs")
    
    print("\n" + "="*80)
    print("🎯 PRIORIDADES PARA CRIAÇÃO DE NOVOS MAPAS")
    print("="*80)
    
    for i, p in enumerate(priorities[:15], 1):
        print(f"\n{i}. {p['combo']}")
        print(f"   📊 {p['count']} PDFs afetados | Média campos: {p['avg_fields_extracted']} | Score: {p['impact_score']:.0f}")
        print(f"   🗺️  Mapas atuais: {p['current_maps_used']}")
        print(f"   📁 Exemplos:")
        for f in p['sample_files'][:3]:
            print(f"      - {f[:80]}...")
    
    return priorities

def save_analysis(analysis: dict, priorities: list, output_path: Path):
    """Save analysis to JSON file."""
    report = {
        'summary': {
            'total_partial': analysis['total_partial'],
            'total_success': analysis['total_success'],
            'success_rate': f"{analysis['total_success']/(analysis['total_success']+analysis['total_partial'])*100:.1f}%"
        },
        'partial_by_distributor': analysis['partial_by_distributor'],
        'partial_by_map': analysis['partial_by_map'],
        'partial_by_pages': analysis['partial_by_pages'],
        'partial_by_combo': analysis['partial_by_combo'],
        'missing_fields': analysis['missing_fields_count'],
        'priority_maps': priorities,
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Análise salva em: {output_path}")

def main():
    # Paths
    base_path = Path(__file__).parent.parent
    results_path = base_path / "output" / "extraction_full_results.json"
    output_path = base_path / "output" / "partial_analysis_report.json"
    
    if not results_path.exists():
        print(f"❌ Arquivo não encontrado: {results_path}")
        sys.exit(1)
    
    print(f"📂 Carregando resultados de: {results_path}")
    results = load_results(results_path)
    
    print(f"🔍 Analisando extrações parciais...")
    analysis = analyze_partial_extractions(results)
    
    print(f"🎯 Identificando prioridades para novos mapas...")
    priorities = identify_priority_maps(analysis, results)
    
    print_analysis(analysis, priorities)
    save_analysis(analysis, priorities, output_path)

if __name__ == "__main__":
    main()
