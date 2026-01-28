"""Teste do organizer V4"""
import importlib.util
spec = importlib.util.spec_from_file_location('organizer', 'scripts/legacy/super_organizer_v4.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Testar o contrato BTT (deve ser CEMIG)
pdf_btt = r'C:\Projetos\Raizen\contratos_por_paginas\05_paginas\CPFL_PAULISTA\SOLAR 33525 - BTT TELECOMUNICACOES S.A. - ADITIVO - 39565567000140 - Clicksign.pdf'
result = mod.identify_distributor(pdf_btt)
print(f'BTT (Belo Horizonte/MG): {result}')
print(f'  Esperado: CEMIG')

# Testar se clientes de Piracicaba seriam detectados corretamente
print()
print('Teste de lógica de cidade:')
test_lines = [
    'Endereco: Rua Jose Carlos, 123 - Piracicaba/SP',
    'ROD SP-308, SANTA TEREZINHA, PIRACICABA, SP, CEP 13411-900',
]
for line in test_lines:
    is_raizen = mod.is_raizen_address(line)
    city = mod.extract_client_city(line) if not is_raizen else None
    print(f'  "{line[:50]}..."')
    print(f'    É Raízen: {is_raizen}, Cidade: {city}')
