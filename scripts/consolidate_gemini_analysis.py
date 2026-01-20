"""
Consolida as respostas do Gemini dos batches de investigação.
"""
import json
import re
from pathlib import Path

BATCH_DIR = Path('output/investigar_gemini_batches')
OUTPUT_FILE = BATCH_DIR / 'analise_consolidada.json'

def extract_json_from_text(text):
    """Extrai o primeiro objeto JSON válido do texto."""
    # Procura por { seguido de "analises"
    match = re.search(r'\{\s*"analises"\s*:', text, re.DOTALL)
    if match:
        start = match.start()
        # Encontra o } final correspondente
        brace_count = 0
        for i, char in enumerate(text[start:]):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    return text[start:start+i+1]
    return None


def main():
    consolidado = []
    
    for batch_dir in sorted(BATCH_DIR.glob('batch_*')):
        resp_file = batch_dir / 'RESPOSTA.txt'
        if not resp_file.exists():
            print(f'{batch_dir.name}: RESPOSTA.txt não encontrado')
            continue
            
        content = resp_file.read_text(encoding='utf-8')
        json_str = extract_json_from_text(content)
        
        if not json_str:
            print(f'{batch_dir.name}: JSON não encontrado no arquivo')
            continue
            
        try:
            data = json.loads(json_str)
            analises = data.get('analises', []) if isinstance(data, dict) else data
            consolidado.extend(analises)
            print(f'{batch_dir.name}: {len(analises)} análises extraídas')
        except json.JSONDecodeError as e:
            print(f'{batch_dir.name}: Erro de JSON - {e}')
    
    # Salvar consolidado
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(consolidado, f, indent=2, ensure_ascii=False)
    
    print(f'\nConsolidado salvo em {OUTPUT_FILE}')
    print(f'Total de arquivos analisados: {len(consolidado)}')
    
    # Estatísticas
    ucs_perdidas = [r for r in consolidado if r.get('deveria_ter_uc') and r.get('ucs_encontradas')]
    validos_negativos = [r for r in consolidado if not r.get('deveria_ter_uc')]
    
    print(f'\n=== ESTATÍSTICAS ===')
    print(f'Documentos com UCs perdidas: {len(ucs_perdidas)}')
    print(f'Válidos negativos (sem UCs esperadas): {len(validos_negativos)}')
    
    if ucs_perdidas:
        print(f'\nExemplos de UCs perdidas:')
        for r in ucs_perdidas[:5]:
            print(f"  - {r.get('arquivo', 'N/A')[:50]}: {r.get('ucs_encontradas', [])}")
        
        # Analisar motivos
        motivos = {}
        for r in ucs_perdidas:
            motivo = r.get('motivo_falha', 'Desconhecido')
            if 'curto' in motivo.lower() or 'dígito' in motivo.lower():
                motivos['UC curta (5-7 dígitos)'] = motivos.get('UC curta (5-7 dígitos)', 0) + 1
            elif 'tabela' in motivo.lower() or 'coluna' in motivo.lower() or 'layout' in motivo.lower():
                motivos['Layout tabular'] = motivos.get('Layout tabular', 0) + 1
            elif 'cnpj' in motivo.lower() or 'erro' in motivo.lower():
                motivos['Erro de preenchimento'] = motivos.get('Erro de preenchimento', 0) + 1
            else:
                motivos['Outro'] = motivos.get('Outro', 0) + 1
        
        print(f'\nMotivos de falha:')
        for motivo, count in sorted(motivos.items(), key=lambda x: -x[1]):
            print(f"  - {motivo}: {count}")

if __name__ == "__main__":
    main()
