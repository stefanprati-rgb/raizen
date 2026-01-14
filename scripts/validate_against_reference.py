"""
Script de Validação Cruzada com Excel de Referência
Versão: 1.0

Compara os resultados da extração automática com o Excel do outro time.

Uso:
    python scripts/validate_against_reference.py
"""

import json
import sys
import re
from pathlib import Path
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Paths
EXTRACTION_RESULTS = Path("output/extraction_results.json")
REFERENCE_EXCEL = Path("extracao-termos.xlsx")

def normalize_cnpj(cnpj: str) -> str:
    """Remove formatting from CNPJ."""
    if not cnpj:
        return ""
    return re.sub(r'\D', '', str(cnpj))

def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    if not text:
        return ""
    return str(text).strip().upper()

def compare_field(extracted: str, reference: str) -> str:
    """Compare two field values."""
    if not extracted and not reference:
        return "both_empty"
    if not extracted:
        return "missing_extracted"
    if not reference:
        return "missing_reference"
    
    ext_norm = normalize_text(extracted)
    ref_norm = normalize_text(reference)
    
    if ext_norm == ref_norm:
        return "match"
    if ext_norm in ref_norm or ref_norm in ext_norm:
        return "partial_match"
    return "mismatch"

def load_extraction_results():
    """Load extraction results JSON."""
    with open(EXTRACTION_RESULTS, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_reference_excel():
    """Load reference Excel file."""
    df = pd.read_excel(REFERENCE_EXCEL)
    # Normalize CNPJ column
    if 'CNPJ' in df.columns:
        df['cnpj_normalized'] = df['CNPJ'].apply(normalize_cnpj)
    return df

def validate():
    """Run validation comparison."""
    
    print("Carregando resultados da extração...")
    extraction = load_extraction_results()
    print(f"  {extraction['stats']['total']} extrações carregadas")
    
    print("\nCarregando Excel de referência...")
    reference = load_reference_excel()
    print(f"  {len(reference)} registros no Excel")
    
    # Build lookup by CNPJ
    ref_by_cnpj = {}
    for _, row in reference.iterrows():
        cnpj = normalize_cnpj(row.get('CNPJ'))
        if cnpj:
            if cnpj not in ref_by_cnpj:
                ref_by_cnpj[cnpj] = []
            ref_by_cnpj[cnpj].append(row)
    
    print(f"  {len(ref_by_cnpj)} CNPJs únicos")
    
    # Compare results
    print("\n" + "=" * 60)
    print("VALIDAÇÃO CRUZADA")
    print("=" * 60)
    
    stats = {
        "total_extracted": 0,
        "found_in_reference": 0,
        "not_found": 0,
        "field_matches": {},
        "field_mismatches": {}
    }
    
    matches = []
    not_found = []
    
    for result in extraction['results']:
        if result.get('error'):
            continue
        
        stats["total_extracted"] += 1
        
        extracted_cnpj = normalize_cnpj(result.get('data', {}).get('cnpj', ''))
        
        if extracted_cnpj and extracted_cnpj in ref_by_cnpj:
            stats["found_in_reference"] += 1
            ref_rows = ref_by_cnpj[extracted_cnpj]
            
            # Compare fields
            for ref_row in ref_rows[:1]:  # Take first match
                match_info = {
                    "file": result["file"],
                    "cnpj": extracted_cnpj,
                    "comparisons": {}
                }
                
                # Field mapping: extracted -> reference
                field_map = {
                    "razao_social": "Razão Social",
                    "data_adesao": "Data de Adesão",
                    "participacao_percentual": "Participacao Contratada",
                    "representante_nome": "Representante Legal",
                    "num_instalacao": "UC",
                    "num_cliente": "Número do cliente",
                    "distribuidora": "Distribuidora"
                }
                
                for ext_field, ref_field in field_map.items():
                    ext_val = result.get('data', {}).get(ext_field, '')
                    ref_val = ref_row.get(ref_field, '')
                    
                    comparison = compare_field(str(ext_val), str(ref_val))
                    match_info["comparisons"][ext_field] = {
                        "extracted": str(ext_val)[:50],
                        "reference": str(ref_val)[:50],
                        "result": comparison
                    }
                    
                    if comparison not in stats["field_matches"]:
                        stats["field_matches"][comparison] = {}
                    if ext_field not in stats["field_matches"][comparison]:
                        stats["field_matches"][comparison][ext_field] = 0
                    stats["field_matches"][comparison][ext_field] += 1
                
                matches.append(match_info)
        else:
            stats["not_found"] += 1
            not_found.append({
                "file": result["file"],
                "extracted_cnpj": extracted_cnpj
            })
    
    # Print results
    print(f"\n📊 Resultados da Validação:")
    print(f"  Total extraído: {stats['total_extracted']}")
    print(f"  Encontrado no Excel: {stats['found_in_reference']} ({100*stats['found_in_reference']/max(stats['total_extracted'],1):.1f}%)")
    print(f"  Não encontrado: {stats['not_found']}")
    
    print("\n📋 Comparação por Campo:")
    
    for comparison_type in ["match", "partial_match", "mismatch", "missing_extracted", "missing_reference"]:
        if comparison_type in stats["field_matches"]:
            print(f"\n  {comparison_type.upper()}:")
            for field, count in stats["field_matches"][comparison_type].items():
                print(f"    {field}: {count}")
    
    # Show sample matches
    if matches:
        print("\n" + "=" * 60)
        print("EXEMPLOS DE COMPARAÇÃO")
        print("=" * 60)
        
        for match in matches[:3]:
            print(f"\n📄 {match['file'][:50]}...")
            print(f"   CNPJ: {match['cnpj']}")
            for field, comp in match['comparisons'].items():
                icon = "✅" if comp['result'] == 'match' else "⚠️" if comp['result'] == 'partial_match' else "❌"
                print(f"   {icon} {field}:")
                print(f"      Extraído: {comp['extracted']}")
                print(f"      Referência: {comp['reference']}")
    
    # Save validation results
    output_file = Path("output/validation_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "stats": stats,
            "matches": matches[:100],
            "not_found": not_found[:50]
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 Resultados salvos em: {output_file}")
    
    return stats

def main():
    if not EXTRACTION_RESULTS.exists():
        print("❌ Execute primeiro: python scripts/extract_all_contracts.py")
        sys.exit(1)
    
    if not REFERENCE_EXCEL.exists():
        print(f"❌ Excel de referência não encontrado: {REFERENCE_EXCEL}")
        sys.exit(1)
    
    validate()

if __name__ == "__main__":
    main()
