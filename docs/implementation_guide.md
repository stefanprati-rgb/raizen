# Guia Prático: Implementação Visual Fingerprinting

## 🚀 Instalação Rápida

```bash
# 1. Instalar dependências
pip install pdf2image imagehash pillow pydantic numpy scipy pymupdf

# 2. Se usar Windows, instalar Poppler
# Download: https://github.com/oschwartz10612/poppler-windows/releases/
# Ou via conda:
conda install poppler

# Linux/Mac
# Linux: sudo apt-get install poppler-utils
# Mac: brew install poppler
```

## 📝 Exemplo 1: Classificar um PDF

```python
from pdf_fingerprint import PDFModelIdentifier

# Inicializar
identifier = PDFModelIdentifier(db_path="./hube_models.json")

# Classificar PDF
result = identifier.classify_pdf(
    pdf_path="./contratos/contrato_001.pdf",
    distributor="HUBE",
    threshold=0.85
)

print(f"✓ Model encontrado: {result['model_id']}")
print(f"✓ É novo modelo: {result['is_new_model']}")
print(f"✓ Confiança: {result['confidence']:.1%}")

# Se encontrou similaridade, mostra detalhes
if result['similar_models']:
    print("\nModelos similares encontrados:")
    for model in result['similar_models']:
        print(f"  - {model['model_id']}: {model['similarity']:.1%}")
```

## 📝 Exemplo 2: Processar Lote de PDFs

```python
from pathlib import Path
from pdf_fingerprint import PDFModelIdentifier
import json

identifier = PDFModelIdentifier(db_path="./hube_models.json")

# Processa todos os PDFs em um diretório
pdf_dir = Path("./contratos")
results_by_model = {}

for pdf_file in pdf_dir.glob("*.pdf"):
    print(f"Processando {pdf_file.name}...")
    
    result = identifier.classify_pdf(
        pdf_path=str(pdf_file),
        distributor="HUBE",
        threshold=0.85
    )
    
    model_id = result['model_id']
    
    if model_id not in results_by_model:
        results_by_model[model_id] = {
            "is_new": result['is_new_model'],
            "confidence": result['confidence'],
            "files": []
        }
    
    results_by_model[model_id]['files'].append(str(pdf_file))

# Salvar resultado
with open("classification_results.json", "w") as f:
    json.dump(results_by_model, f, indent=2)

# Gerar relatório
print("\n📊 RELATÓRIO DE CLASSIFICAÇÃO\n")
for model_id, info in results_by_model.items():
    print(f"Modelo: {model_id}")
    print(f"  Novo: {'Sim' if info['is_new'] else 'Não'}")
    print(f"  Confiança: {info['confidence']:.1%}")
    print(f"  PDFs: {len(info['files'])}")
    print()
```

## 📝 Exemplo 3: Integração com seu Mapa OCR

```python
from pdf_fingerprint import PDFModelIdentifier
import your_ocr_module  # seu módulo de OCR/extração

identifier = PDFModelIdentifier(db_path="./hube_models.json")

# Dicionário de modelos e seus mapas
MODEL_TO_MAPPING = {
    "HUBE_5pages_model_abc123": "./mappings/contrato_tipo_a.json",
    "HUBE_5pages_model_def456": "./mappings/contrato_tipo_b.json",
    # ... adicionar mais conforme necessário
}

def process_pdf_with_fingerprinting(pdf_path, distributor):
    """
    Processa PDF com identificação automática de modelo
    """
    # Step 1: Classificar
    result = identifier.classify_pdf(pdf_path, distributor)
    model_id = result['model_id']
    
    # Step 2: Buscar mapa correto
    if model_id not in MODEL_TO_MAPPING:
        print(f"⚠️  Aviso: Novo modelo {model_id} sem mapa configurado")
        return None
    
    mapping_file = MODEL_TO_MAPPING[model_id]
    
    # Step 3: Processar com OCR
    extracted_data = your_ocr_module.extract_with_mapping(
        pdf_path=pdf_path,
        mapping_file=mapping_file,
        confidence_threshold=0.85
    )
    
    # Step 4: Adicionar metadados
    extracted_data['_metadata'] = {
        'model_id': model_id,
        'confidence': result['confidence'],
        'is_new_model': result['is_new_model'],
        'fingerprint_composite_id': result['fingerprint']['composite_id']
    }
    
    return extracted_data

# Usar
data = process_pdf_with_fingerprinting(
    pdf_path="./contratos/novo_contrato.pdf",
    distributor="HUBE"
)
print(data)
```

## 📝 Exemplo 4: Validar Modelo Existente

```python
from pdf_fingerprint import PDFModelIdentifier

identifier = PDFModelIdentifier(db_path="./hube_models.json")

# Validar que um novo PDF corresponde ao modelo esperado
pdf_test = "./contratos/teste.pdf"
expected_model = "HUBE_5pages_model_abc123"

result = identifier.classify_pdf(
    pdf_path=pdf_test,
    distributor="HUBE",
    threshold=0.80  # Mais permissivo para validação
)

if result['model_id'] == expected_model:
    print(f"✓ PDF corresponde ao modelo esperado ({result['confidence']:.1%})")
else:
    print(f"✗ PDF NÃO corresponde!")
    print(f"  Esperado: {expected_model}")
    print(f"  Encontrado: {result['model_id']} ({result['confidence']:.1%})")
    if result['similar_models']:
        print(f"  Sugestões: {[m['model_id'] for m in result['similar_models']]}")
```

## 📝 Exemplo 5: Monitorar Performance

```python
from pdf_fingerprint import PDFModelIdentifier
import time
from pathlib import Path

identifier = PDFModelIdentifier(db_path="./hube_models.json")

# Benchmark
print("⏱️  BENCHMARK DE PERFORMANCE\n")

pdf_files = list(Path("./contratos").glob("*.pdf"))[:10]  # Primeiros 10
times = []

for pdf in pdf_files:
    start = time.time()
    result = identifier.classify_pdf(str(pdf), "HUBE")
    elapsed = time.time() - start
    times.append(elapsed)
    
    status = "✓ Existente" if not result['is_new_model'] else "✕ Novo"
    print(f"{status} - {pdf.name}: {elapsed*1000:.0f}ms")

print(f"\nTempo médio: {sum(times)/len(times)*1000:.0f}ms")
print(f"Throughput: {len(times)/sum(times):.1f} PDFs/seg")

# Estatísticas do BD
stats = identifier.get_model_stats()
print(f"\n📊 BD de Modelos:")
print(f"  Total: {stats['total_models']} modelos")
print(f"  Por distribuidora: {stats['by_distributor']}")
print(f"  Por página: {stats['by_page_count']}")
```

## 📝 Exemplo 6: Ajustar Threshold

```python
from pdf_fingerprint import PDFModelIdentifier

identifier = PDFModelIdentifier(db_path="./hube_models.json")

# Testar diferentes thresholds
pdf_path = "./contratos/teste.pdf"
distributor = "HUBE"

thresholds = [0.75, 0.80, 0.85, 0.90, 0.95]

print("Testando diferentes thresholds:\n")

for threshold in thresholds:
    result = identifier.classify_pdf(
        pdf_path=pdf_path,
        distributor=distributor,
        threshold=threshold
    )
    
    is_new = "NOVO" if result['is_new_model'] else "EXISTENTE"
    model = result['model_id']
    confidence = result['confidence']
    
    print(f"Threshold {threshold}: {is_new} - {model} ({confidence:.1%})")

# Interpretação:
# threshold=0.75 → Mais permissivo, agrupa PDFs mesmo com variações
# threshold=0.85 → Balanço (recomendado)
# threshold=0.95 → Rigoroso, apenas PDFs praticamente idênticos
```

## 🔧 Troubleshooting

### Problema: ImportError com pdf2image

```bash
# Solução para Windows:
pip install pdf2image
# Baixar Poppler: https://github.com/oschwartz10612/poppler-windows/releases/
# Adicionar ao PATH ou passar path explícito:

from pdf2image import convert_from_path
images = convert_from_path(
    "file.pdf",
    poppler_path=r"C:\Program Files\poppler\Library\bin"  # Windows
)
```

### Problema: Imagens aparecem em branco

```python
# Aumentar DPI se renderização fica ruim
images = pdf2image.convert_from_path(
    pdf_path,
    dpi=200,  # Default é 100, aumentar para mais precisão
    first_page=1,
    last_page=2
)
```

### Problema: Memoria insuficiente em PDFs grandes

```python
# Processar uma página por vez se houver limite de RAM
def extract_visual_hash_memory_efficient(pdf_path):
    images = []
    for page_num in [0, 1]:
        img = pdf2image.convert_from_path(pdf_path, first_page=page_num+1, last_page=page_num+1)
        images.append(img[0])
        # Processar imediatamente em vez de acumular
    
    # ... continuar
```

## 📐 Tuning de Parâmetros

### Visual Hash Threshold (Hamming Distance)

```
0-3 bits: Copias perfeitas/idênticas
4-8 bits: Mesma página com leve compressão/rotação
9-15 bits: Layouts similares mas diferentes
16+ bits: Completamente diferentes
```

**Recomendação:** Usar 8 como default

### Structural Similarity Weight

```python
# Current: 70% visual + 30% estrutural
# Ajustes possíveis:

# Se muitos falsos positivos (agrupando diferentes layouts):
composite = (visual_sim * 0.80) + (struct_sim * 0.20)  # Mais rigoroso

# Se perdendo modelos legítimos:
composite = (visual_sim * 0.60) + (struct_sim * 0.40)  # Mais permissivo
```

## 📚 Referências Técnicas

- **dHash vs pHash**: dHash é mais robusto para layouts estruturados (PDFs), pHash é melhor para fotos
- **Hamming Distance**: Número de bits diferentes entre dois hashes
- **Perceptual Hashing**: Técnica que captura características visuais, não bit-perfeito
- **Composite Fingerprint**: Combinação de múltiplas features para maior robustez

---

**Última atualização:** 2026-01-20 | **Versão:** 1.0
