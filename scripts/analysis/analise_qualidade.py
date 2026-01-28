#!/usr/bin/env python3
"""
Script para analisar qualidade da extração e campos preenchidos.
Gera relatório detalhado de preenchimento por campo e por distribuidora.
"""

import pandas as pd
from pathlib import Path
import json
from datetime import datetime

# Diretório dos datasets consolidados
INPUT_DIR = Path("C:/Projetos/Raizen/output/datasets_consolidados")
OUTPUT_DIR = Path("C:/Projetos/Raizen/output/reports")

# Campos obrigatórios do schema (conforme projeto_raizen.md)
CAMPOS_OBRIGATORIOS = [
    "num_instalacao",       # UC / Instalação
    "num_cliente",          # Número do Cliente
    "distribuidora",        # Distribuidora
    "razao_social",         # Razão Social
    "cnpj",                 # CNPJ
    "data_adesao",          # Data de Adesão
    "duracao_meses",        # Fidelidade (meses)
    "aviso_previo",         # Aviso Prévio (dias)
    "representante_nome",   # Representante Legal
    "representante_cpf",    # CPF Representante
    "participacao_percentual",  # Participação Contratada
]

# Todos os campos possíveis
TODOS_CAMPOS = CAMPOS_OBRIGATORIOS + [
    "arquivo_origem", "status", "cidade", "uf", "cep",
    "endereco", "email", "email_secundario",
    "consorcio_nome", "consorcio_cnpj",
    "tipo_documento", "modelo_detectado",
    "pagamento_mensal", "valor_cota", "qtd_cotas",
    "performance_alvo", "vencimento",
    "confianca_score", "alertas", "data_extracao",
    "caminho_completo", "metodo_distribuidora"
]

def calcular_taxa_preenchimento(df: pd.DataFrame, campo: str) -> float:
    """Calcula taxa de preenchimento de um campo (0-100%)"""
    if campo not in df.columns:
        return 0.0
    
    total = len(df)
    if total == 0:
        return 0.0
    
    # Contar não-nulos e não-vazios
    preenchidos = df[campo].notna() & (df[campo].astype(str).str.strip() != "")
    return round(preenchidos.sum() / total * 100, 1)

def analisar_distribuidora(dist_dir: Path) -> dict:
    """Analisa qualidade de uma distribuidora"""
    csv_files = list(dist_dir.glob("*.csv"))
    if not csv_files:
        return None
    
    # Ler todos os CSVs da distribuidora
    dfs = []
    for f in csv_files:
        try:
            dfs.append(pd.read_csv(f, sep=";", low_memory=False))
        except:
            pass
    
    if not dfs:
        return None
    
    df = pd.concat(dfs, ignore_index=True)
    
    # Calcular métricas
    resultado = {
        "distribuidora": dist_dir.name,
        "total_registros": len(df),
        "campos_presentes": [c for c in df.columns if c in TODOS_CAMPOS],
        "preenchimento": {},
        "preenchimento_obrigatorios": {},
    }
    
    # Taxa por campo
    for campo in TODOS_CAMPOS:
        taxa = calcular_taxa_preenchimento(df, campo)
        if taxa > 0 or campo in CAMPOS_OBRIGATORIOS:
            resultado["preenchimento"][campo] = taxa
    
    # Taxa campos obrigatórios
    for campo in CAMPOS_OBRIGATORIOS:
        resultado["preenchimento_obrigatorios"][campo] = calcular_taxa_preenchimento(df, campo)
    
    # Média de preenchimento obrigatórios
    taxas_obrig = [resultado["preenchimento_obrigatorios"][c] for c in CAMPOS_OBRIGATORIOS]
    resultado["media_obrigatorios"] = round(sum(taxas_obrig) / len(taxas_obrig), 1)
    
    return resultado

def main():
    print("=" * 70)
    print("ANÁLISE DE QUALIDADE DA EXTRAÇÃO")
    print("=" * 70)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Analisar cada distribuidora
    resultados = []
    
    for dist_dir in sorted(INPUT_DIR.iterdir()):
        if not dist_dir.is_dir():
            continue
        
        resultado = analisar_distribuidora(dist_dir)
        if resultado:
            resultados.append(resultado)
            print(f"✓ {resultado['distribuidora']}: {resultado['total_registros']} regs, "
                  f"qualidade média: {resultado['media_obrigatorios']:.1f}%")
    
    # Consolidar estatísticas gerais
    total_registros = sum(r["total_registros"] for r in resultados)
    
    # Calcular taxa global por campo
    print("\n" + "=" * 70)
    print("TAXA DE PREENCHIMENTO POR CAMPO (GERAL)")
    print("=" * 70)
    
    # Precisamos recalcular com todos os dados
    todos_dfs = []
    for dist_dir in INPUT_DIR.iterdir():
        if not dist_dir.is_dir():
            continue
        for f in dist_dir.glob("*.csv"):
            try:
                todos_dfs.append(pd.read_csv(f, sep=";", low_memory=False))
            except:
                pass
    
    df_total = pd.concat(todos_dfs, ignore_index=True) if todos_dfs else pd.DataFrame()
    
    taxa_global = {}
    print("\n📋 CAMPOS OBRIGATÓRIOS:")
    for campo in CAMPOS_OBRIGATORIOS:
        taxa = calcular_taxa_preenchimento(df_total, campo)
        taxa_global[campo] = taxa
        emoji = "✅" if taxa >= 80 else "⚠️" if taxa >= 50 else "❌"
        print(f"  {emoji} {campo}: {taxa:.1f}%")
    
    print("\n📋 CAMPOS AUXILIARES:")
    for campo in TODOS_CAMPOS:
        if campo not in CAMPOS_OBRIGATORIOS:
            taxa = calcular_taxa_preenchimento(df_total, campo)
            if taxa > 0:
                taxa_global[campo] = taxa
                emoji = "✅" if taxa >= 80 else "⚠️" if taxa >= 50 else "❌"
                print(f"  {emoji} {campo}: {taxa:.1f}%")
    
    # Resumo
    print("\n" + "=" * 70)
    print("RESUMO GERAL")
    print("=" * 70)
    print(f"Total de registros: {total_registros}")
    print(f"Distribuidoras analisadas: {len(resultados)}")
    
    # Média de campos obrigatórios
    media_obrig = sum(taxa_global.get(c, 0) for c in CAMPOS_OBRIGATORIOS) / len(CAMPOS_OBRIGATORIOS)
    print(f"Média preenchimento obrigatórios: {media_obrig:.1f}%")
    
    # Campos críticos (abaixo de 50%)
    criticos = [c for c in CAMPOS_OBRIGATORIOS if taxa_global.get(c, 0) < 50]
    if criticos:
        print(f"\n⚠️ CAMPOS CRÍTICOS (< 50%): {', '.join(criticos)}")
    
    # Top 5 distribuidoras por qualidade
    print("\n🏆 TOP 5 DISTRIBUIDORAS POR QUALIDADE:")
    top5 = sorted(resultados, key=lambda x: x["media_obrigatorios"], reverse=True)[:5]
    for i, r in enumerate(top5, 1):
        print(f"  {i}. {r['distribuidora']}: {r['media_obrigatorios']:.1f}% ({r['total_registros']} regs)")
    
    # Bottom 5 distribuidoras
    print("\n⚠️ DISTRIBUIDORAS COM MENOR QUALIDADE:")
    bottom5 = sorted(resultados, key=lambda x: x["media_obrigatorios"])[:5]
    for r in bottom5:
        if r["media_obrigatorios"] < 50:
            print(f"  - {r['distribuidora']}: {r['media_obrigatorios']:.1f}% ({r['total_registros']} regs)")
    
    # Salvar relatório JSON
    relatorio = {
        "data_analise": datetime.now().isoformat(),
        "total_registros": total_registros,
        "distribuidoras": len(resultados),
        "media_preenchimento_obrigatorios": round(media_obrig, 1),
        "taxa_por_campo": taxa_global,
        "campos_criticos": criticos,
        "por_distribuidora": resultados,
    }
    
    relatorio_path = OUTPUT_DIR / "analise_qualidade.json"
    with open(relatorio_path, "w", encoding="utf-8") as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False)
    
    print(f"\nRelatório salvo em: {relatorio_path}")
    print("=" * 70)

if __name__ == "__main__":
    main()
