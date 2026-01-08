import sys
from pathlib import Path
import json
from dataclasses import asdict

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.extrator_contratos.extractor import ContractExtractor

files = [
    r"C:\Projetos\Raizen\contratos_por_paginas\11_paginas\RGE\SOLAR 22787 - NYC GASTRONOMIA LTDA - 10877790000141 - Clicksign.pdf",
    r"C:\Projetos\Raizen\contratos_por_paginas\10_paginas\RGE\GD Fresh4Pet.pdf"
]

results = []
extractor = ContractExtractor()

for f in files:
    if not Path(f).exists():
        results.append({"file": f, "error": "not found"})
        continue
        
    try:
        res = extractor.extract_from_pdf(f)
        
        # Serializar registros
        regs = []
        for r in res.registros:
            regs.append({
                "razao_social": r.get('razao_social'),
                "distribuidora_final": r.get('distribuidora'),
                "metodo": r.get('metodo_distribuidora'),
                "cnpj": r.get('cnpj')
            })
            
        results.append({
            "file": Path(f).name,
            "paginas": res.paginas,
            "categoria": res.categoria,
            "distribuidora_classificada": res.distribuidora_classificada,
            "registros": regs
        })
    except Exception as e:
        results.append({"file": Path(f).name, "error": str(e)})

with open("tests/debug/verification_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
    
print("Verificação concluída. Resultados salvos em tests/debug/verification_results.json")
