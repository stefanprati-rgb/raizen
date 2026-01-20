"""
Cliente Gemini AI para Mapeamento de Contratos
Versão: 1.0

Este módulo gerencia a comunicação com a API do Gemini para:
- Analisar PDFs de amostra
- Gerar mapas de extração
- Validar e salvar mapas

Configuração:
    1. Obtenha sua API Key em: https://aistudio.google.com/app/apikey
    2. Crie arquivo .env na raiz do projeto:
       GEMINI_API_KEY=sua_chave_aqui
    3. Ou copie .env.example para .env e preencha
"""
import os
import re
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Carregar variáveis do arquivo .env automaticamente
try:
    from dotenv import load_dotenv
    # Buscar .env na raiz do projeto
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        logging.getLogger(__name__).info(f"Carregado .env de: {env_path}")
except ImportError:
    pass  # python-dotenv não instalado, usar apenas variáveis de ambiente

logger = logging.getLogger(__name__)

# Tentar importar google-generativeai
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger.warning("google-generativeai não instalado. Execute: pip install google-generativeai")


# Limites da API (carregados de settings.yaml)
try:
    from raizen_power.core.config import settings
    API_LIMITS = {
        "rpm": settings.gemini.rpm,
        "rpd": settings.gemini.rpd,
        "tpm": settings.gemini.tpm,
        "delay_seconds": settings.gemini.delay_seconds,
        "max_text_length": settings.gemini.max_text_length,
        "model": settings.gemini.model,
    }
except ImportError:
    # Fallback para valores padrão
    API_LIMITS = {
        "rpm": 5,
        "rpd": 20,
        "tpm": 250_000,
        "delay_seconds": 15,
        "max_text_length": 50000,
        "model": "gemini-2.0-flash",
    }

# Prompt para mapeamento de contratos
MAPPING_PROMPT = """
Você é um especialista em extração de dados de contratos de energia solar.

Analise o texto do contrato abaixo e gere um JSON com padrões de extração para os seguintes campos:

CAMPOS REQUERIDOS:
1. cnpj - CNPJ da empresa contratante
2. razao_social - Nome/Razão Social da empresa
3. num_instalacao - Número da Unidade Consumidora (UC)
4. num_cliente - Código do cliente
5. distribuidora - Nome da distribuidora de energia
6. data_adesao - Data de assinatura/adesão do contrato
7. duracao_meses - Período de fidelidade em meses
8. aviso_previo - Prazo de aviso prévio em dias
9. representante_nome - Nome do representante legal
10. representante_cpf - CPF do representante legal
11. participacao_percentual - Percentual de participação no consórcio

Para CADA campo encontrado, retorne:
- "ancora": texto que aparece ANTES do valor (ex: "CNPJ:", "Razão Social:")
- "regex": padrão regex para capturar o valor (use grupo de captura)
- "valor_amostra": valor que você extraiu do texto
- "pagina_estimada": número da página onde encontrou (se identificável)
- "confianca": sua confiança na extração (alto/medio/baixo)

Se um campo NÃO for encontrado no texto, retorne null para esse campo.

TEXTO DO CONTRATO:
---
{contract_text}
---

Retorne APENAS o JSON, sem explicações. Formato:
{{
    "campos": {{
        "cnpj": {{
            "ancora": "...",
            "regex": "...",
            "valor_amostra": "...",
            "pagina_estimada": 1,
            "confianca": "alto"
        }},
        ...
    }},
    "observacoes": ["..."]
}}
"""


class GeminiClient:
    """
    Cliente para API do Gemini.
    
    Gerencia autenticação, rate limiting e geração de mapas.
    """
    
    def __init__(self, api_key: str = None):
        """
        Inicializa cliente Gemini.
        
        Args:
            api_key: Chave API (ou usa GEMINI_API_KEY do ambiente)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = None
        self.requests_today = 0
        self.last_request_time = 0
        
        if not GENAI_AVAILABLE:
            raise ImportError(
                "google-generativeai não instalado. "
                "Execute: pip install google-generativeai"
            )
        
        if not self.api_key:
            raise ValueError(
                "API Key não configurada. Configure via:\n"
                "1. Variável de ambiente: GEMINI_API_KEY=sua_chave\n"
                "2. Arquivo .env: GEMINI_API_KEY=sua_chave\n"
                "3. Parâmetro api_key no construtor\n\n"
                "Obtenha sua chave em: https://aistudio.google.com/app/apikey"
            )
        
        # Configurar API
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(API_LIMITS["model"])
        
        logger.info("GeminiClient inicializado com sucesso")
    
    def _rate_limit(self):
        """Aplica rate limiting para respeitar limites da API."""
        # Verificar limite diário
        if self.requests_today >= API_LIMITS["rpd"]:
            raise Exception(
                f"Limite diário atingido ({API_LIMITS['rpd']} requisições). "
                "Aguarde reset às 00:00 UTC ou use API paga."
            )
        
        # Delay entre requisições
        elapsed = time.time() - self.last_request_time
        if elapsed < API_LIMITS["delay_seconds"]:
            wait = API_LIMITS["delay_seconds"] - elapsed
            logger.info(f"Rate limiting: aguardando {wait:.1f}s...")
            time.sleep(wait)
        
        self.last_request_time = time.time()
        self.requests_today += 1
    
    def generate_mapping(
        self, 
        contract_text: str,
        grupo: str = None
    ) -> Dict[str, Any]:
        """
        Gera um mapa de extração para um contrato.
        
        Args:
            contract_text: Texto extraído do PDF
            grupo: Nome do grupo (opcional, para logging)
            
        Returns:
            Dicionário com mapa de extração
        """
        self._rate_limit()
        
        logger.info(f"Gerando mapeamento para grupo: {grupo or 'unknown'}")
        
        # Montar prompt
        prompt = MAPPING_PROMPT.format(contract_text=contract_text[:50000])  # Limitar tamanho
        
        try:
            # Chamar API
            response = self.model.generate_content(prompt)
            
            # Extrair JSON da resposta
            response_text = response.text
            
            # Limpar markdown se presente
            if "```json" in response_text:
                response_text = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
                if response_text:
                    response_text = response_text.group(1)
            elif "```" in response_text:
                response_text = re.search(r'```\s*(.*?)\s*```', response_text, re.DOTALL)
                if response_text:
                    response_text = response_text.group(1)
            
            # Parse JSON
            mapa = json.loads(response_text)
            
            # Adicionar metadados
            mapa['grupo'] = grupo
            mapa['data_geracao'] = datetime.now().isoformat()
            mapa['modelo_ia'] = 'gemini-2.0-flash'
            
            logger.info(f"Mapeamento gerado com sucesso: {len(mapa.get('campos', {}))} campos")
            
            return mapa
            
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear resposta JSON: {e}")
            logger.error(f"Resposta raw: {response_text[:500]}...")
            raise ValueError(f"Gemini retornou JSON inválido: {e}")
            
        except Exception as e:
            logger.error(f"Erro na API Gemini: {e}")
            raise
    
    def generate_batch_mapping(
        self,
        contracts: List[Dict[str, str]],
        progress_callback: callable = None
    ) -> List[Dict[str, Any]]:
        """
        Gera mapas para múltiplos contratos.
        
        Args:
            contracts: Lista de {"grupo": str, "text": str}
            progress_callback: Função de callback (current, total)
            
        Returns:
            Lista de mapas gerados
        """
        results = []
        total = len(contracts)
        
        for i, contract in enumerate(contracts):
            grupo = contract.get('grupo', f'contrato_{i}')
            text = contract.get('text', '')
            
            try:
                mapa = self.generate_mapping(text, grupo)
                results.append({
                    'grupo': grupo,
                    'status': 'success',
                    'mapa': mapa
                })
            except Exception as e:
                results.append({
                    'grupo': grupo,
                    'status': 'error',
                    'erro': str(e)
                })
            
            if progress_callback:
                progress_callback(i + 1, total)
        
        return results
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de uso da API."""
        return {
            "requests_today": self.requests_today,
            "remaining_today": API_LIMITS["rpd"] - self.requests_today,
            "rpm_limit": API_LIMITS["rpm"],
            "rpd_limit": API_LIMITS["rpd"],
            "delay_seconds": API_LIMITS["delay_seconds"]
        }


def check_api_key() -> bool:
    """Verifica se a API key está configurada."""
    return bool(os.getenv("GEMINI_API_KEY"))


def setup_api_key(api_key: str):
    """Configura a API key no ambiente."""
    os.environ["GEMINI_API_KEY"] = api_key
    logger.info("API Key configurada no ambiente")


# Exemplo de uso
if __name__ == "__main__":
    print("=" * 60)
    print("VERIFICAÇÃO DE CONFIGURAÇÃO GEMINI")
    print("=" * 60)
    
    if not GENAI_AVAILABLE:
        print("\n❌ Biblioteca não instalada!")
        print("   Execute: pip install google-generativeai")
    elif not check_api_key():
        print("\n⚠️  API Key não configurada!")
        print("   1. Obtenha sua chave em: https://aistudio.google.com/app/apikey")
        print("   2. Configure via:")
        print("      - Variável de ambiente: set GEMINI_API_KEY=sua_chave")
        print("      - Arquivo .env: GEMINI_API_KEY=sua_chave")
    else:
        print("\n✅ Configuração OK!")
        print(f"   API Key: {os.getenv('GEMINI_API_KEY')[:10]}...")
        
        try:
            client = GeminiClient()
            print(f"   Modelo: gemini-2.0-flash")
            print(f"   Limite diário: {API_LIMITS['rpd']} requisições")
        except Exception as e:
            print(f"\n❌ Erro ao inicializar: {e}")
