"""
Verificações de inicialização e diagnóstico de dependências.

Emite warnings no arranque se dependências opcionais não estão instaladas.
Útil para debug em produção.

Uso:
    from raizen_power.core.startup import check_dependencies, print_status
    
    check_dependencies()  # Emite warnings se libs faltam
    print_status()        # Imprime status completo
"""
import logging
import warnings

logger = logging.getLogger(__name__)

# Status das dependências opcionais
_DEPS_STATUS = {}


def _check_import(module_name: str, package_name: str = None, feature: str = "unknown") -> bool:
    """Tenta importar módulo e registra status."""
    package_name = package_name or module_name
    try:
        __import__(module_name)
        _DEPS_STATUS[package_name] = {"available": True, "feature": feature}
        return True
    except ImportError:
        _DEPS_STATUS[package_name] = {"available": False, "feature": feature}
        return False


def check_dependencies(warn: bool = True) -> dict:
    """
    Verifica dependências opcionais e emite warnings se ausentes.
    
    Args:
        warn: Se True, emite logger.warning para cada lib faltante
        
    Returns:
        Dict com status de cada dependência
    """
    checks = [
        # (module, package, feature, is_critical)
        ("psutil", "psutil", "Monitoramento de memória", True),
        ("imagehash", "imagehash", "Fingerprinting visual de PDFs", False),
        ("PIL", "Pillow", "Processamento de imagens", False),
        ("easyocr", "easyocr", "OCR para PDFs escaneados", False),
        ("google.generativeai", "google-generativeai", "Geração de mapas via Gemini", False),
        ("dotenv", "python-dotenv", "Carregamento de .env", False),
    ]
    
    missing_critical = []
    missing_optional = []
    
    for module, package, feature, critical in checks:
        available = _check_import(module, package, feature)
        
        if not available:
            if critical:
                missing_critical.append((package, feature))
            else:
                missing_optional.append((package, feature))
    
    # Emitir warnings
    if warn:
        if missing_critical:
            for pkg, feat in missing_critical:
                logger.warning(
                    f"⚠️  Dependência de performance não instalada: {pkg} ({feat}). "
                    f"Instale com: pip install raizen-power-extractor[performance]"
                )
        
        if missing_optional:
            features = ", ".join(f for _, f in missing_optional)
            logger.info(
                f"ℹ️  Funcionalidades opcionais desabilitadas: {features}. "
                f"Para todas as funcionalidades: pip install raizen-power-extractor[full]"
            )
    
    return _DEPS_STATUS


def get_status() -> dict:
    """Retorna status das dependências (roda check se ainda não rodou)."""
    if not _DEPS_STATUS:
        check_dependencies(warn=False)
    return _DEPS_STATUS


def print_status():
    """Imprime status de todas as dependências no console."""
    status = get_status()
    
    print("=" * 50)
    print("STATUS DAS DEPENDÊNCIAS")
    print("=" * 50)
    
    for pkg, info in sorted(status.items()):
        icon = "✅" if info["available"] else "❌"
        print(f"{icon} {pkg:25} - {info['feature']}")
    
    print("=" * 50)
    
    # Resumo
    available = sum(1 for s in status.values() if s["available"])
    total = len(status)
    print(f"Instaladas: {available}/{total}")
    
    if available < total:
        print("\nPara instalar todas: pip install raizen-power-extractor[full]")


def is_available(package: str) -> bool:
    """Verifica se um pacote específico está disponível."""
    status = get_status()
    return status.get(package, {}).get("available", False)


# Verificar dependências no import do módulo
# Só emite warnings se RAIZEN_CHECK_DEPS=1
import os
if os.environ.get("RAIZEN_CHECK_DEPS", "0") == "1":
    check_dependencies(warn=True)
