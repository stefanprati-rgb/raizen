"""
Create investigation batches for Gemini analysis.
Max 10 PDFs per batch (Gemini limit).
"""
import json
import shutil
from pathlib import Path

V5_RESULTS_PATH = Path('output/cpfl_paulista_final/cpfl_v5_full_results.json')
OUTPUT_DIR = Path('output/investigar_gemini_batches')

PROMPT_TEMPLATE = '''Você é um engenheiro de dados especialista em extração de informações de contratos de energia.

## CONTEXTO
Estou extraindo dados de contratos da CPFL/Raízen. Esses {count} PDFs **não retornaram nenhuma UC** no meu extrator automático.

Preciso que você analise cada PDF e me diga:
1. O documento DEVERIA conter UCs (Unidades Consumidoras / Instalações)?
2. Se sim, quais são os números de UC presentes?
3. Por que meu extrator pode ter falhado?

## CAMPOS QUE BUSCO
- **Nº da Instalação / Nº Conta Contrato (UC)**: Números de 8-10 dígitos que identificam a unidade elétrica
- Padrões CPFL comuns: 40XXXXXXXX, 70XXXXXXX, 71XXXXXXX, ou sequências genéricas

## FORMATO DE RESPOSTA
Retorne um JSON com a análise de cada arquivo:

```json
{{
  "analises": [
    {{
      "arquivo": "nome_do_arquivo.pdf",
      "tipo_documento": "ADESAO | CONDICOES | ANEXO | OUTRO",
      "deveria_ter_uc": true | false,
      "ucs_encontradas": ["123456789", "987654321"],
      "numero_cliente": "XXXXX (se houver)",
      "motivo_falha": "Ex: UC está em tabela, V5 não lê tabelas | UC usa padrão diferente | Documento não contém UCs"
    }}
  ]
}}
```

Analise os {count} PDFs anexados e retorne o JSON completo.
'''

def main():
    print("Loading V5 results...")
    with open(V5_RESULTS_PATH, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    # Filter empty SOLAR + TERMO_ADESAO
    target_types = ['SOLAR', 'TERMO_ADESAO']
    empty_docs = [r for r in results if r['status'] == 'VAZIO' and r['type'] in target_types]
    
    print(f"Total empty docs to investigate: {len(empty_docs)}")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Split into batches of 10
    batch_size = 10
    batches = [empty_docs[i:i+batch_size] for i in range(0, len(empty_docs), batch_size)]
    
    print(f"Creating {len(batches)} batches...")
    
    for batch_num, batch in enumerate(batches, 1):
        batch_dir = OUTPUT_DIR / f"batch_{batch_num:02d}"
        batch_dir.mkdir(exist_ok=True)
        
        print(f"\nBatch {batch_num}: {len(batch)} files")
        
        # Copy PDFs
        for i, doc in enumerate(batch, 1):
            src = Path(doc['path'])
            if src.exists():
                # Use short name to avoid path length issues
                dst = batch_dir / f"{i:02d}_{doc['type']}_{src.stem[:40]}.pdf"
                try:
                    shutil.copy2(src, dst)
                    print(f"  - {dst.name[:50]}...")
                except Exception as e:
                    print(f"  - ERROR: {e}")
            else:
                print(f"  - NOT FOUND: {src}")
        
        # Create prompt
        prompt_file = batch_dir / "PROMPT.txt"
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("INSTRUÇÕES PARA O GEMINI\n")
            f.write("=" * 60 + "\n\n")
            f.write("1. Acesse https://gemini.google.com\n")
            f.write("2. Faça upload de TODOS os PDFs desta pasta\n")
            f.write("3. Cole o prompt abaixo e envie\n")
            f.write("4. Copie a resposta para RESPOSTA.txt\n\n")
            f.write("=" * 60 + "\n")
            f.write("PROMPT:\n")
            f.write("=" * 60 + "\n\n")
            f.write(PROMPT_TEMPLATE.format(count=len(batch)))
        
        # Create response placeholder
        resposta_file = batch_dir / "RESPOSTA.txt"
        with open(resposta_file, 'w', encoding='utf-8') as f:
            f.write("[Cole a resposta do Gemini aqui]\n")
        
        # Create file list
        lista_file = batch_dir / "ARQUIVOS.txt"
        with open(lista_file, 'w', encoding='utf-8') as f:
            for doc in batch:
                f.write(f"{doc['type']} | {doc['folder']} | {doc['file']}\n")
    
    print("\n" + "=" * 60)
    print(f"Batches criados em: {OUTPUT_DIR.absolute()}")
    print(f"Total de batches: {len(batches)}")
    print("Cada batch contém até 10 PDFs + PROMPT.txt + RESPOSTA.txt")
    print("=" * 60)

if __name__ == "__main__":
    main()
