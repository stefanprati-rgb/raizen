#!/usr/bin/env python
"""
Script de Extração OCR Focado - Termos de Adesão sem Identificação
Usa Tesseract para ler tabelas que o pdfplumber não consegue extrair.
Registra arquivos que falham mesmo com OCR para análise com Gemini Web.
"""
import json
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import pytesseract
from pdf2image import convert_from_path
import warnings
warnings.filterwarnings('ignore')

# Config
INPUT_JSON = Path("output/cpfl_paulista_final/cpfl_full_extraction_v6_final.json")
OUTPUT_JSON = Path("output/cpfl_paulista_final/cpfl_full_extraction_v6_ocr.json")
FAILED_LOG = Path("output/cpfl_paulista_final/ocr_failures.json")
MAX_WORKERS = 8  # Máximo de workers para processamento paralelo
TEST_MODE = False  # Desativado para processar lote completo
TEST_LIMIT = 10

# Regexes do Gemini Web para layout 9 páginas (formato CSV de tabela OCR)
REGEX_INSTALACAO = r'(?:N[º°].?\s*(?:da\s*)?Instala[çc][ãa]o.*?(?:Unidade\s*Consumidora)?.*?)["\s,]+(\d{5,12})'
REGEX_UC = r'(?:Unidade\s*Consumidora|Conta\s*Contrato.*?UC)["\s,]+(\d{5,12})'
REGEX_CLIENTE = r'(?:N[º°].?\s*do\s*Cliente)["\s,]+(\d{5,12})'
# Regex para tabela de múltiplas UCs (Ex: FORTBRAS) -> CNPJ + Instalação + Cliente
REGEX_TABLE_ROW = r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})[\s,]+(\d+)[\s,]+(\d+)'

def clean_ocr_text(text):
    """Normaliza texto OCR para facilitar regex"""
    # Mantém aspas e vírgulas pois são parte do padrão CSV
    return text.replace('\n', ' ').replace('\r', ' ')

def extract_ocr_from_pdf(pdf_path, pages_to_ocr=None):
    """Converte TODAS as páginas para imagem e extrai texto via OCR"""
    try:
        images = convert_from_path(pdf_path, dpi=200)
        texts = []
        for img in images:
            text = pytesseract.image_to_string(img, lang='por')
            texts.append(text)
        return "\n".join(texts)
    except Exception as e:
        return f"ERROR: {e}"

def find_uc_instalacao(text):
    """Busca UC, Instalação e Cliente no texto OCR (suporta múltiplos valores)"""
    # Limpar ruídos de tabela antes da busca
    cleaned_text = clean_ocr_text(text)
    
    uc = None
    instalacao = None
    cliente = None
    
    # 1. Tentar encontrar tabela com múltiplos valores usando texto bruto/parcial ou limpo
    # A regex REGEX_TABLE_ROW funciona melhor com espaços normalizados
    
    table_matches = re.findall(REGEX_TABLE_ROW, cleaned_text)
    if table_matches:
        # Extrai listas de instalação (índice 1) e cliente (índice 2)
        # Remove duplicatas preservando ordem
        inst_list = list(dict.fromkeys([m[1] for m in table_matches]))
        cli_list = list(dict.fromkeys([m[2] for m in table_matches]))
        
        if inst_list:
            instalacao = " ; ".join(inst_list)
        if cli_list:
            cliente = " ; ".join(cli_list)
            
    # 2. Se não achou tabela ou para complementar
    if not uc:
        match_uc = re.search(REGEX_UC, cleaned_text, re.IGNORECASE)
        if match_uc:
            uc = re.sub(r'[^\d]', '', match_uc.group(1).strip())
    
    if not instalacao: # Só busca individual se não achou na tabela
        match_inst = re.search(REGEX_INSTALACAO, cleaned_text, re.IGNORECASE)
        if match_inst:
            instalacao = match_inst.group(1).strip()
    
    if not cliente:
        match_cli = re.search(REGEX_CLIENTE, cleaned_text, re.IGNORECASE)
        if match_cli:
            cliente = match_cli.group(1).strip()
    
    return uc, instalacao, cliente

def process_file(entry):
    """Processa um arquivo com OCR"""
    pdf_path = entry.get('path')
    if not pdf_path or not Path(pdf_path).exists():
        return entry, False, "FILE_NOT_FOUND"
    
    try:
        # OCR na página 2 (índice 1) onde geralmente está a tabela
        text = extract_ocr_from_pdf(pdf_path, pages_to_ocr=[1])
        
        if text.startswith("ERROR:"):
            return entry, False, text
        
        uc, instalacao, cliente = find_uc_instalacao(text)
        
        # Atualizar dados se encontrou algo
        if entry.get('data') is None:
            entry['data'] = {}
        
        if instalacao:
            entry['data']['num_instalacao'] = instalacao
        if uc:
            entry['data']['num_conta_contrato'] = uc
        if cliente:
            entry['data']['num_cliente'] = cliente
        
        # Retorna sucesso se encontrou qualquer identificador
        found = uc or instalacao or cliente
        return entry, found, None if found else "NO_ID_FOUND"
    except Exception as e:
        return entry, False, str(e)

def main():
    print("📖 Carregando dados...")
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Filtrar apenas TERMO_ADESAO sem identificação
    to_process = []
    skipped = []
    for entry in data:
        if entry.get('type') != 'TERMO_ADESAO':
            skipped.append(entry)
            continue
        
        d = entry.get('data', {}) or {}
        has_id = d.get('num_instalacao') or d.get('num_conta_contrato') or d.get('num_cliente')
        if has_id:
            skipped.append(entry)
        else:
            to_process.append(entry)
    
    if TEST_MODE:
        to_process = to_process[:TEST_LIMIT]
        print(f"🧪 MODO TESTE: Processando apenas {TEST_LIMIT} arquivos")
    
    print(f"📊 Total: {len(data)} | A processar: {len(to_process)} | Ignorados: {len(skipped)}")
    print(f"🚀 Iniciando OCR com {MAX_WORKERS} workers...")
    
    results = []
    failures = []
    success_count = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_file, e): e for e in to_process}
        
        for i, future in enumerate(as_completed(futures), 1):
            entry, success, error = future.result()
            results.append(entry)
            
            if success:
                success_count += 1
                print(f"  ✅ [{i}/{len(to_process)}] Encontrado!")
            else:
                failures.append({"path": entry.get('path'), "error": error})
                print(f"  ❌ [{i}/{len(to_process)}] Falha: {error[:50] if error else 'Unknown'}")
    
    # Combinar resultados
    final_data = skipped + results
    
    # Salvar resultados
    print(f"\n💾 Salvando {OUTPUT_JSON}...")
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    
    # Salvar log de falhas (para Gemini Web)
    print(f"📝 Salvando log de falhas: {FAILED_LOG}...")
    with open(FAILED_LOG, 'w', encoding='utf-8') as f:
        json.dump(failures, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== RESULTADO OCR ===")
    print(f"Total Processados: {len(to_process)}")
    print(f"Sucesso OCR: {success_count} ({success_count/len(to_process)*100:.1f}%)")
    print(f"Falhas Persistentes: {len(failures)} (salvos em {FAILED_LOG})")

if __name__ == "__main__":
    main()
