"""
Gerenciamento de blacklist dinâmica para códigos recorrentes.

Detecta e filtra códigos que aparecem em mais de N% dos documentos,
tipicamente códigos de sistema (usina, formulário, protocolo).
"""
import json
from pathlib import Path
from typing import Dict, List, Set


class DynamicBlacklist:
    """
    Detecta e filtra códigos que aparecem em mais de N% dos documentos.
    Esses são tipicamente códigos de sistema (usina, formulário, protocolo).
    """
    
    DEFAULT_BLACKLIST_FILE = Path("output/blacklist_codigos.json")
    THRESHOLD_PERCENT = 80  # Se aparece em >80% dos docs, é código de sistema
    
    def __init__(self, blacklist_file: Path = None):
        """
        Inicializa a blacklist.
        
        Args:
            blacklist_file: Caminho para o arquivo de blacklist (opcional)
        """
        self.blacklist_file = blacklist_file or self.DEFAULT_BLACKLIST_FILE
        self.blacklist: Set[str] = set()
        self.frequency: Dict[str, int] = {}
        self.total_docs: int = 0
        self._load_blacklist()
    
    def _load_blacklist(self):
        """Carrega blacklist de arquivo se existir."""
        if self.blacklist_file.exists():
            try:
                with open(self.blacklist_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.blacklist = set(data.get('blacklist', []))
                    self.frequency = data.get('frequency', {})
                    self.total_docs = data.get('total_docs', 0)
            except:
                pass
    
    def save_blacklist(self):
        """Salva blacklist em arquivo."""
        self.blacklist_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.blacklist_file, 'w', encoding='utf-8') as f:
            json.dump({
                'blacklist': list(self.blacklist),
                'frequency': self.frequency,
                'total_docs': self.total_docs
            }, f, indent=2)
    
    def update_frequency(self, numbers: List[str]):
        """Atualiza contagem de frequência após processar um documento."""
        self.total_docs += 1
        seen_in_doc = set(numbers)
        
        for num in seen_in_doc:
            self.frequency[num] = self.frequency.get(num, 0) + 1
    
    def analyze_and_update_blacklist(self):
        """Analisa frequências e atualiza blacklist."""
        if self.total_docs < 10:  # Precisa de pelo menos 10 docs
            return
        
        threshold = self.total_docs * (self.THRESHOLD_PERCENT / 100)
        
        new_blacklist = set()
        for num, count in self.frequency.items():
            if count >= threshold:
                new_blacklist.add(num)
        
        self.blacklist = new_blacklist
        self.save_blacklist()
    
    def is_blacklisted(self, number: str) -> bool:
        """Verifica se número está na blacklist."""
        return number in self.blacklist
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas da blacklist."""
        return {
            'total_docs': self.total_docs,
            'blacklist_size': len(self.blacklist),
            'blacklist': list(self.blacklist)[:10]  # Primeiros 10
        }
    
    def reset(self):
        """Reseta a blacklist e frequências."""
        self.blacklist = set()
        self.frequency = {}
        self.total_docs = 0
