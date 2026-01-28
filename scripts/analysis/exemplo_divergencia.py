"""
Mostra exemplo concreto de divergência.
"""
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.extrator_contratos.table_extractor import open_pdf, extract_all_text_from_pdf

# Carregar dados
df_val = pd.read_excel('output/relatorio_validacao_automatica.xlsx')
df_am = pd.read_excel('output/amostra_validacao_50.xlsx')

# Pegar primeiro caso de divergência
div = df_val[df_val['status'] == 'DIVERGENCIA'].iloc[0]

print('=' * 70)
print('EXEMPLO DE DIVERGÊNCIA')
print('=' * 70)
print()
print(f"Arquivo: {div['arquivo']}")
print()
print("STATUS DO MEU VALIDADOR:")
print(f"  UC: {div['uc']}")
print(f"  CNPJ: {div['cnpj']}")
print(f"  Razão: {div['razao']}")
print()

# Buscar dados do Excel
arquivo = div['arquivo']
for i, r in df_am.iterrows():
    arq_orig = str(r['Arquivo Original'])[:25] if pd.notna(r['Arquivo Original']) else ''
    if arq_orig == arquivo[:25]:
        row = r
        print("VALORES NO EXCEL (OUTRA EQUIPE):")
        print(f"  UC: {row['UC']}")
        print(f"  CNPJ: {row['CNPJ']}")
        print(f"  Razão: {str(row['Razao Social'])[:50]}")
        
        # Agora vamos ver o texto do PDF
        pdf_path = None
        for pdf in Path('output/validacao_amostra_50').glob('*.pdf'):
            if arquivo[:20] in pdf.name:
                pdf_path = pdf
                break
        
        if pdf_path:
            print()
            print("TRECHO DO TEXTO DO PDF:")
            print("-" * 50)
            with open_pdf(str(pdf_path)) as pdf:
                texto = extract_all_text_from_pdf(pdf, max_pages=2, use_ocr_fallback=False)
            # Mostrar primeiros 600 caracteres
            print(texto[:600])
            print("-" * 50)
            
            # Explicar a divergência
            uc_val = str(row['UC'])
            print()
            print("ANÁLISE DA DIVERGÊNCIA:")
            if uc_val in texto:
                print(f"  A UC '{uc_val}' EXISTE no PDF.")
                print("  CONCLUSÃO: Meu script falhou em encontrar (falso negativo).")
            else:
                print(f"  A UC '{uc_val}' NÃO existe no PDF.")
                print("  CONCLUSÃO: A outra equipe pode ter extraído incorretamente.")
        break
