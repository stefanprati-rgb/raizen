import json
import re
from pathlib import Path

# Pasta onde salvaremos os mapas finais
MAPS_DIR = Path("maps")
MAPS_DIR.mkdir(exist_ok=True)

def save_manual_maps(json_content):
    """
    Recebe o JSON "grandão" do Gemini e salva em arquivos individuais.
    """
    try:
        data = json.loads(json_content)
        
        # Se for um único objeto wrappado em array ou não
        if isinstance(data, dict):
            data = [data]
            
        saved_count = 0
        
        for item in data:
            # 1. Identificar Nome do Arquivo
            model_id = item.get("modelo_identificado", "UNKNOWN")
            
            # Tentar extrair a chave do cluster do nome do arquivo
            # Ex: [CEA_EQUATORIAL_08p] AMOSTRA_... -> CEA_EQUATORIAL_08p
            match = re.search(r'\[(.*?)\]', model_id)
            if match:
                cluster_key = match.group(1)
            else:
                # Fallback: tentar construir do nome
                dist = item.get("distribuidora_principal", "UNKNOWN").replace(" ", "_")
                pages = item.get("paginas_analisadas", 0)
                cluster_key = f"{dist}_{pages:02d}p"
            
            # Limpar caracteres inválidos no nome do arquivo
            safe_key = re.sub(r'[<>:"/\\|?*]', '', cluster_key)
            filename = f"{safe_key}_v1.json"
            
            filepath = MAPS_DIR / filename
            
            # Salvar
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(item, f, indent=4, ensure_ascii=False)
                
            print(f"[OK] Salvo: {filepath}")
            saved_count += 1
            
        print(f"\nTotal salvos: {saved_count}")
        
    except json.JSONDecodeError as e:
        print(f"❌ Erro ao ler JSON: {e}")

# COLE O JSON ABAIXO ENTRE AS ASPAS TRIPLAS
RAW_JSON = r"""
[
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
  }
[
  {
    "modelo_identificado": "[CEA_EQUATORIAL_08p] AMOSTRA_CEA_EQUATORIAL_08p.pdf",
    "distribuidora_principal": "BA NEOENERGIA COELBA",
    "paginas_analisadas": 8,
    "campos": {
      "sic_ec_cliente": {
        "encontrado": false,
        "pagina": null,
        "ancora": "SIC-EC Cliente",
        "regex": "r'SIC-EC Cliente[:\\s]*(\\d{5,6})'",
        "valor_extraido": null,
        "confianca": "baixa"
      },
      "razao_social": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "Razão Social:",
        "regex": "r'Razão Social[:\\s]*([^\\-]+?)(?:\\s*-\\s*CNPJ|$)'",
        "valor_extraido": "JC DA C CAMPOS LTDA",
        "confianca": "alta"
      },
      "cnpj": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "CNPJ",
        "regex": "r'(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'",
        "valor_extraido": "23.511.995/0001-50",
        "confianca": "alta"
      },
      "nire": {
        "encontrado": false,
        "pagina": null,
        "ancora": "NIRE:",
        "regex": "r'NIRE[:\\s]*(\\d+)'",
        "valor_extraido": null,
        "confianca": "baixa"
      },
      "endereco": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "Endereço:",
        "regex": "r'Endereço[:\\s]*([\\s\\S]+?)(?=\\s*Titular|\\s*CONSÓRCIO|$)'",
        "valor_extraido": "AV MONSENHOR MARIO PESSOA SN, FEIRA DE SANTANA, Bahia, CEP 44001-775",
        "confianca": "alta"
      },
      "email": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "E-mail:",
        "regex": "r'E-mail[:\\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})'",
        "valor_extraido": "jafehcampos@gmail.com",
        "confianca": "alta"
      },
      "representante_nome": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "Nome:",
        "regex": "r'Nome[:\\s]*([^\\-]+?)(?:\\s*-\\s*CPF|$)'",
        "valor_extraido": "JAFEH CORREIA DA COSTA CAMPOS",
        "confianca": "alta"
      },
      "consorcio_nome": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "Razão Social:",
        "regex": "r'Razão Social[:\\s]*(Consórcio\\s+[^\\-]+)'",
        "valor_extraido": "Consórcio RZ Pernambuco",
        "confianca": "alta"
      },
      "consorcio_cnpj": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "CNPJ nº",
        "regex": "r'CNPJ\\s*nº\\s*(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'",
        "valor_extraido": "35.299.820/0001-00",
        "confianca": "alta"
      },
      "distribuidora": {
        "encontrado": true,
        "pagina": 2,
        "ancora": "Distribuidora:",
        "regex": "r'Distribuidora[:\\s]*(.+)'",
        "valor_extraido": "BA NEOENERGIA COELBA",
        "confianca": "alta"
      },
      "num_instalacao": {
        "encontrado": true,
        "pagina": 2,
        "ancora": "Nº da Instalação da Unidade Consumidora:",
        "regex": "r'Instalação da Unidade Consumidora[:\\s]*(\\d+)'",
        "valor_extraido": "1513717",
        "confianca": "alta"
      },
      "num_cliente": {
        "encontrado": true,
        "pagina": 2,
        "ancora": "Nº do Cliente:",
        "regex": "r'Nº do Cliente[:\\s]*(\\d+)'",
        "valor_extraido": "7065821049",
        "confianca": "alta"
      },
      "participacao_percentual": {
        "encontrado": false,
        "pagina": null,
        "ancora": "Participação no Consórcio/",
        "regex": "r'Participação.*?[:\\s]*(\\d+,?\\d*\\s*%)'",
        "valor_extraido": null,
        "confianca": "baixa"
      },
      "duracao_meses": {
        "encontrado": true,
        "pagina": 2,
        "ancora": "Duração:",
        "regex": "r'Duração[:\\s]*(\\d+)\\s*meses'",
        "valor_extraido": "60",
        "confianca": "alta"
      },
      "data_adesao": {
        "encontrado": true,
        "pagina": 6,
        "ancora": "Piracicaba,",
        "regex": "r'Piracicaba,\\s*(\\d{1,2}\\s*de\\s*\\w+\\s*de\\s*\\d{4})'",
        "valor_extraido": "11 de Setembro de 2023",
        "confianca": "alta"
      }
    },
    "alertas": ["O CNPJ da consorciada foi quebrado em duas linhas no texto extraído.", "Distribuidora identificada como Coelba, divergindo do nome do arquivo (Equatorial)."]
  },
  {
    "modelo_identificado": "[CEB-DIS_13p] AMOSTRA_CEB-DIS_13p.pdf",
    "distribuidora_principal": "CEB-DIS",
    "paginas_analisadas": 13,
    "campos": {
      "sic_ec_cliente": {
        "encontrado": false,
        "pagina": null,
        "ancora": "SIC-EC Cliente",
        "regex": "r'SIC-EC Cliente[:\\s]*(\\d{5,6})'",
        "valor_extraido": null,
        "confianca": "baixa"
      },
      "razao_social": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "Razão Social:",
        "regex": "r'Razão Social[:\\s]*\\n?\\s*(.+)'",
        "valor_extraido": "LEM LANCHONETE LTDA",
        "confianca": "alta"
      },
      "cnpj": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "CNPJ:",
        "regex": "r'(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'",
        "valor_extraido": "33.469.174/0001-57",
        "confianca": "alta"
      },
      "nire": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "NIRE:",
        "regex": "r'NIRE[:\\s]*(\\d+)'",
        "valor_extraido": "53202232101",
        "confianca": "alta"
      },
      "endereco": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "Endereço:",
        "regex": "r'Endereço[:\\s]*\\n?\\s*Interno\\s*\\n?\\s*([^\\n]+)'",
        "valor_extraido": "Q QNN 31 AREA ESPECIAL F LOJA, 01, CEILANDIA NORTE (CEILANDIA), BRASILIA/DF, CEP:72.225-310",
        "confianca": "alta"
      },
      "email": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "E-mail:",
        "regex": "r'E-mail[:\\s]*\\n?\\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})'",
        "valor_extraido": "luizfillipe.cunha@gmail.com",
        "confianca": "alta"
      },
      "representante_nome": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "DADOS DO REPRESENTANTE LEGAL:",
        "regex": "r'REPRESENTANTE LEGAL[:\\s]*\\n?\\s*(.+)'",
        "valor_extraido": "LUIZ FILLIPE CUNHA SILVA",
        "confianca": "alta"
      },
      "consorcio_nome": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "membro do",
        "regex": "r'membro do\\s*(Consórcio\\s+[^,]+)'",
        "valor_extraido": "Consórcio RZ Distrito Federal",
        "confianca": "alta"
      },
      "consorcio_cnpj": {
        "encontrado": true,
        "pagina": 2,
        "ancora": "inscrito no CNPJ/MF sob o nº",
        "regex": "r'CNPJ\\/MF\\s*sob\\s*o\\s*nº\\s*(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'",
        "valor_extraido": "35.339.789/0001-94",
        "confianca": "alta"
      },
      "distribuidora": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "Distribuidora:",
        "regex": "r'Distribuidora[:\\s]*\\n?\",\\s*\"(.+)\"'",
        "valor_extraido": "CEB-DIS",
        "confianca": "alta"
      },
      "num_instalacao": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "Nº da Instalação (Unidade Consumidora):",
        "regex": "r'Instalação.*?\":\\n?\",\\s*\"(\\d+)\"'",
        "valor_extraido": "651187",
        "confianca": "alta"
      },
      "num_cliente": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "Nº do Cliente:",
        "regex": "r'Nº do Cliente.*?\":\\n?\",\\s*\"(\\d+)\"'",
        "valor_extraido": "02445113",
        "confianca": "alta"
      },
      "participacao_percentual": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "Participação no Consórcio/ Rateio:",
        "regex": "r'Participação.*?\":\\n?\",\\s*\"(\\d+,?\\d*\\s*%)'",
        "valor_extraido": "0,31%",
        "confianca": "alta"
      },
      "duracao_meses": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "Vigência Inicial:",
        "regex": "r'Vigência Inicial.*?\",\\s*\"(\\d+)\\s*meses'",
        "valor_extraido": "60",
        "confianca": "alta"
      },
      "data_adesao": {
        "encontrado": true,
        "pagina": 4,
        "ancora": "Piracicaba,",
        "regex": "r'Piracicaba,\\s*(\\d{1,2}\\s*de\\s*\\w+\\s*de\\s*\\d{4})'",
        "valor_extraido": "21 de Fevereiro de 2022",
        "confianca": "alta"
      }
    },
    "alertas": ["Os dados de participação estão em formato de tabela CSV processada."]
  },
  {
    "modelo_identificado": "[CELESC-DIS_09p] AMOSTRA_CELESC-DIS_09p.pdf",
    "distribuidora_principal": "SP CPFL PAULISTA",
    "paginas_analisadas": 9,
    "campos": {
      "sic_ec_cliente": {
        "encontrado": false,
        "pagina": null,
        "ancora": "SIC-EC Cliente",
        "regex": "r'SIC-EC Cliente[:\\s]*(\\d{5,6})'",
        "valor_extraido": null,
        "confianca": "baixa"
      },
      "razao_social": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "Razão Social:",
        "regex": "r'Razão Social[:\\s]*(.+?)\\s*CNPJ'",
        "valor_extraido": "HIPERGRAF IND GRAFICA COM LTDA",
        "confianca": "alta"
      },
      "cnpj": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "CNPJ nº",
        "regex": "r'(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'",
        "valor_extraido": "53.263.828/0001-07",
        "confianca": "alta"
      },
      "nire": {
        "encontrado": false,
        "pagina": null,
        "ancora": "NIRE:",
        "regex": "r'NIRE[:\\s]*(\\d+)'",
        "valor_extraido": null,
        "confianca": "baixa"
      },
      "endereco": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "Endereço:",
        "regex": "r'Endereço[:\\s]*([\\s\\S]+?)(?=\\s*CONSÓRCIO|$)'",
        "valor_extraido": "Rua Francisca Alves Pereira Borges, 426, Vila Boca Rica, Gráfica, Barra Bonita, São Paulo, CEP 17347-302",
        "confianca": "alta"
      },
      "email": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "E-mail:",
        "regex": "r'E-mail[:\\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})'",
        "valor_extraido": "hipergraf@gmail.com",
        "confianca": "alta"
      },
      "representante_nome": {
        "encontrado": true,
        "pagina": 7,
        "ancora": "Assinaturas",
        "regex": "r'Assinaturas\\s*([^\\n]+)\\s*CPF'",
        "valor_extraido": "Pedro Paulo Zaratini",
        "confianca": "media"
      },
      "consorcio_nome": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "Razão Social:",
        "regex": "r'Razão Social[:\\s]*(Consórcio\\s+RZ\\s+[^C]+)'",
        "valor_extraido": "Consórcio RZ São Paulo",
        "confianca": "alta"
      },
      "consorcio_cnpj": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "CNPJ nº",
        "regex": "r'RZ\\s+São\\s+Paulo\\s+CNPJ\\s*nº\\s*(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'",
        "valor_extraido": "35.300.150/0001-03",
        "confianca": "alta"
      },
      "distribuidora": {
        "encontrado": true,
        "pagina": 2,
        "ancora": "Distribuidora:",
        "regex": "r'Distribuidora[:\\s]*(.+)'",
        "valor_extraido": "SP CPFL PAULISTA",
        "confianca": "alta"
      },
      "num_instalacao": {
        "encontrado": true,
        "pagina": 2,
        "ancora": "Nº da Instalação da Unidade Consumidora:",
        "regex": "r'Instalação.*?[:\\s]*(\\d+)'",
        "valor_extraido": "7600445",
        "confianca": "alta"
      },
      "num_cliente": {
        "encontrado": true,
        "pagina": 2,
        "ancora": "Nº do Cliente:",
        "regex": "r'Nº do Cliente[:\\s]*(\\d+)'",
        "valor_extraido": "701906578",
        "confianca": "alta"
      },
      "participacao_percentual": {
        "encontrado": false,
        "pagina": null,
        "ancora": "Rateio:",
        "regex": "r'Rateio[:\\s]*(\\d+,?\\d*\\s*%)'",
        "valor_extraido": null,
        "confianca": "baixa"
      },
      "duracao_meses": {
        "encontrado": true,
        "pagina": 2,
        "ancora": "Duração:",
        "regex": "r'Duração[:\\s]*(\\d+)\\s*meses'",
        "valor_extraido": "60",
        "confianca": "alta"
      },
      "data_adesao": {
        "encontrado": true,
        "pagina": 7,
        "ancora": "Piracicaba,",
        "regex": "r'Piracicaba,\\s*(\\d{1,2}\\s*de\\s*\\w+\\s*de\\s*\\d{4})'",
        "valor_extraido": "12 de Fevereiro de 2024",
        "confianca": "alta"
      }
    },
    "alertas": ["Distribuidora identificada como CPFL Paulista, divergindo do nome do arquivo (Celesc)."]
  },
  {
    "modelo_identificado": "[CELETRO_10p] AMOSTRA_CELETRO_10p.pdf",
    "distribuidora_principal": "RAÍZEN GD",
    "paginas_analisadas": 10,
    "campos": {
      "sic_ec_cliente": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "SIC-EC Cliente:",
        "regex": "r'SIC-EC Cliente[:\\s]*(\\d+)'",
        "valor_extraido": "8949",
        "confianca": "alta"
      },
      "razao_social": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "celebrado entre:",
        "regex": "r'e\\s*\\n?\\s*([A-Z\\s]+LTDA|[A-Z\\s]+S\\sA)'",
        "valor_extraido": "RAÍZEN COMBUSTÍVEIS S A",
        "confianca": "alta"
      },
      "cnpj": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "inscrita no CNPJ sob o nº",
        "regex": "r'CNPJ\\s*sob\\s*o\\s*nº\\s*(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'",
        "valor_extraido": "33.453.598/0001-23",
        "confianca": "alta"
      },
      "nire": {
        "encontrado": false,
        "pagina": null,
        "ancora": "NIRE",
        "regex": "r'NIRE[:\\s]*(\\d+)'",
        "valor_extraido": null,
        "confianca": "baixa"
      },
      "endereco": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "sede na",
        "regex": "r'sede\\s*na\\s*([^,]+,[^,]+,[^,]+,[^,]+,[^,]+CEP:\\s*\\d{2}\\.\\d{3}\\-\\d{3})'",
        "valor_extraido": "AV ALMIRANTE BARROSO, 8136 ANDAR, SALA 36A104, CENTRO, RIO DE JANEIRO/RJ, CEP: 20.030-004",
        "confianca": "alta"
      },
      "email": {
        "encontrado": true,
        "pagina": 7,
        "ancora": "E-mail:",
        "regex": "r'CONSORCIADA:.*?E-mail[:\\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})'",
        "valor_extraido": "fabiana.zuino@raizen.com",
        "confianca": "alta"
      },
      "representante_nome": {
        "encontrado": true,
        "pagina": 8,
        "ancora": "Representante",
        "regex": "r'Representante\\n?\\\",\\?\\\"(.+)\\\"'",
        "valor_extraido": "Fabiana Samblas Zuino Moraes",
        "confianca": "media"
      },
      "consorcio_nome": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "Consórcio",
        "regex": "r'Consórcio\\s+(CONSÓRCIO\\s+SOLução)'",
        "valor_extraido": "CONSÓRCIO SOLução",
        "confianca": "alta"
      },
      "consorcio_cnpj": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "inscrito no CNPJ/MF sob o nº",
        "regex": "r'inscrito\\s*no\\s*CNPJ\\/MF\\s*sob\\s*o\\s*nº\\s*(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'",
        "valor_extraido": "32.770.493/0001-35",
        "confianca": "alta"
      },
      "distribuidora": {
        "encontrado": false,
        "pagina": null,
        "ancora": "Distribuidora:",
        "regex": "r'Distribuidora[:\\s]*(.+)'",
        "valor_extraido": null,
        "confianca": "baixa"
      },
      "num_instalacao": {
        "encontrado": false,
        "pagina": null,
        "ancora": "Nº da Instalação",
        "regex": "r'Instalação[:\\s]*(\\d+)'",
        "valor_extraido": null,
        "confianca": "baixa"
      },
      "num_cliente": {
        "encontrado": false,
        "pagina": null,
        "ancora": "Nº do Cliente",
        "regex": "r'Cliente[:\\s]*(\\d+)'",
        "valor_extraido": null,
        "confianca": "baixa"
      },
      "participacao_percentual": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "Objeto:",
        "regex": "r'Objeto[:\\s]*(\\d+,?\\d*\\s*%)'",
        "valor_extraido": "5,701%",
        "confianca": "alta"
      },
      "duracao_meses": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "Período de Adesão:",
        "regex": "r'Período\\s*de\\s*Adesão[:\\s]*(\\d+)\\s*meses'",
        "valor_extraido": "60",
        "confianca": "alta"
      },
      "data_adesao": {
        "encontrado": true,
        "pagina": 8,
        "ancora": "Data da Criação",
        "regex": "r'Criação\\n?\",\\\"\\s*(\\d{2}\\/\\d{2}\\/\\d{4})'",
        "valor_extraido": "20/05/2021",
        "confianca": "alta"
      }
    },
    "alertas": ["Modelo antigo (SIC-EC). Razão social capturada no preâmbulo entre 'e' e 'sociedade empresarial'."]
  },
  {
    "modelo_identificado": "[CELPE_05p] AMOSTRA_CELPE_05p.pdf",
    "distribuidora_principal": "CELPE",
    "paginas_analisadas": 5,
    "campos": {
      "sic_ec_cliente": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "SIC-EC Cliente:",
        "regex": "r'SIC-EC Cliente[:\\s]*(\\d+)'",
        "valor_extraido": "7993",
        "confianca": "alta"
      },
      "razao_social": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "Razão Social:",
        "regex": "r'Razão Social[:\\s]*\\n?\",\\n?\"([A-Z\\s]+LTDA)'",
        "valor_extraido": "ALBUQUERQUE PNEUS LTDA",
        "confianca": "alta"
      },
      "cnpj": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "CNPJ:",
        "regex": "r'(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'",
        "valor_extraido": "11.117.785/0005-27",
        "confianca": "alta"
      },
      "nire": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "NIRE:",
        "regex": "r'NIRE[:\\s]*\\n?\",\\\"(\\d+)\"'",
        "valor_extraido": "26900238901",
        "confianca": "alta"
      },
      "endereco": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "Endereço:",
        "regex": "r'([A-Z\\s\\d,\\.]+KM[^,]+,[^,]+,[^,]+\\/PE\\s*-\\s*CEP\\s*\\d{2}\\.\\d{3}\\-\\d{3})'",
        "valor_extraido": "ROD PE 75, S/N, KM 4.5, CENTRO, GOIANA/PE - CEP 55.900-000",
        "confianca": "alta"
      },
      "email": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "E-MAIL:",
        "regex": "r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})\\s*E-MAIL'",
        "valor_extraido": "junior@albuquerquepneus.com.br",
        "confianca": "alta"
      },
      "representante_nome": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "Representante Legal:",
        "regex": "r'Representante Legal[:\\s]*\\n?\",\\n?\"([A-Z\\s]+)\"'",
        "valor_extraido": "ANTONIO ALVES DE ALBUQUERQUE JUNIOR",
        "confianca": "alta"
      },
      "consorcio_nome": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "membro do",
        "regex": "r'membro do\\s*(CONSORCIO\\s+RZ\\s+[^,]+)'",
        "valor_extraido": "CONSORCIO RZ PERNAMBUCO",
        "confianca": "alta"
      },
      "consorcio_cnpj": {
        "encontrado": true,
        "pagina": 1,
        "ancora": "inscrita no CNPJ/MF sob o nº",
        "regex": "r'CNPJ\\/MF\\s*sob\\s*o\\s*nº\\s*(\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2})'",
        "valor_extraido": "35.299.820/0001-00",
        "confianca": "alta"
      },
      "distribuidora": {
        "encontrado": true,
        "pagina": 2,
        "ancora": "Distribuidora",
        "regex": "r'Distribuidora.*?\",\\s*\"(.+)\"'",
        "valor_extraido": "CELPE",
        "confianca": "alta"
      },
      "num_instalacao": {
        "encontrado": true,
        "pagina": 2,
        "ancora": "Nº da Instalação",
        "regex": "r'Instalação.*?\",\\s*\"([\\d\\se]+)\"'",
        "valor_extraido": "1219685 e 1219687",
        "confianca": "alta"
      },
      "num_cliente": {
        "encontrado": true,
        "pagina": 2,
        "ancora": "Número Conta Contrato (UC)",
        "regex": "r'Conta Contrato.*?\",\\s*\"(\\d+)\"'",
        "valor_extraido": "2001230255",
        "confianca": "alta"
      },
      "participacao_percentual": {
        "encontrado": true,
        "pagina": 2,
        "ancora": "Participação no Consórcio / Rateio",
        "regex": "r'Rateio.*?\",\\s*\"(\\d+,?\\d*)\"'",
        "valor_extraido": "2,82",
        "confianca": "alta"
      },
      "duracao_meses": {
        "encontrado": true,
        "pagina": 2,
        "ancora": "Tempo de Vigência",
        "regex": "r'Tempo\\s*de\\s*Vigência.*?\",\\s*\"(\\d+)\\s*meses'",
        "valor_extraido": "60",
        "confianca": "alta"
      },
      "data_adesao": {
        "encontrado": true,
        "pagina": 2,
        "ancora": "Piracicaba,",
        "regex": "r'Piracicaba,\\s*(\\d{1,2}\\s*de\\s*\\w+\\s*de\\s*\\d{4})'",
        "valor_extraido": "11 de fevereiro de 2021",
        "confianca": "alta"
      }
    },
    "alertas": ["Campos NIRE e Endereço estão em blocos de texto formatados com aspas."]
  }
]
"""

if __name__ == "__main__":
    save_manual_maps(RAW_JSON)
