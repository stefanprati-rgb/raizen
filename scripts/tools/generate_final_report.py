import pandas as pd
from pathlib import Path

REFINED_CSV = Path("C:/Projetos/Raizen/output/GOLDEN_DATASET_REFINED.csv")
FINAL_EXCEL = Path("C:/Projetos/Raizen/output/DATASET_FINAL_GOLDEN_RAIZEN.xlsx")

def main():
    print("="*60)
    print("GERANDO DATASET FINAL DE ENTREGA")
    print("="*60)

    if not REFINED_CSV.exists():
        print(f"❌ Arquivo não encontrado: {REFINED_CSV}")
        return

    # Ler dados (garantindo que zeros à esquerda não sumam)
    df = pd.read_csv(REFINED_CSV, sep=";", dtype=str)
    
    # Mapa de Colunas para o Schema Obrigatório
    col_map = {
        "num_instalacao": "UC / Instalação",
        "num_cliente": "Número do Cliente",
        "distribuidora": "Distribuidora",
        "razao_social": "Razão Social",
        "cnpj": "CNPJ",
        "data_adesao": "Data de Adesão",
        "fidelidade": "Fidelidade",
        "aviso_previo": "Aviso Prévio (Dias)",
        "representante_nome": "Representante Legal",
        "representante_cpf": "CPF Representante",
        "participacao_percentual": "Participação Contratada"
    }

    # Renomear
    df_final = df.rename(columns=col_map)

    # Colunas Auxiliares que queremos manter no final para auditoria
    meta_cols = ["arquivo_origem", "status_proc", "score_confianca", "tipo_erro", "erro_detalhe"]
    
    # Ordenar Colunas (Prioridade para o Schema Obrigatório)
    final_ordered_cols = list(col_map.values()) + [c for c in meta_cols if c in df_final.columns]
    
    # Filtrar apenas o que existe
    final_ordered_cols = [c for c in final_ordered_cols if c in df_final.columns]
    
    # Sanitização extra: remover aspas de strings (limpeza de OCR)
    for col in df_final.columns:
        if df_final[col].dtype == 'object':
            df_final[col] = df_final[col].astype(str).str.replace('"', '').str.replace("'", "")
            # Substituir 'nan' ou 'None' string por vazio real
            df_final[col] = df_final[col].replace(['nan', 'None'], '')

    # Salvar Excel
    df_final[final_ordered_cols].to_excel(FINAL_EXCEL, index=False)
    
    print(f"✅ DATASET FINAL GERADO: {FINAL_EXCEL}")
    print(f"📈 Total de Linhas: {len(df_final)}")
    
    # Estatística de Sucesso
    sucesso = len(df_final[df_final['status_proc'].str.contains('OK', na=False)])
    baixa_qualidade = len(df_final[df_final['status_proc'].str.contains('BAIXA', na=False)])
    erros = len(df_final[df_final['status_proc'].str.contains('ERRO', na=False)])
    
    print(f"   - Sucesso/Ok: {sucesso}")
    print(f"   - Baixa Qualidade: {baixa_qualidade}")
    print(f"   - Erros/Falhas: {erros}")

if __name__ == "__main__":
    main()
