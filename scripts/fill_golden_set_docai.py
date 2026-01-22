"""
Preenchimento do Golden Set usando Google Cloud Document AI.

Usa o processador OCR do Document AI para extrair texto dos PDFs
e depois usa regex/NLP para estruturar os campos.
"""
import os
import json
import re
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Tentar importar Document AI
try:
    from google.cloud import documentai_v1 as documentai
    from google.api_core.client_options import ClientOptions
except ImportError:
    print("❌ Erro: google-cloud-documentai não instalado.")
    print("   Execute: pip install google-cloud-documentai")
    exit(1)

# Schema de extração (mesmo do Gemini)
CAMPOS_EXTRACAO = [
    "num_instalacao",
    "num_cliente", 
    "distribuidora",
    "razao_social",
    "cnpj",
    "data_adesao",
    "duracao_meses",
    "aviso_previo",
    "representante_nome",
    "representante_cpf",
    "participacao_percentual",
]

# Padrões regex para extração estruturada do texto OCR
PATTERNS = {
    "cnpj": r"(\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2})",
    "cpf": r"(\d{3}[.\s]?\d{3}[.\s]?\d{3}[-\s]?\d{2})",
    "data": r"(\d{2}/\d{2}/\d{4})",
    "num_instalacao": r"(?:Instalação|UC|Unidade Consumidora)[:\s]*(\d{5,15})",
    "num_cliente": r"(?:Cliente|Número do Cliente)[:\s]*(\d{5,15})",
    "duracao_meses": r"(?:prazo|vigência|fidelidade)[^\d]*(\d{2,3})\s*(?:meses|m)",
    "aviso_previo": r"(?:aviso prévio|antecedência)[^\d]*(\d{2,3})\s*(?:dias|d)",
    "participacao": r"(?:participação|desconto|percentual)[^\d]*(\d{1,3}[,.]?\d*)\s*%?",
}


def get_docai_client(project_id: str, location: str):
    """Cria cliente Document AI."""
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    return documentai.DocumentProcessorServiceClient(client_options=opts)


def process_pdf_with_docai(
    client,
    project_id: str,
    location: str,
    processor_id: str,
    pdf_path: str
) -> Optional[str]:
    """
    Processa um PDF com Document AI e retorna o texto extraído.
    """
    if not os.path.exists(pdf_path):
        return None
    
    # Ler arquivo
    with open(pdf_path, "rb") as f:
        content = f.read()
    
    # Criar request
    name = f"projects/{project_id}/locations/{location}/processors/{processor_id}"
    
    raw_document = documentai.RawDocument(
        content=content,
        mime_type="application/pdf"
    )
    
    request = documentai.ProcessRequest(
        name=name,
        raw_document=raw_document
    )
    
    # Processar
    result = client.process_document(request=request)
    return result.document.text


def extract_fields_from_text(text: str) -> Dict[str, Any]:
    """
    Extrai campos estruturados do texto OCR usando regex.
    """
    result = {campo: None for campo in CAMPOS_EXTRACAO}
    
    if not text:
        return result
    
    # Normalizar texto
    text_upper = text.upper()
    
    # CNPJ
    cnpj_match = re.search(PATTERNS["cnpj"], text)
    if cnpj_match:
        result["cnpj"] = cnpj_match.group(1)
    
    # CPF do representante
    cpf_matches = re.findall(PATTERNS["cpf"], text)
    if cpf_matches:
        result["representante_cpf"] = cpf_matches[-1]  # Último geralmente é do representante
    
    # Data de adesão (procurar perto de "assinatura" ou "adesão")
    data_match = re.search(r"(?:assinatura|adesão|firmado)[^\d]*" + PATTERNS["data"], text, re.I)
    if data_match:
        result["data_adesao"] = data_match.group(1)
    else:
        # Fallback: primeira data encontrada
        data_matches = re.findall(PATTERNS["data"], text)
        if data_matches:
            result["data_adesao"] = data_matches[0]
    
    # Número de Instalação
    inst_match = re.search(PATTERNS["num_instalacao"], text, re.I)
    if inst_match:
        result["num_instalacao"] = inst_match.group(1)
    
    # Número do Cliente
    cli_match = re.search(PATTERNS["num_cliente"], text, re.I)
    if cli_match:
        result["num_cliente"] = cli_match.group(1)
    
    # Duração em meses
    dur_match = re.search(PATTERNS["duracao_meses"], text, re.I)
    if dur_match:
        result["duracao_meses"] = int(dur_match.group(1))
    
    # Aviso prévio
    aviso_match = re.search(PATTERNS["aviso_previo"], text, re.I)
    if aviso_match:
        result["aviso_previo"] = int(aviso_match.group(1))
    
    # Participação percentual
    part_match = re.search(PATTERNS["participacao"], text, re.I)
    if part_match:
        val = part_match.group(1).replace(",", ".")
        result["participacao_percentual"] = float(val)
    
    # Distribuidora (buscar padrões conhecidos)
    distribuidoras = ["CPFL", "ENEL", "CEMIG", "COPEL", "ENERGISA", "LIGHT", "ELEKTRO", "EDP", "NEOENERGIA", "RGE"]
    for dist in distribuidoras:
        if dist in text_upper:
            result["distribuidora"] = dist
            break
    
    # Razão Social (linha após "CONTRATANTE" ou "CONSORCIADO")
    razao_match = re.search(r"(?:CONTRATANTE|CONSORCIADO|CONSUMIDOR)[:\s]*\n?\s*([A-Z][A-Z\s\-\.]+(?:LTDA|S\.?A\.?|ME|EPP)?)", text_upper)
    if razao_match:
        result["razao_social"] = razao_match.group(1).strip()
    
    # Nome do representante (linha após "Representante Legal" ou similar)
    rep_match = re.search(r"(?:Representante Legal|Nome do Representante)[:\s]*\n?\s*([A-Z][a-zA-Z\s]+)", text, re.I)
    if rep_match:
        result["representante_nome"] = rep_match.group(1).strip()
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Preencher Golden Set com Document AI")
    parser.add_argument("--input", default="output/golden_set_100.json", help="Arquivo de entrada")
    parser.add_argument("--output", default="output/golden_set_100_docai.json", help="Arquivo de saída")
    parser.add_argument("--limit", type=int, default=100, help="Limite de arquivos")
    
    args = parser.parse_args()
    
    # Carregar configuração
    project_id = os.getenv("DOCAI_PROJECT_ID")
    location = os.getenv("DOCAI_LOCATION", "us")
    processor_id = os.getenv("DOCAI_PROCESSOR_ID")
    
    if not all([project_id, processor_id]):
        print("❌ Erro: Configure as variáveis de ambiente:")
        print("   DOCAI_PROJECT_ID, DOCAI_LOCATION, DOCAI_PROCESSOR_ID")
        print("   E GOOGLE_APPLICATION_CREDENTIALS apontando para o JSON da Service Account")
        return
    
    # Criar cliente
    print(f"🔧 Conectando ao Document AI...")
    client = get_docai_client(project_id, location)
    
    # Carregar Golden Set
    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    samples = data.get("amostras", [])
    print(f"🚀 Processando {min(len(samples), args.limit)} amostras com Document AI")
    print("=" * 60)
    
    count = 0
    for i, sample in enumerate(samples):
        if count >= args.limit:
            break
        
        # Pular se já preenchido
        real_data = sample.get("real", {})
        if real_data and any(v is not None for v in real_data.values()):
            print(f"[{i+1}] ⏭️  {sample['arquivo'][:40]}... (Já preenchido)")
            continue
        
        pdf_path = sample.get("caminho")
        print(f"[{i+1}] 📄 {sample['arquivo'][:40]}...")
        
        try:
            # Extrair texto com Document AI
            text = process_pdf_with_docai(
                client, project_id, location, processor_id, pdf_path
            )
            
            if not text:
                print(f"   ❌ Erro: Não foi possível extrair texto")
                continue
            
            # Extrair campos estruturados
            extracted = extract_fields_from_text(text)
            
            # Atualizar campo "real"
            for key in sample["real"].keys():
                if key in extracted and extracted[key] is not None:
                    sample["real"][key] = extracted[key]
            
            print(f"   ✅ Sucesso!")
            count += 1
            
        except Exception as e:
            print(f"   ❌ Erro: {str(e)[:50]}")
        
        # Salvar parcial a cada 10 arquivos
        if count % 10 == 0:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    
    # Salvar final
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("=" * 60)
    print(f"🏁 Concluído! {count} arquivos processados.")
    print(f"   Arquivo salvo em: {args.output}")


if __name__ == "__main__":
    main()
