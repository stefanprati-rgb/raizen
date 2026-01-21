"""
PDF Model Identification com Visual Fingerprinting.

Sistema híbrido que combina perceptual hash (dHash) + análise estrutural
para identificar modelos de PDF e agrupar contratos similares.

Uso principal: Agrupar contratos por layout para otimizar envio ao Gemini.
Em vez de enviar 6000 PDFs, enviamos apenas 1 representante de cada layout.

Dependências:
    pip install imagehash Pillow  # Para hash visual
    pymupdf já instalado          # Para renderização

Uso:
    from raizen_power.utils.pdf_fingerprint import PDFModelIdentifier
    
    identifier = PDFModelIdentifier()
    result = identifier.classify_pdf("contrato.pdf", "CPFL")
    print(result["model_id"])  # "CPFL_5p_a1b2c3d4"
"""
import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Tentar importar imagehash
try:
    import imagehash
    from PIL import Image
    import io
    IMAGEHASH_AVAILABLE = True
except ImportError:
    IMAGEHASH_AVAILABLE = False
    logger.warning("imagehash não instalado. Usando fallback textual. pip install imagehash Pillow")


@dataclass
class PDFFingerprint:
    """Fingerprint composto de um PDF."""
    pdf_path: str
    page_count: int
    visual_hash: str      # dHash em hex
    structure_hash: str   # Hash das features estruturais
    composite_id: str     # ID único do modelo
    structure: Dict[str, Any]
    confidence: float
    created_at: str
    
    def to_dict(self) -> Dict:
        return asdict(self)


class PDFModelIdentifier:
    """
    Identificação inteligente de modelos de PDF.
    
    Combina:
    - Perceptual Hash (dHash) das primeiras 2 páginas
    - Análise estrutural (colunas, tabelas, densidade)
    - Similarity scoring (70% visual + 30% estrutural)
    
    CACHE: Fingerprints são cacheados por arquivo (mtime + size).
    Se o arquivo não mudou, usa cache em vez de recalcular o hash visual.
    """
    
    def __init__(
        self,
        db_path: str = "output/pdf_models_db.json",
        cache_path: str = "output/fingerprint_cache.json",
        pages_to_hash: int = 2,
        visual_threshold: int = 8,  # Hamming distance
        similarity_threshold: float = 0.85,
        use_cache: bool = True
    ):
        """
        Args:
            db_path: Caminho para banco de dados de modelos
            cache_path: Caminho para cache de fingerprints
            pages_to_hash: Páginas a usar para hash (default: 2)
            visual_threshold: Max hamming distance para considerar similar
            similarity_threshold: Min similarity score (0-1)
            use_cache: Se True, usa cache de fingerprints (default: True)
        """
        self.db_path = Path(db_path)
        self.cache_path = Path(cache_path)
        self.pages_to_hash = pages_to_hash
        self.visual_threshold = visual_threshold
        self.similarity_threshold = similarity_threshold
        self.use_cache = use_cache
        
        self.models_db = self._load_db()
        self._fingerprint_cache = self._load_cache() if use_cache else {}
        self._cache_hits = 0
        self._cache_misses = 0
    
    def _load_db(self) -> Dict:
        """Carrega banco de dados de modelos."""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"models": {}, "metadata": {"created": datetime.now().isoformat()}}
    
    def _save_db(self):
        """Persiste banco de dados."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(self.models_db, f, indent=2, ensure_ascii=False)
    
    def _load_cache(self) -> Dict:
        """Carrega cache de fingerprints."""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_cache(self):
        """Persiste cache de fingerprints."""
        if not self.use_cache:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, 'w', encoding='utf-8') as f:
            json.dump(self._fingerprint_cache, f, ensure_ascii=False)
    
    def _get_file_key(self, pdf_path: str) -> str:
        """Gera chave de cache baseada em path + mtime + size."""
        try:
            p = Path(pdf_path)
            stat = p.stat()
            # Chave: path canônico + mtime + size
            return f"{p.resolve()}|{stat.st_mtime}|{stat.st_size}"
        except:
            return pdf_path
    
    def _get_cached_fingerprint(self, pdf_path: str) -> Optional[PDFFingerprint]:
        """Busca fingerprint no cache se arquivo não mudou."""
        if not self.use_cache:
            return None
        
        key = self._get_file_key(pdf_path)
        
        if key in self._fingerprint_cache:
            self._cache_hits += 1
            cached = self._fingerprint_cache[key]
            return PDFFingerprint(**cached)
        
        self._cache_misses += 1
        return None
    
    def _cache_fingerprint(self, pdf_path: str, fingerprint: PDFFingerprint):
        """Adiciona fingerprint ao cache."""
        if not self.use_cache:
            return
        
        key = self._get_file_key(pdf_path)
        self._fingerprint_cache[key] = fingerprint.to_dict()
    
    def get_cache_stats(self) -> Dict:
        """Retorna estatísticas de cache."""
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "total": total,
            "hit_rate_percent": round(hit_rate, 1),
            "cache_size": len(self._fingerprint_cache),
        }
    
    # =========================================================================
    # STEP 1: Extract Visual Hash (usando PyMuPDF em vez de pdf2image)
    # =========================================================================
    
    def _render_page_to_image(self, page: fitz.Page) -> Optional['Image.Image']:
        """Renderiza página para PIL Image usando PyMuPDF."""
        if not IMAGEHASH_AVAILABLE:
            return None
        
        try:
            # Resolução baixa para speed (72 DPI = 1x)
            zoom = 1.5  # 108 DPI - bom balanço
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
            
            # Converter para PIL Image
            img = Image.frombytes("L", [pix.width, pix.height], pix.samples)
            return img
        except Exception as e:
            logger.warning(f"Erro ao renderizar página: {e}")
            return None
    
    def _extract_visual_hash(self, pdf_path: str) -> str:
        """
        Extrai dHash das primeiras páginas.
        
        dHash é mais robusto para layouts estruturados (PDFs).
        """
        if not IMAGEHASH_AVAILABLE:
            return self._extract_text_hash(pdf_path)[:16]
        
        try:
            doc = fitz.open(pdf_path)
            images = []
            
            for i in range(min(self.pages_to_hash, len(doc))):
                page = doc[i]
                img = self._render_page_to_image(page)
                if img:
                    images.append(img)
            
            doc.close()
            
            if not images:
                return "0" * 16
            
            # Combinar imagens verticalmente
            if len(images) > 1:
                combined = self._stack_images(images)
            else:
                combined = images[0]
            
            # Calcular dHash (mais robusto para layouts)
            dhash = imagehash.dhash(combined, hash_size=8)
            return str(dhash)
            
        except Exception as e:
            logger.warning(f"Erro ao extrair visual hash: {e}")
            return "0" * 16
    
    @staticmethod
    def _stack_images(images: List['Image.Image']) -> 'Image.Image':
        """Empilha imagens verticalmente."""
        if len(images) == 1:
            return images[0]
        
        # Redimensionar para mesma largura
        width = max(img.width for img in images)
        resized = []
        for img in images:
            if img.width != width:
                ratio = width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((width, new_height))
            resized.append(img)
        
        # Combinar
        total_height = sum(img.height for img in resized)
        combined = Image.new('L', (width, total_height))
        
        y_offset = 0
        for img in resized:
            combined.paste(img, (0, y_offset))
            y_offset += img.height
        
        return combined
    
    def _extract_text_hash(self, pdf_path: str) -> str:
        """Fallback: hash baseado em texto estrutural."""
        try:
            doc = fitz.open(pdf_path)
            structural_text = []
            
            for i in range(min(self.pages_to_hash, len(doc))):
                page = doc[i]
                text = page.get_text()
                
                # Extrair labels estruturais (terminam com : ou são curtos em CAPS)
                for line in text.split('\n'):
                    line = line.strip().upper()
                    if line.endswith(':') or (len(line) < 30 and line.isupper() and len(line) > 3):
                        structural_text.append(line[:20])
            
            doc.close()
            
            combined = "|".join(structural_text[:30])
            return hashlib.md5(combined.encode()).hexdigest()
            
        except Exception as e:
            logger.warning(f"Erro ao extrair text hash: {e}")
            return "0" * 32
    
    # =========================================================================
    # STEP 2: Extract Structural Features
    # =========================================================================
    
    def _extract_structural_features(self, pdf_path: str) -> Dict[str, Any]:
        """Analisa características estruturais do PDF."""
        try:
            doc = fitz.open(pdf_path)
            page = doc[0]
            
            # Extrair blocos de texto
            blocks = page.get_text("blocks")
            text_blocks = [b for b in blocks if b[6] == 0]  # Tipo 0 = texto
            
            # Features
            features = {
                "page_count": len(doc),
                "width": int(page.rect.width),
                "height": int(page.rect.height),
                "aspect_ratio": round(page.rect.width / page.rect.height, 2),
                "text_block_count": len(text_blocks),
                "has_tables": self._detect_tables(page),
                "text_density": self._calculate_text_density(text_blocks, page),
                "columns": self._estimate_columns(text_blocks),
            }
            
            doc.close()
            return features
            
        except Exception as e:
            logger.warning(f"Erro ao extrair features: {e}")
            return {"page_count": 0, "error": str(e)}
    
    @staticmethod
    def _detect_tables(page: fitz.Page) -> bool:
        """Detecta presença de tabelas."""
        try:
            tables = page.find_tables()
            return len(tables.tables) > 0
        except:
            # Fallback: detectar por linhas
            try:
                paths = page.get_drawings()
                lines = [p for p in paths if p.get("type") == "l"]
                return len(lines) > 5
            except:
                return False
    
    @staticmethod
    def _calculate_text_density(text_blocks: List, page: fitz.Page) -> float:
        """Calcula densidade de texto (0-1)."""
        if not text_blocks:
            return 0.0
        
        text_area = sum((b[2] - b[0]) * (b[3] - b[1]) for b in text_blocks)
        page_area = page.rect.width * page.rect.height
        
        return round(min(text_area / page_area, 1.0), 2) if page_area > 0 else 0.0
    
    @staticmethod
    def _estimate_columns(text_blocks: List) -> int:
        """Estima número de colunas."""
        if not text_blocks:
            return 1
        
        # Analisar distribuição de coordenadas X
        x_positions = sorted([b[0] for b in text_blocks])
        
        if len(x_positions) < 3:
            return 1
        
        # Detectar gaps significativos entre colunas
        gaps = [x_positions[i+1] - x_positions[i] for i in range(len(x_positions)-1)]
        large_gaps = sum(1 for g in gaps if g > 100)  # Gap > 100px
        
        return min(max(1, large_gaps + 1), 3)  # Max 3 colunas
    
    # =========================================================================
    # STEP 3: Create Composite Fingerprint
    # =========================================================================
    
    def _create_fingerprint(self, pdf_path: str, distributor: str) -> PDFFingerprint:
        """
        Cria fingerprint completo do PDF.
        
        Usa cache se disponível para evitar recálculo do hash visual (operação lenta).
        """
        # Verificar cache primeiro
        cached = self._get_cached_fingerprint(pdf_path)
        if cached:
            logger.debug(f"Cache hit para {Path(pdf_path).name}")
            return cached
        
        # Cache miss - calcular fingerprint
        visual_hash = self._extract_visual_hash(pdf_path)
        structure = self._extract_structural_features(pdf_path)
        
        # Hash estrutural
        structure_str = json.dumps(structure, sort_keys=True)
        structure_hash = hashlib.md5(structure_str.encode()).hexdigest()[:8]
        
        # Composite ID
        composite_str = f"{visual_hash}{structure_hash}"
        composite_id = hashlib.sha256(composite_str.encode()).hexdigest()[:8]
        
        fingerprint = PDFFingerprint(
            pdf_path=str(pdf_path),
            page_count=structure.get("page_count", 0),
            visual_hash=visual_hash,
            structure_hash=structure_hash,
            composite_id=composite_id,
            structure=structure,
            confidence=0.95 if IMAGEHASH_AVAILABLE else 0.70,
            created_at=datetime.now().isoformat()
        )
        
        # Salvar no cache
        self._cache_fingerprint(pdf_path, fingerprint)
        
        return fingerprint
    
    # =========================================================================
    # STEP 4: Similarity Calculation
    # =========================================================================
    
    def _hamming_distance(self, hash1: str, hash2: str) -> int:
        """Calcula distância de Hamming entre dois hashes."""
        if not IMAGEHASH_AVAILABLE:
            # Fallback: comparar strings
            return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
        
        try:
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            return h1 - h2
        except:
            return 64  # Max distance
    
    def _calculate_visual_similarity(self, hash1: str, hash2: str) -> float:
        """Similaridade visual (0-1)."""
        distance = self._hamming_distance(hash1, hash2)
        
        if distance <= 5:
            return 1.0
        elif distance <= 10:
            return 0.7
        elif distance <= 15:
            return 0.4
        else:
            return 0.0
    
    def _calculate_structural_similarity(self, s1: Dict, s2: Dict) -> float:
        """Compara features estruturais."""
        if not s1 or not s2:
            return 0.5
        
        scores = []
        
        # Página count
        page_diff = abs(s1.get("page_count", 0) - s2.get("page_count", 0))
        scores.append(1.0 if page_diff <= 1 else max(0, 1.0 - page_diff * 0.1))
        
        # Colunas
        col_diff = abs(s1.get("columns", 1) - s2.get("columns", 1))
        scores.append(1.0 if col_diff == 0 else 0.5)
        
        # Densidade
        density_diff = abs(s1.get("text_density", 0.5) - s2.get("text_density", 0.5))
        scores.append(max(0, 1.0 - density_diff * 2))
        
        # Tabelas
        scores.append(1.0 if s1.get("has_tables") == s2.get("has_tables") else 0.5)
        
        return sum(scores) / len(scores)
    
    def _calculate_composite_similarity(self, fp1: PDFFingerprint, fp2: PDFFingerprint) -> float:
        """Similaridade composta: 70% visual + 30% estrutural."""
        visual_sim = self._calculate_visual_similarity(fp1.visual_hash, fp2.visual_hash)
        struct_sim = self._calculate_structural_similarity(fp1.structure, fp2.structure)
        
        return (visual_sim * 0.70) + (struct_sim * 0.30)
    
    # =========================================================================
    # STEP 5: Find or Create Model
    # =========================================================================
    
    def classify_pdf(self, pdf_path: str, distributor: str) -> Dict[str, Any]:
        """
        Classifica PDF e encontra ou cria novo submodelo.
        
        Returns:
            {
                "model_id": "CPFL_5p_a1b2c3d4",
                "is_new_model": False,
                "confidence": 0.94,
                "fingerprint": {...},
                "similar_models": [...]
            }
        """
        # Criar fingerprint
        fingerprint = self._create_fingerprint(pdf_path, distributor)
        
        # Buscar modelos similares
        similar_models = self._find_similar_models(fingerprint, distributor)
        
        if similar_models:
            # Usar modelo existente
            best = similar_models[0]
            return {
                "model_id": best["model_id"],
                "is_new_model": False,
                "confidence": best["similarity"],
                "fingerprint": fingerprint.to_dict(),
                "similar_models": similar_models,
            }
        else:
            # Criar novo modelo
            model_id = f"{distributor}_{fingerprint.page_count}p_{fingerprint.composite_id}"
            self._save_model(model_id, fingerprint, distributor)
            
            return {
                "model_id": model_id,
                "is_new_model": True,
                "confidence": fingerprint.confidence,
                "fingerprint": fingerprint.to_dict(),
                "similar_models": [],
            }
    
    def _find_similar_models(self, fingerprint: PDFFingerprint, distributor: str) -> List[Dict]:
        """Encontra modelos similares no DB."""
        similar = []
        
        for model_id, model_data in self.models_db.get("models", {}).items():
            if model_data.get("distributor") != distributor:
                continue
            
            if "fingerprint" not in model_data:
                continue
            
            # Reconstruir fingerprint
            stored_fp = PDFFingerprint(**model_data["fingerprint"])
            
            # Calcular similaridade
            similarity = self._calculate_composite_similarity(fingerprint, stored_fp)
            
            if similarity >= self.similarity_threshold:
                similar.append({
                    "model_id": model_id,
                    "similarity": round(similarity, 3),
                })
        
        similar.sort(key=lambda x: x["similarity"], reverse=True)
        return similar[:5]
    
    def _save_model(self, model_id: str, fingerprint: PDFFingerprint, distributor: str):
        """Salva novo modelo no DB."""
        self.models_db["models"][model_id] = {
            "model_id": model_id,
            "distributor": distributor,
            "fingerprint": fingerprint.to_dict(),
            "created_at": datetime.now().isoformat(),
            "usage_count": 0,
        }
        self._save_db()
    
    def get_model_stats(self) -> Dict:
        """Estatísticas do DB."""
        models = self.models_db.get("models", {})
        
        by_distributor = {}
        by_pages = {}
        
        for model_id, data in models.items():
            dist = data.get("distributor", "unknown")
            pages = data.get("fingerprint", {}).get("page_count", 0)
            
            by_distributor[dist] = by_distributor.get(dist, 0) + 1
            by_pages[pages] = by_pages.get(pages, 0) + 1
        
        return {
            "total_models": len(models),
            "by_distributor": by_distributor,
            "by_page_count": by_pages,
        }
    
    def group_pdfs(self, pdf_paths: List[str], distributor: str) -> Dict[str, List[str]]:
        """
        Agrupa lista de PDFs por modelo.
        
        Returns:
            {"model_id": [pdf_paths, ...], ...}
        """
        groups = {}
        
        for path in pdf_paths:
            try:
                result = self.classify_pdf(path, distributor)
                model_id = result["model_id"]
                
                if model_id not in groups:
                    groups[model_id] = []
                groups[model_id].append(path)
                
            except Exception as e:
                logger.warning(f"Erro ao classificar {path}: {e}")
        
        return groups


# Funções de conveniência
def classify_pdf(pdf_path: str, distributor: str = "UNKNOWN") -> Dict:
    """Classifica um PDF rapidamente."""
    identifier = PDFModelIdentifier()
    return identifier.classify_pdf(pdf_path, distributor)


def group_pdfs_by_model(pdf_paths: List[str], distributor: str = "UNKNOWN") -> Dict[str, List[str]]:
    """Agrupa PDFs por modelo."""
    identifier = PDFModelIdentifier()
    return identifier.group_pdfs(pdf_paths, distributor)
