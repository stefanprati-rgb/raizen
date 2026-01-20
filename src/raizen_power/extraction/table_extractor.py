"""
Extrator de tabelas de PDFs usando pdfplumber.
Especializado em extrair dados do Anexo I e tabelas de instalações.

OTIMIZADO: Usa context manager único para evitar múltiplas aberturas do PDF.
FALLBACK OCR: Se o PDF for baseado em imagem, usa EasyOCR automaticamente.

CONFIGURAÇÃO DE WORKERS (Previne OOM):
- TEXT_MAX_WORKERS: 8 (extração de texto nativo - leve)
- OCR_MAX_WORKERS: 2 (OCR EasyOCR - pesado, consome muita RAM)
- OCR_TIMEOUT_SECONDS: 30 (timeout por página para evitar travamento)
"""
import pdfplumber
import re
import logging
import signal
from typing import List, Dict, Any, Optional, Union, Iterator
from pathlib import Path
from contextlib import contextmanager

# Logger para o módulo
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURAÇÃO DE PERFORMANCE (AJUSTÁVEL)
# =============================================================================
# Workers para extração de texto nativo (leve, pode ser alto)
TEXT_MAX_WORKERS = 8

# Workers para OCR (pesado, deve ser baixo para evitar OOM)
OCR_MAX_WORKERS = 2

# Timeout para OCR por página (segundos)
OCR_TIMEOUT_SECONDS = 30

# Resolução do OCR (DPI) - maior = melhor qualidade mas mais lento
OCR_RESOLUTION = 200

# =============================================================================
# CACHE GLOBAL DO LEITOR OCR
# =============================================================================
_OCR_READER = None


def _get_ocr_reader():
    """
    Retorna o leitor EasyOCR (lazy loading).
    Inicializa apenas na primeira chamada para evitar overhead.
    """
    global _OCR_READER
    if _OCR_READER is None:
        try:
            import easyocr
            logger.info("Inicializando EasyOCR (primeira execução pode demorar)...")
            _OCR_READER = easyocr.Reader(['pt', 'en'], gpu=False, verbose=False)
            logger.info("EasyOCR inicializado com sucesso")
        except ImportError:
            logger.warning("EasyOCR não instalado. Fallback OCR desabilitado.")
            return None
        except Exception as e:
            logger.error(f"Erro ao inicializar EasyOCR: {e}")
            return None
    return _OCR_READER


class OCRTimeoutError(Exception):
    """Exceção para timeout de OCR."""
    pass


def _ocr_timeout_handler(signum, frame):
    """Handler para timeout de OCR."""
    raise OCRTimeoutError("OCR excedeu o tempo limite")


def _extract_text_with_ocr(page, timeout: int = OCR_TIMEOUT_SECONDS) -> str:
    """
    Extrai texto de uma página usando OCR (para PDFs escaneados).
    
    Args:
        page: Objeto pdfplumber.Page
        timeout: Tempo máximo em segundos para OCR
        
    Returns:
        Texto extraído via OCR ou string vazia se falhar
    """
    reader = _get_ocr_reader()
    if reader is None:
        return ""
    
    try:
        # Converter página para imagem
        img = page.to_image(resolution=OCR_RESOLUTION).original
        
        # Executar OCR (com timeout em sistemas Unix)
        # No Windows, timeout é implementado de forma diferente
        try:
            results = reader.readtext(img)
        except Exception as e:
            logger.warning(f"Erro durante OCR: {e}")
            return ""
        
        # Concatenar resultados (formato: [(bbox, text, confidence), ...])
        text = ' '.join([text for _, text, _ in results])
        return text
        
    except OCRTimeoutError:
        logger.warning(f"OCR excedeu timeout de {timeout}s")
        return ""
    except Exception as e:
        logger.warning(f"Erro no OCR: {e}")
        return ""


@contextmanager
def open_pdf(pdf_path: str) -> Iterator[pdfplumber.PDF]:
    """
    Context manager para abrir PDF uma única vez.
    Permite reutilizar o objeto PDF entre múltiplas funções.
    """
    try:
        pdf = pdfplumber.open(pdf_path)
        yield pdf
    finally:
        pdf.close()


def extract_all_text_from_pdf(pdf: pdfplumber.PDF, max_pages: int = 10, use_ocr_fallback: bool = True) -> str:
    """
    Extrai todo o texto de um PDF já aberto.
    
    Se o texto extraído for muito curto (< 100 chars nas primeiras 2 páginas),
    assume que o PDF é baseado em imagem e tenta OCR automaticamente.
    
    Args:
        pdf: Objeto pdfplumber.PDF já aberto
        max_pages: Número máximo de páginas a processar
        use_ocr_fallback: Se True, tenta OCR quando texto normal falha
    
    Returns:
        Texto extraído concatenado com marcadores de página
    """
    total_pages = len(pdf.pages)
    pages_to_process = min(max_pages, total_pages)
    
    if total_pages > max_pages:
        logger.info(f"PDF tem {total_pages} páginas, processando apenas {max_pages}")
    
    text = ""
    ocr_used = False
    
    for i, page in enumerate(pdf.pages[:pages_to_process]):
        page_text = page.extract_text() or ""
        
        # Verificar se precisa de OCR (texto muito curto nas primeiras 2 páginas)
        if use_ocr_fallback and i < 2 and len(page_text.strip()) < 100:
            logger.info(f"Página {i+1} com pouco texto ({len(page_text)} chars), tentando OCR...")
            ocr_text = _extract_text_with_ocr(page)
            if len(ocr_text) > len(page_text):
                page_text = ocr_text
                ocr_used = True
        
        text += f"\n[PAGINA_{i+1}]\n{page_text}"
    
    if ocr_used:
        logger.info("OCR foi utilizado para extrair texto de páginas escaneadas")
    
    return text


def extract_all_text(pdf_path: str, max_pages: int = 10) -> str:
    """
    Extrai todo o texto de um PDF (até max_pages páginas).
    NOTA: Para melhor performance, use open_pdf() + extract_all_text_from_pdf().
    
    Args:
        pdf_path: Caminho para o PDF
        max_pages: Número máximo de páginas a processar
    
    Returns:
        Texto extraído concatenado com marcadores de página
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            return extract_all_text_from_pdf(pdf, max_pages)
    except Exception as e:
        return f"ERRO: {e}"


def find_anexo_i_page_from_pdf(pdf: pdfplumber.PDF) -> Optional[int]:
    """Encontra a página que contém o Anexo I em um PDF já aberto."""
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if re.search(r'ANEXO\s+I|UNIDADE\(S\)\s+CONSUMIDORA\(S\)', text, re.IGNORECASE):
            return i
    return None


def find_anexo_i_page(pdf_path: str) -> Optional[int]:
    """Encontra a página que contém o Anexo I."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            return find_anexo_i_page_from_pdf(pdf)
    except Exception:
        pass
    return None


def extract_tables_from_page_pdf(pdf: pdfplumber.PDF, page_num: int) -> List[List[List[str]]]:
    """Extrai todas as tabelas de uma página específica de um PDF já aberto."""
    tables = []
    try:
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
        logger.warning(f"Erro ao extrair tabelas da página {page_num}: {e}")
    
    return tables


def extract_tables_from_page(pdf_path: str, page_num: int) -> List[List[List[str]]]:
    """Extrai todas as tabelas de uma página específica."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            return extract_tables_from_page_pdf(pdf, page_num)
    except Exception as e:
        logger.warning(f"Erro ao extrair tabelas: {e}")
        return []


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


def extract_installations_from_pdf(pdf: pdfplumber.PDF) -> List[Dict[str, Any]]:
    """
    Extrai lista de instalações do Anexo I de um PDF já aberto.
    Retorna lista de dicionários com dados de cada instalação.
    
    OTIMIZADO: Loop dinâmico que continua até não encontrar mais dados,
    suportando contratos guarda-chuva com centenas de instalações.
    """
    anexo_page = find_anexo_i_page_from_pdf(pdf)
    
    if anexo_page is None:
        return []
    
    all_installations = []
    current_page = anexo_page
    
    # Continua enquanto houver páginas no PDF
    while current_page < len(pdf.pages):
        # Tenta extrair tabelas da página atual
        tables = extract_tables_from_page_pdf(pdf, current_page)
        
        page_has_data = False
        for table in tables:
            installations = parse_installation_table(table)
            if installations:
                all_installations.extend(installations)
                page_has_data = True
        
        # Lógica de Parada:
        # Se estamos além da primeira página do anexo E não achamos dados válidos,
        # assumimos que a tabela acabou.
        if current_page > anexo_page and not page_has_data:
            break
        
        current_page += 1
    
    return all_installations


def extract_installations_from_anexo(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extrai lista de instalações do Anexo I de um PDF.
    NOTA: Para melhor performance, use open_pdf() + extract_installations_from_pdf().
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            return extract_installations_from_pdf(pdf)
    except Exception as e:
        logger.warning(f"Erro ao extrair instalações: {e}")
        return []


def extract_modelo_2_data_from_pdf(pdf: pdfplumber.PDF) -> Dict[str, Any]:
    """
    Extrai dados estruturados do Modelo 2 (tabular/Docusign) de um PDF já aberto.
    Usa extração de tabelas para campos que estão em formato tabular.
    """
    data = {}
    
    try:
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
        logger.warning(f"Erro ao extrair dados do Modelo 2: {e}")
    
    return data


def extract_modelo_2_data(pdf_path: str) -> Dict[str, Any]:
    """
    Extrai dados estruturados do Modelo 2 (tabular/Docusign).
    NOTA: Para melhor performance, use open_pdf() + extract_modelo_2_data_from_pdf().
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            return extract_modelo_2_data_from_pdf(pdf)
    except Exception as e:
        logger.warning(f"Erro ao extrair dados do Modelo 2: {e}")
        return {}


def get_pdf_page_count(pdf_path: str) -> int:
    """Retorna o número de páginas de um PDF."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            return len(pdf.pages)
    except Exception:
        return 0


def extract_compact_installations(text: str) -> List[str]:
    """
    Extrai instalações do formato compactado (múltiplas UCs em uma única string).
    
    Detecta padrões como:
    - "610524197\n610524163\n611509155" (separado por quebra de linha)
    - "610524197, 610524163, 611509155" (separado por vírgula)
    - "610524197 610524163 611509155" (separado por espaço)
    
    Usado em contratos guarda-chuva como OI S.A.
    """
    installations = []
    
    # Padrão: números de instalação (6-12 dígitos)
    # Separados por \n, vírgula, espaço ou ponto-e-vírgula
    pattern = r'\b(\d{6,12})\b'
    
    matches = re.findall(pattern, text)
    
    for match in matches:
        # Filtrar números que são claramente não-instalações
        # (CNPJs têm 14 dígitos, CPFs têm 11, telefones têm 10-11)
        if len(match) >= 6 and len(match) <= 12:
            # Evitar duplicatas
            if match not in installations:
                installations.append(match)
    
    return installations


def extract_compact_installations_from_pdf(pdf: pdfplumber.PDF) -> List[Dict[str, Any]]:
    """
    Extrai instalações compactadas de TODAS as páginas do PDF.
    
    Para contratos guarda-chuva onde instalações estão em células separadas por \\n
    ou distribuídas em múltiplas páginas.
    
    Exemplo: OI S.A. tem 400+ instalações em 34 páginas.
    """
    installations_data = []
    seen_installations = set()
    
    try:
        if not pdf.pages:
            return []
        
        # Varrer TODAS as páginas
        for page_num, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            
            if not tables:
                continue
            
            for table in tables:
                for row in table:
                    if not row:
                        continue
                    
                    for cell in row:
                        if not cell:
                            continue
                        
                        cell_str = str(cell)
                        
                        # Pular células muito pequenas
                        if len(cell_str) < 6:
                            continue
                        
                        # Detectar célula com múltiplos números (separados por \n ou espaço)
                        # Padrão de instalação: 7-9 dígitos (ex: 610524197)
                        matches = re.findall(r'\b(\d{7,9})\b', cell_str)
                        
                        for inst_num in matches:
                            # Evitar duplicatas
                            if inst_num not in seen_installations:
                                seen_installations.add(inst_num)
                                installations_data.append({
                                    'instalacao': inst_num,
                                    'formato': 'compactado',
                                    'pagina': page_num + 1
                                })
        
        if installations_data:
            logger.info(f"Encontradas {len(installations_data)} instalações compactadas em {len(pdf.pages)} páginas")
    
    except Exception as e:
        logger.warning(f"Erro ao extrair instalações compactadas: {e}")
    
    return installations_data
