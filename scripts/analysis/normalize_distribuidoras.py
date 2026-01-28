#!/usr/bin/env python3
"""
Script para normalizar e consolidar datasets por distribuidora.
Unifica nomes variantes (ex: CEMIG, MG_-_CEMIG, CEMIG-D -> CEMIG)
e organiza em subpastas por distribuidora.
"""

import pandas as pd
from pathlib import Path
import json
import re
from datetime import datetime

# Diretórios
INPUT_DIR = Path("C:/Projetos/Raizen/output/datasets_finais")
OUTPUT_DIR = Path("C:/Projetos/Raizen/output/datasets_consolidados")

# Mapa de normalização: nome_canônico -> [variantes]
NORMALIZACAO = {
    "CEMIG": [
        "CEMIG", "CEMIG-D", "MG_-_CEMIG", "MG-CEMIG", "MG_–_CEMIG"
    ],
    "CPFL_PAULISTA": [
        "CPFL_PAULISTA", "SP_-_CPFL_PAULISTA", "SP_–_CPFL_PAULISTA"
    ],
    "CPFL_PIRATININGA": [
        "CPFL_PIRATININGA", "SP_-_CPFL_PIRATININGA"
    ],
    "CPFL_SANTA_CRUZ": [
        "CPFL_SANTA_CRUZ"
    ],
    "CPFL": [
        "CPFL"  # Genérico - manter separado
    ],
    "ELEKTRO": [
        "ELEKTRO", "SP_-_ELEKTRO", "SP_–_ELEKTRO", "NEOENERGIA_ELEKTRO"
    ],
    "LIGHT": [
        "LIGHT", "LIGHT_RJ", "LIGHT_-_RJ", "RJ_-_LIGHT"
    ],
    "ENEL_CE": [
        "ENEL_CE", "CE_-_ENEL_CE", "ENEL-CE"
    ],
    "ENEL_RJ": [
        "ENEL_RJ", "RJ_-_ENEL_RJ"
    ],
    "ENEL_SP": [
        "ENEL_SP", "SP_-_ENEL_SP"
    ],
    "ENEL_GO": [
        "ENEL_GO", "GO_-_ENEL_GO"
    ],
    "ENEL": [
        "ENEL"  # Genérico
    ],
    "COPEL": [
        "PR_-_COPEL", "PR_–_COPEL"
    ],
    "NEOENERGIA_PE": [
        "NEOENERGIA_PE", "PE_-_NEOENERGIA_PE", "NEOENERGIA_PERNAMBUCO"
    ],
    "NEOENERGIA_BRASILIA": [
        "NEOENERGIA_BRASÍLIA", "NEOENERGIA_DF", "DF_-_NEOENERGIA_BRASÍLIA", "CEB-DIS"
    ],
    "NEOENERGIA_COELBA": [
        "NEOENERGIA_COELBA", "BA_-_NEOENERGIA_COELBA", "COELBA"
    ],
    "NEOENERGIA_COSERN": [
        "RN_-_NEOENERGIA_COSERN"
    ],
    "ENERGISA_MT": [
        "ENERGISA_MT", "MT_-_ENERGISA_MT", "ENERGISA-MT", "EMT"
    ],
    "ENERGISA_MS": [
        "MS_-_ENERGISA_MS"
    ],
    "ENERGISA_TO": [
        "TO_-_ENERGISA_TO"
    ],
    "ENERGISA_PB": [
        "ENERGISA_PB"
    ],
    "ENERGISA_AC": [
        "ENERGISA_AC"
    ],
    "ENERGISA": [
        "ENERGISA"  # Genérico
    ],
    "ENERGISA_SUL_SUDESTE": [
        "SP_-_ENERGISA_SUL-SUDESTE"
    ],
    "EDP_SP": [
        "EDP_SP", "SP_-_EDP_SP"
    ],
    "EDP_ES": [
        "EDP_ES", "ES_-_EDP_ES"
    ],
    "CELPE": [
        "CELPE", "PE_-_CELPE"
    ],
    "EQUATORIAL_AL": [
        "EQUATORIAL_AL", "AL_-_EQUATORIAL_AL"
    ],
    "EQUATORIAL_GO": [
        "GO_-_EQUATORIAL_GO"
    ],
    "EQUATORIAL_PA": [
        "PA_-_EQUATORIAL_PA"
    ],
    "EQUATORIAL_PI": [
        "PI_-_EQUATORIAL_PI"
    ],
    "CELETRO": [
        "CELETRO"
    ],
    "NAO_IDENTIFICADA": [
        "NAO_IDENTIFICADA", "UFV_AMONTADA_II"  # Usinas não são distribuidoras
    ],
}

def criar_mapa_reverso():
    """Cria mapa variante -> nome_canônico"""
    mapa = {}
    for canonico, variantes in NORMALIZACAO.items():
        for variante in variantes:
            mapa[variante] = canonico
    return mapa

def eh_valor_monetario(nome: str) -> bool:
    """Verifica se o nome parece um valor monetário (R$_xxx)"""
    return nome.startswith("R$_") or re.match(r"^\d+$", nome)

def normalizar_nome(nome: str, mapa_reverso: dict) -> str:
    """Normaliza nome da distribuidora"""
    # Valores monetários -> NAO_IDENTIFICADA
    if eh_valor_monetario(nome):
        return "NAO_IDENTIFICADA"
    
    # Buscar no mapa
    if nome in mapa_reverso:
        return mapa_reverso[nome]
    
    # Não encontrado, manter original
    return nome

def main():
    print("=" * 60)
    print("NORMALIZADOR DE DISTRIBUIDORAS")
    print("=" * 60)
    
    # Criar diretório de saída
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Criar mapa reverso
    mapa_reverso = criar_mapa_reverso()
    
    # Estatísticas
    stats = {
        "arquivos_processados": 0,
        "registros_total": 0,
        "por_distribuidora": {},
        "normalizacoes": [],
    }
    
    # Ler todos os CSVs
    todos_dados = []
    
    for csv_file in sorted(INPUT_DIR.glob("dataset_*.csv")):
        nome_dist_original = csv_file.stem.replace("dataset_", "")
        
        try:
            df = pd.read_csv(csv_file, sep=";", low_memory=False)
            
            # Normalizar nome
            nome_canonico = normalizar_nome(nome_dist_original, mapa_reverso)
            
            # Registrar normalização
            if nome_dist_original != nome_canonico:
                stats["normalizacoes"].append({
                    "original": nome_dist_original,
                    "canonico": nome_canonico,
                    "registros": len(df)
                })
            
            # Atualizar coluna distribuidora se existir
            if "distribuidora" in df.columns:
                df["distribuidora"] = nome_canonico
            
            # Adicionar metadados
            df["_arquivo_origem"] = csv_file.name
            df["_distribuidora_normalizada"] = nome_canonico
            
            todos_dados.append(df)
            
            stats["arquivos_processados"] += 1
            stats["registros_total"] += len(df)
            
            print(f"✓ {nome_dist_original} -> {nome_canonico} ({len(df)} registros)")
            
        except Exception as e:
            print(f"✗ Erro em {csv_file.name}: {e}")
    
    # Concatenar todos os dados
    print("\nConsolidando dados...")
    df_total = pd.concat(todos_dados, ignore_index=True)
    
    # Agrupar e salvar por distribuidora
    print("\nSalvando por distribuidora...")
    
    for dist, grupo in df_total.groupby("_distribuidora_normalizada"):
        # Criar subpasta
        dist_dir = OUTPUT_DIR / dist
        dist_dir.mkdir(parents=True, exist_ok=True)
        
        # Remover colunas temporárias
        grupo_limpo = grupo.drop(columns=["_arquivo_origem", "_distribuidora_normalizada"], errors="ignore")
        
        # Salvar
        output_file = dist_dir / f"{dist}.csv"
        grupo_limpo.to_csv(output_file, sep=";", index=False)
        
        stats["por_distribuidora"][dist] = len(grupo)
        print(f"  {dist}: {len(grupo)} registros -> {output_file}")
    
    # Relatório final
    print("\n" + "=" * 60)
    print("RESUMO DA CONSOLIDAÇÃO")
    print("=" * 60)
    print(f"Arquivos processados: {stats['arquivos_processados']}")
    print(f"Total de registros: {stats['registros_total']}")
    print(f"Distribuidoras únicas: {len(stats['por_distribuidora'])}")
    
    print("\nNormalizações aplicadas:")
    for norm in stats["normalizacoes"]:
        print(f"  {norm['original']} -> {norm['canonico']} ({norm['registros']} regs)")
    
    print("\nDistribuição final:")
    for dist, count in sorted(stats["por_distribuidora"].items(), key=lambda x: -x[1]):
        print(f"  {dist}: {count}")
    
    # Salvar relatório JSON
    relatorio_path = OUTPUT_DIR / "relatorio_consolidacao.json"
    with open(relatorio_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    print(f"\nRelatório salvo em: {relatorio_path}")
    print("=" * 60)
    print("CONCLUÍDO!")
    print("=" * 60)

if __name__ == "__main__":
    main()
