# Relatório de Comparação: Extrator Local vs Document AI

## Resumo por Campo

| Campo | Acurácia | Total Amostras | Falhas Extrator | Real Vazio |
|-------|----------|----------------|-----------------|------------|
| num_instalacao | 40.2% | 97 | 0 | 64 |
| num_cliente | 51.5% | 97 | 10 | 34 |
| distribuidora | 3.1% | 97 | 4 | 10 |
| razao_social | 0.0% | 97 | 7 | 8 |
| cnpj | 86.6% | 97 | 0 | 0 |
| data_adesao | 43.3% | 97 | 55 | 42 |
| duracao_meses | 89.7% | 97 | 8 | 12 |
| aviso_previo | 75.3% | 97 | 24 | 73 |
| representante_nome | 44.3% | 97 | 2 | 47 |
| representante_cpf | 6.2% | 97 | 2 | 0 |
| participacao_percentual | 1.0% | 97 | 47 | 1 |

## Amostra de Erros (Top 20)

- **distribuidora** em `SOLAR 3307 - PANIFICADORA E CONFEITARIA SANTA HELENA - 25180375000101.pdf`
  - Esperado: `CPFL`
  - Encontrado: `CPFL PAULISTA`
- **razao_social** em `SOLAR 3307 - PANIFICADORA E CONFEITARIA SANTA HELENA - 25180375000101.pdf`
  - Esperado: `AS`
  - Encontrado: `PANIFICADORA E CONFEITARIA SANTA HELENA`
- **data_adesao** em `SOLAR 3307 - PANIFICADORA E CONFEITARIA SANTA HELENA - 25180375000101.pdf`
  - Esperado: `17/04/2012`
  - Encontrado: ``
- **aviso_previo** em `SOLAR 3307 - PANIFICADORA E CONFEITARIA SANTA HELENA - 25180375000101.pdf`
  - Esperado: `180`
  - Encontrado: ``
- **representante_nome** em `SOLAR 3307 - PANIFICADORA E CONFEITARIA SANTA HELENA - 25180375000101.pdf`
  - Esperado: `NOME`
  - Encontrado: `OSMAR JESUINO DE JESUS`
- **representante_cpf** em `SOLAR 3307 - PANIFICADORA E CONFEITARIA SANTA HELENA - 25180375000101.pdf`
  - Esperado: `090.365.526-80`
  - Encontrado: `350.719.406-64`
- **participacao_percentual** em `SOLAR 3307 - PANIFICADORA E CONFEITARIA SANTA HELENA - 25180375000101.pdf`
  - Esperado: `4000111585.0`
  - Encontrado: `1.32`
- **distribuidora** em `SOLAR 3959 - GBR ADMINISTRACAO E PARTICIPACOES - 26939016000158 - Qualisign.pdf`
  - Esperado: `ENEL`
  - Encontrado: `ENEL GO`
- **razao_social** em `SOLAR 3959 - GBR ADMINISTRACAO E PARTICIPACOES - 26939016000158 - Qualisign.pdf`
  - Esperado: `AS`
  - Encontrado: `GBR ADMINISTRACAO E PARTICIPACOES LTDA`
- **data_adesao** em `SOLAR 3959 - GBR ADMINISTRACAO E PARTICIPACOES - 26939016000158 - Qualisign.pdf`
  - Esperado: `17/04/2012`
  - Encontrado: ``
- **aviso_previo** em `SOLAR 3959 - GBR ADMINISTRACAO E PARTICIPACOES - 26939016000158 - Qualisign.pdf`
  - Esperado: `180`
  - Encontrado: ``
- **representante_nome** em `SOLAR 3959 - GBR ADMINISTRACAO E PARTICIPACOES - 26939016000158 - Qualisign.pdf`
  - Esperado: `NOME`
  - Encontrado: `GABRIEL BRETAS BRANDÃO SOARES`
- **representante_cpf** em `SOLAR 3959 - GBR ADMINISTRACAO E PARTICIPACOES - 26939016000158 - Qualisign.pdf`
  - Esperado: `090.365.526-80`
  - Encontrado: `699.570.701-00`
- **participacao_percentual** em `SOLAR 3959 - GBR ADMINISTRACAO E PARTICIPACOES - 26939016000158 - Qualisign.pdf`
  - Esperado: `10028726926.0`
  - Encontrado: `1.21`
- **num_cliente** em `TERMO_ADESAO_0013176 - CONDOMINIO RESIDENCIAL ANDORRA - Clicksign.pdf`
  - Esperado: `701851859`
  - Encontrado: `02`
- **distribuidora** em `TERMO_ADESAO_0013176 - CONDOMINIO RESIDENCIAL ANDORRA - Clicksign.pdf`
  - Esperado: `CPFL`
  - Encontrado: `SP - CPFL PAULISTA`
- **razao_social** em `TERMO_ADESAO_0013176 - CONDOMINIO RESIDENCIAL ANDORRA - Clicksign.pdf`
  - Esperado: `AS`
  - Encontrado: `CONDOMINIO RESIDENCIAL ANDORRA`
- **data_adesao** em `TERMO_ADESAO_0013176 - CONDOMINIO RESIDENCIAL ANDORRA - Clicksign.pdf`
  - Esperado: `17/04/2012`
  - Encontrado: ``
- **representante_nome** em `TERMO_ADESAO_0013176 - CONDOMINIO RESIDENCIAL ANDORRA - Clicksign.pdf`
  - Esperado: `NOME`
  - Encontrado: `CELMA PERES CARVALHO LEMOS DE MELO`
- **representante_cpf** em `TERMO_ADESAO_0013176 - CONDOMINIO RESIDENCIAL ANDORRA - Clicksign.pdf`
  - Esperado: `342.989.298-84`
  - Encontrado: `004.703.528-50`
