"""
Orquestrador de Recuperação de Falhas de Extração (Hybrid Recovery Pipeline).
Executa o Plano de Recuperação conforme especificado:
1. Sanitização Lógica de CNPJ/CPF.
2. Localização de PDFs através de indexador híbrido.
3. Inspeção cirúrgica com Gemini 2.0 Flash para campos faltantes.
"""
import os
import re
import json
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional
import google.generativeai as genai
from dotenv import load_dotenv

# Adicionar src ao path para importações
import sys
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.raizen_power.utils.text_sanitizer import TextSanitizer
from src.raizen_power.utils.file_indexer import build_file_index, find_pdf_path
from src.raizen_power.utils.validators import validate_cnpj_checksum, validate_cpf_checksum

# Configuração de Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(project_root / "output" / "recovery_pipeline.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Carregar .env
load_dotenv(project_root / ".env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.error("Chave API Gemini não encontrada no arquivo .env")

# Prompt conforme especificado no plano
RECOVERY_PROMPT = """
Você é um especialista em auditoria de contratos de energia.
Analise o documento fornecido. Sua missão é recuperar dados que falharam na extração via Regex.

ALVOS:
1. Endereço da Instalação/UC: Procure no cabeçalho, preâmbulo ou anexos.
2. CNPJ/CPF do Cliente: Procure próximo à Razão Social ou na assinatura.

Retorne APENAS um JSON:
{{
  "endereco_encontrado": "string completa ou null",
  "cep": "string (somente números) ou null",
  "logradouro": "string ou null",
  "numero": "string ou null",
  "bairro": "string ou null",
  "cidade": "string ou null",
  "uf": "string (sigla) ou null",
  "documento_cliente_corrigido": "string (somente números) ou null"
}}
"""

def extract_with_gemini(pdf_path: str) -> Optional[Dict[str, Any]]:
    """Envia o PDF para o Gemini extrair os campos faltantes."""
    if not GEMINI_API_KEY:
        return None
    
    try:
        model = genai.GenerativeModel("gemini-2.0-flash-lite")
        
        # Carregar arquivo para a API (método recomendado para PDFs)
        sample_file = genai.upload_file(path=pdf_path, display_name="Contrato Recuperacao")
        
        # Gerar conteúdo
        response = model.generate_content([RECOVERY_PROMPT, sample_file])
        
        # Limpar resposta para extrair JSON
        text = response.text
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return None
    except Exception as e:
        logger.error(f"Erro na extração Gemini para {pdf_path}: {e}")
        return None

def main():
    # Caminhos dos arquivos
    errors_path = project_root / "docs" / "ERROS CADASTRO RZ 1.xlsx"
    dataset_path = project_root / "output" / "DATASET_FINAL_.xlsx"
    output_dir = project_root / "output" / "recovery"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("Iniciando Pipeline de Recuperação Híbrida")
    
    # 1. Carregar Dados
    if not errors_path.exists():
        logger.error(f"Arquivo de erros não encontrado em {errors_path}")
        return
    
    df_errors = pd.read_excel(errors_path)
    df_dataset = pd.read_excel(dataset_path) if dataset_path.exists() else None
    
    # 2. Construir Indexador de Arquivos
    logger.info("Construindo indexador de arquivos...")
    index_name, renamed_files = build_file_index()
    
    results = []
    
    # 3. Processar cada erro
    total = len(df_errors)
    for idx, row in df_errors.iterrows():
        uc = row.get('UC')
        tipo_erro = str(row.get('ERRO APRESENTADO', '')).lower()
        
        logger.info(f"[{idx+1}/{total}] Processando UC: {uc} - Erro: {tipo_erro}")
        
        recovered_data = {
            'UC': uc,
            'erro_original': tipo_erro,
            'recuperado_por': 'Nenhum',
            'status': 'Falha'
        }
        
        # Tentar localizar dados no dataset original se existir
        orig_row = None
        if df_dataset is not None:
            # Busca flexível por UC
            mask = df_dataset['UC / Instalação'].astype(str).str.contains(str(uc), na=False)
            matches = df_dataset[mask]
            if not matches.empty:
                orig_row = matches.iloc[0]
                recovered_data['arquivo_origem'] = orig_row.get('arquivo_origem', '')
                recovered_data['razao_social'] = orig_row.get('Razão Social', '')

        # STAGE 1: Sanitização Lógica (para erros de CNPJ/CPF)
        if 'cnpj' in tipo_erro or 'documento' in tipo_erro or 'inválido' in tipo_erro:
            current_cnpj = str(orig_row.get('CNPJ', '')) if orig_row is not None else ""
            
            # Tentar zfill e fuzzy
            fixed_cnpj = TextSanitizer.repair_id_zeros(current_cnpj, 'CNPJ')
            if validate_cnpj_checksum(fixed_cnpj):
                recovered_data['documento_corrigido'] = fixed_cnpj
                recovered_data['recuperado_por'] = 'Logica (zfill)'
                recovered_data['status'] = 'Sucesso'
                logger.info(f"   ✅ Recuperado via Logica: {fixed_cnpj}")
            else:
                fuzzy_cnpj = TextSanitizer.fuzzy_fix_ocr(current_cnpj)
                if validate_cnpj_checksum(fuzzy_cnpj):
                    recovered_data['documento_corrigido'] = fuzzy_cnpj
                    recovered_data['recuperado_por'] = 'Logica (Fuzzy OCR)'
                    recovered_data['status'] = 'Sucesso'
                    logger.info(f"   ✅ Recuperado via Fuzzy OCR: {fuzzy_cnpj}")

        # STAGE 2 & 3: Localização e Gemini (se não recuperou logicamente ou se for endereço)
        if recovered_data['status'] == 'Falha':
            # Tentar localizar PDF
            pdf_path = find_pdf_path(uc, recovered_data.get('arquivo_origem'), index_name, renamed_files)
            
            if pdf_path:
                logger.info(f"   📄 PDF localizado: {pdf_path}. Chamando Gemini...")
                # STAGE 3: IA
                ai_data = extract_with_gemini(pdf_path)
                if ai_data:
                    recovered_data.update(ai_data)
                    recovered_data['recuperado_por'] = 'Gemini 2.0'
                    recovered_data['status'] = 'Sucesso'
                    logger.info("   ✅ Recuperado via Gemini")
                else:
                    recovered_data['status'] = 'Falha (IA retornou vazio)'
            else:
                logger.warning(f"   ❌ PDF não localizado para UC {uc}")
                recovered_data['status'] = 'Falha (PDF não encontrado)'

        results.append(recovered_data)
        
        # Salvar checkpoint a cada 10 registros
        if (idx + 1) % 10 == 0:
            pd.DataFrame(results).to_excel(output_dir / "recovered_data_partial.xlsx", index=False)

    # 4. Salvar Resultado Final
    df_recovered = pd.DataFrame(results)
    final_output = output_dir / "recovered_data_final.xlsx"
    df_recovered.to_excel(final_output, index=False)
    logger.info(f"Processo concluído. Resultado salvo em: {final_output}")

if __name__ == "__main__":
    main()
