"""
Módulo principal de extração de dados de contratos PDF.
Orquestra a extração usando regex e tabelas conforme o modelo detectado.

OTIMIZADO: Abre cada PDF apenas uma vez para melhor performance.
"""
import re
import logging
import traceback
import fitz  # PyMuPDF
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

# Configurar logging
logger = logging.getLogger(__name__)

from .patterns import PatternsMixin, extract_field, FLAGS
from raizen_power.utils.validators import (
    validate_record, 
    calculate_confidence_score, 
    is_umbrella_contract,
    normalize_cnpj
)
from raizen_power.utils.normalizers import normalize_all
from .table_extractor import (
    extract_all_text,
    extract_all_text_from_pdf,
    extract_installations_from_anexo,
    extract_installations_from_pdf,
    extract_compact_installations_from_pdf,
    extract_modelo_2_data,
    extract_modelo_2_data_from_pdf,
    get_pdf_page_count
)
from raizen_power.analysis import classifier


@dataclass
class ExtractionResult:
    """Resultado da extração de um PDF."""
    arquivo: str
    tipo_documento: str
    modelo_detectado: str
    registros: List[Dict[str, Any]] = field(default_factory=list)
    alertas: List[str] = field(default_factory=list)
    confianca_score: int = 0
    is_guarda_chuva: bool = False
    paginas: int = 0
    distribuidora_classificada: str = ''
    categoria: str = ''


class ContractExtractor:
    """Extrator principal de contratos PDF."""
    
    def __init__(self):
        self.patterns = PatternsMixin()
    
    def detect_document_type(self, text: str) -> str:
        """Detecta o tipo de documento baseado no conteúdo."""
        for doc_type, pattern in self.patterns.DOCUMENT_TYPE_PATTERNS.items():
            if re.search(pattern, text, FLAGS):
                return doc_type
        return 'DESCONHECIDO'
    
    def detect_model(self, text: str) -> str:
        """Detecta o modelo/layout do documento."""
        for model, indicators in self.patterns.MODEL_INDICATORS.items():
            matches = sum(1 for ind in indicators if re.search(ind, text, FLAGS))
            if matches >= 2:
                return model
        
        # Fallback baseado em indicadores únicos fortes
        # SmartFit tem "DA QUALIFICAÇÃO DA CONSORCIADA" (não "DADOS DA")
        if re.search(r'DA\s+QUALIFICA[CÇ][ÃA]O\s+DA\s+CONSORCIADA|DADOS\s+DA\s+CONSORCIADA:', text, FLAGS):
            return 'MODELO_2_TABULAR'
        if re.search(r'CONSORCIADA\s*\(VOC[ÊE]\)', text, FLAGS):
            return 'MODELO_1_VISUAL'
        
        return 'MODELO_1_VISUAL'  # Default
    
    def extract_base_data(self, text: str, model: str) -> Dict[str, Any]:
        """Extrai dados básicos usando regex."""
        fields = [
            'razao_social', 'cnpj', 'email', 'email_secundario', 'endereco', 'cep',
            'distribuidora', 'num_instalacao', 'num_cliente',
            'qtd_cotas', 'valor_cota', 'pagamento_mensal',
            'vencimento', 'performance_alvo', 'duracao_meses',
            'representante_nome', 'representante_nome_secundario', 
            'representante_cpf', 'participacao_percentual'
        ]
        
        data = {}
        for field_name in fields:
            value = extract_field(text, field_name, model)
            if value:
                data[field_name] = value
        
        # Extrair dados do consórcio
        for field_name, patterns in self.patterns.CONSORCIO_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text, FLAGS)
                if match:
                    data[field_name] = match.group(1).strip()
                    break
        
        # Extrair cidade/UF do endereço
        if data.get('endereco'):
            self._parse_address(data)
        
        return data
    
    def _parse_address(self, data: Dict[str, Any]) -> None:
        """Extrai cidade e UF do endereço."""
        endereco = data.get('endereco', '')
        
        # Inicializar com valores vazios
        data['cidade'] = ''
        data['uf'] = ''
        
        # Se endereço está vazio ou inválido (só vírgulas e espaços)
        # Ex: "Endereço: , , , CEP" -> inválido
        if not endereco or len(endereco.strip(' ,')) < 10:
            return
        
        # Padrão: ..., Cidade, UF ou ..., Cidade - UF
        match = re.search(r',\s*([^,]+),\s*([A-Z]{2})\s*(?:,|$)', endereco)
        if match:
            data['cidade'] = match.group(1).strip()
            data['uf'] = match.group(2).strip()
        else:
            # Tentar outro padrão: ..., Cidade - UF
            match = re.search(r',\s*([^,-]+)\s*[-–]\s*([A-Z]{2})', endereco)
            if match:
                data['cidade'] = match.group(1).strip()
                data['uf'] = match.group(2).strip()
    
    def extract_from_pdf(self, pdf_path: str) -> ExtractionResult:
        """
        Extrai todos os dados de um PDF de contrato.
        
        OTIMIZADO: Abre o PDF apenas uma vez.
        
        Fluxo:
        1. Abre o PDF uma única vez
        2. Extrai texto completo
        3. Detecta tipo e modelo
        4. Extrai dados base via regex
        5. Se campos vazios, busca no Anexo I
        6. Se múltiplas instalações, gera múltiplos registros
        7. Valida e calcula score de confiança
        """
        pdf_path = Path(pdf_path)
        result = ExtractionResult(
            arquivo=pdf_path.name,
            tipo_documento='',
            modelo_detectado='',
            paginas=0
        )
        
        try:
            # Abrir PDF UMA ÚNICA VEZ (usando PyMuPDF)
            with fitz.open(str(pdf_path)) as pdf:
                # Obter número de páginas
                result.paginas = len(pdf)
                
                # Extrair texto completo (até 10 páginas)
                text = extract_all_text_from_pdf(pdf, max_pages=10)
                
                if not text:
                    result.alertas.append("Erro ao ler PDF: texto vazio")
                    return result
                
                # Classificar contrato (Dist + Categoria)
                dist_identified = classifier.identify_distributor_from_text(text)
                result.distribuidora_classificada = dist_identified
                
                if result.paginas <= 7:
                    result.categoria = 'SIMPLES'
                elif result.paginas > 16:
                    result.categoria = 'GUARDA_CHUVA'
                else:
                    result.categoria = 'PADRAO'
                
                # Detectar tipo e modelo
                result.tipo_documento = self.detect_document_type(text)
                result.modelo_detectado = self.detect_model(text)
                
                # Verificar se é contrato guarda-chuva
                result.is_guarda_chuva = is_umbrella_contract(text)
                if result.is_guarda_chuva:
                    result.alertas.append("Contrato Guarda-Chuva detectado - requer revisão manual")
                
                # Extrair dados base
                if result.modelo_detectado == 'MODELO_2_TABULAR':
                    # Para Modelo 2: regex primeiro (mais confiável para campos-chave)
                    base_data = self.extract_base_data(text, result.modelo_detectado)
                    # Complementar com extração tabular para campos não encontrados
                    table_data = extract_modelo_2_data_from_pdf(pdf)
                    for key, value in table_data.items():
                        if key not in base_data or not base_data[key]:
                            base_data[key] = value
                else:
                    base_data = self.extract_base_data(text, result.modelo_detectado)
                
                # IMPORTANTE: Verificar instalações compactadas PRIMEIRO
                # Contratos guarda-chuva (OI S.A.) têm centenas de UCs em uma célula
                compact_installations = extract_compact_installations_from_pdf(pdf)
                
                if compact_installations and len(compact_installations) > 1:
                    # Encontrou múltiplas instalações compactadas - é contrato guarda-chuva
                    result.is_guarda_chuva = True
                    result.alertas.append(f"Contrato guarda-chuva com {len(compact_installations)} instalações compactadas")
                    
                    seen_installations = set()
                    
                    for inst in compact_installations:
                        num_inst = inst.get('instalacao', '')
                        
                        if num_inst in seen_installations:
                            continue
                        seen_installations.add(num_inst)
                        
                        record = base_data.copy()
                        record['num_instalacao'] = num_inst
                        record['arquivo_origem'] = pdf_path.name
                        record['tipo_documento'] = result.tipo_documento
                        record['modelo_detectado'] = result.modelo_detectado
                        record['data_extracao'] = datetime.now().isoformat()
                        
                        alerts = validate_record(record)
                        record['alertas'] = '; '.join(alerts) if alerts else ''
                        record['confianca_score'] = calculate_confidence_score(record, alerts)
                        
                        result.registros.append(record)
                
                # Se não encontrou compactadas, buscar no Anexo I tradicional
                elif not base_data.get('num_instalacao'):
                    installations = extract_installations_from_pdf(pdf)
                    
                    if installations:
                        # Verificar duplicatas por número de instalação
                        seen_installations = set()
                        
                        # Gerar um registro para cada instalação única
                        for inst in installations:
                            num_inst = inst.get('instalacao', '')
                            
                            # Pular duplicatas
                            if num_inst in seen_installations:
                                result.alertas.append(f"Instalação duplicada ignorada: {num_inst}")
                                continue
                            seen_installations.add(num_inst)
                            
                            record = base_data.copy()
                            record['num_instalacao'] = num_inst
                            record['num_cliente'] = inst.get('cliente', record.get('num_cliente', ''))
                            record['qtd_cotas'] = inst.get('cotas', record.get('qtd_cotas', ''))
                            record['valor_cota'] = inst.get('valor_cota', record.get('valor_cota', ''))
                            record['performance_alvo'] = inst.get('performance', record.get('performance_alvo', ''))
                            
                            if inst.get('distribuidora'):
                                record['distribuidora'] = inst.get('distribuidora')
                            
                            # Adicionar metadados
                            record['arquivo_origem'] = pdf_path.name
                            record['tipo_documento'] = result.tipo_documento
                            record['modelo_detectado'] = result.modelo_detectado
                            record['data_extracao'] = datetime.now().isoformat()
                            
                            # Validar
                            alerts = validate_record(record)
                            record['alertas'] = '; '.join(alerts) if alerts else ''
                            record['confianca_score'] = calculate_confidence_score(record, alerts)
                            
                            result.registros.append(record)
                            result.alertas.extend(alerts)
                    else:
                        # Não encontrou instalações no Anexo I tradicional
                        # Tentar formato compactado (contratos guarda-chuva como OI S.A.)
                        compact_installations = extract_compact_installations_from_pdf(pdf)
                        
                        if compact_installations:
                            result.is_guarda_chuva = True
                            result.alertas.append(f"Contrato com {len(compact_installations)} instalações compactadas")
                            
                            seen_installations = set()
                            
                            for inst in compact_installations:
                                num_inst = inst.get('instalacao', '')
                                
                                if num_inst in seen_installations:
                                    continue
                                seen_installations.add(num_inst)
                                
                                record = base_data.copy()
                                record['num_instalacao'] = num_inst
                                record['arquivo_origem'] = pdf_path.name
                                record['tipo_documento'] = result.tipo_documento
                                record['modelo_detectado'] = result.modelo_detectado
                                record['data_extracao'] = datetime.now().isoformat()
                                
                                # Normalizar dados antes da validação
                                record = normalize_all(record)
                                
                                alerts = validate_record(record)
                                record['alertas'] = '; '.join(alerts) if alerts else ''
                                record['confianca_score'] = calculate_confidence_score(record, alerts)
                                
                                result.registros.append(record)
                        else:
                            result.alertas.append("Anexo I não encontrado ou sem instalações")
                
                # Se ainda não tem registros, criar registro único
                if not result.registros:
                    base_data['arquivo_origem'] = pdf_path.name
                    base_data['tipo_documento'] = result.tipo_documento
                    base_data['modelo_detectado'] = result.modelo_detectado
                    base_data['tipo_documento'] = result.tipo_documento
                    base_data['modelo_detectado'] = result.modelo_detectado
                    base_data['data_extracao'] = datetime.now().isoformat()
                    
                    # Se não encontrou distribuidora no texto, usar a classificada
                    if not base_data.get('distribuidora') and result.distribuidora_classificada not in ['OUTRAS_DESCONHECIDAS', 'ERRO_LEITURA', 'ERRO_OCR']:
                         base_data['distribuidora'] = result.distribuidora_classificada
                         base_data['metodo_distribuidora'] = 'CLASSIFICADOR_AUTO'
                    
                    # Normalizar dados antes da validação
                    base_data = normalize_all(base_data)
                    
                    alerts = validate_record(base_data)
                    base_data['alertas'] = '; '.join(alerts) if alerts else ''
                    base_data['confianca_score'] = calculate_confidence_score(base_data, alerts)
                    
                    result.registros.append(base_data)
                    result.alertas.extend(alerts)
                
                # Calcular score geral
                if result.registros:
                    result.confianca_score = min(
                        r.get('confianca_score', 0) for r in result.registros
                    )
        
        except Exception as e:
            result.alertas.append(f"Erro ao processar PDF: {e}")
            logger.error(f"Erro ao processar {pdf_path}: {e}")
        
        return result
    
    def process_batch(
        self, 
        pdf_paths: List[str], 
        progress_callback: callable = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Processa um lote de PDFs (versão sequencial).
        
        Retorna:
            - Lista de registros válidos (confiança >= 70)
            - Lista de registros para revisão (confiança < 70 ou guarda-chuva)
        """
        valid_records = []
        review_records = []
        
        total = len(pdf_paths)
        
        for i, pdf_path in enumerate(pdf_paths):
            try:
                result = self.extract_from_pdf(pdf_path)
                
                for record in result.registros:
                    # Adicionar flag de guarda-chuva
                    record['is_guarda_chuva'] = result.is_guarda_chuva
                    
                    # Classificar
                    if result.is_guarda_chuva or record.get('confianca_score', 0) < 70:
                        review_records.append(record)
                    else:
                        valid_records.append(record)
                
            except (FileNotFoundError, PermissionError) as e:
                # Erros de arquivo conhecidos
                logger.warning(f"Erro de arquivo em {pdf_path}: {e}")
                review_records.append({
                    'arquivo_origem': Path(pdf_path).name,
                    'alertas': f"Erro de arquivo: {str(e)}",
                    'confianca_score': 0,
                    'data_extracao': datetime.now().isoformat()
                })
            except Exception as e:
                # Erro genérico - log completo para debug
                error_detail = traceback.format_exc()
                logger.error(f"Erro crítico em {pdf_path}: {e}\n{error_detail}")
                review_records.append({
                    'arquivo_origem': Path(pdf_path).name,
                    'alertas': f"Erro crítico: {str(e)}",
                    'confianca_score': 0,
                    'data_extracao': datetime.now().isoformat()
                })
            
            # Callback de progresso
            if progress_callback:
                progress_callback(i + 1, total)
        
        return valid_records, review_records
    
    def process_batch_parallel(
        self, 
        pdf_paths: List[str], 
        max_workers: int = None,
        progress_callback: callable = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Processa um lote de PDFs em PARALELO usando múltiplos núcleos da CPU.
        
        PERFORMANCE: 4-8x mais rápido que sequencial em CPUs multi-core.
        
        Args:
            pdf_paths: Lista de caminhos para PDFs
            max_workers: Número de workers (padrão: núcleos da CPU)
            progress_callback: Função de callback para progresso
        
        Retorna:
            - Lista de registros válidos (confiança >= 70)
            - Lista de registros para revisão (confiança < 70 ou guarda-chuva)
        """
        from concurrent.futures import ProcessPoolExecutor, as_completed
        import multiprocessing
        
        valid_records = []
        review_records = []
        
        total = len(pdf_paths)
        
        # Determinar número de workers (padrão: núcleos - 1, mínimo 1)
        if max_workers is None:
            max_workers = max(1, multiprocessing.cpu_count() - 1)
        
        logger.info(f"Processamento paralelo: {max_workers} workers para {total} PDFs")
        
        # Processar em paralelo
        completed = 0
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submeter todos os jobs
            future_to_path = {
                executor.submit(_extract_single_pdf, pdf_path): pdf_path 
                for pdf_path in pdf_paths
            }
            
            # Coletar resultados conforme completam
            for future in as_completed(future_to_path):
                pdf_path = future_to_path[future]
                completed += 1
                
                try:
                    result_dict = future.result()
                    
                    for record in result_dict.get('registros', []):
                        record['is_guarda_chuva'] = result_dict.get('is_guarda_chuva', False)
                        
                        if result_dict.get('is_guarda_chuva') or record.get('confianca_score', 0) < 70:
                            review_records.append(record)
                        else:
                            valid_records.append(record)
                            
                except Exception as e:
                    logger.error(f"Erro ao processar {pdf_path}: {e}")
                    review_records.append({
                        'arquivo_origem': Path(pdf_path).name,
                        'alertas': f"Erro: {str(e)}",
                        'confianca_score': 0,
                        'data_extracao': datetime.now().isoformat()
                    })
                
                # Callback de progresso
                if progress_callback:
                    progress_callback(completed, total)
        
        return valid_records, review_records


def _extract_single_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Função auxiliar para extração paralela (executada em processo separado).
    
    Retorna dicionário serializável (não dataclass) para multiprocessing.
    """
    try:
        extractor = ContractExtractor()
        result = extractor.extract_from_pdf(pdf_path)
        
        # Converter para dict serializável
        return {
            'arquivo': result.arquivo,
            'tipo_documento': result.tipo_documento,
            'modelo_detectado': result.modelo_detectado,
            'registros': result.registros,
            'alertas': result.alertas,
            'confianca_score': result.confianca_score,
            'is_guarda_chuva': result.is_guarda_chuva,
            'paginas': result.paginas,
            'distribuidora_classificada': result.distribuidora_classificada,
            'categoria': result.categoria,
        }
    except Exception as e:
        return {
            'arquivo': Path(pdf_path).name,
            'registros': [],
            'alertas': [str(e)],
            'confianca_score': 0,
            'is_guarda_chuva': False,
        }
