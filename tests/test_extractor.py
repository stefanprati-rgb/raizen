"""
Teste rápido do extrator com amostra de PDFs.
Salva resultado em arquivo para análise.
"""
import sys
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Import do módulo raizen_power
from raizen_power.extraction.extractor import ContractExtractor
import json

PDF_DIR = Path(r"c:\Projetos\Raizen\OneDrive_2026-01-06\TERMO DE ADESÃO")

def test_sample():
    """Testa extração em alguns PDFs de exemplo."""
    
    # Selecionar amostras de diferentes modelos
    samples = [
        # Modelo 1 - GD
        "GD  Condomínio Edifício Capri – CNPJ nº 19.264.9190001-10.pdf",
        # Modelo 2 - Fortbras
        "Fortbras - Raízen - Quotas Consórcio 40864 - 22761584010385.pdf",
        # Modelo 1 - Corporeos (com Anexo I)
        "05 07 2024 SOLAR 40908 - CORPOREOS - SERVICOS TERAPEUTICOS SA.pdf",
        # SOLAR padrão
        "SOLAR 10935 - CANOPUS DESENVOLVIMENTO IMOBILIARIO LTDA - 04505660000185 - Clicksign.pdf",
        # TERMO ADESAO
        "TERMO ADESAO 0013222 - AUTO POSTO E SERVICO MJM DE MARICA LTDA - 07604073Clicksign.pdf",
    ]
    
    extractor = ContractExtractor()
    
    output_lines = []
    output_lines.append("=" * 80)
    output_lines.append("TESTE DE EXTRAÇÃO - AMOSTRA")
    output_lines.append("=" * 80)
    
    for sample_name in samples:
        pdf_path = PDF_DIR / sample_name
        
        if not pdf_path.exists():
            output_lines.append(f"\n⚠ Arquivo não encontrado: {sample_name}")
            continue
        
        output_lines.append(f"\n{'='*80}")
        output_lines.append(f"📄 {sample_name}")
        output_lines.append("=" * 80)
        
        try:
            result = extractor.extract_from_pdf(str(pdf_path))
            
            output_lines.append(f"Tipo: {result.tipo_documento}")
            output_lines.append(f"Modelo: {result.modelo_detectado}")
            output_lines.append(f"Páginas: {result.paginas}")
            output_lines.append(f"Guarda-Chuva: {result.is_guarda_chuva}")
            output_lines.append(f"Score: {result.confianca_score}")
            output_lines.append(f"Alertas gerais: {result.alertas[:3] if result.alertas else 'Nenhum'}")
            output_lines.append(f"Qtd Registros: {len(result.registros)}")
            
            for i, record in enumerate(result.registros[:3]):  # Max 3 registros
                output_lines.append(f"\n--- Registro {i+1} ---")
                for key in ['razao_social', 'cnpj', 'email', 'distribuidora', 
                            'num_instalacao', 'num_cliente', 'qtd_cotas', 
                            'valor_cota', 'pagamento_mensal', 'performance_alvo',
                            'representante_nome', 'representante_cpf']:
                    value = record.get(key, '')
                    if value:
                        output_lines.append(f"  {key}: {value}")
                
                alerts = record.get('alertas', '')
                if alerts:
                    output_lines.append(f"  ⚠ Alertas: {alerts}")
                output_lines.append(f"  Score: {record.get('confianca_score', 'N/A')}")
            
            if len(result.registros) > 3:
                output_lines.append(f"\n  ... e mais {len(result.registros) - 3} registros")
        
        except Exception as e:
            output_lines.append(f"❌ ERRO: {e}")
            import traceback
            output_lines.append(traceback.format_exc())
    
    # Salvar resultado
    output_text = "\n".join(output_lines)
    Path("test_result.txt").write_text(output_text, encoding='utf-8')
    print("Resultado salvo em test_result.txt")

if __name__ == "__main__":
    test_sample()
