"""
Script to salvar mapas JSON fornecidos pelo usuário.
"""
import json
import re
from pathlib import Path

# JSON fornecido (coloque aqui exatamente como foi enviado)
JSON_INPUT = r'''[
  {
    "modelo_identificado": "[CEA_EQUATORIAL_08p] AMOSTRA_CEA_EQUATORIAL_08p.pdf",
    "distribuidora_principal": "EQUATORIAL",
    "paginas_analisadas": 8,
    "campos": {
      "sic_ec_cliente": { "encontrado": false, "pagina": 1, "ancora": "N/A", "regex": "r'SIC-EC Cliente[:\\s]*(\\d+)'", "valor_extraido": null, "confianca": "baixa" },
      "razao_social": { "encontrado": true, "pagina": 1, "ancora": "Razão Social:", "regex": "r'Razão Social[:\\s]*([^–\\n]+)'", "valor_extraido": "J C DA C CAMPOS LTDA", "confianca": "alta" },
      "cnpj": { "encontrado": true, "pagina": 1, "ancora": "CNPJ nº", "regex": "r'(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'", "valor_extraido": "23.511.995/0001-50", "confianca": "alta" },
      "nire": { "encontrado": false, "pagina": 1, "ancora": "N/A", "regex": "r'NIRE[:\\s]*(\\d+)'", "valor_extraido": null, "confianca": "baixa" },
      "endereco": { "encontrado": true, "pagina": 1, "ancora": "Endereço:", "regex": "r'Endereço[:\\s]*([\\s\\S]+?)(?=\\s*Fazer|$)'", "valor_extraido": "AV MONSENHOR MARIO PESSOA SN, FEIRA DE SANTANA, Bahia, CEP 44001-775", "confianca": "alta" },
      "email": { "encontrado": true, "pagina": 1, "ancora": "E-mail:", "regex": "r'E-mail[:\\s]*([\\w.-]+@[\\w.-]+\\.\\w+)'", "valor_extraido": "jafehcampos@gmail.com", "confianca": "alta" },
      "representante_nome": { "encontrado": true, "pagina": 1, "ancora": "Nome:", "regex": "r'Nome[:\\s]*([^–\\n]+)'", "valor_extraido": "JAFEH CORREIA DA COSTA CAMPOS", "confianca": "alta" },
      "consorcio_nome": { "encontrado": true, "pagina": 1, "ancora": "CONSÓRCIO", "regex": "r'Razão Social[:\\s]*(Consórcio\\s+[^–\\n]+)'", "valor_extraido": "Consórcio RZ Pernambuco", "confianca": "alta" },
      "consorcio_cnpj": { "encontrado": true, "pagina": 1, "ancora": "CNPJ nº", "regex": "r'Consórcio.*?CNPJ\\s*nº\\s*(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'", "valor_extraido": "35.299.820/0001-00", "confianca": "alta" },
      "distribuidora": { "encontrado": true, "pagina": 1, "ancora": "Arquivo", "regex": "r'([A-Z]+_EQUATORIAL)'", "valor_extraido": "CEA_EQUATORIAL", "confianca": "media" },
      "num_instalacao": { "encontrado": false, "pagina": 2, "ancora": "N/A", "regex": "r'Instalação.*?[:\\s]*(\\d+)'", "valor_extraido": null, "confianca": "baixa" },
      "num_cliente": { "encontrado": false, "pagina": 2, "ancora": "N/A", "regex": "r'Cliente[:\\s]*(\\d+)'", "valor_extraido": null, "confianca": "baixa" },
      "participacao_percentual": { "encontrado": false, "pagina": 2, "ancora": "N/A", "regex": "r'(\\d+,?\\d*%)'", "valor_extraido": null, "confianca": "baixa" },
      "duracao_meses": { "encontrado": false, "pagina": 2, "ancora": "N/A", "regex": "r'(\\d+)\\s*meses'", "valor_extraido": null, "confianca": "baixa" },
      "data_adesao": { "encontrado": true, "pagina": 8, "ancora": "Log gerado em", "regex": "r'(\\d{1,2}\\s*de\\s*\\w+\\s*de\\s*\\d{4})'", "valor_extraido": "10 de dezembro de 2023", "confianca": "alta" }
    },
    "alertas": ["Campos de instalação e participação não localizados nas primeiras páginas de texto extraível."]
  },
  {
    "modelo_identificado": "[CEB-DIS_13p] AMOSTRA_CEB-DIS_13p.pdf",
    "distribuidora_principal": "CEB-DIS",
    "paginas_analisadas": 13,
    "campos": {
      "sic_ec_cliente": { "encontrado": false, "pagina": 1, "ancora": "N/A", "regex": "r'SIC-EC Cliente[:\\s]*(\\d+)'", "valor_extraido": null, "confianca": "baixa" },
      "razao_social": { "encontrado": true, "pagina": 1, "ancora": "Razão Social:", "regex": "r'Razão Social[:\\s]*([^\\n]+)'", "valor_extraido": "LEM LANCHONETE LTDA", "confianca": "alta" },
      "cnpj": { "encontrado": true, "pagina": 1, "ancora": "CNPJ:", "regex": "r'CNPJ[:\\s]*(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'", "valor_extraido": "33.469.174/0001-57", "confianca": "alta" },
      "nire": { "encontrado": true, "pagina": 1, "ancora": "NIRE:", "regex": "r'NIRE[:\\s]*(\\d+)'", "valor_extraido": "53202232101", "confianca": "alta" },
      "endereco": { "encontrado": true, "pagina": 1, "ancora": "Endereço:", "regex": "r'Endereço[:\\s]*([\\s\\S]+?)(?=\\s*DADOS|$)'", "valor_extraido": "Q QNN 31 AREA ESPECIAL F LOJA, 01, CEILANDIA NORTE (CEILANDIA), BRASILIA/DF, CEP:72.225-310", "confianca": "alta" },
      "email": { "encontrado": true, "pagina": 1, "ancora": "E-mail:", "regex": "r'E-mail[:\\s]*([\\w.-]+@[\\w.-]+\\.\\w+)'", "valor_extraido": "luizfillipe.cunha@gmail.com", "confianca": "alta" },
      "representante_nome": { "encontrado": true, "pagina": 1, "ancora": "Nome:", "regex": "r'Nome[:\\s]*([^\\n]+)'", "valor_extraido": "LUIZ FILLIPE CUNHA SILVA", "confianca": "alta" },
      "consorcio_nome": { "encontrado": true, "pagina": 1, "ancora": "membro do", "regex": "r'membro do\\s*(Consórcio\\s+[^,]+)'", "valor_extraido": "Consórcio RZ Distrito Federal", "confianca": "alta" },
      "consorcio_cnpj": { "encontrado": true, "pagina": 2, "ancora": "CNPJ/MF sob o nº", "regex": "r'CNPJ\\/MF\\s*sob\\s*o\\s*nº\\s*(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'", "valor_extraido": "35.339.789/0001-94", "confianca": "alta" },
      "distribuidora": { "encontrado": true, "pagina": 1, "ancora": "Distribuidora:", "regex": "r'Distribuidora[:\\s]*(.+)'", "valor_extraido": "CEB-DIS", "confianca": "alta" },
      "num_instalacao": { "encontrado": true, "pagina": 1, "ancora": "Instalação", "regex": "r'Instalação.*?\\n(\\d+)'", "valor_extraido": "651187", "confianca": "alta" },
      "num_cliente": { "encontrado": true, "pagina": 1, "ancora": "Nº do Cliente:", "regex": "r'Cliente[:\\s]*(\\d+)'", "valor_extraido": "02445113", "confianca": "alta" },
      "participacao_percentual": { "encontrado": true, "pagina": 1, "ancora": "Rateio:", "regex": "r'(\\d+,?\\d*%)'", "valor_extraido": "0,31%", "confianca": "alta" },
      "duracao_meses": { "encontrado": true, "pagina": 1, "ancora": "Vigência Inicial:", "regex": "r'(\\d+)\\s*meses'", "valor_extraido": "60", "confianca": "alta" },
      "data_adesao": { "encontrado": true, "pagina": 12, "ancora": "Log gerado em", "regex": "r'(\\d{1,2}\\s*de\\s*\\w+\\s*de\\s*\\d{4})'", "valor_extraido": "24 de fevereiro de 2022", "confianca": "alta" }
    }
  },
  {
    "modelo_identificado": "[CELESC-DIS_09p] AMOSTRA_CELESC-DIS_09p.pdf",
    "distribuidora_principal": "CPFL PAULISTA",
    "paginas_analisadas": 9,
    "campos": {
      "sic_ec_cliente": { "encontrado": false, "pagina": 1, "regex": "r'SIC-EC Cliente[:\\s]*(\\d+)'", "valor_extraido": null, "confianca": "baixa" },
      "razao_social": { "encontrado": true, "pagina": 1, "ancora": "Razão Social:", "regex": "r'Razão Social[:\\s]*([^–\\n]+)'", "valor_extraido": "HIPERGRAF IND GRAFICA COM LTDA", "confianca": "alta" },
      "cnpj": { "encontrado": true, "pagina": 1, "ancora": "CNPJ nº", "regex": "r'(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'", "valor_extraido": "53.263.828/0001-07", "confianca": "alta" },
      "nire": { "encontrado": false, "pagina": 1, "regex": "r'NIRE[:\\s]*(\\d+)'", "valor_extraido": null, "confianca": "baixa" },
      "endereco": { "encontrado": true, "pagina": 1, "ancora": "Endereço:", "regex": "r'Endereço[:\\s]*([\\s\\S]+?)(?=\\s*Fazer|$)'", "valor_extraido": "Rua Francisca Alves Pereira Borges, 426, Vila Boca Rica, Gráfica, Barra Bonita, São Paulo, CEP 17347-302", "confianca": "alta" },
      "email": { "encontrado": true, "pagina": 1, "ancora": "E-mail:", "regex": "r'E-mail[:\\s]*([\\w.-]+@[\\w.-]+\\.\\w+)'", "valor_extraido": "hipergraf@gmail.com", "confianca": "alta" },
      "representante_nome": { "encontrado": false, "pagina": 1, "regex": "r'Nome[:\\s]*([^–\\n]+)'", "valor_extraido": null, "confianca": "baixa" },
      "consorcio_nome": { "encontrado": true, "pagina": 1, "ancora": "CONSÓRCIO", "regex": "r'Razão Social[:\\s]*(Consórcio\\s+[^–\\n]+)'", "valor_extraido": "Consórcio RZ São Paulo", "confianca": "alta" },
      "consorcio_cnpj": { "encontrado": true, "pagina": 1, "ancora": "CNPJ nº", "regex": "r'RZ\\s+São\\s+Paulo\\s+–\\s+CNPJ\\s+nº\\s+(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'", "valor_extraido": "35.300.150/0001-03", "confianca": "alta" },
      "distribuidora": { "encontrado": false, "pagina": 2, "regex": "r'Distribuidora[:\\s]*(.+)'", "valor_extraido": null, "confianca": "baixa" },
      "num_instalacao": { "encontrado": false, "pagina": 2, "regex": "r'Instalação.*?[:\\s]*(\\d+)'", "valor_extraido": null, "confianca": "baixa" },
      "num_cliente": { "encontrado": false, "pagina": 2, "regex": "r'Cliente[:\\s]*(\\d+)'", "valor_extraido": null, "confianca": "baixa" },
      "participacao_percentual": { "encontrado": false, "pagina": 2, "regex": "r'(\\d+,?\\d*%)'", "valor_extraido": null, "confianca": "baixa" },
      "duracao_meses": { "encontrado": false, "pagina": 2, "regex": "r'(\\d+)\\s*meses'", "valor_extraido": null, "confianca": "baixa" },
      "data_adesao": { "encontrado": true, "pagina": 9, "ancora": "Log gerado em", "regex": "r'(\\d{1,2}\\s*de\\s*\\w+\\s*de\\s*\\d{4})'", "valor_extraido": "15 de fevereiro de 2024", "confianca": "alta" }
    },
    "alertas": ["Localidade Barra Bonita indica CPFL Paulista, apesar do nome do arquivo citar CELESC."]
  },
  {
    "modelo_identificado": "[CELESC-DIS_10p] AMOSTRA_CELESC-DIS_10p.pdf",
    "distribuidora_principal": "CPFL PAULISTA",
    "paginas_analisadas": 10,
    "campos": {
      "sic_ec_cliente": { "encontrado": false, "pagina": 1, "regex": "r'SIC-EC Cliente[:\\s]*(\\d+)'", "valor_extraido": null, "confianca": "baixa" },
      "razao_social": { "encontrado": true, "pagina": 1, "ancora": "Razão Social:", "regex": "r'Razão Social[:\\s]*([^–\\n]+)'", "valor_extraido": "FERNANDES COM DE CALCADOS LTDA", "confianca": "alta" },
      "cnpj": { "encontrado": true, "pagina": 1, "ancora": "CNPJ nº", "regex": "r'(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'", "valor_extraido": "26.060.241/0001-10", "confianca": "alta" },
      "nire": { "encontrado": false, "pagina": 1, "regex": "r'NIRE[:\\s]*(\\d+)'", "valor_extraido": null, "confianca": "baixa" },
      "endereco": { "encontrado": true, "pagina": 1, "ancora": "Endereço:", "regex": "r'Endereço[:\\s]*([^\\n]+)'", "valor_extraido": "RUA SALVADOR DE TOLEDO 929 - BARRA BONITA-SP", "confianca": "alta" },
      "email": { "encontrado": true, "pagina": 1, "ancora": "E-mail:", "regex": "r'E-mail[:\\s]*([\\w.-]+@[\\w.-]+\\.\\w+)'", "valor_extraido": "joel@lojasilva.com.br", "confianca": "alta" },
      "representante_nome": { "encontrado": false, "pagina": 1, "regex": "r'Nome[:\\s]*([^–\\n]+)'", "valor_extraido": null, "confianca": "baixa" },
      "consorcio_nome": { "encontrado": true, "pagina": 1, "ancora": "Razão Social:", "regex": "r'Razão Social[:\\s]*(Consórcio\\s+[^–\\n]+)'", "valor_extraido": "Consórcio RZ São Paulo", "confianca": "alta" },
      "consorcio_cnpj": { "encontrado": true, "pagina": 1, "ancora": "CNPJ nº", "regex": "r'São\\s+Paulo\\s+–\\s+CNPJ\\s+nº\\s+(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'", "valor_extraido": "35.300.150/0001-03", "confianca": "alta" },
      "distribuidora": { "encontrado": false, "pagina": 2, "regex": "r'Distribuidora[:\\s]*(.+)'", "valor_extraido": null, "confianca": "baixa" },
      "num_instalacao": { "encontrado": false, "pagina": 2, "regex": "r'Instalação.*?[:\\s]*(\\d+)'", "valor_extraido": null, "confianca": "baixa" },
      "num_cliente": { "encontrado": false, "pagina": 2, "regex": "r'Cliente[:\\s]*(\\d+)'", "valor_extraido": null, "confianca": "baixa" },
      "participacao_percentual": { "encontrado": false, "pagina": 2, "regex": "r'(\\d+,?\\d*%)'", "valor_extraido": null, "confianca": "baixa" },
      "duracao_meses": { "encontrado": false, "pagina": 2, "regex": "r'(\\d+)\\s*meses'", "valor_extraido": null, "confianca": "baixa" },
      "data_adesao": { "encontrado": true, "pagina": 10, "ancora": "Log gerado em", "regex": "r'(\\d{1,2}\\s*de\\s*\\w+\\s*de\\s*\\d{4})'", "valor_extraido": "12 de setembro de 2023", "confianca": "alta" }
    }
  },
  {
    "modelo_identificado": "[CELETRO_10p] AMOSTRA_CELETRO_10p.pdf",
    "distribuidora_principal": "SOLUÇÃO",
    "paginas_analisadas": 10,
    "campos": {
      "sic_ec_cliente": { "encontrado": true, "pagina": 1, "ancora": "Cliente:", "regex": "r'SIC-EC Cliente[:\\s]*(\\d+)'", "valor_extraido": "8949", "confianca": "alta" },
      "razao_social": { "encontrado": true, "pagina": 1, "ancora": "celebrado entre:", "regex": "r'e\\s*\\n*\\s*([A-Z\\sÁÉÍÓÚ]{5,})\\s+sociedade'", "valor_extraido": "RAÍZEN COMBUSTÍVEIS S A", "confianca": "alta" },
      "cnpj": { "encontrado": true, "pagina": 1, "ancora": "CNPJ sob o nº", "regex": "r'CNPJ\\s*sob\\s*o\\s*nº\\s*(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'", "valor_extraido": "33.453.598/0001-23", "confianca": "alta" },
      "nire": { "encontrado": false, "pagina": 1, "regex": "r'NIRE[:\\s]*(\\d+)'", "valor_extraido": null, "confianca": "baixa" },
      "endereco": { "encontrado": true, "pagina": 1, "ancora": "sede na", "regex": "r'sede\\s*na\\s*([\\s\\S]+?CEP:\\s*\\d{2}\\.\\d{3}-\\d{3})'", "valor_extraido": "AV ALMIRANTE BARROSO, 81 - 36 ANDAR, SALA 36A104, CENTRO, RIO DE JANEIRO/RJ, CEP: 20.030-004", "confianca": "alta" },
      "email": { "encontrado": false, "pagina": 1, "regex": "r'E-mail[:\\s]*([\\w.-]+@[\\w.-]+\\.\\w+)'", "valor_extraido": null, "confianca": "baixa" },
      "representante_nome": { "encontrado": true, "pagina": 10, "ancora": "Representante", "regex": "r'Representante\\s*\\n?([^\\n\\d]+)'", "valor_extraido": "Luisa Batista Zefredo de Oliveira", "confianca": "alta" },
      "consorcio_nome": { "encontrado": true, "pagina": 1, "ancora": "Consórcio", "regex": "r'(CONSÓRCIO\\s+SOLução)'", "valor_extraido": "CONSÓRCIO SOLução", "confianca": "alta" },
      "consorcio_cnpj": { "encontrado": true, "pagina": 1, "ancora": "CNPJ/MF sob o nº", "regex": "r'CNPJ\\/MF\\s*sob\\s*o\\s*nº\\s*(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'", "valor_extraido": "32.770.493/0001-35", "confianca": "alta" },
      "distribuidora": { "encontrado": false, "pagina": 1, "regex": "r'Distribuidora[:\\s]*(.+)'", "valor_extraido": null, "confianca": "baixa" },
      "num_instalacao": { "encontrado": false, "pagina": 1, "regex": "r'Instalação.*?[:\\s]*(\\d+)'", "valor_extraido": null, "confianca": "baixa" },
      "num_cliente": { "encontrado": false, "pagina": 1, "regex": "r'Cliente[:\\s]*(\\d+)'", "valor_extraido": null, "confianca": "baixa" },
      "participacao_percentual": { "encontrado": true, "pagina": 1, "ancora": "Objeto:", "regex": "r'Objeto[:\\s]*(\\d+,?\\d*%)'", "valor_extraido": "5,701%", "confianca": "alta" },
      "duracao_meses": { "encontrado": true, "pagina": 1, "ancora": "Período de Adesão:", "regex": "r'(\\d+)\\s*meses'", "valor_extraido": "60", "confianca": "alta" },
      "data_adesao": { "encontrado": true, "pagina": 10, "ancora": "Assinado em", "regex": "r'(\\d{2}\\/\\d{2}\\/\\d{4})'", "valor_extraido": "08/06/2021", "confianca": "alta" }
    }
  },
  {
    "modelo_identificado": "[CELPE_05p] AMOSTRA_CELPE_05p.pdf",
    "distribuidora_principal": "CELPE",
    "paginas_analisadas": 5,
    "campos": {
      "sic_ec_cliente": { "encontrado": true, "pagina": 1, "ancora": "Cliente:", "regex": "r'SIC-EC Cliente[:\\s]*(\\d+)'", "valor_extraido": "7993", "confianca": "alta" },
      "razao_social": { "encontrado": true, "pagina": 1, "ancora": "Razão Social:", "regex": "r'Razão Social[:\\s]*([^\\n]+)'", "valor_extraido": "ALBUQUERQUE PNEUS LTDA", "confianca": "alta" },
      "cnpj": { "encontrado": true, "pagina": 1, "ancora": "CNPJ:", "regex": "r'CNPJ[:\\s]*(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'", "valor_extraido": "11.117.785/0005-27", "confianca": "alta" },
      "nire": { "encontrado": true, "pagina": 1, "ancora": "NIRE:", "regex": "r'NIRE[:\\s]*(\\d+)'", "valor_extraido": "26900238901", "confianca": "alta" },
      "endereco": { "encontrado": true, "pagina": 1, "ancora": "Endereço:", "regex": "r'Endereço[:\\s]*([^\\n]+CEP\\s*\\d{2}\\.\\d{3}-\\d{3})'", "valor_extraido": "ROD PE 75, S/N, KM 4.5, CENTRO, GOIANA/PE - CEP 55.900-000", "confianca": "alta" },
      "email": { "encontrado": true, "pagina": 1, "ancora": "E-MAIL:", "regex": "r'E-MAIL[:\\s]*([\\w.-]+@[\\w.-]+\\.\\w+)'", "valor_extraido": "junior@albuquerquepneus.com.br", "confianca": "alta" },
      "representante_nome": { "encontrado": true, "pagina": 1, "ancora": "Legal:", "regex": "r'Legal[:\\s]*([^\\n]+)'", "valor_extraido": "ANTONIO ALVES DE ALBUQUERQUE JUNIOR", "confianca": "alta" },
      "consorcio_nome": { "encontrado": true, "pagina": 1, "ancora": "membro do", "regex": "r'Consórcio\\s+([A-Z\\s]+PERNAMBUCO)'", "valor_extraido": "CONSORCIO RZ PERNAMBUCO", "confianca": "alta" },
      "consorcio_cnpj": { "encontrado": true, "pagina": 1, "ancora": "CNPJ\/MF sob o nº", "regex": "r'CNPJ\/MF\\s*sob\\s*o\\s*nº\\s*(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'", "valor_extraido": "35.299.820/0001-00", "confianca": "alta" },
      "distribuidora": { "encontrado": false, "pagina": 2, "regex": "r'Distribuidora[:\\s]*(.+)'", "valor_extraido": null, "confianca": "baixa" },
      "num_instalacao": { "encontrado": false, "pagina": 2, "regex": "r'Instalação.*?[:\\s]*(\\d+)'", "valor_extraido": null, "confianca": "baixa" },
      "num_cliente": { "encontrado": false, "pagina": 2, "regex": "r'Cliente[:\\s]*(\\d+)'", "valor_extraido": null, "confianca": "baixa" },
      "participacao_percentual": { "encontrado": false, "pagina": 2, "regex": "r'(\\d+,?\\d*%)'", "valor_extraido": null, "confianca": "baixa" },
      "duracao_meses": { "encontrado": false, "pagina": 2, "regex": "r'(\\d+)\\s*meses'", "valor_extraido": null, "confianca": "baixa" },
      "data_adesao": { "encontrado": true, "pagina": 4, "ancora": "Assinado em", "regex": "r'(\\d{2}\\/\\d{2}\\/\\d{4})'", "valor_extraido": "15/02/2021", "confianca": "alta" }
    }
  },
  {
    "modelo_identificado": "[CELPE_11p] AMOSTRA_CELPE_11p.pdf",
    "distribuidora_principal": "CELPE",
    "paginas_analisadas": 11,
    "campos": {
      "sic_ec_cliente": { "encontrado": false, "pagina": 1, "regex": "r'SIC-EC Cliente[:\\s]*(\\d+)'", "valor_extraido": null, "confianca": "baixa" },
      "razao_social": { "encontrado": true, "pagina": 1, "ancora": "Razão Social:", "regex": "r'Razão Social[:\\s]*([^\\n]+)'", "valor_extraido": "POSTO MARACAJA LTDA", "confianca": "alta" },
      "cnpj": { "encontrado": true, "pagina": 1, "ancora": "CNPJ:", "regex": "r'CNPJ[:\\s]*(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'", "valor_extraido": "24.336.166/0001-41", "confianca": "alta" },
      "nire": { "encontrado": true, "pagina": 1, "ancora": "NIRE:", "regex": "r'NIRE[:\\s]*(\\d+)'", "valor_extraido": "26200557574", "confianca": "alta" },
      "end": { "encontrado": true, "pagina": 1, "ancora": "Endereço:", "regex": "r'Endereço[:\\s]*([\\s\\S]+?)(?=\\s*DADOS|$)'", "valor_extraido": "Rodovia PE 90, s/nº, complemento KM 63,3, Riacho da Onça, Surubim, CEP 55.750-000, UF PE", "confianca": "alta" },
      "email": { "encontrado": true, "pagina": 1, "ancora": "E-mail:", "regex": "r'E-mail[:\\s]*([\\w.-]+@[\\w.-]+\\.\\w+)'", "valor_extraido": "zhbbarros\u00e9@hotmail.com", "confianca": "alta" },
      "representante_nome": { "encontrado": true, "pagina": 1, "ancora": "Nome:", "regex": "r'Nome[:\\s]*([^\\n]+)'", "valor_extraido": "JOSE HELIO BARBOSA BARROS", "confianca": "alta" },
      "consorcio_nome": { "encontrado": true, "pagina": 1, "ancora": "membro do", "regex": "r'Consórcio\\s+([^,]+)'", "valor_extraido": "RZ Pernambuco", "confianca": "alta" },
      "consorcio_cnpj": { "encontrado": true, "pagina": 1, "ancora": "CNPJ\/MF sob o nº", "regex": "r'CNPJ\/MF\\s*sob\\s*o\\s*nº\\s*(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'", "valor_extraido": "35.299.820/0001-00", "confianca": "alta" },
      "distribuidora": { "encontrado": true, "pagina": 1, "ancora": "Distribuidora:", "regex": "r'Distribuidora[:\\s]*(.+)'", "valor_extraido": "PE - CELPE", "confianca": "alta" },
      "num_instalacao": { "encontrado": true, "pagina": 1, "ancora": "Instalação", "regex": "r'Instalação.*?\\n(\\d+)'", "valor_extraido": "8043941", "confianca": "alta" },
      "num_cliente": { "encontrado": true, "pagina": 1, "ancora": "Nº do Cliente:", "regex": "r'Cliente[:\\s]*(\\d+)'", "valor_extraido": "2001127785", "confianca": "alta" },
      "participacao_percentual": { "encontrado": true, "pagina": 1, "ancora": "Rateio:", "regex": "r'(\\d+,?\\d*%)'", "valor_extraido": "1,16", "confianca": "alta" },
      "duracao_meses": { "encontrado": true, "pagina": 1, "ancora": "Vigência Inicial:", "regex": "r'(\\d+)\\s*meses'", "valor_extraido": "60", "confianca": "alta" },
      "data_adesao": { "encontrado": true, "pagina": 10, "ancora": "Log gerado em", "regex": "r'(\\d{1,2}\\s*de\\s*\\w+\\s*de\\s*\\d{4})'", "valor_extraido": "18 de fevereiro de 2022", "confianca": "alta" }
    }
  },
  {
    "modelo_identificado": "[CELPE_12p] AMOSTRA_CELPE_12p.pdf",
    "distribuidora_principal": "CELPE",
    "paginas_analisadas": 12,
    "campos": {
      "sic_ec_cliente": { "encontrado": false, "pagina": 1, "regex": "r'SIC-EC Cliente[:\\s]*(\\d+)'", "valor_extraido": null, "confianca": "baixa" },
      "razao_social": { "encontrado": true, "pagina": 1, "ancora": "Razão Social:", "regex": "r'Razão Social[:\\s]*([^\\n]+)'", "valor_extraido": "HNK BR INDUSTRIA DE BEBIDAS LTDA", "confianca": "alta" },
      "cnpj": { "encontrado": true, "pagina": 1, "ancora": "CNPJ:", "regex": "r'CNPJ[:\\s]*(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'", "valor_extraido": "50.221.019/0063-39", "confianca": "alta" },
      "nire": { "encontrado": true, "pagina": 1, "ancora": "NIRE:", "regex": "r'NIRE[:\\s]*(\\d+)'", "valor_extraido": "26900648467", "confianca": "alta" },
      "endereco": { "encontrado": true, "pagina": 1, "ancora": "Endereço:", "regex": "r'Endereço[:\\s]*([\\s\\S]+?)(?=\\s*DADOS|$)'", "valor_extraido": "RUA NOSSA SENHORA DE FATIMA, 244, JARDIM JORDAO, JABOATAO DOS GUARARAPES/PE, CEP: 54.320-250", "confianca": "alta" },
      "email": { "encontrado": true, "pagina": 1, "ancora": "E-mail:", "regex": "r'E-mail[:\\s]*([\\w.-]+@[\\w.-]+\\.\\w+)'", "valor_extraido": "jose.oliveira@heineken.com.br", "confianca": "alta" },
      "representante_nome": { "encontrado": true, "pagina": 1, "ancora": "Nome:", "regex": "r'Nome[:\\s]*([^\\n]+)'", "valor_extraido": "JOSE ROBERTO APARECIDO DE OLIVEIRA", "confianca": "alta" },
      "consorcio_nome": { "encontrado": true, "pagina": 2, "ancora": "membro do", "regex": "r'Consórcio\\s+([^,]+)'", "valor_extraido": "RZ Pernambuco", "confianca": "alta" },
      "consorcio_cnpj": { "encontrado": true, "pagina": 2, "ancora": "CNPJ\/MF sob o nº", "regex": "r'CNPJ\/MF\\s*sob\\s*o\\s*nº\\s*(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'", "valor_extraido": "35.299.820/0001-00", "confianca": "alta" },
      "distribuidora": { "encontrado": true, "pagina": 1, "ancora": "Distribuidora:", "regex": "r'Distribuidora[:\\s]*(.+)'", "valor_extraido": "CELPE", "confianca": "alta" },
      "num_instalacao": { "encontrado": true, "pagina": 1, "ancora": "Instalação", "regex": "r'Instalação.*?\\n(\\d+)'", "valor_extraido": "7015592472", "confianca": "alta" },
      "num_cliente": { "encontrado": true, "pagina": 1, "ancora": "Nº do Cliente:", "regex": "r'Cliente[:\\s]*(\\d+)'", "valor_extraido": "2013163580", "confianca": "alta" },
      "participacao_percentual": { "encontrado": true, "pagina": 1, "ancora": "Rateio:", "regex": "r'(\\d+,?\\d*%)'", "valor_extraido": "2,14%", "confianca": "alta" },
      "duracao_meses": { "encontrado": true, "pagina": 1, "ancora": "Vigência Inicial:", "regex": "r'(\\d+)\\s*\\(onze\\)\\s*anos'", "valor_extraido": "132", "confianca": "alta" },
      "data_adesao": { "encontrado": true, "pagina": 12, "ancora": "Assinado em", "regex": "r'(\\d{2}\\/\\d{2}\\/\\d{4})'", "valor_extraido": "09/11/2021", "confianca": "alta" }
    }
  },
  {
    "modelo_identificado": "[CELPE_13p] AMOSTRA_CELPE_13p.pdf",
    "distribuidora_principal": "CELPE",
    "paginas_analisadas": 13,
    "campos": {
      "sic_ec_cliente": { "encontrado": false, "pagina": 1, "regex": "r'SIC-EC Cliente[:\\s]*(\\d+)'", "valor_extraido": null, "confianca": "baixa" },
      "razao_social": { "encontrado": true, "pagina": 1, "ancora": "Razão Social:", "regex": "r'Razão Social[:\\s]*([^\\n]+)'", "valor_extraido": "A.C.J. REFEICOES DELIVERY LTDA", "confianca": "alta" },
      "cnpj": { "encontrado": true, "pagina": 1, "ancora": "CNPJ:", "regex": "r'CNPJ[:\\s]*(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'", "valor_extraido": "36.075.686/0001-27", "confianca": "alta" },
      "nire": { "encontrado": true, "pagina": 1, "ancora": "NIRE:", "regex": "r'NIRE[:\\s]*(\\d+)'", "valor_extraido": "26202537554", "confianca": "alta" },
      "endereco": { "encontrado": true, "pagina": 1, "ancora": "Endereço:", "regex": "r'Endereço[:\\s]*([\\s\\S]+?)(?=\\s*DADOS|$)'", "valor_extraido": "RUA SAO SEBASTIAO, 625 - LJ 01, PIEDADE, JABOATAO DOS GUARARAPES/PE, CEP: 54.410-500", "confianca": "alta" },
      "email": { "encontrado": true, "pagina": 1, "ancora": "E-mail:", "regex": "r'E-mail[:\\s]*([\\w.-]+@[\\w.-]+\\.\\w+)'", "valor_extraido": "n1chickenjaboatao@gmail.com", "confianca": "alta" },
      "representante_nome": { "encontrado": true, "pagina": 1, "ancora": "Nome:", "regex": "r'Nome[:\\s]*([^\\n]+)'", "valor_extraido": "EDUARDO RODRIGUES CASTRO", "confianca": "alta" },
      "consorcio_nome": { "encontrado": true, "pagina": 2, "ancora": "membro do", "regex": "r'Consórcio\\s+([^,]+)'", "valor_extraido": "RZ PERNAMBUCO", "confianca": "alta" },
      "consorcio_cnpj": { "encontrado": true, "pagina": 2, "ancora": "CNPJ\/MF sob o nº", "regex": "r'CNPJ\/MF\\s*sob\\s*o\\s*nº\\s*(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'", "valor_extraido": "35.299.820/0001-00", "confianca": "alta" },
      "distribuidora": { "encontrado": true, "pagina": 1, "ancora": "Distribuidora:", "regex": "r'Distribuidora[:\\s]*(.+)'", "valor_extraido": "CELPE", "confianca": "alta" },
      "num_instalacao": { "encontrado": true, "pagina": 1, "ancora": "Instalação", "regex": "r'Instalação.*?\\n(\\d+)'", "valor_extraido": "6895782", "confianca": "alta" },
      "num_cliente": { "encontrado": true, "pagina": 1, "ancora": "Nº do Cliente:", "regex": "r'Cliente[:\\s]*(\\d+)'", "valor_extraido": "2017032861", "confianca": "alta" },
      "participacao_percentual": { "encontrado": true, "pagina": 1, "ancora": "Rateio:", "regex": "r'(\\d+,?\\d*%)'", "valor_extraido": "0,31%", "confianca": "alta" },
      "duracao_meses": { "encontrado": true, "pagina": 1, "ancora": "Vigência Inicial:", "regex": "r'(\\d+)\\s*meses'", "valor_extraido": "60", "confianca": "alta" },
      "data_adesao": { "encontrado": true, "pagina": 12, "ancora": "Assinado em", "regex": "r'(\\d{2}\\/\\d{2}\\/\\d{4})'", "valor_extraido": "21/12/2021", "confianca": "alta" }
    }
  },
  {
    "modelo_identificado": "[CEMIG-D_04p] AMOSTRA_CEMIG-D_04p.pdf",
    "distribuidora_principal": "CEMIG-D",
    "paginas_analisadas": 4,
    "campos": {
      "sic_ec_cliente": { "encontrado": false, "pagina": 1, "regex": "r'SIC-EC Cliente[:\\s]*(\\d+)'", "valor_extraido": null, "confianca": "baixa" },
      "razao_social": { "encontrado": true, "pagina": 1, "ancora": "II – CONSORCIADA:", "regex": "r'Razão Social[:\\s]*([^\\n]+)'", "valor_extraido": "THE BRIDGE LTDA", "confianca": "alta" },
      "cnpj": { "encontrado": true, "pagina": 1, "ancora": "CNPJ/MF nº:", "regex": "r'CNPJ\\/MF\\s*nº[:\\s]*(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'", "valor_extraido": "30.877.197/0001-02", "confianca": "alta" },
      "nire": { "encontrado": false, "pagina": 1, "regex": "r'NIRE[:\\s]*(\\d+)'", "valor_extraido": null, "confianca": "baixa" },
      "endereco": { "encontrado": true, "pagina": 1, "ancora": "Sede:", "regex": "r'Sede[:\\s]*([^\\n]+CEP:\\d{5}-\\d{3})'", "valor_extraido": "RUA DOS TIMBIRAS 834 -BELO HORIZONTE-MG – CEP:30140-068", "confianca": "alta" },
      "email": { "encontrado": true, "pagina": 2, "ancora": "E-mail", "regex": "r'([\\w.-]+@[\\w.-]+\\.\\w+)'", "valor_extraido": "thebridgepub.contato@gmail.com", "confianca": "alta" },
      "representante_nome": { "encontrado": true, "pagina": 1, "ancora": "assinado:", "regex": "r'assinado:\\s*\\n?([^,]+)'", "valor_extraido": "Rodrigo Corrêa Fernandes Boson", "confianca": "alta" },
      "consorcio_nome": { "encontrado": true, "pagina": 1, "ancora": "CONSORCIADA LÍDER:", "regex": "r'Razão Social[:\\s]*(RAÍZEN GD LTDA)'", "valor_extraido": "RAÍZEN GD LTDA", "confianca": "alta" },
      "consorcio_cnpj": { "encontrado": true, "pagina": 1, "ancora": "CNPJ/MF nº:", "regex": "r'CNPJ\\/MF\\s*nº[:\\s]*(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'", "valor_extraido": "28.986.143/0001-33", "confianca": "alta" },
      "distribuidora": { "encontrado": true, "pagina": 1, "ancora": "Arquivo", "regex": "r'(CEMIG-D)'", "valor_extraido": "CEMIG-D", "confianca": "media" },
      "num_instalacao": { "encontrado": true, "pagina": 1, "ancora": "Instalação", "regex": "r'Instalação.*?[:\\s]*(\\d+)'", "valor_extraido": "3004870529", "confianca": "alta" },
      "num_cliente": { "encontrado": false, "pagina": 1, "regex": "r'Cliente[:\\s]*(\\d+)'", "valor_extraido": null, "confianca": "baixa" },
      "participacao_percentual": { "encontrado": false, "pagina": 1, "regex": "r'(\\d+,?\\d*%)'", "valor_extraido": null, "confianca": "baixa" },
      "duracao_meses": { "encontrado": false, "pagina": 1, "regex": "r'(\\d+)\\s*meses'", "valor_extraido": null, "confianca": "baixa" },
      "data_adesao": { "encontrado": true, "pagina": 1, "ancora": "identificadas em", "regex": "r'(\\d{2}\\/\\d{2}\\/\\d{4})'", "valor_extraido": "03/06/2022", "confianca": "alta" }
    },
    "alertas": ["Este documento é um Termo de Distrato, portanto alguns campos de vigência e participação referem-se ao contrato original citado no preâmbulo."]
  }
]''' 

def save_maps(json_str: str):
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"[ERRO] JSON inválido: {e}")
        return
    maps_dir = Path('maps')
    maps_dir.mkdir(exist_ok=True)
    for item in data:
        model_id = item.get('modelo_identificado', '')
        # extrair chave entre colchetes
        m = re.search(r'\[(.*?)\]', model_id)
        if not m:
            key = 'UNKNOWN'
        else:
            key = m.group(1)
        filename = f"{key}_v1.json"
        path = maps_dir / filename
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(item, f, indent=4, ensure_ascii=False)
        print(f"[OK] {filename}")
    print(f"\nTotal salvo: {len(data)} mapas.")

if __name__ == '__main__':
    save_maps(JSON_INPUT)
"
