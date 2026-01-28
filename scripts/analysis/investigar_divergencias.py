"""
Investiga casos de divergência na validação.
"""
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.extrator_contratos.table_extractor import open_pdf, extract_all_text_from_pdf

def investigar_divergencias():
    # Carregar dados
    df_validacao = pd.read_excel('output/relatorio_validacao_automatica.xlsx')
    df_amostra = pd.read_excel('output/amostra_validacao_50.xlsx')
    
    # Pegar divergências
    divergencias = df_validacao[df_validacao['status'] == 'DIVERGENCIA']
    
    print("INVESTIGAÇÃO DE DIVERGÊNCIAS")
    print("=" * 70)
    print(f"Total de divergências: {len(divergencias)}")
    
    pasta_pdfs = Path('output/validacao_amostra_50')
    
    resultados = []
    
    # Investigar os primeiros 5 casos
    for i, (idx, val_row) in enumerate(divergencias.head(5).iterrows()):
        arquivo = val_row['arquivo']
        
        # Buscar dados originais
        amostra_row = df_amostra[df_amostra['Arquivo Original'].str.contains(arquivo[:30], na=False)]
        if amostra_row.empty:
            continue
        
        amostra_row = amostra_row.iloc[0]
        
        print(f"\n{'='*70}")
        print(f"CASO {i+1}: {arquivo}")
        print(f"{'='*70}")
        
        # Valores do Excel (outra equipe)
        uc_excel = amostra_row.get('UC', 'N/A')
        cnpj_excel = amostra_row.get('CNPJ', 'N/A')
        razao_excel = amostra_row.get('Razao Social', 'N/A')
        
        print(f"\nVALORES EXTRAÍDOS (Excel outra equipe):")
        print(f"  UC: {uc_excel}")
        print(f"  CNPJ: {cnpj_excel}")
        print(f"  Razão: {str(razao_excel)[:60]}")
        
        # Buscar PDF e extrair texto
        pdf_path = None
        for pdf in pasta_pdfs.glob('*.pdf'):
            if arquivo[:30] in pdf.name:
                pdf_path = pdf
                break
        
        if pdf_path:
            try:
                with open_pdf(str(pdf_path)) as pdf:
                    texto = extract_all_text_from_pdf(pdf, max_pages=3, use_ocr_fallback=False)
                
                # Mostrar trecho relevante do PDF
                print(f"\nTRECHO DO PDF (primeiros 500 chars):")
                print(texto[:500].replace('\n', ' '))
                
                # Verificar presença manual
                uc_str = str(uc_excel) if pd.notna(uc_excel) else ''
                cnpj_str = str(cnpj_excel) if pd.notna(cnpj_excel) else ''
                
                print(f"\nVERIFICAÇÃO MANUAL:")
                if uc_str and uc_str in texto:
                    print(f"  UC '{uc_str}': ENCONTRADA ✓")
                else:
                    print(f"  UC '{uc_str}': NÃO ENCONTRADA ✗")
                    
                if cnpj_str and cnpj_str in texto:
                    print(f"  CNPJ '{cnpj_str}': ENCONTRADO ✓")
                else:
                    # Tentar sem formatação
                    cnpj_limpo = ''.join(c for c in cnpj_str if c.isdigit())
                    if cnpj_limpo and cnpj_limpo in texto:
                        print(f"  CNPJ '{cnpj_str}': ENCONTRADO (sem formatação) ✓")
                    else:
                        print(f"  CNPJ '{cnpj_str}': NÃO ENCONTRADO ✗")
                
            except Exception as e:
                print(f"  Erro ao ler PDF: {e}")
        
        resultados.append({
            'arquivo': arquivo,
            'uc_excel': uc_excel,
            'cnpj_excel': cnpj_excel,
            'status_uc': val_row['uc'],
            'status_cnpj': val_row['cnpj']
        })
    
    print("\n" + "=" * 70)
    print("CONCLUSÃO DA INVESTIGAÇÃO")
    print("=" * 70)
    
    return resultados

if __name__ == "__main__":
    investigar_divergencias()
