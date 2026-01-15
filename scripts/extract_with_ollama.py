"""
Extração com Ollama (Llama 3) para casos parciais.
Calibrado para: Intel i5-1135G7, 20GB RAM, CPU inference.
V2: Timeout aumentado, texto reduzido, prompt otimizado.
"""
import json
import requests
import time
from pathlib import Path
from datetime import datetime
import sys
import warnings
warnings.filterwarnings('ignore')

# Configuração Ollama
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "phi3"  # Mais rápido que llama3

# Configuração calibrada para hardware (V2 - otimizado para CPU lenta)
NUM_CTX = 2048   # Context reduzido
TIMEOUT = 180    # Timeout aumentado para 3 minutos
MAX_TEXT = 3000  # Texto máximo reduzido

# Paths
OUTPUT_DIR = Path("output")
RESULTS_FILE = OUTPUT_DIR / "extraction_full_results.json"
OLLAMA_RESULTS_FILE = OUTPUT_DIR / "ollama_extraction_results.json"

# Prompt compacto para extração rápida
EXTRACTION_PROMPT = """Extraia do contrato abaixo os campos em JSON:
razao_social, cnpj, num_instalacao, num_cliente, distribuidora, duracao_meses, email, representante_nome

Use null se não encontrar. Responda APENAS o JSON.

CONTRATO:
{text}

JSON:"""


def query_ollama(text: str) -> dict:
    """Envia texto para Ollama e retorna campos extraídos."""
    prompt = EXTRACTION_PROMPT.format(text=text[:MAX_TEXT])
    
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_ctx": NUM_CTX,
            "temperature": 0,
            "top_p": 0.9,
            "num_predict": 500,  # Limitar resposta
        }
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        
        result = response.json()
        response_text = result.get("response", "")
        
        # Parsear JSON
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = response_text[start:end]
            return json.loads(json_str)
        
        return {}
    except requests.exceptions.Timeout:
        return {"error": "timeout"}
    except json.JSONDecodeError:
        return {"error": "json_parse_error"}
    except Exception as e:
        return {"error": str(e)}


def get_partial_files() -> list:
    """Retorna lista de arquivos com extração parcial."""
    with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    partials = []
    for r in data['results']:
        if r.get('fields_extracted', 0) < 5:
            partials.append({
                'path': r['path'],
                'file': r['file'],
                'distributor': r.get('distributor', 'UNKNOWN'),
            })
    
    return partials


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extrai texto do PDF."""
    sys.path.insert(0, str(Path.cwd()))
    from src.extrator_contratos.table_extractor import open_pdf, extract_all_text_from_pdf
    
    try:
        with open_pdf(pdf_path) as pdf:
            return extract_all_text_from_pdf(pdf, max_pages=5, use_ocr_fallback=False)
    except:
        return ""


def main():
    print("=" * 60)
    print("EXTRAÇÃO COM OLLAMA V2 (otimizado para CPU)")
    print(f"Modelo: {MODEL} | Timeout: {TIMEOUT}s | Texto max: {MAX_TEXT}")
    print("=" * 60)
    
    # Verificar Ollama
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        print("✅ Ollama conectado\n")
    except:
        print("❌ Ollama não está rodando! Execute: ollama serve")
        return
    
    # Carregar parciais
    partials = get_partial_files()
    print(f"📄 {len(partials)} arquivos parciais\n")
    
    # Teste com 1 arquivo
    MAX_FILES = 1
    print(f"🧪 Teste: {MAX_FILES} arquivos (estimativa: ~{MAX_FILES * 2} min)\n")
    
    results = []
    start_time = time.time()
    
    for i, item in enumerate(partials[:MAX_FILES], 1):
        file_short = item['file'][:45] + "..." if len(item['file']) > 45 else item['file']
        print(f"[{i}/{MAX_FILES}] {file_short}")
        
        # Extrair texto
        text = extract_text_from_pdf(item['path'])
        if not text:
            print("  ⏭️ Sem texto")
            results.append({**item, "status": "no_text", "extracted": {}})
            continue
        
        # Enviar para Ollama
        t0 = time.time()
        extracted = query_ollama(text)
        elapsed = time.time() - t0
        
        # Contar campos
        if "error" in extracted:
            print(f"  ⚠️ {extracted['error']} ({elapsed:.0f}s)")
            fields_count = 0
        else:
            fields_count = sum(1 for v in extracted.values() if v and v != "null")
            print(f"  ✅ {fields_count} campos ({elapsed:.0f}s)")
        
        results.append({
            **item,
            "status": "success" if fields_count >= 5 else "partial",
            "fields_extracted_ollama": fields_count,
            "extracted": extracted,
            "time": elapsed
        })
    
    # Salvar
    total_time = time.time() - start_time
    
    output = {
        "timestamp": datetime.now().isoformat(),
        "model": MODEL,
        "processed": len(results),
        "total_time_min": total_time / 60,
        "results": results
    }
    
    with open(OLLAMA_RESULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    # Resumo
    success = len([r for r in results if r.get('fields_extracted_ollama', 0) >= 5])
    print(f"\n{'=' * 60}")
    print(f"✅ Sucesso: {success}/{len(results)} ({100*success/len(results):.0f}%)")
    print(f"⏱️ Tempo: {total_time/60:.1f} min ({total_time/len(results):.0f}s/arquivo)")
    print(f"📁 Salvo: {OLLAMA_RESULTS_FILE}")


if __name__ == "__main__":
    main()
