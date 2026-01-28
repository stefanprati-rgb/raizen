#!/usr/bin/env python3
"""
Script de Finalização com IA (Gemini) para CPFL Paulista.
Processa apenas os registros que falharam na extração via Regex.

Requisitos:
- Arquivo .env com GEMINI_API_KEY configurada.
"""

import os
import sys
import json
import time
import pandas as pd
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurações
BASE_DIR = Path("C:/Projetos/Raizen/data/processed")
CSV_PATH = Path("C:/Projetos/Raizen/output/datasets_consolidados/CPFL_PAULISTA/CPFL_PAULISTA.csv")
MODEL_NAME = "gemini-2.5-flash-lite"

SCHEMA_PROMPT = """
Atue como um especialista em contratos de energia (CPFL). Analise o texto extraído do PDF.
Extraia os seguintes campos com precisão cirúrgica. Retorne JSON.

Campos:
1. "data_adesao": (string DD/MM/AAAA) Data de assinatura do contrato ou termo de adesão. Procure em logs de assinatura eletrônica (Clicksign, Qualisign, Docusign) no final do documento.
2. "participacao_percentual": (number) Percentual de participação, rateio, cota ou alocação de energia (ex: 12.5).
3. "representante_nome": (string) Nome do representante legal que assinou o contrato.
4. "aviso_previo": (number) Número de dias para aviso prévio de denúncia/rescisão.
5. "num_instalacao": (string) Número da instalação/UC.

Regras:
- Se não encontrar, retorne null.
- Priorize logs de assinatura para Data e Representante.
- Converta datas por extenso para formato numérico.
"""

def setup_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Erro: GEMINI_API_KEY não encontrada no .env ou ambiente.")
        sys.exit(1)
    genai.configure(api_key=api_key)

def process_with_gemini(pdf_path, current_data):
    """Envia PDF para Gemini apenas para campos que estão vazios."""
    
    if not os.path.exists(pdf_path):
        return None

    # Verifica o que falta
    missing_fields = []
    if pd.isna(current_data.get("data_adesao")): missing_fields.append("data_adesao")
    if pd.isna(current_data.get("participacao_percentual")): missing_fields.append("participacao_percentual")
    if pd.isna(current_data.get("representante_nome")): missing_fields.append("representante_nome")
    if pd.isna(current_data.get("aviso_previo")): missing_fields.append("aviso_previo")
    
    if not missing_fields:
        return None  # Nada a fazer

    try:
        # Upload
        print(f"   ⬆️  Gemini: Enviando PDF...", end="\r")
        sample_file = genai.upload_file(path=pdf_path)
        
        while sample_file.state.name == "PROCESSING":
            time.sleep(1)
            sample_file = genai.get_file(sample_file.name)
            
        if sample_file.state.name == "FAILED":
            return None

        # Generate
        print(f"   🧠 Gemini: Analisando {', '.join(missing_fields)}...", end="\r")
        model = genai.GenerativeModel(MODEL_NAME)
        
        response = model.generate_content(
            [sample_file, SCHEMA_PROMPT],
            generation_config={"response_mime_type": "application/json"}
        )
        
        # Cleanup
        try:
            genai.delete_file(sample_file.name)
        except:
            pass
            
        return json.loads(response.text)

    except Exception as e:
        print(f"   ❌ Erro Gemini: {e}")
        return None

def find_pdf_path(filename, base_dir):
    # Lógica de busca otimizada (mesma do outro script)
    candidate = base_dir / "16_paginas/CPFL_PAULISTA" / filename
    if candidate.exists(): return candidate
    
    # Busca rápida em pastas comuns CPFL
    for subdir in ["05_paginas", "11_paginas", "02_paginas"]:
        candidate = base_dir / subdir / "CPFL_PAULISTA" / filename
        if candidate.exists(): return candidate

    results = list(base_dir.rglob(filename))
    if results: return results[0]
    return None

def main():
    print("=" * 70)
    print("FINALIZAÇÃO COM IA (GEMINI) - CPFL PAULISTA")
    print("=" * 70)
    
    setup_gemini()
    
    if not CSV_PATH.exists():
        print(f"Erro: CSV não encontrado: {CSV_PATH}")
        return
        
    df = pd.read_csv(CSV_PATH, sep=";", low_memory=False)
    
    # Filtrar registros incompletos
    # Consideramos incompleto se faltar Data Adesão OU (Participação E Representante)
    mask_incompleto = (
        pd.isna(df["data_adesao"]) | 
        pd.isna(df["participacao_percentual"]) |
        pd.isna(df["representante_nome"])
    )
    
    df_processar = df[mask_incompleto]
    print(f"Total registros: {len(df)}")
    print(f"Registros incompletos (Alvo da IA): {len(df_processar)}")
    
    if len(df_processar) == 0:
        print("✅ Base completa! Nada a processar.")
        return
        
    print("\nIniciando processamento com IA...")
    
    updates = 0
    errors = 0
    
    # Iterar sobre os índices filtrados
    for i, (idx, row) in enumerate(df_processar.iterrows()):
        arquivo = row.get("arquivo_origem")
        print(f"[{i+1}/{len(df_processar)}] {arquivo[:50]}...")
        
        pdf_path = find_pdf_path(arquivo, BASE_DIR)
        
        if pdf_path:
            result = process_with_gemini(str(pdf_path), row)
            
            if result:
                # Atualizar campos se retornou valor válido
                if result.get("data_adesao"):
                    df.at[idx, "data_adesao"] = result["data_adesao"]
                    print(f"   ✨ Data: {result['data_adesao']}")
                    
                if result.get("participacao_percentual"):
                    val = result["participacao_percentual"]
                    if isinstance(val, (int, float)) or (isinstance(val, str) and val.replace('.','').isdigit()):
                         df.at[idx, "participacao_percentual"] = val
                         print(f"   ✨ Part: {val}%")

                if result.get("representante_nome"):
                    df.at[idx, "representante_nome"] = result["representante_nome"]
                    
                if result.get("aviso_previo"):
                    df.at[idx, "aviso_previo"] = result["aviso_previo"]
                
                updates += 1
            else:
                print("   ⚠️ Sem resultado da IA")
        else:
            print("   ❌ PDF não encontrado")
            
        # Checkpoint
        if (i + 1) % 10 == 0:
            df.to_csv(CSV_PATH, sep=";", index=False)
            print("💾 Checkpoint salvo")
            
        # Rate limit preventivo (Flash tem limite alto mas bom prevenir)
        time.sleep(2) 

    # Final save
    df.to_csv(CSV_PATH, sep=";", index=False)
    print("=" * 70)
    print(f"Processamento IA concluído!")
    print(f"Registros enviados: {len(df_processar)}")
    print(f"Atualizados com sucesso: {updates}")
    
    # Gerar Excel
    excel_path = Path("C:/Projetos/Raizen/output/datasets/cpfl/dataset_CPFL_PAULISTA_final_AI.xlsx")
    df.to_excel(excel_path, index=False)
    print(f"Excel Final com IA: {excel_path}")

if __name__ == "__main__":
    main()
