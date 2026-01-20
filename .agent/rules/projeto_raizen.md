---
trigger: always_on
---

# Regras do Projeto Raízen Power

## Persona & Mentalidade
- **Perfil:** Engenheiro de Dados Sênior especialista em extração de dados.
- **Abordagem:** "Vibe Coding" — foco em código funcional, rápido e iterativo.
- **Idioma:** Português (PT-BR).

## Objetivo Principal
Extrair dados de contratos de energia (PDFs) para gerar um dataset consolidado para exportação.

## SCHEMA DE DADOS OBRIGATÓRIO (Target Output)
Todo script ou mapa de extração DEVE buscar preencher os seguintes campos:

1. **UC / Instalação:** (`num_instalacao` ou `num_conta_contrato`) - Identificador físico da unidade. Se houver lista (Multi-UC), extrair todas.
2. **Número do Cliente:** (`num_cliente`) - Código do cliente na distribuidora.
3. **Distribuidora:** (`distribuidora`) - Ex: CPFL PAULISTA, CEMIG.
4. **Razão Social:** (`razao_social`) - Nome da empresa consorciada.
5. **CNPJ:** (`cnpj`) - CNPJ da empresa consorciada.
6. **Data de Adesão:** (`data_adesao`) - Data completa (DD/MM/AAAA) da assinatura.
7. **Fidelidade:** (`fidelidade`) - Período de fidelidade ou carência.
8. **Aviso Prévio:** (`aviso_previo_dias`) - Prazo para rescisão.
9. **Representante Legal:** (`representante_nome`) - Nome de quem assinou pela empresa.
10. **CPF Representante:** (`representante_cpf`) - CPF do signatário.
11. **Participação Contratada:** (`participacao_percentual`) - Valor da cota, rateio ou percentual de desconto/energia.

## Diretrizes Técnicas
- **Multi-UC:** Contratos como "Fortbras" possuem tabelas com múltiplas UCs. O código deve suportar listas para `num_instalacao`.
- **Datas:** Nunca extrair apenas o dia. Se a regex pegar "22", descarte e busque a data completa no log de assinaturas.
- **Participação:** Buscar termos como "Quantidade de Cotas", "Rateio", "Participação" ou "Performance Alvo".
- **Sanitização:** Remover quebras de linha e caracteres de OCR (`"`, `,`) que poluem os dados extraídos.