"""
Regras de negócio para validação de números de instalação por distribuidora.

Arquitetura extensível: cada distribuidora implementa sua própria classe de regras.
"""
from abc import ABC, abstractmethod
from typing import Tuple


class DistributorRules(ABC):
    """
    Interface base para regras de distribuidoras.
    Implementar uma subclasse para cada distribuidora.
    """
    
    @staticmethod
    @abstractmethod
    def is_numero_cliente(number: str) -> bool:
        """Verifica se o número é um código de cliente."""
        pass
    
    @staticmethod
    @abstractmethod
    def is_instalacao(number: str, from_label: bool = False) -> bool:
        """Verifica se o número é uma instalação (UC)."""
        pass
    
    @classmethod
    def classify(cls, number: str, from_label: bool = False) -> Tuple[str, float]:
        """
        Classifica um número.
        Returns: (tipo, confiança)
        """
        if cls.is_numero_cliente(number):
            return 'cliente', 0.99
        if cls.is_instalacao(number, from_label=from_label):
            return 'instalacao', 0.95
        return 'unknown', 0.0


class CPFLRules(DistributorRules):
    """
    Regras de negócio para classificar números CPFL.
    
    Padrões CPFL:
    - Nº Cliente: 9 dígitos, começa com 70 ou 71
    - Nº Instalação: 5-8 dígitos OU 10 dígitos começando com 40
    """
    
    @staticmethod
    def is_numero_cliente(number: str) -> bool:
        """
        Nº do Cliente CPFL:
        - SEMPRE 9 dígitos
        - SEMPRE começa com 70 ou 71
        """
        return len(number) == 9 and number.startswith(('70', '71'))
    
    @staticmethod
    def is_instalacao(number: str, from_label: bool = False) -> bool:
        """
        Nº da Instalação (UC) CPFL:
        - 5-8 dígitos (padrão comum, inclui formato legado)
        - OU 10 dígitos começando com 40
        - NUNCA começa com 70/71 (a menos que venha de label explícito)
        
        Args:
            from_label: Se True, veio de label explícito "Nº da Instalação"
                       e aceita formatos mais flexíveis
        """
        length = len(number)
        
        # Se veio de label explícito, aceitar formatos legados (5-12 dígitos)
        if from_label:
            if 5 <= length <= 12:
                return True
            return False
        
        # Modo padrão (sem label): NÃO pode começar com 70/71 (é Cliente)
        if number.startswith(('70', '71')):
            return False
        
        # 5-8 dígitos: instalação (inclui formato legado)
        if 5 <= length <= 8:
            return True
        
        # 10 dígitos começando com 40: instalação especial
        if length == 10 and number.startswith('40'):
            return True
        
        return False


class CEMIGRules(DistributorRules):
    """
    Regras de negócio para CEMIG (placeholder para implementação futura).
    
    TODO: Implementar padrões específicos da CEMIG quando disponíveis.
    """
    
    @staticmethod
    def is_numero_cliente(number: str) -> bool:
        # CEMIG: padrão a definir
        return False
    
    @staticmethod
    def is_instalacao(number: str, from_label: bool = False) -> bool:
        # CEMIG: padrão a definir - por enquanto aceita 7-10 dígitos
        length = len(number)
        if from_label:
            return 5 <= length <= 12
        return 7 <= length <= 10


# Registry de regras por distribuidora
_RULES_REGISTRY = {
    'CPFL': CPFLRules,
    'CPFL_PAULISTA': CPFLRules,
    'CPFL_PIRATININGA': CPFLRules,
    'CEMIG': CEMIGRules,
}


def get_rules(distributor: str) -> type[DistributorRules]:
    """
    Factory para obter regras de uma distribuidora.
    
    Args:
        distributor: Nome da distribuidora (ex: 'CPFL', 'CEMIG')
        
    Returns:
        Classe de regras para a distribuidora (default: CPFLRules)
    """
    distributor_upper = distributor.upper().replace(' ', '_')
    return _RULES_REGISTRY.get(distributor_upper, CPFLRules)


# Aliases para compatibilidade com código existente
CPFLBusinessRules = CPFLRules
