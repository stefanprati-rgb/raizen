import json
from pathlib import Path

print("RELATÓRIO DE FALHAS POR ARQUIVO")
print("=" * 60)

for f in sorted(Path('output').rglob('*_relatorio.json')):
    try:
        data = json.load(open(f, encoding='utf-8', errors='ignore'))
        modelo = data.get('modelo', 'Desconhecido')
        
        # Check files in 'revisao' (processed but validation failed)
        revisao = data.get('revisao', [])
        if revisao:
            for item in revisao:
                # item might be dict or string
                nome = item.get('arquivo') if isinstance(item, dict) else str(item)
                erro = item.get('motivo') if isinstance(item, dict) else "Revisão necessária"
                print(f"[REVISÃO] [{modelo}] {nome} | Motivo: {erro}")
                
        # Check files in 'erros' (processing failed)
        erros = data.get('erros', [])
        if erros:
            for item in erros:
                nome = item.get('arquivo') if isinstance(item, dict) else str(item)
                erro = item.get('erro') if isinstance(item, dict) else "Erro desconhecido"
                print(f"[ERRO   ] [{modelo}] {nome} | Erro: {erro}")

    except Exception as e:
        # print(f"Erro ao processar {f}: {e}")
        pass
