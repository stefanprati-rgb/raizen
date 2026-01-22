"""
Script para analisar PDFs e gerar mapas de extração usando Gemini API.

Limites do tier gratuito:
- gemini-2.5-flash-lite: 10 RPM, 20 RPD
- gemini-2.5-flash: 5 RPM, 20 RPD

Uso:
    python scripts/analyze_pdf_gemini.py --api-key YOUR_API_KEY
    python scripts/analyze_pdf_gemini.py --list-priority  # Lista combinações prioritárias
    python scripts/analyze_pdf_gemini.py --combo "NEOENERGIA_ELEKTRO_9p"  # Analisa combo específico
"""

import os
import sys
import json
import time
import argparse
import random
from pathlib import Path
from typing import Optional, List, Dict

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import google.generativeai as genai
except ImportError:
    print("❌ Biblioteca não encontrada. Instale com:")
    print("   pip install google-generativeai")
    sys.exit(1)


# Diretórios
PROJECT_ROOT = Path(__file__).parent.parent
MAPS_DIR = PROJECT_ROOT / "maps"
OUTPUT_DIR = PROJECT_ROOT / "output"
PDFS_DIR = PROJECT_ROOT / "OneDrive_2026-01-06" / "TERMO DE ADESÃO"


# Prompt otimizado para gerar mapa de extração
EXTRACTION_MAP_PROMPT = """
Você é um especialista em extração de dados de contratos PDF brasileiros.

Analise este contrato PDF da distribuidora **{distributor}** com **{pages} páginas**.

## Sua Tarefa
Identifique os padrões de texto (regex) para extrair os seguintes campos:

### Campos Obrigatórios (tentar extrair todos)
1. **sic_ec_cliente** - Código SIC ou EC do cliente (5-6 dígitos)
2. **razao_social** - Nome da empresa (Razão Social)
3. **cnpj** - CNPJ no formato XX.XXX.XXX/XXXX-XX
4. **nire** - Número NIRE (registro empresarial)
5. **endereco** - Endereço completo
6. **email** - E-mail de contato
7. **representante_nome** - Nome do representante legal
8. **consorcio_nome** - Nome do consórcio (ex: "RZ SÃO PAULO")
9. **consorcio_cnpj** - CNPJ do consórcio
10. **distribuidora** - Nome da distribuidora de energia
11. **num_instalacao** - Número da instalação
12. **num_cliente** - Número do cliente / Conta Contrato / UC
13. **participacao_percentual** - Percentual de participação (ex: "1,5%")
14. **duracao_meses** - Prazo de vigência em meses
15. **data_adesao** - Data de adesão ao contrato

## Regras para Regex
- Use grupos de captura `()` para o valor a extrair
- Escape caracteres especiais: `.` → `\\.`, `/` → `/`
- Use `[:\\s]*` para separadores flexíveis
- Use `(?:X|Y)` para alternativas
- Considere acentuação em português: `[ãáâ]`, `[éê]`, etc.

## Formato de Resposta
Retorne APENAS um JSON válido (sem markdown, sem ```):

{{
    "modelo_identificado": "Descrição do tipo de contrato",
    "distribuidora_principal": "{distributor}",
    "paginas_analisadas": {pages},
    "fonte": "Gemini API - {date}",
    "campos": {{
        "nome_campo": {{
            "encontrado": true,
            "pagina": 1,
            "ancora": "Texto que aparece antes do valor",
            "regex": "padrão regex com grupo de captura",
            "valor_extraido": "exemplo extraído do PDF",
            "confianca": "alta"
        }}
    }},
    "campos_nao_encontrados": ["lista", "de", "campos", "ausentes"],
    "alertas": ["observações importantes sobre o documento"]
}}
"""


def load_partial_analysis() -> Dict:
    """Carrega o relatório de análise das extrações parciais."""
    report_path = OUTPUT_DIR / "partial_analysis_report.json"
    if not report_path.exists():
        print(f"⚠️ Arquivo não encontrado: {report_path}")
        return {}
    
    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_extraction_results() -> Dict:
    """Carrega os resultados da extração para encontrar PDFs de exemplo."""
    results_path = OUTPUT_DIR / "extraction_full_results.json"
    if not results_path.exists():
        print(f"⚠️ Arquivo não encontrado: {results_path}")
        return {}
    
    with open(results_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_priority_combos() -> List[Dict]:
    """Retorna as combinações prioritárias para criar novos mapas."""
    analysis = load_partial_analysis()
    return analysis.get("priority_maps", [])


def find_sample_pdfs(combo: str, count: int = 3) -> List[Path]:
    """Encontra PDFs de exemplo para uma combinação distribuidor_páginas."""
    analysis = load_partial_analysis()
    priority_maps = analysis.get("priority_maps", [])
    
    # Encontrar a combo nos mapas prioritários
    for item in priority_maps:
        if item["combo"] == combo:
            sample_files = item.get("sample_files", [])
            
            # Verificar quais arquivos existem
            existing = []
            for filename in sample_files[:count * 2]:  # Tentar mais para garantir
                pdf_path = PDFS_DIR / filename
                if pdf_path.exists():
                    existing.append(pdf_path)
                    if len(existing) >= count:
                        break
            
            return existing
    
    return []


def analyze_pdf_with_gemini(
    pdf_path: Path,
    distributor: str,
    pages: int,
    api_key: str,
    model_name: str = "gemini-2.5-flash-lite"
) -> Optional[Dict]:
    """
    Analisa um PDF usando a API do Gemini e retorna o mapa de extração.
    
    Args:
        pdf_path: Caminho para o arquivo PDF
        distributor: Nome da distribuidora
        pages: Número de páginas do PDF
        api_key: Chave da API do Gemini
        model_name: Modelo a usar (gemini-2.5-flash-lite recomendado por ter mais RPM)
    
    Returns:
        Dict com o mapa de extração ou None se falhar
    """
    from datetime import datetime
    
    # Configurar API
    genai.configure(api_key=api_key)
    
    print(f"\n📄 Analisando: {pdf_path.name}")
    print(f"   Distribuidora: {distributor}")
    print(f"   Páginas: {pages}")
    
    try:
        # Upload do arquivo
        print("   ⏳ Fazendo upload do PDF...")
        uploaded_file = genai.upload_file(str(pdf_path))
        
        # Aguardar processamento
        while uploaded_file.state.name == "PROCESSING":
            print("   ⏳ Processando arquivo...")
            time.sleep(2)
            uploaded_file = genai.get_file(uploaded_file.name)
        
        if uploaded_file.state.name == "FAILED":
            print(f"   ❌ Falha no upload: {uploaded_file.state.name}")
            return None
        
        print("   ✅ Upload completo")
        
        # Preparar prompt
        prompt = EXTRACTION_MAP_PROMPT.format(
            distributor=distributor,
            pages=pages,
            date=datetime.now().strftime("%Y-%m-%d")
        )
        
        # Gerar resposta
        print(f"   ⏳ Gerando mapa com {model_name}...")
        model = genai.GenerativeModel(model_name)
        
        response = model.generate_content(
            [uploaded_file, prompt],
            generation_config={
                "temperature": 0.1,  # Baixa para respostas mais consistentes
                "max_output_tokens": 4096,
            }
        )
        
        # Extrair JSON da resposta
        response_text = response.text.strip()
        
        # Limpar markdown se presente
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        # Parse JSON
        map_data = json.loads(response_text.strip())
        print("   ✅ Mapa gerado com sucesso!")
        
        # Limpar arquivo uploadado
        try:
            genai.delete_file(uploaded_file.name)
        except:
            pass
        
        return map_data
        
    except json.JSONDecodeError as e:
        print(f"   ❌ Erro ao parsear JSON: {e}")
        # Save raw response for debugging
        debug_file = OUTPUT_DIR / f"debug_gemini_response_{distributor}_{pages}p.txt"
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(response_text)
        print(f"   💾 Resposta bruta salva em: {debug_file}")
        return None
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return None


def create_map_for_combo(
    combo: str,
    api_key: str,
    model_name: str = "gemini-2.5-flash-lite"
) -> Optional[Path]:
    """
    Cria um mapa de extração para uma combinação distribuidora_páginas.
    
    Args:
        combo: Ex: "NEOENERGIA_ELEKTRO_9p"
        api_key: Chave da API
        model_name: Modelo Gemini a usar
    
    Returns:
        Caminho do mapa salvo ou None se falhar
    """
    # Parsear combo
    parts = combo.rsplit("_", 1)
    if len(parts) != 2:
        print(f"❌ Formato de combo inválido: {combo}")
        return None
    
    distributor = parts[0]
    pages_str = parts[1]
    
    if not pages_str.endswith("p"):
        print(f"❌ Formato de páginas inválido: {pages_str}")
        return None
    
    pages = int(pages_str[:-1])
    
    # Encontrar PDF de exemplo
    sample_pdfs = find_sample_pdfs(combo)
    if not sample_pdfs:
        print(f"❌ Nenhum PDF encontrado para: {combo}")
        return None
    
    # Usar o primeiro PDF disponível
    pdf_path = sample_pdfs[0]
    
    # Analisar com Gemini
    map_data = analyze_pdf_with_gemini(
        pdf_path=pdf_path,
        distributor=distributor,
        pages=pages,
        api_key=api_key,
        model_name=model_name
    )
    
    if not map_data:
        return None
    
    # Salvar mapa
    map_name = f"{distributor}_{pages:02d}p_v1.json"
    map_path = MAPS_DIR / map_name
    
    # Verificar se já existe
    if map_path.exists():
        print(f"   ⚠️ Mapa já existe, salvando como v2...")
        map_name = f"{distributor}_{pages:02d}p_v2.json"
        map_path = MAPS_DIR / map_name
    
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump(map_data, f, indent=4, ensure_ascii=False)
    
    print(f"   💾 Mapa salvo: {map_path}")
    return map_path


def batch_create_maps(
    api_key: str,
    max_maps: int = 20,
    model_name: str = "gemini-2.5-flash-lite",
    delay_seconds: int = 10
):
    """
    Cria mapas em lote para as combinações prioritárias.
    
    Args:
        api_key: Chave da API
        max_maps: Máximo de mapas a criar (limite RPD)
        model_name: Modelo a usar
        delay_seconds: Delay entre requisições para respeitar rate limit
    """
    priority_combos = get_priority_combos()
    
    if not priority_combos:
        print("❌ Nenhuma combinação prioritária encontrada.")
        print("   Execute primeiro: python scripts/extract_parallel.py")
        return
    
    print(f"\n{'='*60}")
    print(f"📊 ANÁLISE EM LOTE COM GEMINI API")
    print(f"{'='*60}")
    print(f"Modelo: {model_name}")
    print(f"Combinações prioritárias: {len(priority_combos)}")
    print(f"Máximo de mapas: {max_maps}")
    print(f"Delay entre requisições: {delay_seconds}s")
    print(f"{'='*60}\n")
    
    created = 0
    failed = 0
    
    for i, item in enumerate(priority_combos[:max_maps]):
        combo = item["combo"]
        count = item["count"]
        impact = item["impact_score"]
        
        print(f"\n[{i+1}/{min(len(priority_combos), max_maps)}] {combo}")
        print(f"    PDFs afetados: {count}")
        print(f"    Impact score: {impact:.1f}")
        
        result = create_map_for_combo(combo, api_key, model_name)
        
        if result:
            created += 1
        else:
            failed += 1
        
        # Rate limiting
        if i < min(len(priority_combos), max_maps) - 1:
            print(f"\n⏳ Aguardando {delay_seconds}s (rate limit)...")
            time.sleep(delay_seconds)
    
    print(f"\n{'='*60}")
    print(f"📊 RESUMO")
    print(f"{'='*60}")
    print(f"✅ Mapas criados: {created}")
    print(f"❌ Falhas: {failed}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="Analisar PDFs e gerar mapas de extração usando Gemini API"
    )
    
    parser.add_argument(
        "--api-key",
        help="Chave da API do Gemini (ou use GEMINI_API_KEY env var)"
    )
    
    parser.add_argument(
        "--list-priority",
        action="store_true",
        help="Listar combinações prioritárias"
    )
    
    parser.add_argument(
        "--combo",
        help="Analisar uma combinação específica (ex: NEOENERGIA_ELEKTRO_9p)"
    )
    
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Criar mapas em lote para todas as combinações prioritárias"
    )
    
    parser.add_argument(
        "--max-maps",
        type=int,
        default=10,
        help="Máximo de mapas a criar em lote (default: 10, max recomendado: 20)"
    )
    
    parser.add_argument(
        "--model",
        default="gemini-2.5-flash-lite",
        choices=["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-1.5-flash"],
        help="Modelo Gemini a usar (default: gemini-2.5-flash-lite)"
    )
    
    parser.add_argument(
        "--delay",
        type=int,
        default=10,
        help="Delay em segundos entre requisições (default: 10)"
    )
    
    args = parser.parse_args()
    
    # Listar prioridades
    if args.list_priority:
        combos = get_priority_combos()
        print(f"\n{'='*70}")
        print(f"{'#':<3} {'Combinação':<30} {'PDFs':<8} {'Campos':<8} {'Impacto':<10}")
        print(f"{'='*70}")
        
        for i, item in enumerate(combos[:20], 1):
            print(f"{i:<3} {item['combo']:<30} {item['count']:<8} {item['avg_fields_extracted']:<8.1f} {item['impact_score']:<10.1f}")
        
        print(f"{'='*70}")
        print(f"\nUse --combo 'NOME' para analisar uma combinação específica")
        print(f"Use --batch para criar mapas em lote")
        return
    
    # Obter API key
    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    
    if not api_key and (args.combo or args.batch):
        print("❌ API key necessária. Use --api-key ou defina GEMINI_API_KEY")
        return
    
    # Analisar combo específico
    if args.combo:
        result = create_map_for_combo(args.combo, api_key, args.model)
        if result:
            print(f"\n✅ Sucesso! Mapa salvo em: {result}")
        else:
            print(f"\n❌ Falha ao criar mapa para: {args.combo}")
        return
    
    # Batch
    if args.batch:
        batch_create_maps(
            api_key=api_key,
            max_maps=args.max_maps,
            model_name=args.model,
            delay_seconds=args.delay
        )
        return
    
    # Sem argumentos - mostrar ajuda
    parser.print_help()
    print("\n" + "="*50)
    print("Exemplos de uso:")
    print("="*50)
    print("1. Listar combinações prioritárias:")
    print("   python scripts/analyze_pdf_gemini.py --list-priority")
    print()
    print("2. Analisar uma combinação específica:")
    print("   python scripts/analyze_pdf_gemini.py --api-key SUA_KEY --combo NEOENERGIA_ELEKTRO_9p")
    print()
    print("3. Criar mapas em lote (máximo 10):")
    print("   python scripts/analyze_pdf_gemini.py --api-key SUA_KEY --batch --max-maps 10")


if __name__ == "__main__":
    main()
