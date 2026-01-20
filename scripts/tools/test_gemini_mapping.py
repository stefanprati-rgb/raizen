"""
Teste de Mapeamento com Gemini AI
Executa um mapeamento de teste em um PDF de amostra.
"""
import sys
import json
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extrator_contratos.gemini_client import GeminiClient
from src.extrator_contratos.map_manager import MapManager
from src.extrator_contratos.table_extractor import extract_all_text_from_pdf


def test_mapping():
    print("=" * 70)
    print("TESTE DE MAPEAMENTO COM GEMINI AI")
    print("=" * 70)
    
    # Encontrar um PDF de amostra
    contracts_dir = Path("contratos_por_paginas")
    
    if not contracts_dir.exists():
        print(f"❌ Pasta não encontrada: {contracts_dir}")
        return
    
    # Pegar primeiro PDF encontrado
    pdf_files = list(contracts_dir.rglob("*.pdf"))[:1]
    
    if not pdf_files:
        print("❌ Nenhum PDF encontrado!")
        return
    
    pdf_path = pdf_files[0]
    print(f"\n📄 PDF selecionado: {pdf_path.name}")
    print(f"   Caminho: {pdf_path}")
    
    # Extrair texto do PDF
    print("\n📖 Extraindo texto do PDF...")
    try:
        text = extract_all_text_from_pdf(str(pdf_path), max_pages=5)
        print(f"   Páginas extraídas: {len(text.split('--- Página'))}")
        print(f"   Caracteres: {len(text):,}")
    except Exception as e:
        print(f"❌ Erro ao extrair texto: {e}")
        return
    
    # Inicializar cliente Gemini
    print("\n🤖 Conectando ao Gemini...")
    try:
        client = GeminiClient()
        print("   ✅ Conectado!")
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return
    
    # Gerar mapeamento
    print("\n🔄 Gerando mapeamento (pode demorar ~15s)...")
    try:
        mapa = client.generate_mapping(text, grupo="TESTE")
        print("   ✅ Mapeamento gerado!")
    except Exception as e:
        print(f"❌ Erro no mapeamento: {e}")
        return
    
    # Exibir resultados
    print("\n" + "=" * 70)
    print("RESULTADOS DO MAPEAMENTO")
    print("=" * 70)
    
    campos = mapa.get('campos', {})
    
    for campo, config in campos.items():
        if config:
            valor = config.get('valor_amostra', 'N/A')
            confianca = config.get('confianca', 'N/A')
            print(f"\n📌 {campo}:")
            print(f"   Valor: {valor}")
            print(f"   Confiança: {confianca}")
            print(f"   Regex: {config.get('regex', 'N/A')[:50]}...")
        else:
            print(f"\n⚠️  {campo}: Não encontrado")
    
    # Validar regex
    print("\n" + "=" * 70)
    print("VALIDAÇÃO DE REGEX")
    print("=" * 70)
    
    manager = MapManager()
    is_valid, errors = manager.validate_map(mapa, text, strict=False)
    
    if is_valid:
        print("\n✅ Todos os regex validados com sucesso!")
    else:
        print(f"\n⚠️  {len(errors)} regex com problemas:")
        for err in errors:
            print(f"   - {err}")
    
    # Salvar mapa
    print("\n" + "=" * 70)
    print("SALVANDO MAPA")
    print("=" * 70)
    
    try:
        filepath = manager.save_map(
            grupo="TESTE_GEMINI",
            campos=campos,
            sample_text=text,
            validate=False  # Já validamos acima
        )
        print(f"\n✅ Mapa salvo em: {filepath}")
    except Exception as e:
        print(f"❌ Erro ao salvar: {e}")
    
    # Estatísticas de uso
    print("\n" + "=" * 70)
    print("ESTATÍSTICAS DE USO DA API")
    print("=" * 70)
    
    stats = client.get_usage_stats()
    print(f"\n📊 Requisições hoje: {stats['requests_today']}/{stats['rpd_limit']}")
    print(f"   Restantes: {stats['remaining_today']}")
    
    # Observações da IA
    if mapa.get('observacoes'):
        print("\n" + "=" * 70)
        print("OBSERVAÇÕES DA IA")
        print("=" * 70)
        for obs in mapa.get('observacoes', []):
            print(f"   💡 {obs}")


if __name__ == "__main__":
    test_mapping()
