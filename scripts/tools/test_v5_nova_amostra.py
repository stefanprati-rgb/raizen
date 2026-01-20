"""
Teste V5 em nova amostra de 10 documentos aleatorios
"""
import json
import random
from pathlib import Path
import sys
sys.path.insert(0, 'scripts')
from uc_extractor_v5 import UCExtractorV5

# Buscar todos os PDFs CPFL
pdf_base = Path("cpfl_paulista_por_tipo")
all_pdfs = []
for subdir in pdf_base.rglob("*.pdf"):
    all_pdfs.append(str(subdir))

print(f"Total de PDFs disponiveis: {len(all_pdfs)}")

# Selecionar 10 aleatorios (seed diferente)
random.seed(2024)  # Seed diferente da validacao original
sample = random.sample(all_pdfs, 10)

# Extrair com V5
extractor = UCExtractorV5(use_dynamic_blacklist=False)

print("=" * 70)
print("TESTE V5 - NOVA AMOSTRA (10 docs)")
print("=" * 70)
print()

total_ucs = 0
docs_com_uc = 0

for i, pdf_path in enumerate(sample, 1):
    result = extractor.extract_from_pdf(pdf_path)
    
    filename = Path(pdf_path).name[:50]
    status = "[OK]" if result.uc_count > 0 else "[VAZIO]"
    
    print(f"{i:02d}. {filename}...")
    print(f"    UCs: {result.uc_count} | Clientes descartados: {len(result.clientes_descartados)} {status}")
    
    if result.ucs:
        print(f"    -> {result.ucs[:5]}{'...' if len(result.ucs) > 5 else ''}")
    if result.clientes_descartados:
        print(f"    -> Clientes: {result.clientes_descartados[:3]}...")
    print()
    
    total_ucs += result.uc_count
    if result.uc_count > 0:
        docs_com_uc += 1

print("=" * 70)
print(f"RESULTADO: {docs_com_uc}/10 docs com UC | Total: {total_ucs} UCs")
print("=" * 70)
