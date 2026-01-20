import yaml
import re
import pdfplumber
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from scripts.enrichment_logger import log_extraction, log_error

# Carregar config
CONFIG_PATH = Path('config/extraction_patterns.yaml')

class SignatureDetector:
    """Detecta páginas de assinatura baseada em heurísticas visuais e textuais."""
    
    @staticmethod
    def is_signature_page(page) -> bool:
        text = page.extract_text() or ""
        text_upper = text.upper()
        
        # Heurística 1: Palavras-chave de assinatura
        keywords = ["ASSINADO POR", "TESTEMUNHAS", "REPRESENTANTE LEGAL", "FIRMA RECONHECIDA"]
        has_keywords = any(k in text_upper for k in keywords)
        
        # Heurística 2: Presença de linhas para assinatura (_____)
        has_lines = bool(re.search(r'_{10,}', text))
        
        # Heurística 3: Densidade de texto (páginas de assinatura costumam ter menos texto corrido)
        lines = [l for l in text.split('\n') if l.strip()]
        low_density = len(lines) < 40 # Ajustável
        
        # Heurística 4: Padrão de CPF ou CNPJ próximo a nomes
        has_gov_id = bool(re.search(r'\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', text))
        
        # Pontuação
        score = 0
        if has_keywords: score += 3
        if has_lines: score += 2
        if low_density: score += 1
        if has_gov_id: score += 2
        
        return score >= 4

class TableExtractor:
    """Extrai tabelas de participação/quadro societário."""
    
    @staticmethod
    def extract_participation(pdf) -> Optional[float]:
        """
        Busca tabelas com 'Cota', 'Rateio', 'Percentual' e tenta extrair a soma ou valores.
        Retorna o maior valor percentual encontrado (assumindo que seja o do cliente) ou a soma se for quebrado.
        Simplificação: Retorna uma string descritiva ou o valor principal.
        """
        for page in pdf.pages:
            # Verificar se a página tem palavras-chave de tabela relevante
            text = page.extract_text() or ""
            if not re.search(r'(?i)(cota|rateio|percentual|participação|quadro\s+societário)', text):
                continue

            tables = page.extract_tables()
            for table in tables:
                # Converter para texto para buscar headers
                table_str = str(table).lower()
                if 'cota' in table_str or 'percentual' in table_str or '%' in table_str:
                    # Tentar extrair números percentuais da tabela
                    # Flatten da tabela
                    cells = [str(cell) for row in table for cell in row if cell]
                    percentages = []
                    for cell in cells:
                        # Buscar números seguidos de % ou em colunas de percentual
                        matches = re.findall(r'(\d+(?:[.,]\d{1,2})?)\s*%', cell)
                        for m in matches:
                            try:
                                val = float(m.replace(',', '.'))
                                if 0 < val <= 100:
                                    percentages.append(val)
                            except:
                                pass
                    
                    if percentages:
                        # Se encontrou percentuais, assumir que é uma tabela válida
                        # Retornar o maior valor (muitas vezes é a participação do cliente ou 100%)
                        # Mas cuidado: pode ser 100% da soma.
                        # Tentar heurística: se tiver múltiplos valores, retornar a lista como string
                        return sorted(percentages, reverse=True)
        return None

class ContractFieldExtractor:
    def __init__(self, config_path: Path = CONFIG_PATH):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        self.rules = self.config['extraction_rules']

    def extract_fields(self, pdf_path: str) -> Dict[str, Any]:
        result = {}
        doc_id = Path(pdf_path).stem
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                signature_text = ""
                
                # 1. Extração de Texto e Identificação de Seções
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    full_text += text + "\n"
                    
                    # Se for página de assinatura, guardar em variável separada para busca de CPF
                    if SignatureDetector.is_signature_page(page):
                        signature_text += text + "\n"
                
                # 2. Extração via Regex (Fidelidade, Aviso Prévio)
                # Fidelidade e Aviso Prévio geralmente estão no corpo do texto
                self._apply_regex_rule(doc_id, full_text, 'fidelidade', result)
                self._apply_regex_rule(doc_id, full_text, 'aviso_previo_dias', result)
                
                # 3. Extração de Representante (CPF) - Prioridade para páginas de assinatura
                # Se não achar na assinatura, busca no texto todo (mas com menos confiança)
                target_text_cpf = signature_text if signature_text else full_text
                self._apply_regex_rule(doc_id, target_text_cpf, 'representante_cpf', result)
                
                # Nome do Representante (Heurística baseada no CPF encontrado)
                if 'representante_cpf' in result and result['representante_cpf']:
                    cpf = result['representante_cpf']
                    # Tentar achar o nome em CAPS antes do CPF
                    name_match = re.search(r'([A-Z\s]{5,50})[\s\n]*' + re.escape(cpf), target_text_cpf)
                    if name_match:
                        name = name_match.group(1).strip()
                        # Limpar ruídos comuns
                        name = re.sub(r'(CPF|MF|INSCRITO|SOB|Nº|NO)\s*$', '', name, flags=re.IGNORECASE).strip()
                        result['representante_nome'] = name
                
                # 4. Extração de Tabela (Participação)
                percentages = TableExtractor.extract_participation(pdf)
                if percentages:
                    # Se tiver um único valor e for < 100, é provavelmente a participação
                    # Se tiver vários, pegar o maior que não seja 100 (se existir), senão o maior
                    valid_pcts = [p for p in percentages if p < 99.9]
                    val = valid_pcts[0] if valid_pcts else percentages[0]
                    result['participacao_percentual'] = val
                    log_extraction(doc_id, 'participacao_percentual', val, 0.9, 'SUCCESS', {'source': 'table'})
                else:
                    # Tentar regex se tabela falhar
                    self._apply_regex_rule(doc_id, full_text, 'participacao_percentual', result)

        except Exception as e:
            log_error(doc_id, "Falha na abertura/processamento do PDF", e)
            
        return result

    def _apply_regex_rule(self, doc_id, text, field, result_dict):
        rule = self.rules.get(field)
        if not rule:
            return

        match = re.search(rule['pattern'], text)
        if match:
            # Pegar o primeiro grupo de captura
            val = match.group(1) 
            
            # Validação simples
            if 'validation' in rule:
                v = rule['validation']
                try:
                    num_val = float(val.replace(',', '.'))
                    if 'min' in v and num_val < v['min']: return
                    if 'max' in v and num_val > v['max']: return
                except:
                    pass # Se não for número, ignora validação numérica por enquanto
            
            result_dict[field] = val
            log_extraction(doc_id, field, val, rule.get('confidence_threshold', 0.8), 'SUCCESS')
        else:
             # Logar apenas em debug ou se for crítico
             pass

if __name__ == "__main__":
    # Teste rápido
    print("Testando ContractFieldExtractor...")
    # Substituir por um PDF real para teste
    import sys
    if len(sys.argv) > 1:
        extractor = ContractFieldExtractor()
        res = extractor.extract_fields(sys.argv[1])
        print(yaml.dump(res, allow_unicode=True))
