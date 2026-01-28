"""
Criar pasta com amostras de documentos que contêm os códigos 13414 e 13411
para investigação via Gemini Vision.
"""
import json
import shutil
from pathlib import Path

V5_RESULTS_PATH = Path('output/cpfl_paulista_final/cpfl_v5_full_results.json')
OUTPUT_DIR = Path('output/investigar_codigos_sistema')

CODIGOS_SUSPEITOS = ['13414', '13411']

PROMPT = '''Você é um engenheiro de dados especialista em extração de dados de contratos de energia.

## CONTEXTO
Estou extraindo UCs (Unidades Consumidoras / Números de Instalação) de contratos da CPFL/Raízen.

Meu extrator automático está capturando os números **13414** e **13411** em muitos documentos (17-18% do total).

Preciso que você analise esses PDFs e me diga:

1. **Esses números (13414, 13411) são UCs reais de clientes?**
2. **Ou são códigos de sistema/usina/contrato que aparecem no template?**
3. **Onde exatamente esses números aparecem no documento?** (ex: cabeçalho, rodapé, corpo do contrato)

## O QUE PROCURAR
- Verificar se 13414/13411 aparecem no campo "Nº da Instalação" ou em outro lugar
- Verificar se outros números (UCs reais) também aparecem nesses documentos
- Identificar se esses números são do cliente ou da usina/consórcio

## FORMATO DE RESPOSTA
```json
{
  "conclusao": "SISTEMA" | "UC_REAL" | "MISTO",
  "motivo": "Explicação detalhada",
  "onde_aparecem": "Local no documento onde 13414/13411 aparecem",
  "uc_real_do_cliente": "Se houver outra UC real, qual é",
  "recomendacao": "BLACKLIST" | "MANTER" | "VERIFICAR_MAIS"
}
```

Analise os PDFs anexados e retorne sua conclusão.
'''

def main():
    print("Carregando resultados V5...")
    with open(V5_RESULTS_PATH, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    # Encontrar documentos que contêm os códigos suspeitos
    docs_com_codigo = []
    for r in results:
        if any(codigo in r.get('ucs', []) for codigo in CODIGOS_SUSPEITOS):
            docs_com_codigo.append(r)
    
    print(f"Documentos com códigos suspeitos: {len(docs_com_codigo)}")
    
    # Criar pasta de saída
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Selecionar amostras variadas (primeiros 10 diferentes)
    selected = []
    seen_files = set()
    
    for doc in docs_com_codigo:
        # Pegar nome sem extensão para evitar duplicatas
        base_name = Path(doc['file']).stem[:30]
        if base_name not in seen_files:
            selected.append(doc)
            seen_files.add(base_name)
        if len(selected) >= 10:
            break
    
    print(f"Amostras selecionadas: {len(selected)}")
    
    # Copiar PDFs
    for i, doc in enumerate(selected, 1):
        src = Path(doc['path'])
        if src.exists():
            # Nome curto para evitar problemas
            dst = OUTPUT_DIR / f"{i:02d}_{doc['type']}_{src.stem[:35]}.pdf"
            try:
                shutil.copy2(src, dst)
                print(f"  {i}. {dst.name[:50]}... (UCs: {doc['ucs'][:3]})")
            except Exception as e:
                print(f"  Erro: {e}")
    
    # Salvar prompt
    prompt_file = OUTPUT_DIR / "PROMPT.txt"
    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("INSTRUÇÕES PARA O GEMINI\n")
        f.write("=" * 60 + "\n\n")
        f.write("1. Acesse https://gemini.google.com\n")
        f.write("2. Faça upload de TODOS os PDFs desta pasta (até 10)\n")
        f.write("3. Cole o prompt abaixo e envie\n")
        f.write("4. Copie a resposta para RESPOSTA.txt\n\n")
        f.write("=" * 60 + "\n")
        f.write("PROMPT:\n")
        f.write("=" * 60 + "\n\n")
        f.write(PROMPT)
    
    # Placeholder para resposta
    resposta_file = OUTPUT_DIR / "RESPOSTA.txt"
    with open(resposta_file, 'w', encoding='utf-8') as f:
        f.write("[Cole a resposta do Gemini aqui]\n")
    
    # Salvar info dos documentos
    info_file = OUTPUT_DIR / "DOCUMENTOS_INFO.json"
    with open(info_file, 'w', encoding='utf-8') as f:
        json.dump([{
            'file': d['file'],
            'ucs': d['ucs'],
            'type': d['type']
        } for d in selected], f, ensure_ascii=False, indent=2)
    
    print()
    print("=" * 60)
    print(f"Pasta criada: {OUTPUT_DIR.absolute()}")
    print("Arquivos:")
    print(f"  - {len(selected)} PDFs para análise")
    print(f"  - PROMPT.txt (instruções)")
    print(f"  - RESPOSTA.txt (placeholder)")
    print("=" * 60)

if __name__ == "__main__":
    main()
