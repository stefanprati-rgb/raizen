# Exemplos de Extração (Do's and Don'ts)

## ❌ Errado (Captura parcial ou suja)
- Padrão: `Instalação:\s*(\d+)`
- Entrada: "Instalação: 12345 (Ativo)"
- Saída Ruim: "12345" (Pode perder o sufixo ou pegar lixo se tiver quebra de linha)

## ✅ Certo (Robusto para OCR)
- Padrão: `Instalação[\s\.:]*([\d\.\-\/]+)`
- Contexto: Permite pontos, traços e ignora ruído de OCR entre o rótulo e o valor.

## Casos Multi-UC (Fortbras)
- Entrada: Tabela visual com colunas.
- Estratégia: Não usar regex de linha única. Usar `re.findall` com padrão de bloco.