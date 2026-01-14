# apps/documents/services/chunk_embedding_service.py
"""
Servicio de Embeddings para Chunks - Versión Mejorada.

Este servicio genera embeddings de alta calidad para chunks usando:
- El modelo multilingüe de 768 dimensiones (paraphrase-multilingual-mpnet-base-v2)
- Limpieza de encabezados repetitivos antes de generar embeddings
- Mismo modelo que clean_embedding del documento

Uso:
    service = get_chunk_embedding_service()
    embedding = service.generate_chunk_embedding(chunk_content)
    embeddings = service.generate_batch_embeddings(chunk_contents)
"""

import logging
import re
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Intentar importar el servicio de limpieza de headers
try:
    from apps.documents.services.header_cleaner_service import get_header_cleaner_service
    HEADER_CLEANER_AVAILABLE = True
except ImportError:
    HEADER_CLEANER_AVAILABLE = False
    logger.warning("HeaderCleanerService no disponible, los chunks no se limpiarán")


class ChunkEmbeddingService:
    """
    Servicio para generar embeddings de alta calidad para chunks.
    
    Características:
    - Usa modelo de 768 dimensiones (mejor calidad)
    - Limpia encabezados repetitivos de chunks
    - Compatible con el modelo usado para Document.clean_embedding
    - Optimizado para búsqueda semántica RAG
    """
    
    # Mismo modelo que CleanEmbeddingsService para consistencia
    MODEL_NAME = 'paraphrase-multilingual-mpnet-base-v2'
    EMBEDDING_DIMENSION = 768
    
    # Patrones a limpiar de chunks
    CHUNK_NOISE_PATTERNS = [
        r'\[Página \d+\]\s*',           # Marcadores de página [Página X]
        r'## PÁGINA \d+\n*',             # Marcadores ## PÁGINA X
        r'Página\s+\d+\s+de\s+\d+',      # Página X de Y
        r'/g\d+',                         # Artefactos OCR
        r'^\s*\d+\s*$',                   # Solo números (pies de página)
    ]
    
    def __init__(self, clean_chunks: bool = True):
        """
        Inicializa el servicio.
        
        Args:
            clean_chunks: Si limpiar encabezados de chunks antes de generar embedding
        """
        self.clean_chunks = clean_chunks
        self._model = None  # Lazy loading
        self._header_cleaner = None  # Lazy loading
        self._compiled_patterns = [re.compile(p, re.MULTILINE) for p in self.CHUNK_NOISE_PATTERNS]
        
        logger.info(f"ChunkEmbeddingService inicializado (modelo: {self.MODEL_NAME}, clean: {clean_chunks})")
    
    @property
    def model(self) -> SentenceTransformer:
        """Carga el modelo de forma lazy."""
        if self._model is None:
            logger.info(f"Cargando modelo {self.MODEL_NAME}...")
            self._model = SentenceTransformer(self.MODEL_NAME, device='cpu')
            logger.info(f"Modelo cargado. Dimensión: {self._model.get_sentence_embedding_dimension()}")
        return self._model
    
    @property
    def header_cleaner(self):
        """Lazy load del servicio de limpieza."""
        if self._header_cleaner is None and self.clean_chunks and HEADER_CLEANER_AVAILABLE:
            self._header_cleaner = get_header_cleaner_service()
        return self._header_cleaner
    
    def clean_chunk_content(self, content: str) -> str:
        """
        Limpia el contenido de un chunk antes de generar embedding.
        
        Elimina:
        - Marcadores de página
        - Artefactos OCR
        - Encabezados repetitivos (si el servicio está disponible)
        
        Args:
            content: Contenido original del chunk
            
        Returns:
            Contenido limpio
        """
        if not content or not content.strip():
            return ""
        
        cleaned = content
        
        # Aplicar patrones de limpieza de chunks
        for pattern in self._compiled_patterns:
            cleaned = pattern.sub('', cleaned)
        
        # Usar servicio de limpieza de headers si está disponible
        if self.header_cleaner:
            cleaned = self.header_cleaner.clean_document_text(cleaned)
        
        # Normalizar espacios
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r' {2,}', ' ', cleaned)
        
        return cleaned.strip()
    
    def generate_chunk_embedding(
        self, 
        content: str, 
        normalize: bool = True,
        apply_cleaning: bool = True
    ) -> Optional[np.ndarray]:
        """
        Genera embedding para un chunk.
        
        Args:
            content: Contenido del chunk
            normalize: Si normalizar el embedding (recomendado para similitud)
            apply_cleaning: Si aplicar limpieza antes de generar embedding
            
        Returns:
            Embedding como numpy array de 768 dimensiones, o None si falla
        """
        if not content or not content.strip():
            logger.warning("Chunk vacío, no se puede generar embedding")
            return None
        
        try:
            # Limpiar si está habilitado
            text_to_encode = content
            if apply_cleaning and self.clean_chunks:
                text_to_encode = self.clean_chunk_content(content)
                if not text_to_encode.strip():
                    logger.warning("Chunk vacío después de limpieza")
                    return None
            
            # Generar embedding
            embedding = self.model.encode(
                text_to_encode,
                normalize_embeddings=normalize,
                show_progress_bar=False
            )
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generando embedding para chunk: {e}")
            return None
    
    def generate_batch_embeddings(
        self,
        contents: List[str],
        normalize: bool = True,
        apply_cleaning: bool = True,
        batch_size: int = 32
    ) -> List[Optional[np.ndarray]]:
        """
        Genera embeddings para múltiples chunks de manera eficiente.
        
        Args:
            contents: Lista de contenidos de chunks
            normalize: Si normalizar embeddings
            apply_cleaning: Si aplicar limpieza
            batch_size: Tamaño de batch para procesamiento
            
        Returns:
            Lista de embeddings (puede contener None para chunks inválidos)
        """
        if not contents:
            return []
        
        results = []
        valid_contents = []
        valid_indices = []
        
        # Preprocesar: limpiar y filtrar
        for i, content in enumerate(contents):
            if not content or not content.strip():
                results.append(None)
                continue
            
            if apply_cleaning and self.clean_chunks:
                cleaned = self.clean_chunk_content(content)
                if not cleaned.strip():
                    results.append(None)
                    continue
                valid_contents.append(cleaned)
            else:
                valid_contents.append(content.strip())
            
            valid_indices.append(i)
            results.append(None)  # Placeholder, será reemplazado
        
        if not valid_contents:
            logger.warning("No hay chunks válidos para procesar")
            return results
        
        try:
            # Generar embeddings en batches
            all_embeddings = []
            for i in range(0, len(valid_contents), batch_size):
                batch = valid_contents[i:i + batch_size]
                batch_embeddings = self.model.encode(
                    batch,
                    normalize_embeddings=normalize,
                    show_progress_bar=False,
                    batch_size=batch_size
                )
                all_embeddings.extend(batch_embeddings)
            
            # Colocar embeddings en posiciones correctas
            for idx, embedding in zip(valid_indices, all_embeddings):
                results[idx] = embedding
            
            logger.info(f"Generados {len(all_embeddings)} embeddings de 768d para chunks")
            return results
            
        except Exception as e:
            logger.error(f"Error en batch embedding: {e}")
            return results
    
    def encode_query(self, query: str, normalize: bool = True) -> Optional[np.ndarray]:
        """
        Genera embedding para una consulta/pregunta.
        
        Método específico para queries de RAG. No aplica limpieza de headers.
        
        Args:
            query: Texto de la consulta
            normalize: Si normalizar el embedding
            
        Returns:
            Embedding de 768 dimensiones
        """
        if not query or not query.strip():
            logger.warning("Query vacía")
            return None
        
        try:
            embedding = self.model.encode(
                query.strip(),
                normalize_embeddings=normalize,
                show_progress_bar=False
            )
            return embedding
        except Exception as e:
            logger.error(f"Error generando embedding para query: {e}")
            return None


# Singleton
_chunk_embedding_service: Optional[ChunkEmbeddingService] = None


def get_chunk_embedding_service() -> ChunkEmbeddingService:
    """
    Obtiene instancia singleton del servicio.
    
    Returns:
        ChunkEmbeddingService instance
    """
    global _chunk_embedding_service
    
    if _chunk_embedding_service is None:
        _chunk_embedding_service = ChunkEmbeddingService()
    
    return _chunk_embedding_service
