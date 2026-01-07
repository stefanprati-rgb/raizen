"""Teste do contrato OI S.A."""
import sys
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, 'src')
from extrator_contratos import ContractExtractor

pdf_path = r'C:\Projetos\Raizen\OneDrive_2026-01-06\TERMO DE ADESÃO\GD - TERMO DE ADESÃO - SOLAR 17486 - OI SA EM RECUPERACAO JUDICIAL - 76535764032932.pdf.pdf'

extractor = ContractExtractor()
result = extractor.extract_from_pdf(pdf_path)

print('='*60)
print('RESULTADO DA EXTRAÇÃO - OI S.A.')
print('='*60)
print(f'Páginas: {result.paginas}')
print(f'Tipo: {result.tipo_documento}')
print(f'Modelo: {result.modelo_detectado}')
print(f'Guarda-Chuva: {result.is_guarda_chuva}')
print(f'Score: {result.confianca_score}')
print(f'Registros extraídos: {len(result.registros)}')

print()
print(f'ALERTAS ({len(result.alertas)}):')
for a in result.alertas[:3]:
    print(f'  - {a[:70]}')

if result.registros:
    print()
    print('PRIMEIROS 3 REGISTROS:')
    for i, r in enumerate(result.registros[:3]):
        print(f"  {i+1}. Instalação: {r.get('num_instalacao', 'N/A')}")
    
    if len(result.registros) > 3:
        print(f'  ... e mais {len(result.registros) - 3} instalações')
