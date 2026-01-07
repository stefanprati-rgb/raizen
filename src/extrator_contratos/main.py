"""
Script principal para extração em lote de contratos PDF.
Processa todos os PDFs da pasta e gera CSVs + relatório HTML.
"""
import csv
import sys
import logging
from pathlib import Path
from datetime import datetime
import warnings

# Suprimir warnings do pdfplumber (CropBox missing, etc.)
warnings.filterwarnings('ignore')
logging.getLogger('pdfminer').setLevel(logging.ERROR)

# Adicionar diretório pai ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from extrator_contratos import (
    ContractExtractor,
    generate_html_report
)


# Configurações
PDF_DIR = Path(r"c:\Projetos\Raizen\OneDrive_2026-01-06\TERMO DE ADESÃO")
OUTPUT_DIR = Path(r"c:\Projetos\Raizen\output")

# Configurar logging global
OUTPUT_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(OUTPUT_DIR / 'extractor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Campos do CSV
CSV_FIELDS = [
    'arquivo_origem',
    'tipo_documento',
    'modelo_detectado',
    'razao_social',
    'cnpj',
    'email',
    'email_secundario',
    'endereco',
    'cep',
    'cidade',
    'uf',
    'distribuidora',
    'num_instalacao',
    'num_cliente',
    'qtd_cotas',
    'valor_cota',
    'pagamento_mensal',
    'vencimento',
    'performance_alvo',
    'duracao_meses',
    'representante_nome',
    'representante_nome_secundario',
    'representante_cpf',
    'participacao_percentual',
    'consorcio_nome',
    'consorcio_cnpj',
    'data_extracao',
    'confianca_score',
    'alertas',
    'is_guarda_chuva',
]


def progress_callback(current: int, total: int):
    """Exibe barra de progresso no terminal."""
    percent = current / total * 100
    bar_len = 50
    filled = int(bar_len * current / total)
    bar = '█' * filled + '░' * (bar_len - filled)
    
    print(f'\r[{bar}] {percent:5.1f}% ({current:,}/{total:,})', end='', flush=True)


def save_csv(records: list, filepath: Path) -> None:
    """Salva registros em arquivo CSV."""
    if not records:
        return
    
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(records)


def main():
    """Função principal de execução."""
    print("=" * 60)
    print("EXTRATOR DE CONTRATOS RAÍZEN")
    print("=" * 60)
    print(f"\nDiretório de entrada: {PDF_DIR}")
    print(f"Diretório de saída: {OUTPUT_DIR}")
    
    # Listar PDFs
    pdf_files = list(PDF_DIR.glob("*.pdf"))
    total_files = len(pdf_files)
    
    if total_files == 0:
        print("\n❌ Nenhum PDF encontrado!")
        return
    
    print(f"\n📁 {total_files:,} PDFs encontrados")
    print("\n🔄 Iniciando extração...\n")
    
    # Inicializar extrator
    extractor = ContractExtractor()
    
    # Processar em lote
    start_time = datetime.now()
    
    valid_records, review_records = extractor.process_batch(
        [str(p) for p in pdf_files],
        progress_callback=progress_callback
    )
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print(f"\n\n✅ Extração concluída em {elapsed:.1f} segundos")
    print(f"   Velocidade: {total_files / elapsed:.1f} PDFs/segundo")
    
    # Estatísticas
    print("\n" + "=" * 60)
    print("RESULTADOS")
    print("=" * 60)
    print(f"✓ Registros válidos: {len(valid_records):,}")
    print(f"⚠ Para revisão: {len(review_records):,}")
    
    if valid_records or review_records:
        total = len(valid_records) + len(review_records)
        success_rate = len(valid_records) / total * 100
        print(f"📊 Taxa de sucesso: {success_rate:.1f}%")
    
    # Salvar CSVs
    print("\n💾 Salvando arquivos...")
    
    valid_csv = OUTPUT_DIR / "contratos_extraidos.csv"
    review_csv = OUTPUT_DIR / "contratos_revisao.csv"
    report_html = OUTPUT_DIR / "relatorio.html"
    
    save_csv(valid_records, valid_csv)
    print(f"   ✓ {valid_csv}")
    
    save_csv(review_records, review_csv)
    print(f"   ✓ {review_csv}")
    
    # Gerar relatório HTML
    generate_html_report(valid_records, review_records, str(report_html))
    print(f"   ✓ {report_html}")
    
    print("\n" + "=" * 60)
    print("PROCESSO CONCLUÍDO!")
    print("=" * 60)
    
    # Resumo de próximos passos
    if review_records:
        print(f"\n📋 Próximo passo: Revise os {len(review_records):,} registros em:")
        print(f"   {review_csv}")
        print(f"\n🌐 Veja o relatório completo em:")
        print(f"   {report_html}")


if __name__ == "__main__":
    main()
