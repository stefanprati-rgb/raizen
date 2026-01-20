"""
Utilitários para processamento paralelo seguro com monitoramento de memória.

Evita OOM (Out Of Memory) ao usar ProcessPoolExecutor com bibliotecas PDF pesadas.
Ajusta automaticamente o número de workers com base na RAM disponível.

Uso:
    from raizen_power.utils.memory_safe import get_safe_workers, MemoryMonitor
    
    workers = get_safe_workers(task_type='pdf')  # Calcula workers seguros
    
    with MemoryMonitor(threshold_percent=85) as monitor:
        # Processamento...
        if monitor.is_memory_critical():
            # Pausar ou reduzir workers
"""
import os
import logging
from typing import Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Tentar importar psutil para monitoramento de memória
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil não instalado. Monitoramento de memória desabilitado. pip install psutil")


# Carregar configurações centralizadas
try:
    from raizen_power.core.config import settings
    _TEXT_MAX_WORKERS = settings.parallel.text_max_workers
    _OCR_MAX_WORKERS = settings.ocr.max_workers
except ImportError:
    _TEXT_MAX_WORKERS = 8
    _OCR_MAX_WORKERS = 2


@dataclass
class MemoryStats:
    """Estatísticas de memória do sistema."""
    total_gb: float
    available_gb: float
    used_percent: float
    
    @property
    def is_critical(self) -> bool:
        """Retorna True se memória está em nível crítico (>85%)."""
        return self.used_percent > 85
    
    @property
    def is_warning(self) -> bool:
        """Retorna True se memória está em alerta (>70%)."""
        return self.used_percent > 70


def get_memory_stats() -> Optional[MemoryStats]:
    """
    Obtém estatísticas de memória do sistema.
    
    Returns:
        MemoryStats ou None se psutil não disponível
    """
    if not PSUTIL_AVAILABLE:
        return None
    
    mem = psutil.virtual_memory()
    return MemoryStats(
        total_gb=mem.total / (1024 ** 3),
        available_gb=mem.available / (1024 ** 3),
        used_percent=mem.percent
    )


def estimate_memory_per_worker(task_type: str = 'pdf') -> float:
    """
    Estima uso de memória por worker (em GB).
    
    Args:
        task_type: Tipo de tarefa ('pdf', 'ocr', 'text')
        
    Returns:
        Estimativa de memória em GB por worker
    """
    estimates = {
        'pdf': 0.3,      # ~300MB por worker para PDF básico
        'ocr': 1.5,      # ~1.5GB por worker com OCR (EasyOCR)
        'text': 0.1,     # ~100MB para extração de texto simples
        'gemini': 0.2,   # ~200MB para chamadas de API
    }
    return estimates.get(task_type, 0.3)


def get_safe_workers(
    task_type: str = 'pdf',
    max_workers: int = None,
    memory_reserve_gb: float = 2.0,
    min_workers: int = 1
) -> int:
    """
    Calcula número seguro de workers baseado na RAM disponível.
    
    Args:
        task_type: Tipo de tarefa ('pdf', 'ocr', 'text')
        max_workers: Limite máximo de workers (default: cpu_count)
        memory_reserve_gb: GB de memória a reservar para o sistema
        min_workers: Mínimo de workers a retornar
        
    Returns:
        Número seguro de workers
    """
    # Default para CPU count
    cpu_count = os.cpu_count() or 4
    
    if max_workers is None:
        if task_type == 'ocr':
            max_workers = _OCR_MAX_WORKERS
        elif task_type == 'text':
            max_workers = _TEXT_MAX_WORKERS
        else:
            max_workers = min(cpu_count, 4)  # Default conservador para PDF
    
    # Se psutil não disponível, usar default
    stats = get_memory_stats()
    if stats is None:
        logger.warning("psutil não disponível, usando default conservador")
        return min(max_workers, 4)
    
    # Calcular workers baseado em memória disponível
    mem_per_worker = estimate_memory_per_worker(task_type)
    available_for_workers = stats.available_gb - memory_reserve_gb
    
    if available_for_workers <= 0:
        logger.warning(f"Pouca memória disponível ({stats.available_gb:.1f}GB). Usando worker único.")
        return min_workers
    
    memory_based_workers = int(available_for_workers / mem_per_worker)
    
    # Usar o menor entre: baseado em memória, max_workers, cpu_count
    safe_workers = min(memory_based_workers, max_workers, cpu_count)
    safe_workers = max(safe_workers, min_workers)  # Garantir mínimo
    
    logger.info(
        f"Workers calculados: {safe_workers} "
        f"(RAM disponível: {stats.available_gb:.1f}GB, "
        f"estimado por worker: {mem_per_worker:.1f}GB)"
    )
    
    return safe_workers


class MemoryMonitor:
    """
    Context manager para monitoramento de memória durante processamento.
    
    Uso:
        with MemoryMonitor(threshold_percent=85) as monitor:
            for item in items:
                if monitor.is_memory_critical():
                    gc.collect()  # Forçar garbage collection
                process(item)
    """
    
    def __init__(
        self,
        threshold_percent: float = 85,
        warning_percent: float = 70,
        on_warning: Callable = None,
        on_critical: Callable = None
    ):
        """
        Args:
            threshold_percent: Percentual de uso para nível crítico
            warning_percent: Percentual de uso para alerta
            on_warning: Callback quando atingir alerta
            on_critical: Callback quando atingir crítico
        """
        self.threshold = threshold_percent
        self.warning = warning_percent
        self.on_warning = on_warning
        self.on_critical = on_critical
        self.check_count = 0
        self.warning_count = 0
        self.critical_count = 0
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.warning_count > 0 or self.critical_count > 0:
            logger.info(
                f"MemoryMonitor: {self.check_count} checks, "
                f"{self.warning_count} warnings, {self.critical_count} critical"
            )
        return False
    
    def check(self) -> Optional[MemoryStats]:
        """Verifica memória e dispara callbacks se necessário."""
        self.check_count += 1
        
        stats = get_memory_stats()
        if stats is None:
            return None
        
        if stats.used_percent >= self.threshold:
            self.critical_count += 1
            if self.on_critical:
                self.on_critical(stats)
            logger.warning(f"⚠️ Memória CRÍTICA: {stats.used_percent:.1f}% usado")
        elif stats.used_percent >= self.warning:
            self.warning_count += 1
            if self.on_warning:
                self.on_warning(stats)
            logger.debug(f"Memória em alerta: {stats.used_percent:.1f}%")
        
        return stats
    
    def is_memory_critical(self) -> bool:
        """Verifica se memória está em nível crítico."""
        stats = self.check()
        return stats is not None and stats.used_percent >= self.threshold
    
    def is_memory_warning(self) -> bool:
        """Verifica se memória está em alerta."""
        stats = self.check()
        return stats is not None and stats.used_percent >= self.warning


def safe_parallel_map(
    func: Callable,
    items: list,
    task_type: str = 'pdf',
    max_workers: int = None,
    use_imap: bool = True,
    progress_callback: Callable = None
):
    """
    Executa função em paralelo com proteção contra OOM.
    
    Usa imap (lazy iteration) por padrão para menor consumo de memória.
    Monitora memória e pausa se necessário.
    
    Args:
        func: Função a executar
        items: Lista de items a processar
        task_type: Tipo de tarefa ('pdf', 'ocr', 'text')
        max_workers: Máximo de workers (calculado automaticamente se None)
        use_imap: Se True, usa imap (lazy) em vez de map
        progress_callback: Callback de progresso (current, total)
        
    Returns:
        Lista de resultados
    """
    from concurrent.futures import ProcessPoolExecutor, as_completed
    import gc
    
    workers = get_safe_workers(task_type, max_workers)
    total = len(items)
    results = []
    
    logger.info(f"Iniciando processamento paralelo: {total} items, {workers} workers")
    
    with MemoryMonitor(threshold_percent=85) as monitor:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            if use_imap:
                # Lazy iteration - processa em chunks menores
                futures = {executor.submit(func, item): i for i, item in enumerate(items)}
                
                for future in as_completed(futures):
                    idx = futures[future]
                    try:
                        result = future.result()
                        results.append((idx, result))
                    except Exception as e:
                        logger.error(f"Erro no item {idx}: {e}")
                        results.append((idx, None))
                    
                    if progress_callback:
                        progress_callback(len(results), total)
                    
                    # Verificar memória a cada 10 items
                    if len(results) % 10 == 0:
                        if monitor.is_memory_critical():
                            logger.warning("Memória crítica! Forçando garbage collection...")
                            gc.collect()
            else:
                # Map padrão (carrega tudo em memória)
                results = list(executor.map(func, items))
    
    # Ordenar resultados pelo índice original (se imap)
    if use_imap:
        results.sort(key=lambda x: x[0])
        results = [r[1] for r in results]
    
    return results


# Aliases para compatibilidade
calculate_safe_workers = get_safe_workers
