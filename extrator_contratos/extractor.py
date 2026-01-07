"""
Módulo principal de extração de dados de contratos PDF.
Orquestra a extração usando regex e tabelas conforme o modelo detectado.
"""
import re
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

from .patterns import PatternsMixin, extract_field, FLAGS
from .validators import (
    validate_record, 
    calculate_confidence_score, 
    is_umbrella_contract,
    normalize_cnpj
)
from .table_extractor import (
    extract_all_text,
    extract_installations_from_anexo,
    extract_modelo_2_data,
    get_pdf_page_count
)


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
        if re.search(r'DADOS\s+DA\s+CONSORCIADA:', text, FLAGS):
            return 'MODELO_2_TABULAR'
        if re.search(r'CONSORCIADA\s*\(VOC[ÊE]\)', text, FLAGS):
            return 'MODELO_1_VISUAL'
        
        return 'MODELO_1_VISUAL'  # Default
    
    def extract_base_data(self, text: str, model: str) -> Dict[str, Any]:
        """Extrai dados básicos usando regex."""
        fields = [
            'razao_social', 'cnpj', 'email', 'endereco', 'cep',
            'distribuidora', 'num_instalacao', 'num_cliente',
            'qtd_cotas', 'valor_cota', 'pagamento_mensal',
            'vencimento', 'performance_alvo', 'duracao_meses',
            'representante_nome', 'representante_cpf', 'participacao_percentual'
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
        
        Fluxo:
        1. Extrai texto completo
        2. Detecta tipo e modelo
        3. Extrai dados base via regex
        4. Se campos vazios, busca no Anexo I
        5. Se múltiplas instalações, gera múltiplos registros
        6. Valida e calcula score de confiança
        """
        pdf_path = Path(pdf_path)
        result = ExtractionResult(
            arquivo=pdf_path.name,
            tipo_documento='',
            modelo_detectado='',
            paginas=get_pdf_page_count(str(pdf_path))
        )
        
        # Extrair texto completo (até 10 páginas)
        text = extract_all_text(str(pdf_path), max_pages=10)
        
        if text.startswith('ERRO:'):
            result.alertas.append(f"Erro ao ler PDF: {text}")
            return result
        
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
            table_data = extract_modelo_2_data(str(pdf_path))
            for key, value in table_data.items():
                if key not in base_data or not base_data[key]:
                    base_data[key] = value
        else:
            base_data = self.extract_base_data(text, result.modelo_detectado)
        
        # Se num_instalacao vazio, buscar no Anexo I
        if not base_data.get('num_instalacao'):
            installations = extract_installations_from_anexo(str(pdf_path))
            
            if installations:
                # Gerar um registro para cada instalação
                for inst in installations:
                    record = base_data.copy()
                    record['num_instalacao'] = inst.get('instalacao', '')
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
                # Não encontrou instalações no Anexo I
                result.alertas.append("Anexo I não encontrado ou sem instalações")
        
        # Se ainda não tem registros, criar registro único
        if not result.registros:
            base_data['arquivo_origem'] = pdf_path.name
            base_data['tipo_documento'] = result.tipo_documento
            base_data['modelo_detectado'] = result.modelo_detectado
            base_data['data_extracao'] = datetime.now().isoformat()
            
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
        
        return result
    
    def process_batch(
        self, 
        pdf_paths: List[str], 
        progress_callback: callable = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Processa um lote de PDFs.
        
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
                
            except Exception as e:
                # Registrar erro e adicionar à lista de revisão
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
