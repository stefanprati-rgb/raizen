#!/usr/bin/env python3
"""
Script para exportar dataset consolidado da CPFL Paulista para Excel.
Garante formatação correta de datas e números.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import re

# Configurações
INPUT_DIR = Path("C:/Projetos/Raizen/output/datasets_consolidados/CPFL_PAULISTA")
OUTPUT_DIR = Path("C:/Projetos/Raizen/output/datasets/cpfl")

def clean_currency(val):
    """Limpa formato de moeda para float"""
    if pd.isna(val):
        return val
    if isinstance(val, (int, float)):
        return val
    val = str(val).replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(val)
    except:
        return val

def format_excel(writer, df):
    """Aplica formatação no Excel"""
    workbook = writer.book
    worksheet = writer.sheets["CPFL_PAULISTA"]
    
    # Formatos
    currency_fmt = workbook.add_format({'num_format': '#,##0.00'})
    date_fmt = workbook.add_format({'num_format': 'dd/mm/yyyy'})
    
    # Largura das colunas
    worksheet.set_column('A:A', 50)  # Arquivo
    worksheet.set_column('B:B', 15)  # Status
    worksheet.set_column('C:C', 20)  # Distribuidora
    worksheet.set_column('D:D', 15)  # Instalação
    worksheet.set_column('E:E', 15)  # Cliente
    worksheet.set_column('F:F', 40)  # Razão Social
    
    # Identificar colunas numéricas
    for idx, col in enumerate(df.columns):
        if col in ["valor_cota", "participacao_percentual", "pagamento_mensal"]:
            worksheet.set_column(idx, idx, 15, currency_fmt)
        elif col in ["data_adesao", "vencimento", "data_extracao"]:
            worksheet.set_column(idx, idx, 15, date_fmt)

def main():
    print("=" * 60)
    print("EXPORTADOR EXCEL - CPFL PAULISTA")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Carregar dataset consolidado
    input_file = INPUT_DIR / "CPFL_PAULISTA.csv"
    if not input_file.exists():
        print(f"Erro: Arquivo não encontrado: {input_file}")
        return
    
    print(f"Lendo: {input_file}")
    df = pd.read_csv(input_file, sep=";", low_memory=False)
    
    print(f"Registros carregados: {len(df)}")
    
    # 2. Tratamento de dados
    print("Tratando dados...")
    
    # Converter numéricos
    cols_num = ["valor_cota", "participacao_percentual", "pagamento_mensal", "qtd_cotas"]
    for col in cols_num:
        if col in df.columns:
            df[col] = df[col].apply(clean_currency)
    
    # Converter datas
    cols_data = ["data_adesao", "vencimento", "data_extracao"]
    for col in cols_data:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
            # Para data_extracao que tem hora
            if col == "data_extracao":
                 df[col] = df[col].dt.normalize()
    
    # 3. Exportar
    output_file = OUTPUT_DIR / "dataset_CPFL_PAULISTA_final.xlsx"
    print(f"Exportando para: {output_file}")
    
    with pd.ExcelWriter(output_file, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="CPFL_PAULISTA", index=False)
        format_excel(writer, df)
    
    print("=" * 60)
    print("Sucesso!")

if __name__ == "__main__":
    main()
