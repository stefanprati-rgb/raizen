"""
Extrator de tabelas de PDFs usando pdfplumber.
Especializado em extrair dados do Anexo I e tabelas de instalações.
"""
import pdfplumber
import re
from typing import List, Dict, Any, Optional
from pathlib import Path


def extract_all_text(pdf_path: str, max_pages: int = 10) -> str:
    """
    Extrai todo o texto de um PDF (até max_pages páginas).
    
    Args:
        pdf_path: Caminho para o PDF
        max_pages: Número máximo de páginas a processar
    
    Returns:
        Texto extraído concatenado com marcadores de página
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            pages_to_process = min(max_pages, total_pages)
            
            text = ""
            
            # Aviso se PDF tem mais páginas do que o limite
            if total_pages > max_pages:
                text += f"\n[AVISO: PDF tem {total_pages} páginas, processando apenas {max_pages}]\n"
            
            for i, page in enumerate(pdf.pages[:pages_to_process]):
                page_text = page.extract_text() or ""
                text += f"\n[PAGINA_{i+1}]\n{page_text}"
            
            return text
    except Exception as e:
        return f"ERRO: {e}"


def find_anexo_i_page(pdf_path: str) -> Optional[int]:
    """Encontra a página que contém o Anexo I."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if re.search(r'ANEXO\s+I|UNIDADE\(S\)\s+CONSUMIDORA\(S\)', text, re.IGNORECASE):
                    return i
    except Exception:
        pass
    return None


def extract_tables_from_page(pdf_path: str, page_num: int) -> List[List[List[str]]]:
    """Extrai todas as tabelas de uma página específica."""
    tables = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if page_num < len(pdf.pages):
                page = pdf.pages[page_num]
                extracted = page.extract_tables()
                if extracted:
                    # Limpar células vazias e normalizar
                    for table in extracted:
                        cleaned_table = []
                        for row in table:
                            cleaned_row = [
                                (cell or '').strip() 
                                for cell in row
                            ]
                            if any(cleaned_row):  # Ignorar linhas vazias
                                cleaned_table.append(cleaned_row)
                        if cleaned_table:
                            tables.append(cleaned_table)
    except Exception as e:
        print(f"Erro ao extrair tabelas: {e}")
    
    return tables


def parse_installation_table(table: List[List[str]]) -> List[Dict[str, Any]]:
    """
    Converte uma tabela de instalações em lista de dicionários.
    Detecta automaticamente os cabeçalhos e mapeia os dados.
    """
    if not table or len(table) < 2:
        return []
    
    # Tentar identificar linha de cabeçalho
    header_row = None
    data_start = 0
    
    header_keywords = {
        'instalacao': ['instalação', 'instalacao', 'unidade consumidora', 'nº instalação'],
        'cliente': ['cliente', 'nº cliente', 'n cliente'],
        'cotas': ['cotas', 'qtd cotas', 'quantidade de cotas'],
        'valor_cota': ['valor cota', 'valor da cota', 'vlr cota'],
        'performance': ['performance', 'performance alvo', 'kwh'],
        'distribuidora': ['distribuidora', 'concessionária'],
    }
    
    for i, row in enumerate(table):
        row_text = ' '.join(str(cell).lower() for cell in row)
        matches = sum(
            1 for keywords in header_keywords.values()
            if any(kw in row_text for kw in keywords)
        )
        if matches >= 2:  # Pelo menos 2 cabeçalhos encontrados
            header_row = row
            data_start = i + 1
            break
    
    if header_row is None:
        # Assumir primeira linha como cabeçalho
        header_row = table[0]
        data_start = 1
    
    # Mapear cabeçalhos para campos
    column_mapping = {}
    for col_idx, header in enumerate(header_row):
        header_lower = str(header).lower().strip()
        for field, keywords in header_keywords.items():
            if any(kw in header_lower for kw in keywords):
                column_mapping[col_idx] = field
                break
    
    # Extrair dados das linhas
    installations = []
    for row in table[data_start:]:
        if len(row) <= max(column_mapping.keys(), default=0):
            continue
        
        record = {}
        for col_idx, field in column_mapping.items():
            if col_idx < len(row):
                value = str(row[col_idx]).strip()
                if value and value.lower() not in ['none', 'nan', '-']:
                    record[field] = value
        
        # Só adicionar se tiver pelo menos instalação ou cliente
        if record.get('instalacao') or record.get('cliente'):
            installations.append(record)
    
    return installations


def extract_installations_from_anexo(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extrai lista de instalações do Anexo I de um PDF.
    Retorna lista de dicionários com dados de cada instalação.
    """
    anexo_page = find_anexo_i_page(pdf_path)
    
    if anexo_page is None:
        return []
    
    # Tentar extrair da página do Anexo I e da próxima (tabela pode continuar)
    all_installations = []
    
    for page_offset in range(3):  # Verificar até 3 páginas a partir do Anexo I
        tables = extract_tables_from_page(pdf_path, anexo_page + page_offset)
        
        for table in tables:
            installations = parse_installation_table(table)
            all_installations.extend(installations)
    
    return all_installations


def extract_modelo_2_data(pdf_path: str) -> Dict[str, Any]:
    """
    Extrai dados estruturados do Modelo 2 (tabular/Docusign).
    Usa extração de tabelas para campos que estão em formato tabular.
    """
    data = {}
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Primeira página geralmente tem os dados principais
            if pdf.pages:
                tables = pdf.pages[0].extract_tables()
                
                for table in tables:
                    for row in table:
                        if not row or len(row) < 2:
                            continue
                        
                        # Mapear campos conhecidos
                        key = str(row[0]).strip().lower() if row[0] else ''
                        value = str(row[1]).strip() if len(row) > 1 and row[1] else ''
                        
                        if 'razão social' in key or 'razao social' in key:
                            data['razao_social'] = value
                        elif 'cnpj' in key:
                            data['cnpj'] = value
                        elif 'endereço' in key or 'endereco' in key:
                            data['endereco'] = value
                        elif 'e-mail' in key or 'email' in key:
                            data['email'] = value
                        elif 'distribuidora' in key:
                            data['distribuidora'] = value
                        elif 'instalação' in key or 'instalacao' in key:
                            data['num_instalacao'] = value
                        elif 'cliente' in key:
                            data['num_cliente'] = value
                        elif 'pagamento mensal' in key:
                            data['pagamento_mensal'] = value
                        elif 'vencimento' in key:
                            data['vencimento'] = value
                        elif 'valor' in key and 'cota' in key:
                            data['valor_cota'] = value
                        elif 'performance' in key:
                            data['performance_alvo'] = value
                        elif 'vigência' in key or 'vigencia' in key:
                            # Extrair número de meses
                            match = re.search(r'(\d+)\s*meses', value, re.IGNORECASE)
                            if match:
                                data['duracao_meses'] = match.group(1)
                        elif 'participação' in key or 'participacao' in key:
                            data['participacao_percentual'] = value
    except Exception as e:
        print(f"Erro ao extrair dados do Modelo 2: {e}")
    
    return data


def get_pdf_page_count(pdf_path: str) -> int:
    """Retorna o número de páginas de um PDF."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            return len(pdf.pages)
    except Exception:
        return 0
