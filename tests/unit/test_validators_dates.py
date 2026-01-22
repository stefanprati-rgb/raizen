"""
Testes unitários para validação de datas em validators.py
"""
import pytest
from raizen_power.utils.validators import validate_dates_order


class TestValidateDatesOrder:
    """Testes para validate_dates_order()"""
    
    def test_valid_order_br_format(self):
        """Testa ordem válida com formato brasileiro DD/MM/AAAA"""
        assert validate_dates_order("01/01/2024", "31/01/2024") is True
        assert validate_dates_order("15/03/2024", "15/04/2024") is True
    
    def test_valid_order_iso_format(self):
        """Testa ordem válida com formato ISO AAAA-MM-DD"""
        assert validate_dates_order("2024-01-01", "2024-01-31") is True
        assert validate_dates_order("2024-03-15", "2024-04-15") is True
    
    def test_valid_order_mixed_format(self):
        """Testa ordem válida com formatos mistos"""
        assert validate_dates_order("01/01/2024", "2024-01-31") is True
        assert validate_dates_order("2024-01-01", "31/01/2024") is True
    
    def test_same_day_allowed(self):
        """Testa que mesma data é permitida por padrão"""
        assert validate_dates_order("01/01/2024", "01/01/2024") is True
        assert validate_dates_order("2024-01-01", "2024-01-01") is True
    
    def test_same_day_not_allowed(self):
        """Testa rejeição de mesma data quando allow_same_day=False"""
        assert validate_dates_order("01/01/2024", "01/01/2024", allow_same_day=False) is False
        assert validate_dates_order("01/01/2024", "02/01/2024", allow_same_day=False) is True
    
    def test_invalid_order(self):
        """Testa que ordem invertida é detectada"""
        assert validate_dates_order("31/01/2024", "01/01/2024") is False
        assert validate_dates_order("2024-01-31", "2024-01-01") is False
    
    def test_alternative_formats(self):
        """Testa formatos alternativos (hífen, ponto)"""
        assert validate_dates_order("01-01-2024", "31-01-2024") is True
        assert validate_dates_order("01.01.2024", "31.01.2024") is True
    
    def test_missing_dates_return_true(self):
        """Testa que datas ausentes não são consideradas erro"""
        assert validate_dates_order(None, "31/01/2024") is True
        assert validate_dates_order("01/01/2024", None) is True
        assert validate_dates_order(None, None) is True
        assert validate_dates_order("", "") is True
    
    def test_invalid_date_format_returns_false(self):
        """Testa que formatos inválidos retornam False"""
        assert validate_dates_order("01/13/2024", "31/01/2024") is False  # Mês inválido
        assert validate_dates_order("32/01/2024", "31/01/2024") is False  # Dia inválido
        assert validate_dates_order("abc", "31/01/2024") is False  # Texto inválido
        assert validate_dates_order("01/01/2024", "xyz") is False
    
    def test_real_world_contract_dates(self):
        """Testa com datas reais de contratos"""
        # Adesão CPFL
        assert validate_dates_order("15/03/2023", "14/03/2026") is True
        
        # Aditivo com mesma data
        assert validate_dates_order("10/05/2024", "10/05/2024") is True
        
        # Distrato (ordem invertida deveria falhar)
        assert validate_dates_order("01/12/2024", "01/06/2024") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
