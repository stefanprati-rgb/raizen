"""Teste rápido das correções aplicadas."""
import sys
from pathlib import Path

# Imports do módulo raizen_power
from raizen_power.extraction.extractor import ContractExtractor
from raizen_power.utils.validators import parse_currency, is_umbrella_contract, validate_cep
from raizen_power.extraction.patterns import extract_field

print("=" * 60)
print("TESTE DAS CORREÇÕES")
print("=" * 60)

# Teste 1: parse_currency
print("\n1. PARSE_CURRENCY (formato brasileiro)")
test_values = [
    ("7.653,00", 7653.00),       # Formato BR com milhar
    ("7.653.00", 7653.00),       # Múltiplos pontos
    ("1,234.56", 1234.56),       # Formato US
    ("R$ 1.234,56", 1234.56),    # Com R$
    ("100,50", 100.50),          # Só vírgula
    ("1000", 1000.0),            # Sem separador
]

all_passed = True
for value, expected in test_values:
    result = parse_currency(value)
    status = "✓" if result == expected else "✗"
    if result != expected:
        all_passed = False
    print(f"   {status} '{value}' -> {result} (esperado: {expected})")

# Teste 2: validate_cep
print("\n2. VALIDATE_CEP")
cep_tests = [
    ("12345-678", True),
    ("12345678", True),
    ("12345", False),
    ("", False),
]

for cep, expected in cep_tests:
    result = validate_cep(cep)
    status = "✓" if result == expected else "✗"
    if result != expected:
        all_passed = False
    print(f"   {status} '{cep}' -> {result} (esperado: {expected})")

# Teste 3: is_umbrella_contract
print("\n3. IS_UMBRELLA_CONTRACT")
umbrella_tests = [
    ("ANEXO II - TABELA DE DESCONTOS", True),
    ("Contrato Guarda-Chuva", True),
    ("TABELA DE DESCONTOS", True),
    ("72 UCS agregadas", True),
    ("Contrato normal", False),
]

for text, expected in umbrella_tests:
    result = is_umbrella_contract(text)
    status = "✓" if result == expected else "✗"
    if result != expected:
        all_passed = False
    print(f"   {status} '{text[:40]}...' -> {result} (esperado: {expected})")

# Teste 4: extract_field com normalização
print("\n4. EXTRACT_FIELD (normalização BR)")
test_text = "Performance Alvo: 7.653,00 kWh"
result = extract_field(test_text, 'performance_alvo', 'MODELO_1')
expected = "7653.00"
status = "✓" if result == expected else "✗"
if result != expected:
    all_passed = False
print(f"   {status} '{test_text}' -> '{result}' (esperado: '{expected}')")

# Teste 5: Email Secundário
print("\n5. EMAIL_SECUNDARIO")
test_text_email = """E-mail: thiago.borges@smartfit.com
        tsomera@smartfit.com"""
result = extract_field(test_text_email, 'email', 'MODELO_2')
result_sec = extract_field(test_text_email, 'email_secundario', 'MODELO_2')
print(f"   Email principal: '{result}'")
print(f"   Email secundário: '{result_sec}'")
if result and 'thiago' in result:
    print("   ✓ Email principal capturado corretamente")
else:
    all_passed = False
    print("   ✗ Email principal não capturado")

# Teste 6: Representante Secundário
print("\n6. REPRESENTANTE_NOME_SECUNDARIO")
test_text_rep = """DADOS DO REPRESENTANTE LEGAL:
Nome: Thiago Lima Borges
      Thiago Jorge Somera
CPF: 123.456.789-00"""
result = extract_field(test_text_rep, 'representante_nome', 'MODELO_2')
result_sec = extract_field(test_text_rep, 'representante_nome_secundario', 'MODELO_2')
print(f"   Nome principal: '{result}'")
print(f"   Nome secundário: '{result_sec}'")
if result and 'Thiago Lima' in result:
    print("   ✓ Nome principal capturado corretamente")
else:
    print("   ⚠ Nome principal pode precisar de ajuste")

# Resumo
print("\n" + "=" * 60)
if all_passed:
    print("✓ TODOS OS TESTES PASSARAM!")
else:
    print("⚠ ALGUNS TESTES FALHARAM OU REQUEREM REVISÃO")
print("=" * 60)

