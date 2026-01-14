"""
Validação Automática: Compara valores extraídos com texto real do PDF.
"""
import pandas as pd
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.extrator_contratos.table_extractor import open_pdf, extract_all_text_from_pdf

def normalizar_cnpj(cnpj):
    """Remove formatação do CNPJ para comparação."""
    if pd.isna(cnpj):
        return ''
    return re.sub(r'[^\d]', '', str(cnpj))

def normalizar_texto(texto):
    """Normaliza texto para comparação."""
    if pd.isna(texto):
        return ''
    return str(texto).upper().strip()

def verificar_valor_no_pdf(texto_pdf, valor, tipo='texto'):
    """Verifica se um valor existe no texto do PDF."""
    if not valor or pd.isna(valor):
        return 'VAZIO_EXCEL'
    
    valor_str = str(valor).strip()
    
    if tipo == 'cnpj':
        # Para CNPJ, procura apenas os dígitos
        cnpj_limpo = normalizar_cnpj(valor_str)
        if len(cnpj_limpo) >= 11:
            # Procura o padrão no texto
            if cnpj_limpo in re.sub(r'[^\d]', '', texto_pdf):
                return 'OK'
            # Tenta formato com pontuação
            if valor_str in texto_pdf:
                return 'OK'
        return 'NAO_ENCONTRADO'
    
    elif tipo == 'uc':
        # Para UC, procura os dígitos
        uc_limpo = re.sub(r'[^\d]', '', str(valor_str))
        if uc_limpo and uc_limpo in texto_pdf:
            return 'OK'
        return 'NAO_ENCONTRADO'
    
    elif tipo == 'razao':
        # Para razão social, procura palavras-chave
        palavras = valor_str.upper().split()[:3]  # Primeiras 3 palavras
        encontradas = sum(1 for p in palavras if p in texto_pdf.upper())
        if encontradas >= 2:
            return 'OK'
        elif encontradas == 1:
            return 'PARCIAL'
        return 'NAO_ENCONTRADO'
    
    else:
        # Busca simples
        if valor_str.upper() in texto_pdf.upper():
            return 'OK'
        return 'NAO_ENCONTRADO'

def validar_amostra():
    print("=" * 70)
    print("VALIDAÇÃO AUTOMÁTICA DA AMOSTRA")
    print("=" * 70)
    
    # Carregar amostra
    df = pd.read_excel('output/amostra_validacao_50.xlsx')
    pasta_pdfs = Path('output/validacao_amostra_50')
    
    print(f"\nRegistros na amostra: {len(df)}")
    print(f"PDFs na pasta: {len(list(pasta_pdfs.glob('*.pdf')))}")
    
    resultados = []
    
    for idx, row in df.iterrows():
        arquivo = row['Arquivo Original']
        if pd.isna(arquivo):
            continue
        
        # Encontrar PDF
        pdf_path = None
        for pdf in pasta_pdfs.glob('*.pdf'):
            if arquivo in pdf.name or pdf.name in arquivo:
                pdf_path = pdf
                break
        
        if not pdf_path:
            resultados.append({
                'arquivo': arquivo[:50],
                'status': 'PDF_NAO_ENCONTRADO',
                'uc': 'N/A', 'cnpj': 'N/A', 'razao': 'N/A'
            })
            continue
        
        # Extrair texto do PDF
        try:
            with open_pdf(str(pdf_path)) as pdf:
                texto = extract_all_text_from_pdf(pdf, max_pages=5, use_ocr_fallback=False)
        except Exception as e:
            resultados.append({
                'arquivo': arquivo[:50],
                'status': f'ERRO_LEITURA: {str(e)[:30]}',
                'uc': 'N/A', 'cnpj': 'N/A', 'razao': 'N/A'
            })
            continue
        
        # Validar cada campo
        val_uc = verificar_valor_no_pdf(texto, row.get('UC'), 'uc')
        val_cnpj = verificar_valor_no_pdf(texto, row.get('CNPJ'), 'cnpj')
        val_razao = verificar_valor_no_pdf(texto, row.get('Razao Social'), 'razao')
        
        # Determinar status geral
        if val_uc == 'OK' and val_cnpj == 'OK' and val_razao in ['OK', 'PARCIAL']:
            status = 'VALIDADO'
        elif 'NAO_ENCONTRADO' in [val_uc, val_cnpj, val_razao]:
            status = 'DIVERGENCIA'
        else:
            status = 'PARCIAL'
        
        resultados.append({
            'arquivo': arquivo[:50],
            'status': status,
            'uc': val_uc,
            'cnpj': val_cnpj,
            'razao': val_razao
        })
        
        print(f"  [{idx+1:02d}] {status:12s} | UC:{val_uc:15s} | CNPJ:{val_cnpj:15s} | Razão:{val_razao}")
    
    # Resumo
    df_result = pd.DataFrame(resultados)
    
    print("\n" + "=" * 70)
    print("RESUMO DA VALIDAÇÃO")
    print("=" * 70)
    
    status_counts = df_result['status'].value_counts()
    for status, count in status_counts.items():
        pct = count / len(df_result) * 100
        print(f"  {status}: {count} ({pct:.1f}%)")
    
    # Métricas por campo
    print("\nMÉTRICAS POR CAMPO:")
    for campo in ['uc', 'cnpj', 'razao']:
        ok = (df_result[campo] == 'OK').sum()
        total = len(df_result[df_result[campo] != 'N/A'])
        if total > 0:
            print(f"  {campo.upper()}: {ok}/{total} corretos ({ok/total*100:.1f}%)")
    
    # Salvar relatório
    output_file = Path('output/relatorio_validacao_automatica.xlsx')
    df_result.to_excel(output_file, index=False)
    print(f"\n✅ Relatório salvo: {output_file}")
    
    return df_result

if __name__ == "__main__":
    validar_amostra()
