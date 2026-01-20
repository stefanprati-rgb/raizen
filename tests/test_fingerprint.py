"""Teste do PDF Fingerprint."""
from pathlib import Path
from raizen_power.utils.pdf_fingerprint import PDFModelIdentifier, IMAGEHASH_AVAILABLE

print(f"imagehash disponível: {IMAGEHASH_AVAILABLE}")
print()

# Encontrar PDFs de teste
pdfs = list(Path("data/raw").rglob("*.pdf"))[:5]

if not pdfs:
    print("Nenhum PDF encontrado em data/raw")
    exit(1)

print(f"Testando com {len(pdfs)} PDFs:")
print("-" * 60)

identifier = PDFModelIdentifier()

for pdf in pdfs:
    try:
        result = identifier.classify_pdf(str(pdf), "CPFL")
        model_id = result["model_id"]
        is_new = "NOVO" if result["is_new_model"] else "EXISTENTE"
        print(f"{pdf.name[:40]:40} -> {model_id} [{is_new}]")
    except Exception as e:
        print(f"{pdf.name[:40]:40} -> ERRO: {e}")

print("-" * 60)
stats = identifier.get_model_stats()
print(f"Total de modelos: {stats['total_models']}")
print(f"Por distribuidora: {stats['by_distributor']}")
print(f"Por páginas: {stats['by_page_count']}")
