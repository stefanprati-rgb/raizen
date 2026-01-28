<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Melhores Práticas Python para Validação de CEP e Endereço

## Visão Geral

A validação de CEP e endereço em Python é fundamental para garantir integridade dos dados, especialmente em aplicações de e-commerce, logística e gestão de cadastros. O Brasil oferece recursos únicos para essa tarefa através de APIs públicas de qualidade e bibliotecas especializadas que simplificam o processo.

## 1. Validação Básica de CEP

### Formatação e Limpeza

O primeiro passo é normalizar o input do usuário, removendo caracteres especiais. CEPs brasileiros podem ser fornecidos em diferentes formatos (com ou sem hífen):[^1_1]

```python
def limpar_cep(cep: str) -> str:
    """Remove caracteres especiais de um CEP"""
    return cep.replace("-", "").replace(".", "").replace(" ", "").strip()

def validar_formato_cep(cep: str) -> bool:
    """Valida se o CEP possui 8 dígitos"""
    cep_limpo = limpar_cep(cep)
    return len(cep_limpo) == 8 and cep_limpo.isdigit()

# Uso
cep_usuario = "20.090-002"
if validar_formato_cep(cep_usuario):
    cep_limpo = limpar_cep(cep_usuario)
    print(f"CEP válido: {cep_limpo}")
```


### Validação com Regex

Para validações mais robustas, use expressões regulares que aceitam formatos com e sem formatação:[^1_2]

```python
import re

def validar_cep_regex(cep: str) -> bool:
    """Valida CEP usando regex - aceita com ou sem hífen"""
    padroes = [
        r'^(\d{5})-(\d{3})$',  # Formato: 12345-678
        r'^\d{8}$'              # Formato: 12345678
    ]
    
    cep_limpo = cep.replace("-", "").replace(".", "").replace(" ", "")
    return any(re.match(padrao, cep_limpo) for padrao in padroes)
```


## 2. Consulta de Endereços com APIs

### Usando a Biblioteca brazilcep

A forma mais moderna e recomendada é usar a biblioteca `brazilcep` (renomeação da antiga `pycep-correios`):[^1_3]

```python
import brazilcep
from brazilcep.exceptions import InvalidCEP, CEPNotFound

def consultar_endereco(cep: str) -> dict:
    """Consulta endereço a partir de CEP com tratamento robusto"""
    try:
        # Limpar e validar input
        cep_limpo = cep.replace("-", "").replace(".", "").strip()
        
        if not validar_cep_regex(cep_limpo):
            raise ValueError("Formato de CEP inválido")
        
        # Consultar endereço
        endereco = brazilcep.get_address_from_cep(cep_limpo)
        return {
            "sucesso": True,
            "dados": endereco,
            "erro": None
        }
    
    except InvalidCEP as e:
        return {
            "sucesso": False,
            "dados": None,
            "erro": f"CEP inválido: {str(e)}"
        }
    
    except CEPNotFound as e:
        return {
            "sucesso": False,
            "dados": None,
            "erro": f"CEP não encontrado: {str(e)}"
        }
    
    except Exception as e:
        return {
            "sucesso": False,
            "dados": None,
            "erro": f"Erro ao consultar CEP: {str(e)}"
        }

# Uso
resultado = consultar_endereco("37503-130")
if resultado["sucesso"]:
    print(f"Cidade: {resultado['dados']['cidade']}")
    print(f"Logradouro: {resultado['dados']['logradouro']}")
```


### Usando ViaCEP Diretamente

Para maior controle ou quando preferir não usar dependências externas:[^1_1]

```python
import requests
import json

def consultar_viacep(cep: str, timeout: int = 5) -> dict:
    """Consulta ViaCEP com tratamento robusto de erros"""
    try:
        cep_limpo = cep.replace("-", "").replace(".", "").strip()
        
        if not len(cep_limpo) == 8 or not cep_limpo.isdigit():
            raise ValueError("CEP deve conter exatamente 8 dígitos")
        
        url = f'https://viacep.com.br/ws/{cep_limpo}/json/'
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        
        dados = response.json()
        
        # ViaCEP retorna {"erro": true} para CEPs não encontrados
        if dados.get('erro'):
            return {"sucesso": False, "erro": "CEP não encontrado"}
        
        return {
            "sucesso": True,
            "logradouro": dados.get('logradouro'),
            "bairro": dados.get('bairro'),
            "localidade": dados.get('localidade'),
            "uf": dados.get('uf'),
            "complemento": dados.get('complemento')
        }
    
    except requests.exceptions.Timeout:
        return {"sucesso": False, "erro": "Timeout na requisição"}
    except requests.exceptions.ConnectionError:
        return {"sucesso": False, "erro": "Erro de conexão"}
    except requests.exceptions.HTTPError as e:
        return {"sucesso": False, "erro": f"Erro HTTP: {e.response.status_code}"}
    except ValueError as e:
        return {"sucesso": False, "erro": str(e)}
    except Exception as e:
        return {"sucesso": False, "erro": f"Erro inesperado: {str(e)}"}
```


## 3. Validação Completa de Endereços

### Modelo com Pydantic

Para aplicações mais robustas, use Pydantic para validação de múltiplos campos:[^1_4]

```python
from pydantic import BaseModel, validator, ValidationError
import re

class Endereco(BaseModel):
    cep: str
    logradouro: str
    numero: str
    bairro: str
    cidade: str
    uf: str
    complemento: str = ""
    
    @validator('cep')
    def validar_cep(cls, v):
        cep_limpo = v.replace("-", "").replace(".", "").strip()
        if not re.match(r'^\d{8}$', cep_limpo):
            raise ValueError('CEP deve conter 8 dígitos')
        return cep_limpo
    
    @validator('uf')
    def validar_uf(cls, v):
        ufs_validos = ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 
                      'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI',
                      'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO']
        v_upper = v.upper()
        if v_upper not in ufs_validos:
            raise ValueError(f'UF inválida: {v}')
        return v_upper
    
    @validator('numero')
    def validar_numero(cls, v):
        if not v or v.strip() == "":
            raise ValueError('Número não pode ser vazio')
        return v.strip()
    
    class Config:
        # Permite remoção automática de espaços em branco
        anystr_strip_whitespace = True

# Uso
try:
    endereco = Endereco(
        cep="37503-130",
        logradouro="Rua Exemplo",
        numero="123",
        bairro="Centro",
        cidade="Itajubá",
        uf="mg",
        complemento="Apto 45"
    )
    print(f"Endereço válido: {endereco.dict()}")
except ValidationError as e:
    print(f"Erro de validação: {e}")
```


## 4. Tratamento de Erros e Exceções

### Estratégia Abrangente

Para sistemas em produção, implemente tratamento específico de exceções:[^1_5]

```python
import logging
from typing import Optional, Dict
from brazilcep.exceptions import (
    InvalidCEP, CEPNotFound, ConnectionError, 
    Timeout, HTTPError, BaseException as BrazilCEPException
)

# Configurar logger
logger = logging.getLogger(__name__)

def consultar_endereco_robusto(cep: str, max_tentativas: int = 3) -> Optional[Dict]:
    """Consulta com retry automático e logging detalhado"""
    
    for tentativa in range(max_tentativas):
        try:
            logger.debug(f"Tentativa {tentativa + 1} de {max_tentativas} para CEP: {cep}")
            
            endereco = brazilcep.get_address_from_cep(cep)
            logger.info(f"CEP {cep} consultado com sucesso")
            return endereco
        
        except InvalidCEP as e:
            logger.error(f"CEP inválido: {cep} - {str(e)}")
            return None  # Falha imediata para input inválido
        
        except CEPNotFound as e:
            logger.warning(f"CEP não encontrado na base: {cep}")
            return None  # CEP não existe, não adianta retry
        
        except Timeout as e:
            logger.warning(f"Timeout na tentativa {tentativa + 1}: {str(e)}")
            if tentativa < max_tentativas - 1:
                import time
                tempo_espera = 2 ** tentativa  # Backoff exponencial
                logger.debug(f"Aguardando {tempo_espera}s antes de retry")
                time.sleep(tempo_espera)
        
        except ConnectionError as e:
            logger.error(f"Erro de conexão na tentativa {tentativa + 1}: {str(e)}")
            if tentativa < max_tentativas - 1:
                import time
                time.sleep(2 ** tentativa)
        
        except HTTPError as e:
            logger.error(f"Erro HTTP: {str(e)}")
            return None
        
        except BrazilCEPException as e:
            logger.error(f"Erro na API brazilcep: {str(e)}")
            return None
    
    logger.error(f"Falha ao consultar CEP {cep} após {max_tentativas} tentativas")
    return None
```


## 5. Validação em Lote

### Processamento com Pandas

Para validar múltiplos CEPs simultaneamente:[^1_6]

```python
import pandas as pd
import logging
from typing import List, Dict

def validar_ceps_em_lote(df: pd.DataFrame, coluna_cep: str = 'cep') -> pd.DataFrame:
    """Valida e enriquece dataframe com informações de endereço"""
    
    logger = logging.getLogger(__name__)
    
    def consultar_cep_seguro(cep):
        """Wrapper para aplicar em DataFrame"""
        try:
            resultado = brazilcep.get_address_from_cep(str(cep))
            return pd.Series({
                'logradouro': resultado.get('logradouro'),
                'bairro': resultado.get('bairro'),
                'cidade': resultado.get('localidade'),
                'uf': resultado.get('uf'),
                'cep_valido': True,
                'erro': None
            })
        except Exception as e:
            logger.warning(f"Erro ao consultar CEP {cep}: {str(e)}")
            return pd.Series({
                'logradouro': None,
                'bairro': None,
                'cidade': None,
                'uf': None,
                'cep_valido': False,
                'erro': str(e)
            })
    
    # Aplicar validação
    resultado = df[coluna_cep].apply(consultar_cep_seguro)
    
    # Combinar com dataframe original
    df_enriquecido = pd.concat([df, resultado], axis=1)
    
    # Estatísticas
    total = len(df_enriquecido)
    validos = df_enriquecido['cep_valido'].sum()
    logger.info(f"Validação concluída: {validos}/{total} CEPs válidos ({100*validos/total:.1f}%)")
    
    return df_enriquecido

# Uso
df = pd.read_csv('clientes.csv')
df_validado = validar_ceps_em_lote(df, 'cep_cliente')
df_validado.to_csv('clientes_validados.csv', index=False)
```


## 6. Boas Práticas de Logging

### Configuração Estruturada

Implemente logging profissional para rastreabilidade:[^1_7][^1_8]

```python
import logging
from logging.handlers import RotatingFileHandler
import json

def configurar_logging_producao():
    """Configura logging estruturado para produção"""
    
    # Logger principal
    logger = logging.getLogger('validacao_cep')
    logger.setLevel(logging.DEBUG)
    
    # Handler para arquivo (com rotação)
    handler_arquivo = RotatingFileHandler(
        'validacao_cep.log',
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    handler_arquivo.setLevel(logging.INFO)
    
    # Handler para console
    handler_console = logging.StreamHandler()
    handler_console.setLevel(logging.WARNING)
    
    # Formatter estruturado
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    handler_arquivo.setFormatter(formatter)
    handler_console.setFormatter(formatter)
    
    logger.addHandler(handler_arquivo)
    logger.addHandler(handler_console)
    
    return logger

# Uso
logger = configurar_logging_producao()

def validar_e_registrar(cep: str) -> bool:
    """Exemplo de validação com logging completo"""
    logger.info(f"Iniciando validação do CEP: {cep}")
    
    try:
        if not validar_cep_regex(cep):
            logger.warning(f"CEP com formato inválido: {cep}")
            return False
        
        resultado = brazilcep.get_address_from_cep(cep.replace("-", ""))
        logger.info(f"CEP {cep} validado com sucesso - Cidade: {resultado['localidade']}")
        return True
    
    except Exception as e:
        logger.error(f"Erro ao validar CEP {cep}: {str(e)}", exc_info=True)
        return False
```


## 7. Testes Automatizados

### Cobertura de Casos de Teste

Use pytest ou unittest para validar a lógica:[^1_9]

```python
import pytest
from unittest.mock import patch, MagicMock

class TestValidacaoCEP:
    """Suite de testes para validação de CEP"""
    
    def test_validar_formato_valido(self):
        """Testa validação com formatos válidos"""
        assert validar_cep_regex("37503130") == True
        assert validar_cep_regex("37503-130") == True
    
    def test_validar_formato_invalido(self):
        """Testa rejeição de formatos inválidos"""
        assert validar_cep_regex("3750313") == False  # Menos de 8 dígitos
        assert validar_cep_regex("375031300") == False  # Mais de 8 dígitos
        assert validar_cep_regex("3750A130") == False  # Contém letra
    
    def test_limpeza_cep(self):
        """Testa remoção de caracteres especiais"""
        assert limpar_cep("37.503-130") == "37503130"
        assert limpar_cep("37 503 130") == "37503130"
    
    @patch('brazilcep.get_address_from_cep')
    def test_consulta_endereco_sucesso(self, mock_api):
        """Testa consulta bem-sucedida com mock da API"""
        mock_api.return_value = {
            'cep': '37503130',
            'logradouro': 'Rua Teste',
            'localidade': 'Itajubá',
            'uf': 'MG'
        }
        
        resultado = consultar_endereco("37503-130")
        assert resultado['sucesso'] == True
        mock_api.assert_called_once_with('37503130')
    
    @patch('brazilcep.get_address_from_cep')
    def test_consulta_endereco_nao_encontrado(self, mock_api):
        """Testa tratamento de CEP não encontrado"""
        from brazilcep.exceptions import CEPNotFound
        mock_api.side_effect = CEPNotFound("CEP não encontrado")
        
        resultado = consultar_endereco("00000000")
        assert resultado['sucesso'] == False
```


## 8. Tratamento de Timeout e Retry

### Estratégia de Retry com Backoff Exponencial

Para sistemas de alta confiabilidade:[^1_10][^1_11]

```python
import time
import random
from typing import Callable, TypeVar, Any

T = TypeVar('T')

def retry_com_backoff(
    funcao: Callable[..., T],
    max_tentativas: int = 3,
    backoff_inicial: float = 1.0,
    backoff_maximo: float = 32.0,
    fator_jitter: float = 0.1
) -> T:
    """
    Executa função com retry, backoff exponencial e jitter
    
    Args:
        funcao: Função a executar
        max_tentativas: Número máximo de tentativas
        backoff_inicial: Tempo inicial de espera em segundos
        backoff_maximo: Tempo máximo de espera
        fator_jitter: Fator de aleatoriedade (0-1)
    """
    
    backoff = backoff_inicial
    
    for tentativa in range(1, max_tentativas + 1):
        try:
            logger.debug(f"Tentativa {tentativa}/{max_tentativas}")
            return funcao()
        
        except Exception as e:
            if tentativa == max_tentativas:
                logger.error(f"Falha final após {max_tentativas} tentativas: {str(e)}")
                raise
            
            # Calcular espera com jitter
            jitter = random.uniform(0, fator_jitter * backoff)
            tempo_espera = min(backoff + jitter, backoff_maximo)
            
            logger.warning(
                f"Tentativa {tentativa} falhou. "
                f"Aguardando {tempo_espera:.2f}s antes de retry"
            )
            
            time.sleep(tempo_espera)
            backoff = min(backoff * 2, backoff_maximo)
    
    raise RuntimeError(f"Falha após {max_tentativas} tentativas")

# Uso
def consultar_com_retry(cep: str) -> dict:
    return retry_com_backoff(
        lambda: brazilcep.get_address_from_cep(cep),
        max_tentativas=3
    )
```


## 9. Caching de Resultados

### Implementação Simples com Decorator

Evite consultas repetidas à API:[^1_12]

```python
import functools
from datetime import datetime, timedelta
import json

class CacheComTTL:
    """Cache com tempo de expiração (TTL)"""
    
    def __init__(self, ttl_segundos: int = 86400):  # 24 horas
        self.ttl_segundos = ttl_segundos
        self.cache = {}
    
    def obter(self, chave: str) -> any:
        """Obtém valor do cache se válido"""
        if chave not in self.cache:
            return None
        
        valor, timestamp = self.cache[chave]
        
        if datetime.now() - timestamp > timedelta(seconds=self.ttl_segundos):
            del self.cache[chave]
            return None
        
        logger.debug(f"Cache hit para {chave}")
        return valor
    
    def set(self, chave: str, valor: any):
        """Armazena valor no cache"""
        self.cache[chave] = (valor, datetime.now())
        logger.debug(f"Valor cacheado para {chave}")

# Instância global
cache_cep = CacheComTTL(ttl_segundos=86400)

def consultar_endereco_com_cache(cep: str) -> dict:
    """Consulta com cache automático"""
    
    cep_limpo = cep.replace("-", "").replace(".", "").strip()
    
    # Tentar obter do cache
    resultado_cache = cache_cep.obter(cep_limpo)
    if resultado_cache:
        return resultado_cache
    
    # Consultar API
    try:
        endereco = brazilcep.get_address_from_cep(cep_limpo)
        
        resultado = {
            "sucesso": True,
            "dados": endereco,
            "origem": "API"
        }
        
        # Armazenar no cache
        cache_cep.set(cep_limpo, resultado)
        return resultado
    
    except Exception as e:
        logger.error(f"Erro ao consultar CEP {cep}: {str(e)}")
        return {
            "sucesso": False,
            "erro": str(e),
            "origem": "Erro"
        }
```


## 10. Checklist de Implementação

Ao integrar validação de CEP e endereço, considere:


| Aspecto | Descrição | Prioridade |
| :-- | :-- | :-- |
| **Validação de Formato** | Verificar 8 dígitos numéricos | Alta |
| **Consulta de API** | Integrar com brazilcep ou ViaCEP | Alta |
| **Tratamento de Erros** | Exceptions específicas e logging | Alta |
| **Timeout** | Definir timeouts adequados (5-10s) | Alta |
| **Retry Logic** | Backoff exponencial com jitter | Média |
| **Caching** | TTL de 24 horas mínimo | Média |
| **Logging Estruturado** | Rastreabilidade completa | Média |
| **Testes Automatizados** | Cobertura mínima 80% | Média |
| **Sanitização de Input** | Remover caracteres especiais | Alta |
| **Validação de UF** | Verificar estados válidos | Média |

## Referências

Consulta de CEPs com Python - Hashtagtreinamentos[^1_1]
Script Python para buscar endereço por CEP - DIO[^1_13]
Consultando CEP via Web Service com Python - Autociência[^1_2]
Validação de CEP com Regex - Alura[^1_14]
Bibliotecas brazilcep/pycep-correios - PyPI[^1_15][^1_16][^1_17][^1_3]
Tratamento de Erro e Validação de Input - DIO[^1_18]
brazilcep - PyPI[^1_3]
Localizando endereço com Python - YouTube[^1_6]
Validação Pydantic - StackOverflow[^1_4]
Tratamento de erro brazilcep - GitHub[^1_5]
Retry com backoff em Python - Oxylabs, PeterBe[^1_11][^1_10]
Logging best practices - Datacamp, Coralogix[^1_8][^1_7]
Unittest framework - Documentação Python[^1_9]
<span style="display:none">[^1_19][^1_20][^1_21][^1_22][^1_23][^1_24][^1_25][^1_26][^1_27][^1_28][^1_29][^1_30][^1_31][^1_32][^1_33][^1_34][^1_35][^1_36][^1_37][^1_38][^1_39][^1_40][^1_41][^1_42][^1_43][^1_44][^1_45][^1_46][^1_47][^1_48][^1_49][^1_50][^1_51]</span>

<div align="center">⁂</div>

[^1_1]: https://www.hashtagtreinamentos.com/busca-enderecos-com-python

[^1_2]: https://autociencia.blogspot.com/2018/07/consultando-cep-via-web-service-com-python.html

[^1_3]: https://pypi.org/project/brazilcep/

[^1_4]: https://stackoverflow.com/questions/61392633/how-to-validate-more-than-one-field-of-a-pydantic-model

[^1_5]: https://github.com/mstuttgart/pycep-correios/issues/73

[^1_6]: https://www.youtube.com/watch?v=RpHu-YEn0-M

[^1_7]: https://www.datacamp.com/pt/tutorial/loguru-python-logging-tutorial

[^1_8]: https://coralogix.com/blog/python-logging-best-practices-tips/

[^1_9]: https://docs.python.org/pt-br/3/library/unittest.html

[^1_10]: https://oxylabs.io/blog/python-requests-timeout

[^1_11]: https://www.peterbe.com/plog/best-practice-with-retries-with-requests

[^1_12]: https://docs.python.org/pt-br/3.12/c-api/exceptions.html

[^1_13]: https://www.dio.me/articles/script-python-para-buscar-endereco-a-partir-do-cep

[^1_14]: https://cursos.alura.com.br/forum/topico-validacao-do-cep-216198

[^1_15]: https://pypi.org/project/pycep-correios/5.0.0rc0/

[^1_16]: https://pypi.org/project/pycep-correios/4.0.3/

[^1_17]: https://pypi.org/project/pycep-correios/

[^1_18]: https://www.dio.me/articles/tratando-erro-e-validacao-de-input-em-python-com-try-e-except

[^1_19]: https://www.youtube.com/watch?v=lecYCNLgh5U

[^1_20]: https://www.youtube.com/watch?v=WnwSk9WE4-4

[^1_21]: https://www.alura.com.br/conteudo/python-validacao-dados

[^1_22]: https://www.abstractapi.com/guides/api-functions/ip-address-validation-in-python

[^1_23]: https://imasters.com.br/back-end/python-consulta-de-cep-com-pycepcorreios

[^1_24]: https://www.findcep.com/exemplos/api-cep-python

[^1_25]: https://stackoverflow.com/questions/43838792/address-validation-python

[^1_26]: https://codiacademy.com.br/expressoes-regulares-em-python-guia-pratico-para-iniciantes/

[^1_27]: https://github.com/renankalfa/consulta-cep-api-python

[^1_28]: https://github.com/brazilian-utils/python

[^1_29]: https://www.geopostcodes.com/blog/how-to-use-python-to-validate-zip-codes-a-step-by-step-guide/

[^1_30]: https://www.auditwithpython.com/data-analytics-blog/address-verification-using-python-smarty-address-verification

[^1_31]: https://www.youtube.com/watch?v=SKlF2PmIkrU

[^1_32]: https://www.placekey.io/blog/address-matching-python

[^1_33]: https://www.youtube.com/watch?v=m72WIejruxI

[^1_34]: https://translate.google.com/translate?u=https%3A%2F%2Fwww.educative.io%2Fanswers%2Fhow-to-sanitize-user-input-in-python\&hl=pt\&sl=en\&tl=pt\&client=srp

[^1_35]: https://www.geopostcodes.com/blog/address-cleansing/

[^1_36]: https://pt.linkedin.com/posts/lassirati_brazilcep-python-automa%C3%A7%C3%A3o-activity-7298733229707059200-uv4u

[^1_37]: https://cursos.alura.com.br/forum/topico-tratar-erro-na-entrada-de-usuario-158890

[^1_38]: https://www.dataquest.io/guide/data-cleaning-in-python-tutorial/

[^1_39]: https://www.questionpro.com/pt-br/help/regex-validation.html

[^1_40]: https://docs.pydantic.dev/1.10/usage/types/

[^1_41]: https://www.alura.com.br/artigos/php-validacao-dados-nacionais-br

[^1_42]: https://pt.stackoverflow.com/questions/351775/como-tratar-uma-base-de-endereços

[^1_43]: https://github.com/pydantic/pydantic/discussions/7367

[^1_44]: https://stackoverflow.com/questions/66694060/how-to-retry-an-json-api-request-after-a-timeout-using-python

[^1_45]: https://www.datacamp.com/pt/tutorial/python-async-programming

[^1_46]: https://docs.python.org/pt-br/dev/c-api/exceptions.html

[^1_47]: https://docs.python.org/pt-br/3.11/library/asyncio-eventloop.html

[^1_48]: https://translate.google.com/translate?u=https%3A%2F%2Fcoralogix.com%2Fblog%2Fpython-logging-best-practices-tips%2F\&hl=pt\&sl=en\&tl=pt\&client=srp

[^1_49]: https://docs.python.org/pt-br/3.7/howto/logging.html

[^1_50]: https://translate.google.com/translate?u=https%3A%2F%2Flast9.io%2Fblog%2Fpython-logging-best-practices%2F\&hl=pt\&sl=en\&tl=pt\&client=srp

[^1_51]: https://translate.google.com/translate?u=https%3A%2F%2Fdocs.pytest.org%2Fen%2Fstable%2Fhow-to%2Funittest.html\&hl=pt\&sl=en\&tl=pt\&client=srp

