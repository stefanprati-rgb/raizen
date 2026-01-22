"""
Golden Set Creator - Validação de Precisão Real
Versão: 2.0

Este script cria um conjunto de validação (Golden Set) para medir
a precisão REAL do extrator, não apenas o score de confiança.

NOVIDADE v2.0: Amostragem ESTRATIFICADA baseada na análise de distribuição.

Uso:
    python scripts/create_golden_set.py --sample 100
    python scripts/create_golden_set.py --sample 100 --stratified
    python scripts/create_golden_set.py --validate golden_set.json
"""
import argparse
import json
import os
import random
import sys
from pathlib import Path
from datetime import datetime

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from raizen_power.extraction.extractor import ContractExtractor

# Campos a validar
CAMPOS_VALIDACAO = [
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

NOMES_AMIGAVEIS = {
    'num_instalacao': 'UC',
    'num_cliente': 'Nº Cliente',
    'distribuidora': 'Distribuidora',
    'razao_social': 'Razão Social',
    'cnpj': 'CNPJ',
    'data_adesao': 'Data Adesão',
    'duracao_meses': 'Fidelidade',
    'aviso_previo': 'Aviso Prévio',
    'representante_nome': 'Representante',
    'representante_cpf': 'CPF Rep.',
    'participacao_percentual': 'Participação',
}


def carregar_distribuicao() -> dict:
    """
    Carrega a análise de distribuição para amostragem estratificada.
    """
    dist_path = Path("scripts/distribution_analysis.json")
    if dist_path.exists():
        with open(dist_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def criar_golden_set_estratificado(contratos_dir: Path, sample_size: int = 100) -> list:
    """
    Cria um Golden Set com AMOSTRAGEM ESTRATIFICADA.
    
    Estratégia:
    1. Selecionar 2-3 PDFs de cada Top 20 grupos (Pareto) = ~50 PDFs
    2. Preencher restante (~50 PDFs) com amostragem aleatória de outros grupos
    
    Isso garante que modelos de maior volume (CPFL, CEMIG) sejam validados.
    """
    # Carregar análise de distribuição
    distribuicao = carregar_distribuicao()
    top_groups = distribuicao.get('top_groups', [])
    
    if not top_groups:
        print("⚠️  distribution_analysis.json não encontrado. Usando amostragem simples.")
        return criar_golden_set(contratos_dir, sample_size)
    
    print(f"📊 Criando Golden Set ESTRATIFICADO com {sample_size} PDFs...")
    print("-" * 60)
    
    sample = []
    pdfs_por_grupo = {}
    
    # Fase 1: Coletar PDFs por grupo
    print("🔍 Identificando PDFs por grupo...")
    for root, _, files in os.walk(contratos_dir):
        pdf_files = [f for f in files if f.lower().endswith('.pdf')]
        if pdf_files:
            rel_path = Path(root).relative_to(contratos_dir)
            parts = str(rel_path).split(os.sep)
            
            if len(parts) >= 1:
                pages_folder = parts[0]
                distributor = parts[1] if len(parts) > 1 else "ROOT"
                group_key = f"{pages_folder}/{distributor}"
                
                if group_key not in pdfs_por_grupo:
                    pdfs_por_grupo[group_key] = []
                
                for f in pdf_files:
                    pdfs_por_grupo[group_key].append(Path(root) / f)
    
    # Fase 2: Selecionar de Top 20 grupos (obrigatório)
    grupos_cobertos = set()
    pdfs_selecionados = []
    pdfs_por_grupo_top20 = min(3, sample_size // 20)  # 2-3 por grupo
    
    print(f"\n📈 Selecionando {pdfs_por_grupo_top20} PDFs de cada Top 20 grupo...")
    
    for i, group in enumerate(top_groups[:20]):
        group_name = group.get('group', '')
        group_path = group.get('path', '')
        
        if group_name in pdfs_por_grupo and pdfs_por_grupo[group_name]:
            available = pdfs_por_grupo[group_name]
            n_select = min(pdfs_por_grupo_top20, len(available))
            selected = random.sample(available, n_select)
            
            for pdf_path in selected:
                pdfs_selecionados.append({
                    'path': pdf_path,
                    'grupo': group_name,
                    'origem': 'PARETO_TOP20'
                })
            
            grupos_cobertos.add(group_name)
            print(f"  [{i+1:2d}] {group_name}: {n_select} PDFs selecionados")
    
    # Fase 3: Preencher resto com amostragem aleatória de outros grupos
    restante = sample_size - len(pdfs_selecionados)
    
    if restante > 0:
        print(f"\n🎲 Selecionando {restante} PDFs adicionais de grupos restantes...")
        
        outros_pdfs = []
        for group_name, pdfs in pdfs_por_grupo.items():
            if group_name not in grupos_cobertos:
                for pdf_path in pdfs:
                    outros_pdfs.append({
                        'path': pdf_path,
                        'grupo': group_name,
                        'origem': 'ALEATORIO'
                    })
        
        if len(outros_pdfs) >= restante:
            extras = random.sample(outros_pdfs, restante)
        else:
            extras = outros_pdfs
            print(f"  ⚠️  Apenas {len(extras)} PDFs extras disponíveis")
        
        pdfs_selecionados.extend(extras)
    
    print(f"\n✅ Total selecionado: {len(pdfs_selecionados)} PDFs")
    print(f"   - Top 20 Pareto: {len([p for p in pdfs_selecionados if p['origem'] == 'PARETO_TOP20'])}")
    print(f"   - Aleatório: {len([p for p in pdfs_selecionados if p['origem'] == 'ALEATORIO'])}")
    
    # Fase 4: Extrair dados
    print("\n" + "-" * 60)
    print("📄 Extraindo dados dos PDFs selecionados...")
    
    extractor = ContractExtractor()
    golden_set = []
    
    for i, item in enumerate(pdfs_selecionados, 1):
        pdf_path = item['path']
        print(f"[{i}/{len(pdfs_selecionados)}] {pdf_path.name[:50]}...")
        
        try:
            result = extractor.extract_from_pdf(str(pdf_path))
            
            if result.registros:
                registro = result.registros[0]
                
                entry = {
                    "id": i,
                    "arquivo": pdf_path.name,
                    "caminho": str(pdf_path),
                    "grupo": item['grupo'],
                    "origem_amostra": item['origem'],
                    "extraido": {},
                    "real": {},
                    "correto": {},
                    "score_confianca": result.confianca_score,
                    "categoria": result.categoria,
                }
                
                for campo in CAMPOS_VALIDACAO:
                    valor = registro.get(campo, '')
                    entry["extraido"][campo] = valor if valor else None
                    entry["real"][campo] = None
                    entry["correto"][campo] = None
                
                golden_set.append(entry)
            else:
                golden_set.append({
                    "id": i,
                    "arquivo": pdf_path.name,
                    "caminho": str(pdf_path),
                    "grupo": item['grupo'],
                    "erro": "Nenhum registro extraído",
                })
                
        except Exception as e:
            golden_set.append({
                "id": i,
                "arquivo": pdf_path.name,
                "grupo": item.get('grupo', 'UNKNOWN'),
                "erro": str(e),
            })
    
    return golden_set


def criar_golden_set(contratos_dir: Path, sample_size: int) -> list:
    """
    Cria um Golden Set com amostragem SIMPLES (fallback).
    Use criar_golden_set_estratificado() para amostragem estratificada.
    """
    pdf_files = list(contratos_dir.rglob("*.pdf"))
    
    if len(pdf_files) < sample_size:
        print(f"⚠️  Apenas {len(pdf_files)} PDFs encontrados. Usando todos.")
        sample_size = len(pdf_files)
    
    sample = random.sample(pdf_files, sample_size)
    
    print(f"📊 Criando Golden Set SIMPLES com {sample_size} PDFs...")
    print("-" * 60)
    
    extractor = ContractExtractor()
    golden_set = []
    
    for i, pdf_path in enumerate(sample, 1):
        print(f"[{i}/{sample_size}] Processando: {pdf_path.name[:50]}...")
        
        try:
            result = extractor.extract_from_pdf(str(pdf_path))
            
            if result.registros:
                registro = result.registros[0]
                
                entry = {
                    "id": i,
                    "arquivo": pdf_path.name,
                    "caminho": str(pdf_path),
                    "extraido": {},
                    "real": {},
                    "correto": {},
                    "score_confianca": result.confianca_score,
                    "categoria": result.categoria,
                }
                
                for campo in CAMPOS_VALIDACAO:
                    valor = registro.get(campo, '')
                    entry["extraido"][campo] = valor if valor else None
                    entry["real"][campo] = None
                    entry["correto"][campo] = None
                
                golden_set.append(entry)
            else:
                golden_set.append({
                    "id": i,
                    "arquivo": pdf_path.name,
                    "caminho": str(pdf_path),
                    "erro": "Nenhum registro extraído",
                })
                
        except Exception as e:
            golden_set.append({
                "id": i,
                "arquivo": pdf_path.name,
                "erro": str(e),
            })
    
    return golden_set


def salvar_golden_set(golden_set: list, output_path: Path):
    """Salva o Golden Set em JSON para revisão humana."""
    
    metadata = {
        "versao": "1.0",
        "data_criacao": datetime.now().isoformat(),
        "total_amostras": len(golden_set),
        "campos_validacao": CAMPOS_VALIDACAO,
        "instrucoes": [
            "1. Abra cada PDF listado em 'caminho'",
            "2. Preencha os valores REAIS em 'real'",
            "3. Deixe como null se o campo não existe no PDF",
            "4. Execute 'create_golden_set.py --validate' após preencher"
        ],
    }
    
    output = {
        "metadata": metadata,
        "amostras": golden_set,
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Golden Set salvo em: {output_path}")


def validar_golden_set(golden_set_path: Path):
    """
    Valida um Golden Set preenchido e calcula a precisão real.
    """
    with open(golden_set_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    amostras = data.get("amostras", [])
    
    # Estatísticas por campo
    stats = {campo: {"corretos": 0, "incorretos": 0, "na": 0} for campo in CAMPOS_VALIDACAO}
    
    print("=" * 70)
    print("VALIDAÇÃO DO GOLDEN SET")
    print("=" * 70)
    
    for amostra in amostras:
        if "erro" in amostra:
            continue
            
        extraido = amostra.get("extraido", {})
        real = amostra.get("real", {})
        
        for campo in CAMPOS_VALIDACAO:
            valor_extraido = extraido.get(campo)
            valor_real = real.get(campo)
            
            # Se real não foi preenchido, pular
            if valor_real is None:
                stats[campo]["na"] += 1
                continue
            
            # Normalizar para comparação
            if valor_extraido and valor_real:
                # Comparação case-insensitive e sem espaços extras
                v1 = str(valor_extraido).strip().upper().replace(" ", "")
                v2 = str(valor_real).strip().upper().replace(" ", "")
                correto = v1 == v2
            elif valor_extraido is None and valor_real == "N/A":
                correto = True  # Campo ausente no PDF
            else:
                correto = valor_extraido == valor_real
            
            amostra["correto"][campo] = correto
            
            if correto:
                stats[campo]["corretos"] += 1
            else:
                stats[campo]["incorretos"] += 1
    
    # Exibir resultados
    print(f"\n📊 PRECISÃO POR CAMPO")
    print("-" * 70)
    print(f"{'Campo':<20} {'Corretos':>10} {'Erros':>10} {'N/A':>8} {'Precisão':>10}")
    print("-" * 70)
    
    campos_criticos_ok = True
    campos_medios_ok = True
    
    for campo in CAMPOS_VALIDACAO:
        s = stats[campo]
        total = s["corretos"] + s["incorretos"]
        precisao = (s["corretos"] / total * 100) if total > 0 else 0
        
        nome = NOMES_AMIGAVEIS.get(campo, campo)
        
        # Status visual
        if precisao >= 95:
            status = "✅"
        elif precisao >= 85:
            status = "⚠️"
        else:
            status = "❌"
        
        print(f"{nome:<20} {s['corretos']:>10} {s['incorretos']:>10} {s['na']:>8} {precisao:>9.1f}% {status}")
        
        # Verificar critérios
        if campo in ['num_instalacao', 'cnpj', 'razao_social', 'distribuidora', 'participacao_percentual']:
            if precisao < 95:
                campos_criticos_ok = False
        else:
            if precisao < 85:
                campos_medios_ok = False
    
    # Resumo
    print("\n" + "=" * 70)
    print("RESULTADO FINAL")
    print("=" * 70)
    
    if campos_criticos_ok and campos_medios_ok:
        print("✅ APROVADO - Precisão dentro dos critérios de aceite")
    else:
        print("❌ REPROVADO - Necessário ajustar patterns")
        if not campos_criticos_ok:
            print("   - Campos críticos abaixo de 95%")
        if not campos_medios_ok:
            print("   - Campos médios abaixo de 85%")
    
    # Salvar resultado
    output_path = golden_set_path.parent / "golden_set_validado.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Resultado salvo em: {output_path}")


def gerar_planilha_revisao(golden_set_path: Path):
    """
    Gera uma planilha simplificada para revisão humana.
    """
    with open(golden_set_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    import csv
    
    csv_path = golden_set_path.parent / "golden_set_revisao.csv"
    
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        
        # Header
        header = ['ID', 'Arquivo'] + [NOMES_AMIGAVEIS.get(c, c) + ' (Extraído)' for c in CAMPOS_VALIDACAO]
        header += [NOMES_AMIGAVEIS.get(c, c) + ' (Real)' for c in CAMPOS_VALIDACAO]
        writer.writerow(header)
        
        # Dados
        for amostra in data.get("amostras", []):
            if "erro" in amostra:
                continue
            
            row = [amostra['id'], amostra['arquivo']]
            
            # Valores extraídos
            for campo in CAMPOS_VALIDACAO:
                row.append(amostra.get('extraido', {}).get(campo, ''))
            
            # Valores reais (vazios para preencher)
            for campo in CAMPOS_VALIDACAO:
                row.append('')  # Revisor preenche
            
            writer.writerow(row)
    
    print(f"📊 Planilha de revisão salva em: {csv_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Golden Set Creator - Validação de Precisão Real"
    )
    
    parser.add_argument(
        "--sample", "-s",
        type=int,
        default=100,
        help="Número de PDFs para amostragem (padrão: 100)"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=Path("contratos_por_paginas"),
        help="Pasta com contratos PDF (padrão: contratos_por_paginas)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("output/golden_set.json"),
        help="Arquivo de saída (padrão: output/golden_set.json)"
    )
    
    parser.add_argument(
        "--validate", "-v",
        type=Path,
        help="Validar um Golden Set preenchido"
    )
    
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Gerar planilha CSV para revisão"
    )
    
    parser.add_argument(
        "--stratified",
        action="store_true",
        help="Usar amostragem ESTRATIFICADA (recomendado, requer distribution_analysis.json)"
    )
    
    args = parser.parse_args()
    
    if args.validate:
        validar_golden_set(args.validate)
    elif args.csv:
        if args.output.exists():
            gerar_planilha_revisao(args.output)
        else:
            print(f"❌ Arquivo não encontrado: {args.output}")
    else:
        # Criar Golden Set
        args.output.parent.mkdir(parents=True, exist_ok=True)
        
        if args.stratified:
            golden_set = criar_golden_set_estratificado(args.input, args.sample)
        else:
            golden_set = criar_golden_set(args.input, args.sample)
        
        salvar_golden_set(golden_set, args.output)
        
        print(f"\n📋 Próximos passos:")
        print(f"   1. Abra {args.output}")
        print(f"   2. Preencha os valores REAIS de cada campo")
        print(f"   3. Execute: python scripts/create_golden_set.py --validate {args.output}")


if __name__ == "__main__":
    main()
