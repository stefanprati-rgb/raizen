"""
Gerenciador de Mapas de Extração (Gemini AI Integration)
Versão: 1.0

Este módulo gerencia os mapas de extração gerados pelo Gemini AI.
Inclui versionamento, validação de regex e cache de mapas.

Estrutura de um mapa:
{
    "grupo": "CPFL_PAULISTA_09p",
    "versao": "v1",
    "hash": "a1b2c3d4",
    "data_geracao": "2026-01-09T10:00:00",
    "campos": {
        "cnpj": {
            "ancora": "CNPJ:",
            "regex": "\\d{2}\\.\\d{3}\\.\\d{3}/\\d{4}-\\d{2}",
            "valor_amostra": "03.389.281/0001-04",
            "regex_validado": true
        }
    }
}
"""
import re
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)

# Diretório padrão para mapas
MAPS_DIR = Path("maps")


class MapValidationError(Exception):
    """Erro de validação de mapa."""
    pass


class MapManager:
    """
    Gerenciador de Mapas de Extração.
    
    Responsabilidades:
    - Salvar mapas com versionamento
    - Validar regex gerados pela IA
    - Carregar mapa mais recente para um grupo
    - Listar versões disponíveis
    """
    
    def __init__(self, maps_dir: Path = MAPS_DIR):
        self.maps_dir = Path(maps_dir)
        self.maps_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, dict] = {}
    
    def _generate_hash(self, content: str) -> str:
        """Gera hash curto do conteúdo para identificação."""
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    def _get_next_version(self, grupo: str) -> int:
        """Retorna a próxima versão disponível para um grupo."""
        existing = list(self.maps_dir.glob(f"{grupo}_v*.json"))
        if not existing:
            return 1
        
        versions = []
        for f in existing:
            match = re.search(r'_v(\d+)\.json$', f.name)
            if match:
                versions.append(int(match.group(1)))
        
        return max(versions) + 1 if versions else 1
    
    def validate_regex(
        self, 
        regex_pattern: str, 
        sample_text: str, 
        expected_value: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Valida se um regex extrai o valor esperado do texto de amostra.
        
        Args:
            regex_pattern: Padrão regex a testar
            sample_text: Texto onde buscar
            expected_value: Valor que a IA disse ter extraído
            
        Returns:
            (is_valid, extracted_value)
        """
        try:
            # Compilar regex
            pattern = re.compile(regex_pattern, re.IGNORECASE | re.MULTILINE)
            
            # Buscar no texto
            match = pattern.search(sample_text)
            
            if not match:
                logger.warning(f"Regex não encontrou match: {regex_pattern[:50]}...")
                return False, None
            
            # Extrair valor (grupo 1 se existir, senão match completo)
            extracted = match.group(1) if match.groups() else match.group(0)
            
            # Normalizar para comparação
            norm_extracted = re.sub(r'\s+', '', extracted.upper())
            norm_expected = re.sub(r'\s+', '', expected_value.upper())
            
            is_valid = norm_extracted == norm_expected
            
            if not is_valid:
                logger.warning(
                    f"Regex extraiu valor diferente: "
                    f"esperado='{expected_value}', extraído='{extracted}'"
                )
            
            return is_valid, extracted
            
        except re.error as e:
            logger.error(f"Regex inválido: {e}")
            return False, None
    
    def validate_map(
        self, 
        mapa: dict, 
        sample_text: str,
        strict: bool = True
    ) -> Tuple[bool, List[str]]:
        """
        Valida todos os campos de um mapa contra texto de amostra.
        
        Args:
            mapa: Mapa de extração
            sample_text: Texto do PDF de amostra
            strict: Se True, falha se QUALQUER regex falhar
            
        Returns:
            (all_valid, list_of_errors)
        """
        errors = []
        campos = mapa.get('campos', {})
        
        for campo, config in campos.items():
            regex = config.get('regex', '')
            expected = config.get('valor_amostra', '')
            
            if not regex or not expected:
                continue
            
            is_valid, extracted = self.validate_regex(regex, sample_text, expected)
            
            if not is_valid:
                errors.append(
                    f"REGEX_MISMATCH: Campo '{campo}' - "
                    f"IA extraiu '{expected}', regex extraiu '{extracted}'"
                )
                config['regex_validado'] = False
            else:
                config['regex_validado'] = True
        
        all_valid = len(errors) == 0
        
        if strict and not all_valid:
            logger.error(f"Mapa rejeitado: {len(errors)} erros de validação")
        
        return all_valid, errors
    
    def save_map(
        self, 
        grupo: str, 
        campos: dict, 
        sample_text: str = None,
        validate: bool = True,
        metadata: dict = None
    ) -> Path:
        """
        Salva um mapa com versionamento automático.
        
        Args:
            grupo: Nome do grupo (ex: "CPFL_PAULISTA_09p")
            campos: Dicionário de campos com regex
            sample_text: Texto para validação (opcional)
            validate: Se True, valida regex antes de salvar
            metadata: Metadados adicionais
            
        Returns:
            Path do arquivo salvo
            
        Raises:
            MapValidationError: Se validação falhar
        """
        # Construir mapa
        version = self._get_next_version(grupo)
        content_str = json.dumps(campos, sort_keys=True)
        content_hash = self._generate_hash(content_str)
        
        mapa = {
            "grupo": grupo,
            "versao": f"v{version}",
            "hash": content_hash,
            "data_geracao": datetime.now().isoformat(),
            "campos": campos,
            **(metadata or {})
        }
        
        # Validar se solicitado
        if validate and sample_text:
            is_valid, errors = self.validate_map(mapa, sample_text)
            
            if not is_valid:
                error_msg = f"Mapa falhou validação: {'; '.join(errors)}"
                logger.error(error_msg)
                
                # Salvar como rejeitado para análise
                rejected_path = self.maps_dir / f"{grupo}_v{version}_REJECTED.json"
                mapa['validation_errors'] = errors
                mapa['status'] = 'REJECTED'
                
                with open(rejected_path, 'w', encoding='utf-8') as f:
                    json.dump(mapa, f, ensure_ascii=False, indent=2)
                
                raise MapValidationError(error_msg)
        
        # Salvar mapa aprovado
        mapa['status'] = 'VALIDATED' if validate else 'NOT_VALIDATED'
        filename = f"{grupo}_v{version}.json"
        filepath = self.maps_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(mapa, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Mapa salvo: {filepath}")
        
        # Atualizar cache
        self._cache[grupo] = mapa
        
        return filepath
    
    def load_map(self, grupo: str, version: int = None) -> Optional[dict]:
        """
        Carrega um mapa para um grupo.
        
        Args:
            grupo: Nome do grupo
            version: Versão específica (None = mais recente)
            
        Returns:
            Mapa ou None se não encontrado
        """
        # Verificar cache
        if grupo in self._cache and version is None:
            return self._cache[grupo]
        
        # Buscar arquivos
        if version:
            filepath = self.maps_dir / f"{grupo}_v{version}.json"
            if not filepath.exists():
                return None
        else:
            # Buscar versão mais recente
            files = sorted(
                self.maps_dir.glob(f"{grupo}_v*.json"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            # Filtrar rejeitados
            files = [f for f in files if 'REJECTED' not in f.name]
            
            if not files:
                return None
            
            filepath = files[0]
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                mapa = json.load(f)
            
            # Atualizar cache
            if version is None:
                self._cache[grupo] = mapa
            
            return mapa
            
        except Exception as e:
            logger.error(f"Erro ao carregar mapa {filepath}: {e}")
            return None
    
    def list_versions(self, grupo: str) -> List[dict]:
        """Lista todas as versões disponíveis para um grupo."""
        files = sorted(self.maps_dir.glob(f"{grupo}_v*.json"))
        
        versions = []
        for f in files:
            try:
                with open(f, 'r', encoding='utf-8') as fp:
                    mapa = json.load(fp)
                    versions.append({
                        'arquivo': f.name,
                        'versao': mapa.get('versao', 'unknown'),
                        'data': mapa.get('data_geracao', 'unknown'),
                        'status': mapa.get('status', 'unknown'),
                        'hash': mapa.get('hash', 'unknown')
                    })
            except Exception:
                pass
        
        return versions
    
    def list_all_groups(self) -> List[str]:
        """Lista todos os grupos com mapas disponíveis."""
        files = self.maps_dir.glob("*_v*.json")
        groups = set()
        
        for f in files:
            if 'REJECTED' not in f.name:
                match = re.match(r'(.+)_v\d+\.json', f.name)
                if match:
                    groups.add(match.group(1))
        
        return sorted(list(groups))


def extract_with_map(text: str, mapa: dict) -> Dict[str, Any]:
    """
    Extrai campos de um texto usando um mapa de extração.
    
    Args:
        text: Texto do PDF
        mapa: Mapa de extração
        
    Returns:
        Dicionário com campos extraídos
    """
    result = {}
    campos = mapa.get('campos', {})
    
    for campo, config in campos.items():
        regex = config.get('regex', '')
        ancora = config.get('ancora', '')
        
        if not regex:
            continue
        
        try:
            # Se tem âncora, buscar após ela
            search_text = text
            if ancora:
                ancora_match = re.search(re.escape(ancora), text, re.IGNORECASE)
                if ancora_match:
                    search_text = text[ancora_match.end():]
            
            # Executar regex
            pattern = re.compile(regex, re.IGNORECASE | re.MULTILINE)
            match = pattern.search(search_text)
            
            if match:
                value = match.group(1) if match.groups() else match.group(0)
                result[campo] = value.strip()
            else:
                result[campo] = None
                
        except Exception as e:
            logger.warning(f"Erro ao extrair '{campo}': {e}")
            result[campo] = None
    
    return result


# Instância global para uso simplificado
_manager = None

def get_map_manager() -> MapManager:
    """Retorna instância global do MapManager."""
    global _manager
    if _manager is None:
        _manager = MapManager()
    return _manager
