"""
Script de Enriquecimento de Erros (Pipeline de Recuperação) - Versão Enterprise.

Objetivo: Preencher dados faltantes (CNPJ, Endereço) utilizando Base de Clientes e BrasilAPI.
Melhorias v3:
- Resiliência contra arquivos corrompidos (JSON).
- Função de Cleanup para limpeza de ambiente.
- Otimização de Merge com Indexação.
- Logs estatísticos detalhados.
"""
import pandas as pd
import requests
import time
import re
import logging
import sys
import os
import json
import numpy as np
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Configuração de Logs ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("enrichment_full.log")
    ]
)
logger = logging.getLogger(__name__)

# --- Configurações Globais ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "src"))

try:
    from raizen_power.utils.text_sanitizer import TextSanitizer, NoiseFilter
except ImportError:
    logger.error("Falha ao importar TextSanitizer do diretório src.")
    sys.exit(1)

# Constantes de Arquivos
FILE_ERROS = BASE_DIR / "docs/ERROS cadastros RAIZEN 1.xlsx"
FILE_BASE_XLSX = BASE_DIR / "docs/BASE DE CLIENTES - Raizen.xlsx"
FILE_BASE_CSV = BASE_DIR / "docs/BASE DE CLIENTES - Raizen.xlsx - base_clientes.csv"
OUTPUT_FILE = BASE_DIR / "output/enrichment/ERROS_CADASTRO_RAIZEN_1.xlsx"
PARTIAL_FILE = OUTPUT_FILE.with_name("enrich_partial.json")

# Constantes de Execução
BATCH_SAVE_SIZE = 50
MAX_RETRIES_API = 3
API_TIMEOUT = 10

# --- Funções Auxiliares ---

def cleanup_temp_files():
    """Remove arquivos temporários gerados durante o processo."""
    try:
        if PARTIAL_FILE.exists():
            PARTIAL_FILE.unlink()
            logger.info("Limpeza: Arquivo de progresso parcial removido.")
    except Exception as e:
        logger.warning(f"Limpeza: Falha ao remover arquivos temporários: {e}")

def apply_manual_patches(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica patches manuais para endereços conhecidos sem CEP/Cidade."""
    patches = [
        {"key": "OURIQUE", "cidade": "RIO DE JANEIRO", "cep": "21011130", "uf": "RJ"},
        {"key": "JOAO LIERA", "cidade": "RIO DE JANEIRO", "cep": "22430210", "uf": "RJ"},
        {"key": "JOAO LIRA", "cidade": "RIO DE JANEIRO", "cep": "22430210", "uf": "RJ"},
        {"key": "RITA LUDOLF", "cidade": "RIO DE JANEIRO", "cep": "22440060", "uf": "RJ"},
        {"key": "WASHINGTON LUIZ", "cidade": "DUQUE DE CAXIAS", "cep": "25085008", "uf": "RJ"},
        {"key": "AVPRES KENNEDY", "cidade": "DUQUE DE CAXIAS", "cep": "25010001", "uf": "RJ"},
        {"key": "AFONSO MORENO", "cidade": "FRANCISCO MORATO", "cep": "07906000", "uf": "SP"},
        {"key": "CHICO DE PAULA", "cidade": "MOGI GUACU", "cep": "13840001", "uf": "SP"}
    ]
    
    for p in patches:
        # Filtra registros com a chave e sem CEP ou Cidade
        mask = (
            df['FINAL_LOGRADOURO'].astype(str).str.upper().str.contains(p['key'], na=False) & 
            (df['FINAL_CEP'].isna() | df['FINAL_CIDADE'].isna() | df['FINAL_UF'].isna())
        )
        if mask.any():
            logger.info(f"Patch aplicado para: {p['key']} ({mask.sum()} registros)")
            df.loc[mask, 'FINAL_CIDADE'] = df.loc[mask, 'FINAL_CIDADE'].fillna(p['cidade'])
            df.loc[mask, 'FINAL_CEP'] = df.loc[mask, 'FINAL_CEP'].fillna(p['cep'])
            df.loc[mask, 'FINAL_UF'] = df.loc[mask, 'FINAL_UF'].fillna(p['uf'])
            df.loc[mask, 'ORIGEM_DADO'] = "PATCH_MANUAL"
            df.loc[mask, 'STATUS_ENRIQUECIMENTO'] = "ENRIQUECIDO_COMPLETO"
            
    return df

def validate_columns(df: pd.DataFrame, required_columns: list, df_name: str) -> bool:
    """Valida colunas obrigatórias com suporte a renomeação."""
    # Renomeação automática de colunas conhecidas
    col_map = {
        'UNIDADE CONSUMIDORA': 'UC',
        'NUMERO UC': 'UC',
        'CNPJ/CPF': 'CNPJ' # Mapear original para CNPJ se necessário
    }
    
    # Normalizar headers para UPPER para matching
    df.columns = df.columns.astype(str).str.strip().str.upper()
    df.rename(columns=col_map, inplace=True)

    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        logger.error(f"[{df_name}] Colunas obrigatórias ausentes após normalização: {missing}")
        logger.error(f"Colunas disponíveis: {df.columns.tolist()}")
        return False
    return True

def clean_uc_key_vectorized(series: pd.Series) -> pd.Series:
    """Padronização vetorizada de chaves."""
    return (
        series.astype(str)
        .str.strip()
        .str.replace(r'\.0$', '', regex=True)
        .str.replace(r'\D', '', regex=True)
    )

def find_header_row(file_path, hints=['NUMERO UC', 'UC', 'CNPJ'], max_rows=30):
    """Localiza cabeçalho em arquivos Excel/CSV."""
    logger.info(f"Buscando cabeçalho em {file_path.name}...")
    ext = file_path.suffix.lower()
    for i in range(max_rows):
        try:
            if ext == '.csv':
                df_temp = pd.read_csv(file_path, skiprows=i, nrows=1, header=None)
            else:
                df_temp = pd.read_excel(file_path, skiprows=i, nrows=1, header=None)
            
            row_values = df_temp.iloc[0].astype(str).values
            if any(hint in str(v) for v in row_values for hint in hints):
                return i
        except Exception:
            continue
    return 0

def smart_clean_id(val: str) -> tuple[str, str]:
    """Limpa e valida CPF/CNPJ, tentando recuperar zeros à esquerda."""
    if pd.isna(val): return "", "VAZIO"
    
    clean = re.sub(r'\D', '', str(val))
    if not clean: return "", "VAZIO"

    # 1. Se já tem tamanho correto, valida
    if len(clean) == 11:
        if NoiseFilter.is_valid_cpf(clean): return clean, "VALIDO_CPF"
    elif len(clean) == 14:
        if NoiseFilter.is_valid_cnpj(clean): return clean, "VALIDO_CNPJ"

    # 2. Tenta reparar zeros à esquerda
    # Caso 10 -> 11 (CPF)
    if len(clean) == 10:
        test = clean.zfill(11)
        if NoiseFilter.is_valid_cpf(test): return test, "VALIDO_CPF_REPARADO"
    
    # Caso 13 -> 14 (CNPJ)
    if len(clean) == 13:
        test = clean.zfill(14)
        if NoiseFilter.is_valid_cnpj(test) or test.startswith('0'):
            # Mesmo que não valide (OCR erro), o zfill para 14 é o padrão para CNPJ
            if NoiseFilter.is_valid_cnpj(test): return test, "VALIDO_CNPJ_REPARADO"
            return test, "INVALIDO_CNPJ_PROVAVEL"

    # 3. Fallback: zfill padrão se for pequeno
    if len(clean) < 11:
        return clean.zfill(11), "TAMANHO_SUSPEITO_CPF"
    if len(clean) < 14:
        return clean.zfill(14), "TAMANHO_SUSPEITO_CNPJ"
        
    return clean, "VALOR_INVALIDO"

def clean_cnpj(val):
    id_val, status = smart_clean_id(val)
    return id_val

def query_brasil_api(cnpj):
    """Consulta BrasilAPI com backoff e tratamento de exceções."""
    if not cnpj or len(str(cnpj)) != 14:
        return None
    
    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
    backoff = 2
    
    for attempt in range(MAX_RETRIES_API):
        try:
            response = requests.get(url, timeout=API_TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'API_LOGRADOURO': data.get('logradouro'),
                    'API_NUMERO': data.get('numero'),
                    'API_BAIRRO': data.get('bairro'),
                    'API_MUNICIPIO': data.get('municipio'),
                    'API_UF': data.get('uf'),
                    'API_CEP': data.get('cep'),
                    'API_STATUS': 'SUCESSO'
                }
            elif response.status_code == 404:
                return {'API_STATUS': 'NAO_ENCONTRADO_API'}
            elif response.status_code == 429:
                logger.warning(f"Rate Limit (429) para {cnpj}. Aguardando {backoff}s...")
                time.sleep(backoff)
                backoff *= 2
            else:
                return {'API_STATUS': f'ERRO_HTTP_{response.status_code}'}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de rede para {cnpj}: {e}")
            return {'API_STATUS': 'ERRO_REDE'}
        except Exception as e:
            logger.error(f"Erro genérico para {cnpj}: {e}")
            return {'API_STATUS': 'ERRO_GENERICO'}
            
    return {'API_STATUS': 'FALHA_TIMEOUT'}

# --- Pipeline Principal ---

def main():
    os.makedirs(OUTPUT_FILE.parent, exist_ok=True)
    
    try:
        # 1. Carregar Erros
        logger.info(">>> Stage 1: Carregando Erros")
        
        # Determina fonte de erro
        source_erros = FILE_ERROS if FILE_ERROS.exists() else (BASE_DIR / "docs/ERROS CADASTRO RZ 1.xlsx - Planilha1.csv")
        if not source_erros.exists():
            logger.error("Arquivo de erros não encontrado.")
            return

        try:
            if source_erros.suffix == '.csv':
                df_errors = pd.read_csv(source_erros)
            else:
                df_errors = pd.read_excel(source_erros)
        except Exception as e:
            logger.error(f"Falha crítica ao ler erros: {e}")
            return

        if not validate_columns(df_errors, ['UC'], "Planilha Erros"):
            return

        df_errors['UC_KEY'] = clean_uc_key_vectorized(df_errors['UC'])
        logger.info(f"Erros carregados: {len(df_errors)} registros.")

        # 2. Carregar Base de Clientes (Lean Loading)
        logger.info(">>> Stage 2: Carregando Base de Clientes")
        target_base = FILE_BASE_CSV if FILE_BASE_CSV.exists() else FILE_BASE_XLSX
        
        if not target_base.exists():
            logger.error("Base de Clientes não encontrada.")
            return

        header_row = find_header_row(target_base, hints=['NUMERO UC', 'id_uc_negociada'])
        logger.info(f"Header Row Detected: {header_row}")
        
        # Dump debug params
        with open("debug_join_params.txt", "w") as f:
            f.write(f"File: {target_base}\n")
            f.write(f"Header Row: {header_row}\n")
        
        # Carregamento Otimizado (se for CSV usa engine C, se Excel carrega normal)
        # Nota: read_excel não suporta chunksize nativo em todas versões, mantendo load full
        try:
            if target_base.suffix == '.csv':
                df_base = pd.read_csv(target_base, skiprows=header_row, low_memory=False)
            else:
                df_base = pd.read_excel(target_base, skiprows=header_row)
        except Exception as e:
            logger.error(f"Erro ao ler Base: {e}")
            return

        # Normalização de Colunas (Strip + Upper)
        df_base.columns = df_base.columns.astype(str).str.strip().str.upper()
        
        # Mapping base columns to standard names
        # 'CNPJ' is expected. 'NUMERO UC' -> 'UC'
        
        # Tentar identificar CNPJ pela posição K (Index 10) se a col 'CNPJ' não existir ou estiver vazia
        if 'CNPJ' not in df_base.columns and len(df_base.columns) > 10:
             # Check if index 10 looks like it
             col_k = df_base.columns[10]
             logger.warning(f"Coluna 'CNPJ' não encontrada por nome. Tentando Coluna K (Index 10): '{col_k}'")
             df_base.rename(columns={col_k: 'CNPJ'}, inplace=True)
        elif 'CNPJ' in df_base.columns:
             logger.info("Coluna 'CNPJ' encontrada por nome.")
        
        # FIX: Do NOT rename ID_UC_NEGOCIADA to UC, as it masks NUMERO UC
        col_map = {'NUMERO UC': 'UC'}
        df_base.rename(columns=col_map, inplace=True)
        
        # Identificação dinâmica de coluna UC
        col_uc_base = 'UC'
        if col_uc_base not in df_base.columns:
            candidates = [c for c in df_base.columns if 'UC' in str(c).upper()]
            if candidates:
                col_uc_base = candidates[0]
                logger.info(f"Coluna UC detectada na base: {col_uc_base}")
            else:
                logger.error("Coluna UC não encontrada na Base.")
                return

        with open("debug_join_params.txt", "a") as f:
            f.write(f"UC Column Used: {col_uc_base}\n")
            if col_uc_base in df_base.columns:
                sample_vals = df_base[col_uc_base].head().tolist()
                f.write(f"UC Sample Values: {sample_vals}\n")

        # Limpeza e Deduplicação Base
        # Garantir que pegamos apenas a primeira coluna se houver duplicatas
        uc_series = df_base[col_uc_base]
        if isinstance(uc_series, pd.DataFrame):
            uc_series = uc_series.iloc[:, 0]
            
        df_base['UC_KEY'] = clean_uc_key_vectorized(uc_series)
        df_base = df_base.drop_duplicates(subset=['UC_KEY'], keep='first')
        
        cols_base = ['UC_KEY', 'CNPJ', 'ENDEREÇO COMPLETO', 'CEP', 'CIDADE', 'UF', 'RAZÃO SOCIAL FATURAMENTO']
        existing_cols = [c for c in cols_base if c in df_base.columns]
        logger.info(f"Colunas encontradas na Base: {existing_cols}")
        
        df_base_lean = df_base[existing_cols].copy()
        logger.info(f"Base Lean Shape: {df_base_lean.shape}")
        
        # Liberar memória
        del df_base 
        
        # 3. Cruzamento Otimizado (Standard Merge)
        logger.info(">>> Stage 3: Cruzamento (Merge on UC_KEY)")
        
        # Ensure types are string
        df_errors['UC_KEY'] = df_errors['UC_KEY'].astype(str).str.strip()
        df_base_lean['UC_KEY'] = df_base_lean['UC_KEY'].astype(str).str.strip()
        
        # Debug Keys
        with open("keys_dump_errors.txt", "w") as f:
            f.write("\n".join(sorted(df_errors['UC_KEY'].unique())))
        with open("keys_dump_base.txt", "w") as f:
            f.write("\n".join(sorted(df_base_lean['UC_KEY'].unique())))
        
        # Merge
        df_merged = pd.merge(
            df_errors,
            df_base_lean,
            on='UC_KEY',
            how='left',
            suffixes=('', '_BASE')
        )
        
        # Dump debug
        try:
            df_merged.head(10).to_csv("debug_merged_head.csv")
            logger.info("Dumped debug_merged_head.csv")
        except:
            pass
            
        logger.info(f"Colunas após Merge: {df_merged.columns.tolist()}")
        logger.info(f"Amostra Merge (primeiro registro): {df_merged.iloc[0].to_dict()}")

        # Logic to resolve suffixes and rename keys correctly
        # We want to prioritize the data coming from BASE
        # If collision occures, join creates 'Col' (left/original) and 'Col_BASE' (right/base)
        
        column_mapping = {
            'CNPJ': 'BASE_CNPJ',
            'ENDEREÇO COMPLETO': 'BASE_ENDERECO',
            'CEP': 'BASE_CEP',
            'CIDADE': 'BASE_CIDADE',
            'UF': 'BASE_UF'
        }
        
        final_rename_map = {}
        for base_col, target_col in column_mapping.items():
            suffixed_col = f"{base_col}_BASE"
            if suffixed_col in df_merged.columns:
                final_rename_map[suffixed_col] = target_col
            elif base_col in df_merged.columns:
                # If only base_col exists, it might be from Base (no collision) 
                # OR from Error (if Base didn't have it or didn't match).
                # But since we selected `df_base[existing_cols]`, we know Base HAS these columns.
                # Use it, but be aware it might be the Error one if match failed? 
                # No, if match failed, Base columns are NaN. 
                # If collision didn't occur, it means Error didn't have that column, so it MUST be from Base.
                final_rename_map[base_col] = target_col

        logger.info(f"Rename Map resolved: {final_rename_map}")
        df_merged.rename(columns=final_rename_map, inplace=True)

        # 4. Sanitização CNPJ
        logger.info(">>> Stage 4: Sanitização")
        
        # Coalesce: Prioritize Base, then Original
        if 'BASE_CNPJ' in df_merged.columns:
            # If we have original 'CNPJ' column (from Error file), use it as fallback
            if 'CNPJ' in df_merged.columns:
                df_merged['CNPJ_RAW'] = df_merged['BASE_CNPJ'].fillna(df_merged['CNPJ'])
                logger.info("Usando Fallback: BASE_CNPJ + CNPJ Original")
            else:
                df_merged['CNPJ_RAW'] = df_merged['BASE_CNPJ']
        elif 'CNPJ' in df_merged.columns:
            df_merged['CNPJ_RAW'] = df_merged['CNPJ']
        else:
            df_merged['CNPJ_RAW'] = None

        if 'CNPJ_RAW' in df_merged.columns:
            # Aplica smart_clean_id para obter o valor e o status de validação
            logger.info("Executando validação de CPFs/CNPJs...")
            res = df_merged['CNPJ_RAW'].apply(smart_clean_id)
            df_merged['CNPJ_CLEAN'] = res.apply(lambda x: x[0])
            df_merged['VALIDACAO_ID'] = res.apply(lambda x: x[1])
        else:
            df_merged['CNPJ_CLEAN'] = None
            df_merged['VALIDACAO_ID'] = "AUSENTE"

        # 5. API Loop
        # Trigger API if:
        # 1. CNPJ is valid
        # 2. AND (Address is missing OR CEP is missing)
        mask_api = (
            (df_merged['CNPJ_CLEAN'].notna()) & 
            (df_merged['CNPJ_CLEAN'].str.len() == 14) & 
            (
                df_merged['BASE_ENDERECO'].isna() | 
                (df_merged['BASE_ENDERECO'] == '') |
                df_merged['BASE_CEP'].isna() |
                (df_merged['BASE_CEP'] == '')
            )
        )
        cnpjs_to_search = df_merged[mask_api]['CNPJ_CLEAN'].unique()
        logger.info(f"CNPJs para API: {len(cnpjs_to_search)}")

        api_results = {}
        
        # Carregamento Robusto de Parcial
        if PARTIAL_FILE.exists():
            try:
                with open(PARTIAL_FILE, 'r') as f:
                    api_results = json.load(f)
                logger.info(f"Progresso recuperado: {len(api_results)} CNPJs.")
            except json.JSONDecodeError:
                logger.error("Arquivo parcial corrompido. Iniciando do zero.")
                api_results = {}
            except Exception as e:
                logger.warning(f"Erro ao ler parcial: {e}")

        pending = [c for c in cnpjs_to_search if c not in api_results]

        if pending:
            logger.info(f"Iniciando consultas para {len(pending)} CNPJs...")
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_cnpj = {executor.submit(query_brasil_api, c): c for c in pending}
                completed = 0
                
                for future in as_completed(future_to_cnpj):
                    cnpj = future_to_cnpj[future]
                    completed += 1
                    
                    try:
                        res = future.result()
                        if res: api_results[cnpj] = res
                    except Exception as e:
                        logger.error(f"Erro thread {cnpj}: {e}")

                    # Save Batch
                    if completed % BATCH_SAVE_SIZE == 0:
                        logger.info(f"Progresso: {completed}/{len(pending)}...")
                        with open(PARTIAL_FILE, 'w') as f:
                            json.dump(api_results, f)
            
            # Save Final
            with open(PARTIAL_FILE, 'w') as f:
                json.dump(api_results, f)

        # Telemetria API
        successes = sum(1 for r in api_results.values() if r.get('API_STATUS') == 'SUCESSO')
        failures = len(api_results) - successes
        logger.info(f"Estatísticas API: {successes} sucessos, {failures} falhas/não encontrados.")

        # 6. Consolidação
        logger.info(">>> Stage 5: Consolidação")
        
        if api_results:
            df_api = pd.DataFrame.from_dict(api_results, orient='index')
            df_api.index.name = 'CNPJ_CLEAN'
            df_api.reset_index(inplace=True)
            df_merged = pd.merge(df_merged, df_api, on='CNPJ_CLEAN', how='left')
        else:
            for col in ['API_LOGRADOURO', 'API_STATUS']:
                if col not in df_merged.columns: df_merged[col] = None

        # Status Final (Vetorizado)
        conditions = [
            (df_merged['BASE_CNPJ'].notna()) & ((df_merged['BASE_ENDERECO'].notna()) | (df_merged.get('API_LOGRADOURO').notna())),
            (df_merged['BASE_CNPJ'].notna()),
            (df_merged['UC_KEY'].isin(df_base_lean.index if 'df_base_lean' in locals() else [])) # fallback check
        ]
        choices = ["ENRIQUECIDO_COMPLETO", "ENRIQUECIDO_PARCIAL", "DADOS_BASE_INCOMPLETOS"]
        df_merged['STATUS_ENRIQUECIMENTO'] = np.select(conditions, choices, default="NAO_ENCONTRADO_BASE")

        # Coalesce Address Fields (Priority: API > Base)
        def coalesce(df, col1, col2):
            c1 = df[col1] if col1 in df.columns else pd.Series([None]*len(df))
            c2 = df[col2] if col2 in df.columns else pd.Series([None]*len(df))
            return c1.fillna(c2)

        df_merged['FINAL_LOGRADOURO'] = coalesce(df_merged, 'API_LOGRADOURO', 'BASE_ENDERECO')
        df_merged['FINAL_BAIRRO'] = coalesce(df_merged, 'API_BAIRRO', 'BASE_BAIRRO')
        df_merged['FINAL_CIDADE'] = coalesce(df_merged, 'API_MUNICIPIO', 'BASE_CIDADE')
        df_merged['FINAL_UF'] = coalesce(df_merged, 'API_UF', 'BASE_UF')
        df_merged['FINAL_CEP'] = coalesce(df_merged, 'API_CEP', 'BASE_CEP')
        
        # Determine Origin
        df_merged['ORIGEM_DADO'] = np.where(df_merged['API_STATUS'] == 'SUCESSO', 'API', 
                                   np.where(df_merged['STATUS_ENRIQUECIMENTO'] == 'ENRIQUECIDO_COMPLETO', 'BASE', 'N/A'))

        # Define Logical Order
        priority_cols = [
            'STATUS_ENRIQUECIMENTO', 'ORIGEM_DADO', 'UC', 'CNPJ', 'VALIDACAO_ID', 'NOME', 
            'FINAL_LOGRADOURO', 'FINAL_BAIRRO', 'FINAL_CIDADE', 'FINAL_UF', 'FINAL_CEP'
        ]
        
        # Add remaining columns that are not in priority
        remaining_cols = [c for c in df_merged.columns if c not in priority_cols and c != 'CNPJ_RAW']
        final_order = priority_cols + remaining_cols
        
        # Validar se todas priority existem
        final_order = [c for c in final_order if c in df_merged.columns]
        
        df_final = df_merged[final_order].copy()
        
        # Patch Final para os casos sem Cidade/CEP que inferimos
        df_final = apply_manual_patches(df_final)

        df_final.to_excel(OUTPUT_FILE, index=False)
        logger.info(f"Sucesso! Arquivo salvo em: {OUTPUT_FILE}")
        
        # Cleanup
        cleanup_temp_files()

    except Exception as e:
        logger.critical(f"Falha fatal no pipeline: {e}")
        raise

if __name__ == "__main__":
    main()