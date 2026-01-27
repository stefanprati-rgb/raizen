import pandas as pd
from pathlib import Path
import shutil
import re
import os
import unicodedata

# --- CONFIGURAÇÃO ---
DATASET_PATH = Path("C:/Projetos/Raizen/output/DATASET_FINAL_GOLDEN_RAIZEN_EXPLODED.xlsx")
# Diretório onde os PDFs originais estão (busca recursiva)
SOURCE_DIR = Path("C:/Projetos/Raizen/data/golden_source")
# Diretório de destino
OUTPUT_DIR = Path("C:/Projetos/Raizen/output/renamed_pdfs")
# Arquivo de Correlação
CORRELATION_FILE = Path("C:/Projetos/Raizen/output/DE_PARA_RENOMEACAO.xlsx")

# Se True, não copia arquivos, apenas simula e gera o excel
DRY_RUN = False

def sanitize_filename(text):
    """Remove caracteres especiais e espaços, mantendo apenas letras, números e underline."""
    if not isinstance(text, str):
        return "N_A"
    
    # Normalizar (remover acentos)
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    # Substituir espaços e hifens por underline
    text = text.replace(" ", "_").replace("-", "_")
    # Remover tudo que não for alfanumérico ou underscore
    text = re.sub(r'[^a-zA-Z0-9_]', '', text)
    # Remover underscores duplicados
    text = re.sub(r'_{2,}', '_', text)
    return text.upper().strip('_')

def clean_numbers(text):
    """Mantém apenas dígitos."""
    if pd.isna(text):
        return ""
    return re.sub(r'\D', '', str(text))

def main():
    print("="*60)
    print("RENOMEAÇÃO DE PDFs - PADRÃO GOLDEN")
    print("="*60)
    
    if not DATASET_PATH.exists():
        print(f"❌ Dataset não encontrado: {DATASET_PATH}")
        return

    # 1. Carregar Dataset
    print(f"Carregando dataset: {DATASET_PATH.name}...")
    df = pd.read_excel(DATASET_PATH, dtype=str)
    
    # 2. Deduplicar por Arquivo Original
    # Regra: 1 Arquivo Original -> 1 Arquivo Renomeado (usando a primeira linha encontrada)
    print(f"Linhas totais: {len(df)}")
    if 'arquivo_origem' in df.columns:
        df_unique = df.drop_duplicates(subset=['arquivo_origem'], keep='first').copy()
        print(f"Arquivos únicos (Source): {len(df_unique)}")
    else:
        print("❌ Coluna 'arquivo_origem' não encontrada.")
        return

    # 3. Mapear Arquivos Originais no Disco
    print("Mapeando arquivos na pasta de origem (Recursivo)...")
    file_map = {}
    for root, _, files in os.walk(SOURCE_DIR):
        for f in files:
            if f.lower().endswith(".pdf"):
                # Mapeia Nome -> Caminho Completo
                # Obs: Se houver nomes duplicados em subpastas diferentes, o último vence (ou mudar logica)
                # Para golden set, assume-se nomes únicos ou irrelevante qual pegar
                file_map[f] = Path(root) / f
                
    print(f"Arquivos encontrados no disco: {len(file_map)}")

    # 4. Processar Renomeação
    output_rows = []
    
    if not DRY_RUN:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    missing_count = 0
    
    used_names = {} # Para evitar colisão de nomes no destino

    print("Iniciando processamento...")
    for idx, row in df_unique.iterrows():
        original_name = row.get('arquivo_origem')
        
        # Encontrar arquivo físico
        source_path = file_map.get(original_name)
        
        # Montar Novo Nome
        # Padrão: [CNPJ_CPF]_[RazaoSocial]_[UC].pdf
        
        # CNPJ/CPF
        cnpj = clean_numbers(row.get('CNPJ'))
        cpf = clean_numbers(row.get('CPF Representante')) # Nem sempre é o CPF do cliente, mas é o que temos
        # O user pediu "cpf ou cnpj". Vamos tentar CNPJ primeiro, depois CPF, depois "SEM_DOC"
        doc_id = cnpj if len(cnpj) > 5 else (cpf if len(cpf) > 5 else "SEM_DOC")
        
        # Nome/Razão
        razao = row.get('Razão Social')
        nome_cliente = row.get('Número do Cliente') # Fallback ruim, mas...
        # Ideal seria ter Nome Cliente se Razão for nula. Vamos usar Razao ou "SEM_NOME"
        name_part = sanitize_filename(razao) if pd.notna(razao) else "SEM_NOME"
        
        # UC
        uc = clean_numbers(row.get('UC / Instalação'))
        if not uc:
             uc = "SEM_UC"
             
        new_filename = f"{doc_id}_{name_part}_{uc}.pdf"
        
        # Tratar colisão de nomes (Arquivos diferentes gerando mesmo nome)
        if new_filename in used_names:
            counter = used_names[new_filename] + 1
            used_names[new_filename] = counter
            # Inserir contador antes da extensão
            stem = Path(new_filename).stem
            new_filename = f"{stem}_{counter}.pdf"
        else:
            used_names[new_filename] = 1
            
        status = "PENDENTE"
        
        if source_path and source_path.exists():
            dest_path = OUTPUT_DIR / new_filename
            try:
                if not DRY_RUN:
                    shutil.copy2(source_path, dest_path)
                status = "OK"
                success_count += 1
            except Exception as e:
                status = f"ERRO_COPY: {e}"
        else:
            status = "ARQUIVO_ORIGEM_NAO_ENCONTRADO"
            missing_count += 1
            
        output_rows.append({
            "NOME_ANTIGO": original_name,
            "NOME_NOVO": new_filename,
            "CAMINHO_ORIGEM": str(source_path) if source_path else None,
            "STATUS": status,
            "CHAVE_DOC": doc_id,
            "CHAVE_NOME": name_part,
            "CHAVE_UC": uc
        })

    # 5. Gerar Relatório
    df_result = pd.DataFrame(output_rows)
    df_result.to_excel(CORRELATION_FILE, index=False)
    
    print("-" * 60)
    print(f"Processamento Concluído!")
    print(f"Sucesso: {success_count}")
    print(f"Arquivos não encontrados: {missing_count}")
    print(f"Tabela De/Para gerada em: {CORRELATION_FILE}")
    if not DRY_RUN:
        print(f"Arquivos copiados para: {OUTPUT_DIR}")
    else:
        print(f"DRY RUN: NENHUM ARQUIVO COPIADO.")

if __name__ == "__main__":
    main()
