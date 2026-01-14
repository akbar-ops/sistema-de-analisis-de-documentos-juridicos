# apps/documents/services/clean_embeddings_service.py
"""
Servicio para generar embeddings sobre texto LIMPIO (sin encabezados/ruido).

NOTA: Ya NO se remueven stopwords. Solo se limpia ruido técnico:
- Encabezados repetitivos
- Artefactos OCR
- Marcadores de página

Esto mantiene consistencia con ChunkEmbeddingService para RAG.

Versión 3.0: Stopwords DESHABILITADOS para simplificar y unificar el sistema.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer

# Importar servicio de limpieza de headers (lazy load)
try:
    from apps.documents.services.header_cleaner_service import get_header_cleaner_service
    HEADER_CLEANER_AVAILABLE = True
except ImportError:
    HEADER_CLEANER_AVAILABLE = False

logger = logging.getLogger(__name__)


class CleanEmbeddingsService:
    """
    Servicio para generar embeddings semánticos sobre texto limpio.
    
    v3.0: SIMPLIFICADO - Ya NO se remueven stopwords.
    Solo se limpia ruido técnico (headers, OCR, marcadores de página).
    
    Esto unifica el comportamiento con ChunkEmbeddingService para RAG.
    
    Características:
    - Usa modelo multilingüe optimizado para español legal
    - Limpia encabezados y ruido técnico (NO stopwords)
    - Chunking inteligente con overlap
    - Weighted pooling: prioriza chunks iniciales del documento
    - Compatible con pgvector (768 dimensiones)
    
    Uso:
        service = CleanEmbeddingsService()
        embedding = service.generate_document_embedding(text)
    """
    
    # Modelo multilingüe de alta calidad (768 dimensiones)
    # Mejor que MiniLM para español y textos legales
    MODEL_NAME = 'paraphrase-multilingual-mpnet-base-v2'
    EMBEDDING_DIMENSION = 768
    
    # Parámetros de chunking optimizados para documentos legales
    DEFAULT_CHUNK_SIZE = 400  # Palabras por chunk
    DEFAULT_CHUNK_OVERLAP = 40  # Overlap en palabras
    MIN_CHUNK_WORDS = 50  # Mínimo de palabras para chunk válido
    
    def __init__(self, model_name: str = None, clean_headers: bool = True):
        """
        Inicializa el servicio de embeddings limpios.
        
        Args:
            model_name: Nombre del modelo SentenceTransformer (opcional)
            clean_headers: Si True, limpia encabezados repetitivos antes de procesar
        """
        self.model_name = model_name or self.MODEL_NAME
        self.clean_headers = clean_headers
        self._model = None  # Lazy loading
        self._header_cleaner = None  # Lazy loading
        
        logger.info(f"CleanEmbeddingsService v3.0 inicializado (modelo: {self.model_name}, clean_headers: {clean_headers}, stopwords: DESHABILITADO)")
    
    @property
    def header_cleaner(self):
        """Lazy load del servicio de limpieza de encabezados."""
        if self._header_cleaner is None and self.clean_headers and HEADER_CLEANER_AVAILABLE:
            self._header_cleaner = get_header_cleaner_service()
        return self._header_cleaner
    
    @property
    def model(self) -> SentenceTransformer:
        """Carga el modelo de forma lazy (solo cuando se necesita)."""
        if self._model is None:
            logger.info(f"Cargando modelo {self.model_name}...")
            # Forzar CPU para evitar problemas de memoria GPU
            self._model = SentenceTransformer(self.model_name, device='cpu')
            logger.info(f"Modelo cargado en CPU. Dimensión: {self._model.get_sentence_embedding_dimension()}")
        return self._model
    
    def clean_text(self, text: str) -> str:
        """
        Limpia el texto removiendo SOLO ruido técnico (NO stopwords).
        
        v3.0: Ya NO remueve stopwords. Solo limpia:
        - Encabezados/pies de página repetitivos
        - Artefactos OCR
        - Marcadores de página
        
        Args:
            text: Texto original del documento
            
        Returns:
            Texto limpio (manteniendo todas las palabras)
        """
        if not text or not text.strip():
            return ""
        
        # Limpiar encabezados repetitivos y ruido técnico
        if self.header_cleaner:
            text = self.header_cleaner.clean_document_text(text)
        
        # Normalizar espacios (sin remover palabras)
        text = ' '.join(text.split())
        
        return text
    
    def clean_text_preserve_structure(self, text: str) -> str:
        """
        Limpia encabezados pero preserva estructura de texto.
        
        A diferencia de clean_text(), este método:
        - Limpia encabezados/pies de página
        - Limpia artefactos OCR
        - PERO mantiene la estructura del texto (párrafos, etc.)
        - NO remueve stopwords
        
        Útil para RAG y visualización del texto.
        
        Args:
            text: Texto original
            
        Returns:
            Texto limpio manteniendo estructura
        """
        if not text or not text.strip():
            return ""
        
        if self.header_cleaner:
            return self.header_cleaner.clean_document_text(text)
        
        return text
    
    def create_chunks(
        self,
        text: str, 
        chunk_size: int = None,
        overlap: int = None,
        min_words: int = None
    ) -> List[str]:
        """
        Divide texto limpio en chunks con overlap.
        
        Args:
            text: Texto (preferiblemente ya limpio)
            chunk_size: Tamaño de chunk en palabras
            overlap: Overlap en palabras
            min_words: Mínimo de palabras para chunk válido
            
        Returns:
            Lista de chunks
        """
        chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE
        overlap = overlap or self.DEFAULT_CHUNK_OVERLAP
        min_words = min_words or self.MIN_CHUNK_WORDS
        
        words = text.split()
        
        if len(words) < min_words:
            # Texto muy corto, usar completo como único chunk
            return [text] if text.strip() else []
        
        chunks = []
        step = chunk_size - overlap
        
        for i in range(0, len(words), step):
            chunk_words = words[i:i + chunk_size]
            
            # Solo agregar si tiene suficientes palabras
            if len(chunk_words) >= min_words:
                chunks.append(' '.join(chunk_words))
        
        # Si no hay chunks (caso raro), usar texto completo
        if not chunks and text.strip():
            chunks = [text]
        
        return chunks
    
    def generate_chunk_embeddings(
        self, 
        chunks: List[str],
        normalize: bool = True
    ) -> np.ndarray:
        """
        Genera embeddings para una lista de chunks.
        
        Args:
            chunks: Lista de textos de chunks
            normalize: Si True, normaliza embeddings (recomendado)
            
        Returns:
            Array numpy de shape (n_chunks, embedding_dim)
        """
        if not chunks:
            return np.array([])
        
        # Filtrar chunks vacíos
        valid_chunks = [c.strip() for c in chunks if c and c.strip()]
        
        if not valid_chunks:
            return np.array([])
        
        # Generar embeddings
        embeddings = self.model.encode(
            valid_chunks,
            normalize_embeddings=normalize,
            convert_to_numpy=True,
            show_progress_bar=False
        )
        
        return embeddings
    
    def weighted_pooling(
        self, 
        embeddings: np.ndarray,
        strategy: str = 'weighted_start'
    ) -> np.ndarray:
        """
        Aplica pooling para combinar embeddings de chunks en un solo vector.
        
        Estrategias disponibles:
        - 'mean': Promedio simple
        - 'weighted_start': Prioriza chunks del principio (recomendado para docs legales)
        - 'max': Máximo por dimensión
        
        Args:
            embeddings: Array de embeddings (n_chunks, dim)
            strategy: Estrategia de pooling
            
        Returns:
            Embedding único (dim,)
        """
        if len(embeddings) == 0:
            return None
        
        if len(embeddings) == 1:
            return embeddings[0]
        
        n_chunks = len(embeddings)
        
        if strategy == 'mean':
            pooled = np.mean(embeddings, axis=0)
            
        elif strategy == 'weighted_start':
            # Priorizar chunks del principio del documento
            # Los primeros chunks suelen contener información más relevante
            # (identificación del caso, partes, hechos principales)
            
            # Crear pesos decrecientes: [1.0, 0.9, 0.8, ..., 0.5] (mínimo 0.5)
            weights = np.linspace(1.0, 0.5, n_chunks)
            
            # Normalizar pesos para que sumen 1
            weights = weights / weights.sum()
            
            # Aplicar weighted average
            pooled = np.average(embeddings, axis=0, weights=weights)
            
        elif strategy == 'max':
            pooled = np.max(embeddings, axis=0)
            
        else:
            raise ValueError(f"Estrategia no soportada: {strategy}")
        
        # Renormalizar el embedding resultante
        norm = np.linalg.norm(pooled)
        if norm > 0:
            pooled = pooled / norm
        
        return pooled
    
    def generate_document_embedding(
        self,
        text: str,
        clean_text: bool = False, ## Limpiar stopwords por defecto NO
        pooling_strategy: str = 'weighted_start'
    ) -> Optional[np.ndarray]:
        """
        Genera el embedding representativo de un documento completo.
        
        Pipeline completo:
        1. Limpiar texto (remover stopwords) [opcional]
        2. Crear chunks
        3. Generar embeddings por chunk
        4. Aplicar pooling para obtener embedding único
        
        Args:
            text: Texto del documento
            clean_text: Si True, limpia stopwords primero
            pooling_strategy: Estrategia de pooling ('weighted_start' recomendado)
            
        Returns:
            Embedding numpy de 768 dimensiones, o None si falla
        """
        if not text or not text.strip():
            logger.warning("Texto vacío, no se puede generar embedding")
            return None
        
        try:
            # 1. Limpiar texto
            if clean_text:
                processed_text = self.clean_text(text)
                logger.debug(
                    f"Texto limpiado: {len(text.split())} → {len(processed_text.split())} palabras"
                )
            else:
                processed_text = text
            
            # Verificar que quedó contenido después de limpiar
            if not processed_text or len(processed_text.split()) < 10:
                logger.warning("Texto muy corto después de limpiar, usando original")
                processed_text = text
            
            # 2. Crear chunks
            chunks = self.create_chunks(processed_text)
            logger.debug(f"Chunks creados: {len(chunks)}")
            
            # 3. Generar embeddings de chunks
            chunk_embeddings = self.generate_chunk_embeddings(chunks)
            
            if len(chunk_embeddings) == 0:
                logger.warning("No se generaron embeddings de chunks")
                return None
            
            # 4. Aplicar pooling
            doc_embedding = self.weighted_pooling(chunk_embeddings, strategy=pooling_strategy)
            
            if doc_embedding is None:
                logger.warning("Pooling retornó None")
                return None
            
            logger.info(
                f"Embedding generado: {len(chunks)} chunks → vector {doc_embedding.shape}"
            )
            
            return doc_embedding
            
        except Exception as e:
            logger.error(f"Error generando embedding de documento: {e}", exc_info=True)
            return None
    
    def generate_query_embedding(
        self,
        query: str,
        clean_query: bool = True
    ) -> Optional[np.ndarray]:
        """
        Genera embedding para una consulta de búsqueda.
        
        Args:
            query: Texto de la consulta
            clean_query: Si True, limpia stopwords
            
        Returns:
            Embedding numpy normalizado
        """
        if not query or not query.strip():
            return None
        
        try:
            # Limpiar query si se solicita
            if clean_query:
                processed_query = self.clean_text(query)
                # Si quedó muy corto, usar original
                if len(processed_query.split()) < 2:
                    processed_query = query
            else:
                processed_query = query
            
            # Generar embedding
            embedding = self.model.encode(
                processed_query,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generando embedding de query: {e}")
            return None
    
    def compute_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Calcula similitud coseno entre dos embeddings.
        
        Args:
            embedding1: Primer embedding (normalizado)
            embedding2: Segundo embedding (normalizado)
            
        Returns:
            Similitud coseno (0-1 para embeddings normalizados)
        """
        if embedding1 is None or embedding2 is None:
            return 0.0
        
        # Para embeddings normalizados, dot product = cosine similarity
        return float(np.dot(embedding1, embedding2))
    
    def batch_generate_embeddings(
        self,
        texts: List[str],
        clean_texts: bool = True,
        pooling_strategy: str = 'weighted_start',
        show_progress: bool = True
    ) -> List[Optional[np.ndarray]]:
        """
        Genera embeddings para múltiples documentos.
        
        Args:
            texts: Lista de textos de documentos
            clean_texts: Si True, limpia cada texto
            pooling_strategy: Estrategia de pooling
            show_progress: Si True, muestra progreso
            
        Returns:
            Lista de embeddings (o None para textos inválidos)
        """
        embeddings = []
        
        for i, text in enumerate(texts):
            if show_progress and (i + 1) % 10 == 0:
                logger.info(f"Procesando documento {i + 1}/{len(texts)}")
            
            emb = self.generate_document_embedding(
                text,
                clean_text=clean_texts,
                pooling_strategy=pooling_strategy
            )
            embeddings.append(emb)
        
        return embeddings
    
    def get_text_statistics(self, text: str) -> Dict[str, any]:
        """
        Obtiene estadísticas del texto antes y después de limpiar.
        
        Útil para debugging y análisis.
        
        Args:
            text: Texto original
            
        Returns:
            Diccionario con estadísticas
        """
        original_words = len(text.split()) if text else 0
        cleaned_text = self.clean_text(text)
        cleaned_words = len(cleaned_text.split()) if cleaned_text else 0
        
        reduction = 0.0
        if original_words > 0:
            reduction = (1 - cleaned_words / original_words) * 100
        
        chunks = self.create_chunks(cleaned_text)
        
        return {
            'original_words': original_words,
            'cleaned_words': cleaned_words,
            'reduction_percent': round(reduction, 2),
            'num_chunks': len(chunks),
            'avg_chunk_words': round(np.mean([len(c.split()) for c in chunks]), 2) if chunks else 0
        }


# =============================================================================
# Singleton para reutilizar modelo cargado
# =============================================================================

_clean_embedding_service_instance = None


def get_clean_embedding_service() -> CleanEmbeddingsService:
    """
    Obtiene la instancia singleton del servicio de embeddings limpios.
    
    Esto evita cargar el modelo múltiples veces en memoria.
    El modelo paraphrase-multilingual-mpnet-base-v2 usa ~400MB de RAM.
    """
    global _clean_embedding_service_instance
    if _clean_embedding_service_instance is None:
        _clean_embedding_service_instance = CleanEmbeddingsService()
    return _clean_embedding_service_instance
