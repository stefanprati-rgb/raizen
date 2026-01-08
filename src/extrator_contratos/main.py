"""
Script principal para extração em lote de contratos PDF.
Processa todos os PDFs da pasta e gera CSVs + relatório HTML.

Uso:
    python -m src.extrator_contratos.main --input <pasta_pdfs> [--output <pasta_saida>]
    
Exemplos:
    python -m src.extrator_contratos.main -i "C:/Contratos/PDFs"
    python -m src.extrator_contratos.main -i ./pdfs -o ./resultados
"""
import csv
import sys
import logging
import argparse
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


def setup_logging(output_dir: Path) -> None:
    """Configura o sistema de logging."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(output_dir / 'extractor.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


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


from .config_loader import load_config

def parse_args():
    """Parse argumentos de linha de comando."""
    parser = argparse.ArgumentParser(
        description="Extrator de Contratos Raízen - Processa PDFs e extrai dados para CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  %(prog)s -i "C:/Contratos/PDFs"
  %(prog)s --config config_prod.yaml
        """
    )
    
    parser.add_argument(
        "--input", "-i",
        type=Path,
        help="Pasta contendo os PDFs de contratos (sobrescreve config)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Pasta para salvar os resultados (sobrescreve config)"
    )
    
    parser.add_argument(
        "--max-pages",
        type=int,
        help="Máximo de páginas a processar por PDF"
    )
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        default="config.yaml",
        help="Caminho do arquivo de configuração"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Modo verboso (mais detalhes no log)"
    )
    
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Ativar processamento paralelo (4-8x mais rápido)"
    )
    
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=None,
        help="Número de workers para processamento paralelo (padrão: núcleos CPU - 1)"
    )
    
    return parser.parse_args()


def main():
    """Função principal de execução."""
    # Parse CLI params first
    args = parse_args()
    
    # Load config file (CLI arg or default)
    config = load_config(args.config)
    
    # Resolve paths: CLI > Config > Default
    input_path_str = args.input if args.input else config.get('input', {}).get('path')
    output_path_str = args.output if args.output else config.get('output', {}).get('path')
    max_pages = args.max_pages if args.max_pages else config.get('extraction', {}).get('max_pages', 10)
    
    if not input_path_str:
        print("❌ Erro: Input não definido (nem via CLI nem config.yaml)")
        sys.exit(1)
        
    pdf_dir = Path(input_path_str).resolve()
    output_dir = Path(output_path_str).resolve()
    
    # Validação de entrada
    if not pdf_dir.exists():
        print(f"❌ Erro: A pasta de entrada não existe: {pdf_dir}")
        sys.exit(1)
    
    if not pdf_dir.is_dir():
        print(f"❌ Erro: O caminho de entrada não é uma pasta: {pdf_dir}")
        sys.exit(1)
    
    # Configurar logging
    setup_logging(output_dir)
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Banner
    print("=" * 60)
    print("EXTRATOR DE CONTRATOS RAÍZEN")
    print("=" * 60)
    print(f"\n📂 Entrada: {pdf_dir}")
    print(f"📁 Saída: {output_dir}")
    
    # Listar PDFs
    pdf_files = list(pdf_dir.glob("*.pdf"))
    total_files = len(pdf_files)
    
    if total_files == 0:
        print(f"\n❌ Nenhum PDF encontrado em: {pdf_dir}")
        print("   Verifique se o caminho está correto.")
        sys.exit(1)
    
    print(f"\n📁 {total_files:,} PDFs encontrados")
    
    # Modo de processamento
    if args.parallel:
        import multiprocessing
        workers = args.workers or max(1, multiprocessing.cpu_count() - 1)
        print(f"\n🚀 Iniciando extração PARALELA ({workers} workers)...\n")
    else:
        print("\n🔄 Iniciando extração...\n")
    
    # Inicializar extrator
    extractor = ContractExtractor()
    
    # Processar em lote
    start_time = datetime.now()
    
    if args.parallel:
        valid_records, review_records = extractor.process_batch_parallel(
            [str(p) for p in pdf_files],
            max_workers=args.workers,
            progress_callback=progress_callback
        )
    else:
        valid_records, review_records = extractor.process_batch(
            [str(p) for p in pdf_files],
            progress_callback=progress_callback
        )
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print(f"\n\n✅ Extração concluída em {elapsed:.1f} segundos")
    if elapsed > 0:
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
    
    valid_csv = output_dir / "contratos_extraidos.csv"
    review_csv = output_dir / "contratos_revisao.csv"
    report_html = output_dir / "relatorio.html"
    
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
