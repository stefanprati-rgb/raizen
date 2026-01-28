import pandas as pd
import requests
import time
import re
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configura saída UTF-8 para Windows (suporte a emojis)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Tenta importar tqdm para barra de progresso
try:
    from tqdm import tqdm
except ImportError:
    print("⚠️ Dica: Instale 'tqdm' para visualização (pip install tqdm)")
    def tqdm(iterable, **kwargs): return iterable

# --- CONFIGURAÇÃO ---
# [MODIFICAÇÃO] Aponta para o arquivo Excel original
ARQUIVO_ERROS = "ERROS cadastros RAIZEN.xlsx" 
ARQUIVO_SAIDA = "ERROS_COM_ENDERECO_FINAL_V4.xlsx"
ARQUIVO_LOG = "execucao_api.log"
MAX_WORKERS_BRASILAPI = 8
TIMEOUT_REQUEST = 10
MAX_RETRIES = 3

# Configuração de Logs
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(ARQUIVO_LOG, mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logging.getLogger().handlers[1].setLevel(logging.WARNING)

# Controle Global de Rate Limit
ultimo_request_receitaws = 0

def limpar_texto(texto):
    """Padroniza texto para maiúsculo e sem espaços extras."""
    if not texto or pd.isna(texto): return None
    return str(texto).strip().upper()

def limpar_cep(cep):
    """Remove traços e pontos do CEP."""
    if not cep: return None
    return str(cep).replace('-', '').replace('.', '').strip()

def validar_cnpj(cnpj):
    """Validação matemática de CNPJ (Módulo 11)."""
    cnpj = re.sub(r'\D', '', str(cnpj))
    if len(cnpj) != 14 or len(set(cnpj)) == 1: return False
    
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma1 = sum(int(a) * b for a, b in zip(cnpj[:12], pesos1))
    digito1 = 0 if soma1 % 11 < 2 else 11 - (soma1 % 11)
    
    if int(cnpj[12]) != digito1: return False

    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma2 = sum(int(a) * b for a, b in zip(cnpj[:13], pesos2))
    digito2 = 0 if soma2 % 11 < 2 else 11 - (soma2 % 11)
    
    return int(cnpj[13]) == digito2

def consultar_brasilapi(cnpj):
    """Consulta BrasilAPI com Retry Logic."""
    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
    
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, timeout=TIMEOUT_REQUEST)
            
            if resp.status_code == 200:
                data = resp.json()
                if 'cep' not in data: 
                    logging.warning(f"[BrasilAPI] Resposta incompleta para {cnpj}")
                    return None
                    
                return {
                    'cnpj': cnpj,
                    'API_SOURCE': 'BrasilAPI',
                    'FOUND_LOGRADOURO': limpar_texto(f"{data.get('logradouro', '')}, {data.get('numero', '')} {data.get('complemento', '')}"),
                    'FOUND_BAIRRO': limpar_texto(data.get('bairro')),
                    'FOUND_CIDADE': limpar_texto(data.get('municipio')),
                    'FOUND_UF': limpar_texto(data.get('uf')),
                    'FOUND_CEP': limpar_cep(data.get('cep')),
                    'STATUS_API': 'SUCESSO'
                }
            elif resp.status_code == 404:
                return None 
            elif resp.status_code == 429:
                wait = (attempt + 1) * 2
                logging.warning(f"[BrasilAPI] Rate Limit 429 para {cnpj}. Aguardando {wait}s...")
                time.sleep(wait)
            else:
                logging.debug(f"[BrasilAPI] Erro {resp.status_code} para {cnpj}")
                
        except requests.exceptions.RequestException as e:
            logging.debug(f"[BrasilAPI] Erro de conexão {cnpj}: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(1)

    return None

def consultar_receitaws(cnpj):
    """Fallback ReceitaWS com Smart Rate Limiting."""
    global ultimo_request_receitaws
    
    agora = time.time()
    tempo_decorrido = agora - ultimo_request_receitaws
    if tempo_decorrido < 20:
        time.sleep(20 - tempo_decorrido)
    
    url = f"https://www.receitaws.com.br/v1/cnpj/{cnpj}"
    try:
        resp = requests.get(url, timeout=TIMEOUT_REQUEST)
        ultimo_request_receitaws = time.time()
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get('status') == 'ERROR': return None
                
            return {
                'cnpj': cnpj,
                'API_SOURCE': 'ReceitaWS',
                'FOUND_LOGRADOURO': limpar_texto(f"{data.get('logradouro', '')}, {data.get('numero', '')} {data.get('complemento', '')}"),
                'FOUND_BAIRRO': limpar_texto(data.get('bairro')),
                'FOUND_CIDADE': limpar_texto(data.get('municipio')),
                'FOUND_UF': limpar_texto(data.get('uf')),
                'FOUND_CEP': limpar_cep(data.get('cep')),
                'STATUS_API': 'SUCESSO_FALLBACK'
            }
    except Exception as e:
        logging.error(f"[ReceitaWS] Erro crítico {cnpj}: {e}")
    
    return None

def main():
    print(f"📂 Lendo arquivo Excel: {ARQUIVO_ERROS}...")
    
    # [MODIFICAÇÃO] Leitura de XLSX em vez de CSV
    try:
        df = pd.read_excel(ARQUIVO_ERROS)
    except FileNotFoundError:
        print(f"❌ Erro: Arquivo '{ARQUIVO_ERROS}' não encontrado.")
        print("Verifique se o nome está correto e se você está na pasta certa.")
        return
    except ImportError:
        print("❌ Erro: Biblioteca 'openpyxl' não encontrada.")
        print("Execute: pip install openpyxl")
        return

    # Inicializa colunas se não existirem
    cols = ['FOUND_LOGRADOURO', 'FOUND_BAIRRO', 'FOUND_CIDADE', 'FOUND_UF', 'FOUND_CEP', 'API_SOURCE', 'STATUS_API']
    for col in cols:
        if col not in df.columns: df[col] = None

    # Lógica de Seleção
    mask_processar = (
        (df['ERRO'].str.contains('CEP', na=False) | df['ERRO'].str.contains('Cidade', na=False)) &
        (df['FOUND_CEP'].isnull())
    )
    
    df['CNPJ_LIMPO_TEMP'] = df['CNPJ/CPF'].apply(lambda x: re.sub(r'\D', '', str(x)))
    alvos = df[mask_processar]['CNPJ_LIMPO_TEMP'].unique()
    alvos_validos = [cnpj for cnpj in alvos if validar_cnpj(cnpj)]
    
    print(f"🎯 Total de linhas com erro: {mask_processar.sum()}")
    print(f"🔍 CNPJs únicos válidos para consulta: {len(alvos_validos)}")
    
    results_map = {}

    # 1. BRASIL API
    print(f"\n🚀 [1/2] Consultando BrasilAPI ({MAX_WORKERS_BRASILAPI} threads)...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS_BRASILAPI) as executor:
        future_to_cnpj = {executor.submit(consultar_brasilapi, cnpj): cnpj for cnpj in alvos_validos}
        for future in tqdm(as_completed(future_to_cnpj), total=len(alvos_validos)):
            cnpj = future_to_cnpj[future]
            try:
                res = future.result()
                if res: results_map[cnpj] = res
            except Exception as e:
                logging.error(f"Erro Thread {cnpj}: {e}")

    # 2. RECEITA WS
    cnpjs_faltantes = [c for c in alvos_validos if c not in results_map]
    if cnpjs_faltantes:
        print(f"\n🐢 [2/2] Consultando Fallback ReceitaWS ({len(cnpjs_faltantes)} itens)...")
        for cnpj in tqdm(cnpjs_faltantes):
            res = consultar_receitaws(cnpj)
            if res:
                results_map[cnpj] = res
            else:
                results_map[cnpj] = {'cnpj': cnpj, 'STATUS_API': 'NAO_ENCONTRADO'}

    # 3. ATUALIZAÇÃO BATCH
    print("\n💾 Processando resultados e salvando...")
    if results_map:
        df_results = pd.DataFrame(results_map.values())
        df_results.set_index('cnpj', inplace=True)
        
        cols_interesse = ['FOUND_LOGRADOURO', 'FOUND_BAIRRO', 'FOUND_CIDADE', 'FOUND_UF', 'FOUND_CEP', 'API_SOURCE', 'STATUS_API']
        for col in cols_interesse:
            if col not in df_results.columns: df_results[col] = None
            
        rows_affected = df['CNPJ_LIMPO_TEMP'].isin(df_results.index) & mask_processar
        
        for col in cols_interesse:
            novos_valores = df.loc[rows_affected, 'CNPJ_LIMPO_TEMP'].map(df_results[col])
            df.loc[rows_affected, col] = novos_valores

    df.drop(columns=['CNPJ_LIMPO_TEMP'], inplace=True)
    df.to_excel(ARQUIVO_SAIDA, index=False)
    print(f"✅ Sucesso! Log detalhado em: {ARQUIVO_LOG}")
    print(f"📄 Arquivo final: {ARQUIVO_SAIDA}")

if __name__ == "__main__":
    main()