"""
Teste de extração dos campos específicos para exportação.
Campos: UC, Cliente, Distribuidora, Razão Social, CNPJ, Data Adesão, 
        Fidelidade, Aviso Prévio, Representante, CPF, Participação
"""
import sys
import json
from pathlib import Path

# Import do módulo raizen_power
from raizen_power.extraction.extractor import ContractExtractor

# Campos que o usuário precisa exportar
CAMPOS_EXPORTACAO = [
    'num_instalacao',           # UC
    'num_cliente',              # Número do cliente
    'distribuidora',            # Distribuidora
    'razao_social',             # Razão Social
    'cnpj',                     # CNPJ
    'data_adesao',              # Data de Adesão
    'duracao_meses',            # Fidelidade (meses)
    'aviso_previo',             # Aviso prévio
    'representante_nome',       # Representante Legal
    'representante_cpf',        # CPF Representante
    'participacao_percentual',  # Participação contratada
]

# Mapeamento para nomes amigáveis
NOMES_AMIGAVEIS = {
    'num_instalacao': 'UC',
    'num_cliente': 'Nº Cliente',
    'distribuidora': 'Distribuidora',
    'razao_social': 'Razão Social',
    'cnpj': 'CNPJ',
    'data_adesao': 'Data Adesão',
    'duracao_meses': 'Fidelidade (meses)',
    'aviso_previo': 'Aviso Prévio',
    'representante_nome': 'Representante Legal',
    'representante_cpf': 'CPF Representante',
    'participacao_percentual': 'Participação (%)',
}

def testar_extracao(pdf_path: str) -> dict:
    """Extrai dados de um PDF e retorna campos relevantes."""
    extractor = ContractExtractor()
    result = extractor.extract_from_pdf(pdf_path)
    
    # Pegar primeiro registro
    if result.registros:
        registro = result.registros[0]
        dados = {
            'arquivo': Path(pdf_path).name,
            'campos': {}
        }
        for campo in CAMPOS_EXPORTACAO:
            valor = registro.get(campo, '')
            dados['campos'][NOMES_AMIGAVEIS.get(campo, campo)] = valor if valor else '❌ NÃO ENCONTRADO'
        return dados
    return {'arquivo': Path(pdf_path).name, 'campos': {}, 'erro': 'Sem registros'}

def main():
    # PDFs de teste (diferentes tipos)
    base_dir = Path("contratos_por_paginas")
    
    pdfs_teste = [
        base_dir / "05_paginas/SOLAR 9290 - M DE F P CONEGLIAN RESTAURANTE - 03389281000104.pdf",
        base_dir / "05_paginas/SOLAR 9260 - POSTO JOAO ALVES LTDA - 07259850000158.pdf",
        base_dir / "05_paginas/SOLAR 8949 - RAÍZEN COMBUSTÍVEIS S A - 33453598000123.pdf",
    ]
    
    # Buscar mais PDFs de outras pastas
    pastas_extras = ["08_paginas", "10_paginas", "15_paginas"]
    for pasta in pastas_extras:
        pasta_path = base_dir / pasta
        if pasta_path.exists():
            pdfs = list(pasta_path.glob("*.pdf"))[:1]  # 1 de cada
            pdfs_teste.extend(pdfs)
    
    print("=" * 80)
    print("TESTE DE EXTRAÇÃO - CAMPOS PARA EXPORTAÇÃO")
    print("=" * 80)
    
    resultados = []
    
    for pdf_path in pdfs_teste:
        if not pdf_path.exists():
            print(f"\n⚠️  Arquivo não encontrado: {pdf_path.name}")
            continue
            
        print(f"\n📄 Processando: {pdf_path.name}")
        print("-" * 60)
        
        try:
            dados = testar_extracao(str(pdf_path))
            resultados.append(dados)
            
            for campo, valor in dados['campos'].items():
                status = "✅" if valor and "NÃO ENCONTRADO" not in str(valor) else "❌"
                print(f"  {status} {campo}: {valor}")
                
        except Exception as e:
            print(f"  ❌ ERRO: {e}")
            resultados.append({'arquivo': pdf_path.name, 'erro': str(e)})
    
    # Resumo
    print("\n" + "=" * 80)
    print("RESUMO")
    print("=" * 80)
    
    # Contar campos encontrados vs não encontrados
    for campo in CAMPOS_EXPORTACAO:
        nome = NOMES_AMIGAVEIS.get(campo, campo)
        encontrados = sum(
            1 for r in resultados 
            if 'campos' in r and nome in r['campos'] 
            and 'NÃO ENCONTRADO' not in str(r['campos'].get(nome, ''))
        )
        total = len([r for r in resultados if 'campos' in r])
        pct = (encontrados / total * 100) if total > 0 else 0
        status = "✅" if pct >= 50 else "⚠️" if pct > 0 else "❌"
        print(f"  {status} {nome}: {encontrados}/{total} ({pct:.0f}%)")
    
    # Salvar JSON
    output_path = Path("tests/debug/export_fields_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print(f"\n📁 Resultados salvos em: {output_path}")

if __name__ == "__main__":
    main()
