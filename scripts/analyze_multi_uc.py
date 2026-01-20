import json
from collections import Counter

with open('output/multi_uc_test.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('=== ANÁLISE DOS RESULTADOS ===')
print(f'Total de PDFs processados: {len(data)}')
success_rate = sum(1 for r in data if r["uc_count"] > 0) / len(data) * 100
print(f'Taxa de sucesso: {success_rate:.1f}%')
total_ucs = sum(r["uc_count"] for r in data)
print(f'Total de UCs extraídas: {total_ucs}')

# Distribuição de UCs por PDF
uc_counts = [r['uc_count'] for r in data]
print()
print('DISTRIBUIÇÃO DE UCs POR PDF:')
for count, freq in sorted(Counter(uc_counts).items()):
    print(f'  {count} UC(s): {freq} PDFs')

# Métodos usados
methods = [r['method'] for r in data]
print()
print('MÉTODOS UTILIZADOS:')
for method, count in Counter(methods).items():
    print(f'  {method}: {count} PDFs')

# PDFs com mais UCs
print()
print('TOP 5 PDFs COM MAIS UCs:')
top5 = sorted(data, key=lambda x: x['uc_count'], reverse=True)[:5]
for r in top5:
    print(f'  {r["file"]}: {r["uc_count"]} UCs')

# Exemplo de UCs múltiplas
multi_uc = [r for r in data if r['uc_count'] > 1]
if multi_uc:
    print()
    print('EXEMPLO DE MÚLTIPLAS UCs:')
    example = multi_uc[0]
    ucs_str = str(example["ucs"][:10]) + "..." if len(example["ucs"]) > 10 else str(example["ucs"])
    print(f'  Arquivo: {example["file"]}')
    print(f'  UCs: {ucs_str}')
