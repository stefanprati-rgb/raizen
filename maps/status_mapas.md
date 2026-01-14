# Status: Criação de Novos Mapas de Extração

**Data:** 2026-01-14
**Script:** `scripts/analyze_pdf_gemini.py`
**Modelo:** `gemini-2.5-flash`

## Resumo da Execução
Processo de criação em lote iniciado. O script analisa os PDFs e gera arquivos JSON na pasta `maps/`.

### Mapas Criados
- **LIGHT_11p_v1.json** (Concluído)
- *(Outros mapas em processamento via script de lote)*

### Próximos Passos
- Aguardar conclusão do script de lote (verificar `output/map_creation_batch.txt`).
- Validar cobertura dos novos mapas.

### Logs
- Log individual: `output/debug_cmd.txt`
- Log batch: `output/map_creation_batch.txt`
