"""
Gerenciamento de blacklist dinâmica para códigos recorrentes.

Detecta e filtra códigos que aparecem em mais de N% dos documentos,
tipicamente códigos de sistema (usina, formulário, protocolo).

IMPORTANTE: Thread-safe para uso com ProcessPoolExecutor.
- Workers usam BlacklistCollector (apenas coleta, sem I/O)
- Processo principal usa DynamicBlacklist para agregar e salvar
"""
import json
from pathlib import Path
from typing import Dict, List, Set
from dataclasses import dataclass, field


# Carregar configurações centralizadas
try:
    from raizen_power.core.config import settings
    _DEFAULT_THRESHOLD = settings.blacklist.threshold_percent
    _DEFAULT_MIN_DOCS = settings.blacklist.min_docs_for_analysis
    _DEFAULT_BLACKLIST_FILE = Path(settings.blacklist.output_file)
except ImportError:
    _DEFAULT_THRESHOLD = 80
    _DEFAULT_MIN_DOCS = 10
    _DEFAULT_BLACKLIST_FILE = Path("output/blacklist_codigos.json")


@dataclass
class BlacklistCollector:
    """
    Coletor leve para uso em workers paralelos.
    
    NÃO faz I/O de disco. Apenas coleta dados em memória.
    Após processamento, retornar os dados para o processo principal agregar.
    
    Uso em worker:
        collector = BlacklistCollector()
        collector.add_document(["12345", "67890"])
        return collector.get_data()  # Retorna dict serializável
    """
    frequency: Dict[str, int] = field(default_factory=dict)
    total_docs: int = 0
    
    def add_document(self, numbers: List[str]):
        """Registra números encontrados em um documento."""
        self.total_docs += 1
        seen = set(numbers)
        for num in seen:
            self.frequency[num] = self.frequency.get(num, 0) + 1
    
    def get_data(self) -> Dict:
        """Retorna dados para serialização/agregação."""
        return {
            "frequency": self.frequency,
            "total_docs": self.total_docs
        }


class DynamicBlacklist:
    """
    Blacklist dinâmica thread-safe.
    
    PADRÃO DE USO:
    1. Workers usam BlacklistCollector (sem I/O)
    2. Processo principal agrega resultados com merge_from_collectors()
    3. Processo principal salva com save_blacklist()
    
    Exemplo:
        # No processo principal (após processamento paralelo):
        blacklist = DynamicBlacklist()
        blacklist.merge_from_collectors([worker1_data, worker2_data, ...])
        blacklist.analyze_and_update()
        blacklist.save()
    """
    
    def __init__(
        self,
        blacklist_file: Path = None,
        threshold_percent: int = None,
        auto_load: bool = True
    ):
        """
        Args:
            blacklist_file: Caminho para arquivo de persistência
            threshold_percent: % de docs para considerar código de sistema
            auto_load: Se True, carrega blacklist existente do disco
        """
        self.blacklist_file = blacklist_file or _DEFAULT_BLACKLIST_FILE
        self.threshold_percent = threshold_percent or _DEFAULT_THRESHOLD
        self.min_docs = _DEFAULT_MIN_DOCS
        
        self.blacklist: Set[str] = set()
        self.frequency: Dict[str, int] = {}
        self.total_docs: int = 0
        
        if auto_load:
            self._load()
    
    def _load(self):
        """Carrega blacklist do disco (apenas no processo principal)."""
        if self.blacklist_file.exists():
            try:
                with open(self.blacklist_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.blacklist = set(data.get('blacklist', []))
                    self.frequency = data.get('frequency', {})
                    self.total_docs = data.get('total_docs', 0)
            except (json.JSONDecodeError, IOError):
                pass
    
    def save(self):
        """Salva blacklist no disco (apenas no processo principal)."""
        self.blacklist_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.blacklist_file, 'w', encoding='utf-8') as f:
            json.dump({
                'blacklist': list(self.blacklist),
                'frequency': self.frequency,
                'total_docs': self.total_docs
            }, f, indent=2, ensure_ascii=False)
    
    # Aliases para compatibilidade
    save_blacklist = save
    
    def merge_from_collectors(self, collector_data_list: List[Dict]):
        """
        Agrega dados de múltiplos BlacklistCollectors.
        
        Chamado no processo principal após processamento paralelo.
        
        Args:
            collector_data_list: Lista de dicts retornados por collector.get_data()
        """
        for data in collector_data_list:
            freq = data.get("frequency", {})
            docs = data.get("total_docs", 0)
            
            self.total_docs += docs
            
            for num, count in freq.items():
                self.frequency[num] = self.frequency.get(num, 0) + count
    
    def update_frequency(self, numbers: List[str]):
        """
        Atualiza frequência diretamente (uso single-threaded).
        
        AVISO: Não usar em workers paralelos! Use BlacklistCollector.
        """
        self.total_docs += 1
        seen = set(numbers)
        for num in seen:
            self.frequency[num] = self.frequency.get(num, 0) + 1
    
    def analyze_and_update(self):
        """Analisa frequências e atualiza blacklist (sem salvar)."""
        if self.total_docs < self.min_docs:
            return
        
        threshold = self.total_docs * (self.threshold_percent / 100)
        
        new_blacklist = set()
        for num, count in self.frequency.items():
            if count >= threshold:
                new_blacklist.add(num)
        
        self.blacklist = new_blacklist
    
    def analyze_and_update_blacklist(self):
        """Alias com save automático (compatibilidade)."""
        self.analyze_and_update()
        self.save()
    
    def is_blacklisted(self, number: str) -> bool:
        """Verifica se número está na blacklist."""
        return number in self.blacklist
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas."""
        return {
            'total_docs': self.total_docs,
            'blacklist_size': len(self.blacklist),
            'blacklist': list(self.blacklist)[:10],
            'top_frequencies': dict(
                sorted(self.frequency.items(), key=lambda x: -x[1])[:10]
            )
        }
    
    def reset(self):
        """Reseta blacklist e frequências."""
        self.blacklist = set()
        self.frequency = {}
        self.total_docs = 0


# ============================================================================
# EXEMPLO DE USO THREAD-SAFE
# ============================================================================
"""
from concurrent.futures import ProcessPoolExecutor
from raizen_power.utils.blacklist import BlacklistCollector, DynamicBlacklist

def process_pdf(pdf_path):
    \"\"\"Função executada em worker paralelo.\"\"\"
    collector = BlacklistCollector()
    
    # ... processar PDF ...
    ucs_found = extract_ucs(pdf_path)
    collector.add_document(ucs_found)
    
    return {
        "pdf": pdf_path,
        "ucs": ucs_found,
        "blacklist_data": collector.get_data()  # Retorna dados para agregação
    }

def main():
    # Processamento paralelo
    pdfs = get_all_pdfs()
    
    with ProcessPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(process_pdf, pdfs))
    
    # Agregar blacklist no processo principal (thread-safe)
    blacklist = DynamicBlacklist()
    collector_data = [r["blacklist_data"] for r in results]
    blacklist.merge_from_collectors(collector_data)
    blacklist.analyze_and_update()
    blacklist.save()  # Único ponto de escrita no disco
"""
