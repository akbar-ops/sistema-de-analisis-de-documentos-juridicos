from sentence_transformers import SentenceTransformer
import logging
from typing import List, Union
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Servicio para generar embeddings usando sentence-transformers.
    Utiliza el modelo paraphrase-multilingual-MiniLM-L12-v2 que:
    - Genera embeddings de 384 dimensiones
    - Soporta múltiples idiomas incluyendo español
    - Es eficiente y ligero para producción
    """
    
    # Modelo multilingüe optimizado para español
    MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'
    EMBEDDING_DIMENSION = 384
    
    def __init__(self):
        """Inicializa el modelo de sentence-transformers."""
        try:
            logger.info(f"Cargando modelo {self.MODEL_NAME}...")
            self.model = SentenceTransformer(self.MODEL_NAME)
            logger.info(f"Modelo cargado exitosamente. Dimensión: {self.EMBEDDING_DIMENSION}")
        except Exception as e:
            logger.error(f"Error al cargar el modelo: {e}")
            raise
    
    def encode_text(self, text: Union[str, List[str]], normalize: bool = True) -> Union[np.ndarray, List[np.ndarray]]:
        """
        Genera embeddings para uno o múltiples textos.
        
        Args:
            text: Texto o lista de textos a codificar
            normalize: Si True, normaliza los embeddings (recomendado para búsqueda por similitud)
        
        Returns:
            Embedding(s) como array numpy. Si se pasa una lista, retorna lista de arrays.
        """
        try:
            if isinstance(text, str):
                text = [text]
                single_input = True
            else:
                single_input = False
            
            # Filtrar textos vacíos
            valid_texts = [t.strip() for t in text if t and t.strip()]
            
            if not valid_texts:
                logger.warning("No hay textos válidos para codificar")
                return None if single_input else []
            
            # Generar embeddings
            embeddings = self.model.encode(
                valid_texts,
                normalize_embeddings=normalize,
                show_progress_bar=False
            )
            
            logger.info(f"Generados {len(embeddings)} embeddings de dimensión {embeddings[0].shape[0]}")
            
            return embeddings[0] if single_input else embeddings
            
        except Exception as e:
            logger.error(f"Error al generar embeddings: {e}")
            raise
    
    def encode_document_summary(self, summary: str) -> np.ndarray:
        """
        Genera embedding para el resumen de un documento.
        
        Args:
            summary: Texto del resumen del documento
        
        Returns:
            Embedding como array numpy de 384 dimensiones
        """
        if not summary or not summary.strip():
            logger.warning("Resumen vacío, no se puede generar embedding")
            return None
        
        return self.encode_text(summary, normalize=True)
    
    def encode_enhanced_document(self, document_data: dict) -> np.ndarray:
        """
        Genera un embedding enriquecido combinando múltiples campos del documento.
        
        V3.1: Máximo énfasis en CONTENIDO ESPECÍFICO del resumen mejorado por Ollama.
        
        Pesos optimizados (con prompts mejorados de Ollama):
        - Resumen (PESO MÁXIMO - 4x): Contenido ESPECÍFICO y único del caso
        - Materia jurídica (PESO ALTO - 2x): Tema específico con agravantes
        - Título específico (PESO MEDIO - 1x): Ahora más único gracias a Ollama mejorado
        - Metadatos comunes (PESO MÍNIMO): Solo para contexto
        
        Args:
            document_data: Diccionario con los campos del documento
        
        Returns:
            Embedding como array numpy de 384 dimensiones
        """
        # Construir texto enriquecido priorizando especificidad máxima
        parts = []
        
        # 1. RESUMEN - PESO MÁXIMO (repetido 4 veces para máxima influencia)
        # Con prompts mejorados, ahora contiene detalles únicos específicos
        if document_data.get('summary'):
            summary_text = document_data['summary']
            # Expandir a 1000 caracteres para capturar más detalles
            if len(summary_text) > 1000:
                summary_text = summary_text[:1000] + "..."
            
            # Repetir 4 veces con diferentes contextos para dar máximo peso
            parts.append(f"Contenido principal: {summary_text}")
            parts.append(f"Resumen del caso: {summary_text}")
            parts.append(f"Hechos y argumentación: {summary_text}")
            parts.append(f"Detalles específicos: {summary_text}")
        
        # 2. MATERIA JURÍDICA - PESO ALTO (repetido 2 veces)
        # Con prompts mejorados, ahora incluye agravantes y especificidades
        if document_data.get('legal_subject'):
            subject = document_data['legal_subject']
            parts.append(f"Materia específica: {subject}")
            parts.append(f"Tema jurídico: {subject}")
        
        # 3. TÍTULO - PESO MEDIO (1 vez)
        # Con prompts mejorados, ahora más específico y único
        if document_data.get('title'):
            parts.append(f"Título: {document_data['title']}")
        
        # 4. ÁREA LEGAL - PESO MÍNIMO (1 vez, sin repetición)
        # Contexto general, no debe dominar
        if document_data.get('legal_area'):
            parts.append(f"Área: {document_data['legal_area']}")
        
        # 5. PERSONAS - PESO MEDIO (nombres específicos)
        persons = document_data.get('persons', [])
        
        # 5. PERSONAS - PESO MEDIO (nombres específicos)
        persons = document_data.get('persons', [])
        if persons:
            # Solo personas principales (demandante, demandado)
            demandantes = [p['name'] for p in persons if p.get('role') == 'demandante']
            demandados = [p['name'] for p in persons if p.get('role') == 'demandado']
            
            if demandantes:
                names = ', '.join(demandantes[:3])
                parts.append(f"Demandante: {names}")
            
            if demandados:
                names = ', '.join(demandados[:3])
                parts.append(f"Demandado: {names}")
        
        # 6. NÚMERO DE EXPEDIENTE - Para documentos del mismo caso
        if document_data.get('case_number'):
            parts.append(f"Expediente {document_data['case_number']}")
        
        # Unir todas las partes
        enhanced_text = ". ".join(parts)
        
        if not enhanced_text.strip():
            logger.warning("No hay suficiente información para generar embedding enriquecido")
            return None
        
        logger.info(
            f"V3.1: Embedding prioriza contenido específico - {len(enhanced_text)} caracteres "
            f"({len(parts)} componentes, resumen x4 con prompts mejorados)"
        )
        return self.encode_text(enhanced_text, normalize=True)
    
    def encode_chunk(self, chunk_content: str) -> np.ndarray:
        """
        Genera embedding para el contenido de un chunk.
        
        Args:
            chunk_content: Texto del chunk
        
        Returns:
            Embedding como array numpy de 384 dimensiones
        """
        if not chunk_content or not chunk_content.strip():
            logger.warning("Chunk vacío, no se puede generar embedding")
            return None
        
        return self.encode_text(chunk_content, normalize=True)
    
    def encode_chunks_batch(self, chunks: List[str], batch_size: int = 32) -> List[np.ndarray]:
        """
        Genera embeddings para múltiples chunks de manera eficiente.
        
        Args:
            chunks: Lista de textos de chunks
            batch_size: Tamaño de lote para procesamiento por batches
        
        Returns:
            Lista de embeddings como arrays numpy
        """
        if not chunks:
            logger.warning("Lista de chunks vacía")
            return []
        
        try:
            # Filtrar chunks vacíos
            valid_chunks = [c.strip() for c in chunks if c and c.strip()]
            
            if not valid_chunks:
                logger.warning("No hay chunks válidos para codificar")
                return []
            
            # Procesar en batches para mejor eficiencia
            all_embeddings = []
            for i in range(0, len(valid_chunks), batch_size):
                batch = valid_chunks[i:i + batch_size]
                batch_embeddings = self.model.encode(
                    batch,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                    batch_size=batch_size
                )
                all_embeddings.extend(batch_embeddings)
            
            logger.info(f"Generados {len(all_embeddings)} embeddings en batches de {batch_size}")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Error al generar embeddings en batch: {e}")
            raise


# Singleton instance para reutilizar el modelo cargado
_embedding_service_instance = None


def get_embedding_service() -> EmbeddingService:
    """
    Obtiene la instancia singleton del servicio de embeddings.
    Esto evita cargar el modelo múltiples veces en memoria.
    """
    global _embedding_service_instance
    if _embedding_service_instance is None:
        _embedding_service_instance = EmbeddingService()
    return _embedding_service_instance
