"""
Teste V5 em amostra de 50 documentos aleatorios
"""
import json
import random
from pathlib import Path
import sys
sys.path.insert(0, 'scripts')
from uc_extractor_v5 import UCExtractorV5

# Buscar todos os PDFs CPFL
pdf_base = Path("cpfl_paulista_por_tipo")
all_pdfs = list(pdf_base.rglob("*.pdf"))
print(f"Total de PDFs disponiveis: {len(all_pdfs)}")

# Selecionar 50 aleatorios (nova seed)
random.seed(42)
sample = random.sample([str(p) for p in all_pdfs], 50)

# Extrair com V5
extractor = UCExtractorV5(use_dynamic_blacklist=True)

print("=" * 70)
print("TESTE V5 - AMOSTRA 50 DOCS")
print("=" * 70)
print()

total_ucs = 0
docs_com_uc = 0
docs_vazios = []
resultados = []

for i, pdf_path in enumerate(sample, 1):
    result = extractor.extract_from_pdf(pdf_path)
    
    filename = Path(pdf_path).name[:45]
    status = "[OK]" if result.uc_count > 0 else "[VAZIO]"
    
    # Resumo compacto
    print(f"{i:02d}. {filename}... UCs:{result.uc_count} Cli:{len(result.clientes_descartados)} {status}")
    
    total_ucs += result.uc_count
    if result.uc_count > 0:
        docs_com_uc += 1
    else:
        docs_vazios.append(filename)
    
    resultados.append({
        'arquivo': Path(pdf_path).name,
        'ucs': result.ucs,
        'clientes': result.clientes_descartados,
        'method': result.method
    })

# Finalizar batch (atualiza blacklist)
extractor.finalize_batch()

print()
print("=" * 70)
print(f"RESULTADO: {docs_com_uc}/50 docs com UC | Total: {total_ucs} UCs")
print(f"Taxa de sucesso: {docs_com_uc/50*100:.1f}%")
print("=" * 70)

if docs_vazios:
    print(f"\nDocs sem UC ({len(docs_vazios)}):")
    for d in docs_vazios[:10]:
        print(f"  - {d}")
    if len(docs_vazios) > 10:
        print(f"  ... e mais {len(docs_vazios)-10}")

# Salvar resultados
with open('output/teste_v5_50docs.json', 'w', encoding='utf-8') as f:
    json.dump({
        'total_docs': 50,
        'docs_com_uc': docs_com_uc,
        'total_ucs': total_ucs,
        'resultados': resultados
    }, f, ensure_ascii=False, indent=2)
print("\nResultados salvos em output/teste_v5_50docs.json")
