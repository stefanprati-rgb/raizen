"""Teste da normalização de distributor_rules."""
from raizen_power.utils.distributor_rules import get_rules, _normalize_key

print("Testes de normalização:")
print(f"  _normalize_key('CPFL Paulista') = '{_normalize_key('CPFL Paulista')}'")
print(f"  _normalize_key('CEMIG Distribuição') = '{_normalize_key('CEMIG Distribuição')}'")
print(f"  _normalize_key('enel  sp') = '{_normalize_key('enel  sp')}'")
print()

print("Testes de get_rules:")
tests = [
    "CPFL",
    "cpfl paulista",
    "CEMIG Distribuição",
    "",
    "Enel SP",
    "ENERGISA",
]

for t in tests:
    rules = get_rules(t)
    print(f"  '{t}' -> {rules.__name__}")
