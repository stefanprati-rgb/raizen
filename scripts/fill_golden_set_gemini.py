import os
import json
import time
import argparse
from pathlib import Path
from typing import Dict, Any, List
import google.generativeai as genai
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configuração do Modelo
# Se o usuário não definir, usamos o flash como padrão
DEFAULT_MODEL = "gemini-1.5-flash" 

SCHEMA_PROMPT = """
Você é um especialista em extração de dados de contratos de energia.
Analise o documento PDF fornecido e extraia os seguintes campos com precisão.
Retorne APENAS um objeto JSON. Não use markdown, não explique nada.

CAMPOS OBRIGATÓRIOS (use null se não encontrar):
1. "num_instalacao": (string ou lista de strings) Número da instalação ou UC. Se houver tabela, pegue todos.
2. "num_cliente": (string) Número do cliente na distribuidora.
3. "distribuidora": (string) Nome da distribuidora (ex: CPFL, ENEL).
4. "razao_social": (string) Razão social do cliente.
5. "cnpj": (string) CNPJ do cliente.
6. "data_adesao": (string) Data de assinatura/adesão (DD/MM/AAAA).
7. "duracao_meses": (number) Prazo de fidelidade em meses (ex: 60).
8. "aviso_previo": (number) Dias de aviso prévio (ex: 90).
9. "representante_nome": (string) Nome do representante legal.
10. "representante_cpf": (string) CPF do representante legal.
11. "participacao_percentual": (number) Percentual de desconto ou participação (ex: 10.5).

IMPORTANTE:
- Normalize valores monetários para números.
- Normalize datas para DD/MM/AAAA.
- Se houver múltiplas instalações (Guarda-Chuva), extraia todas em "num_instalacao" separadas por ponto e vírgula ou lista.
"""

def setup_gemini(api_key: str):
    """Configura a API do Gemini."""
    genai.configure(api_key=api_key)

def process_pdf(pdf_path: str, model_name: str) -> Dict[str, Any]:
    """
    Envia PDF para o Gemini e retorna os dados extraídos.
    """
    if not os.path.exists(pdf_path):
        return {"erro": "Arquivo não encontrado"}

    try:
        # Upload do arquivo
        print(f"   ⬆️  Enviando para Gemini...", end="\r")
        sample_file = genai.upload_file(path=pdf_path, display_name=Path(pdf_path).name)
        
        # Aguardar processamento (geralmente rápido para PDFs pequenos)
        while sample_file.state.name == "PROCESSING":
            time.sleep(1)
            sample_file = genai.get_file(sample_file.name)
            
        if sample_file.state.name == "FAILED":
            return {"erro": "Falha no processamento do arquivo pelo Gemini"}

        # Gerar conteúdo com retry logic
        print(f"   🧠 Processando com {model_name}...", end="\r")
        model = genai.GenerativeModel(model_name)
        
        max_retries = 5
        base_delay = 10
        
        for attempt in range(max_retries):
            try:
                response = model.generate_content(
                    [sample_file, SCHEMA_PROMPT],
                    generation_config={"response_mime_type": "application/json"}
                )
                return json.loads(response.text)
                
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    wait_time = base_delay * (2 ** attempt)
                    print(f"   ⏳ Cota excedida. Aguardando {wait_time}s... (Tentativa {attempt+1}/{max_retries})", end="\r")
                    time.sleep(wait_time)
                else:
                    raise e
                    
        return {"erro": "Falha após múltiplas tentativas (Cota excedida)"}

    except Exception as e:
        return {"erro": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Preencher Golden Set com Gemini API")
    parser.add_argument("--input", default="output/golden_set_100.json", help="Arquivo de entrada")
    parser.add_argument("--output", default="output/golden_set_100_ai.json", help="Arquivo de saída")
    parser.add_argument("--key", help="Gemini API Key")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Modelo Gemini")
    parser.add_argument("--limit", type=int, help="Limitar número de arquivos")
    # Delay entre arquivos para evitar rate limit
    parser.add_argument("--delay", type=int, default=5, help="Delay entre arquivos em segundos (padrão: 5)")
    
    args = parser.parse_args()
    
    # ... (rest of setup) ...

    # Setup (omitido para brevidade no replace)
    api_key = args.key or os.getenv("GEMINI_API_KEY")
    if not api_key: 
        print("Erro: API Key não fornecida")
        return
    setup_gemini(api_key)
    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)
    samples = data.get("amostras", [])
    
    print(f"🚀 Iniciando processamento de {len(samples)} amostras com modelo {args.model}")
    print("=" * 60)
    
    count = 0
    for i, sample in enumerate(samples):
        if args.limit and count >= args.limit:
            break
            
        real_data = sample.get("real", {})
        if real_data and any(v is not None for v in real_data.values()):
             print(f"[{i+1}/{len(samples)}] ⏭️  {sample['arquivo'][:40]}... (Já preenchido)")
             continue

        if "erro" in sample:
            continue

        pdf_path = sample.get("caminho")
        print(f"[{i+1}/{len(samples)}] 📄 {sample['arquivo'][:40]}...")
        
        extracted = process_pdf(pdf_path, args.model)
        
        if "erro" in extracted:
            print(f"   ❌ Erro: {extracted['erro']}")
        else:
            for key in sample["real"].keys():
                if key in extracted:
                    sample["real"][key] = extracted[key]
            
            print(f"   ✅ Sucesso! Score Gemini: N/A")
            count += 1
            
        # Salvar parcial
        if count % 5 == 0:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Rate limiting preventivo
        time.sleep(args.delay)

    # Salvar final
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

        
    print("=" * 60)
    print(f"🏁 Concluído! Arquivo salvo em: {args.output}")
    print("Execute agora: python scripts/create_golden_set.py --validate output/golden_set_100_ai.json")

if __name__ == "__main__":
    main()
