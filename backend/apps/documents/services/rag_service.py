# apps/documents/services/rag_service.py
"""
RAG (Retrieval Augmented Generation) Service

Este servicio implementa la búsqueda semántica de chunks relevantes
basada en la pregunta del usuario, utilizando embeddings y pgvector.

Versión 2.0 (mejorada):
- Usa modelo de 768 dimensiones (paraphrase-multilingual-mpnet-base-v2)
- Chunks limpios sin encabezados repetitivos
- Consistente con Document.clean_embedding
- Fallback a embeddings legacy de 384d si no hay clean_content_embedding
"""
import logging
import re
from typing import List, Dict, Optional
import numpy as np

from django.db.models import F
from pgvector.django import CosineDistance

from apps.documents.models import Document, DocumentChunk
from apps.documents.services.chunk_embedding_service import get_chunk_embedding_service

logger = logging.getLogger(__name__)


class RAGService:
    """
    Servicio RAG para recuperar chunks relevantes basados en la pregunta del usuario.
    
    Enfoque simplificado (sin keywords hardcoded):
    1. Expande la pregunta con sinónimos legales
    2. Convierte a embedding usando sentence-transformers
    3. Busca chunks por similitud semántica (pgvector + cosine)
    4. Incluye chunks adyacentes para contexto narrativo
    5. Ordena por posición en documento
    6. Modelo LLM (3b + 8k context) interpreta el contenido
    """
    
    # Expansiones de términos legales para mejor matching semántico
    LEGAL_EXPANSIONS = {
        'demandante': ['actor', 'recurrente', 'solicitante', 'peticionante'],
        'demandado': ['emplazado', 'requerido', 'accionado'],
        'juez': ['magistrado', 'juzgador', 'vocal'],
        'sentencia': ['fallo', 'resolución', 'decisión'],
        'expediente': ['caso', 'proceso', 'causa'],
        'prueba': ['evidencia', 'medio probatorio', 'acreditación'],
        'apelación': ['recurso', 'impugnación'],
        'fundada': ['procedente', 'amparada', 'estimada'],
        'infundada': ['improcedente', 'desestimada', 'rechazada'],
        'decidieron': ['resolvieron', 'ordenaron', 'declararon', 'fallaron'],
        'decisión': ['fallo', 'resolución', 'pronunciamiento', 'sentencia'],
    }
    
    def __init__(self, top_k: int = 5, similarity_threshold: float = 0.3):
        """
        Inicializa el servicio RAG.
        
        Args:
            top_k: Número máximo de chunks a recuperar
            similarity_threshold: Umbral mínimo de similitud (0-1, mayor es más similar)
        """
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        self.embedding_service = get_chunk_embedding_service()
        logger.info(f"RAGService v2.0 initialized: top_k={top_k}, threshold={similarity_threshold}, model=768d")
    
    def _expand_query(self, question: str) -> str:
        """
        Expande la consulta con términos legales sinónimos para mejor matching.
        
        Args:
            question: Pregunta original
            
        Returns:
            Pregunta expandida con sinónimos
        """
        expanded = question.lower()
        additions = []
        
        for term, synonyms in self.LEGAL_EXPANSIONS.items():
            if term in expanded:
                # Agregar algunos sinónimos relevantes
                additions.extend(synonyms[:2])
        
        if additions:
            expanded_query = f"{question} {' '.join(additions)}"
            logger.info(f"🔄 Query expandida: '{question}' → agregados: {additions}")
            return expanded_query
        
        return question
    
    def _clean_chunk_content(self, content: str) -> str:
        """
        Limpia el contenido del chunk removiendo marcadores de página y normalizando.
        
        Args:
            content: Contenido original del chunk
            
        Returns:
            Contenido limpio
        """
        # Remover marcadores de página (ambos formatos)
        cleaned = re.sub(r'\[Página \d+\]\s*', '', content)
        cleaned = re.sub(r'\n*## PÁGINA \d+\n*', '\n', cleaned)
        # Normalizar espacios múltiples
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r' {2,}', ' ', cleaned)
        return cleaned.strip()
    
    def encode_question(self, question: str, expand: bool = True) -> Optional[np.ndarray]:
        """
        Convierte la pregunta del usuario a embedding.
        
        Args:
            question: Pregunta del usuario
            expand: Si expandir la query con sinónimos legales
            
        Returns:
            Embedding como numpy array de 768 dimensiones, o None si falla
        """
        if not question or not question.strip():
            logger.warning("🔴 RAG: Pregunta vacía, no se puede generar embedding")
            return None
        
        try:
            # Expandir query si está habilitado
            query_to_encode = self._expand_query(question) if expand else question
            
            # Usar modelo de 768d (mismo que clean_content_embedding)
            logger.info(f"🔵 RAG: Generando embedding 768d para: '{query_to_encode[:80]}...'")
            embedding = self.embedding_service.encode_query(query_to_encode, normalize=True)
            
            if embedding is not None:
                logger.info(f"✅ RAG: Embedding generado exitosamente (shape: {embedding.shape})")
            return embedding
        except Exception as e:
            logger.error(f"🔴 RAG: Error al generar embedding para pregunta: {e}")
            return None
    
    def retrieve_relevant_chunks(
        self, 
        document: Document, 
        question: str,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        include_adjacent: bool = True
    ) -> List[Dict]:
        """
        Recupera los chunks más relevantes para una pregunta sobre un documento.
        
        Versión 2.0:
        - Preferentemente usa clean_content_embedding (768d, texto limpio)
        - Fallback a content_embedding (384d) si no hay clean embeddings
        - Incluye chunks adyacentes para contexto narrativo
        
        Args:
            document: Documento del cual buscar chunks
            question: Pregunta del usuario
            top_k: Número de chunks a recuperar (usa default si no se especifica)
            similarity_threshold: Umbral de similitud (usa default si no se especifica)
            include_adjacent: Si incluir chunks adyacentes para contexto
            
        Returns:
            Lista de diccionarios ordenados por posición en documento
        """
        top_k = top_k or self.top_k
        threshold = similarity_threshold or self.similarity_threshold
        
        # 1. Generar embedding de la pregunta (768d con expansión de términos legales)
        question_embedding = self.encode_question(question, expand=True)
        if question_embedding is None:
            logger.warning("No se pudo generar embedding para la pregunta")
            return []
        
        # 2. Determinar qué campo de embedding usar
        # Preferir clean_content_embedding (768d), fallback a content_embedding (384d)
        chunks_with_clean = DocumentChunk.objects.filter(
            document_id=document,
            clean_content_embedding__isnull=False
        )
        
        use_clean_embedding = chunks_with_clean.exists()
        
        if use_clean_embedding:
            embedding_field = 'clean_content_embedding'
            chunks_query = chunks_with_clean
            logger.info(f"🔵 RAG v2.0: Usando clean_content_embedding (768d, texto limpio)")
        else:
            # Fallback a embedding legacy
            chunks_query = DocumentChunk.objects.filter(
                document_id=document,
                content_embedding__isnull=False
            )
            embedding_field = 'content_embedding'
            logger.warning(f"⚠️ RAG: Usando content_embedding legacy (384d). "
                          f"Ejecuta 'python manage.py regenerate_chunk_embeddings' para mejor calidad")
            
            # Si usamos embedding legacy, necesitamos generar query embedding con modelo de 384d
            # Importamos el servicio legacy
            from apps.documents.services.embedding_service import get_embedding_service
            legacy_service = get_embedding_service()
            question_embedding = legacy_service.encode_text(question, normalize=True)
            if question_embedding is None:
                logger.warning("No se pudo generar embedding legacy para la pregunta")
                return []
        
        if not chunks_query.exists():
            logger.warning(f"🔴 RAG: Documento {document.document_id} no tiene chunks con embeddings")
            return []
        
        total_chunks = chunks_query.count()
        logger.info(f"🔵 RAG: Buscando en {total_chunks} chunks del documento (campo: {embedding_field})")
        
        # 3. Buscar por similitud semántica usando pgvector
        try:
            embedding_list = question_embedding.tolist()
            
            # Obtener más chunks para poder incluir adyacentes
            search_limit = top_k * 3 if include_adjacent else top_k * 2
            
            # Usar el campo de embedding correcto dinámicamente
            relevant_chunks = chunks_query.annotate(
                distance=CosineDistance(embedding_field, embedding_list)
            ).order_by('distance')[:search_limit]
            
            # Convertir a lista de resultados con similitud
            results = []
            selected_orders = set()
            
            logger.info(f"🔵 RAG: Analizando similitud de chunks...")
            
            for chunk in relevant_chunks:
                # Convertir distancia coseno a similitud (0-1)
                similarity = 1 - (chunk.distance / 2)
                
                if similarity >= threshold and len(results) < top_k:
                    selected_orders.add(chunk.order_number)
                    results.append({
                        'content': self._clean_chunk_content(chunk.content),
                        'order_number': chunk.order_number,
                        'similarity': round(similarity, 4),
                        'chunk_id': str(chunk.chunk_id),
                        'is_adjacent': False,
                        'embedding_type': '768d' if use_clean_embedding else '384d'
                    })
                    logger.info(f"   ✅ Chunk #{chunk.order_number}: similitud={similarity:.2%} (INCLUIDO)")
            
            # 4. Incluir chunks adyacentes para contexto narrativo
            if include_adjacent and results:
                adjacent_orders = set()
                for order in selected_orders:
                    adjacent_orders.add(order - 1)  # Chunk anterior
                    adjacent_orders.add(order + 1)  # Chunk siguiente
                
                # Remover los que ya están seleccionados y los inválidos
                adjacent_orders -= selected_orders
                adjacent_orders = {o for o in adjacent_orders if o >= 1 and o <= total_chunks}
                
                # Buscar chunks adyacentes
                if adjacent_orders:
                    adjacent_chunks = DocumentChunk.objects.filter(
                        document_id=document,
                        order_number__in=adjacent_orders,
                        content_embedding__isnull=False
                    )
                    
                    for chunk in adjacent_chunks:
                        results.append({
                            'content': self._clean_chunk_content(chunk.content),
                            'order_number': chunk.order_number,
                            'similarity': 0.5,  # Similitud base para adyacentes
                            'chunk_id': str(chunk.chunk_id),
                            'is_adjacent': True
                        })
                        logger.info(f"   📎 Chunk #{chunk.order_number}: (ADYACENTE para contexto)")
            
            # 5. Ordenar por posición en documento para coherencia narrativa
            results.sort(key=lambda x: x['order_number'])
            
            logger.info(f"🎯 RAG: Seleccionados {len(results)} chunks total")
            
            if results:
                main_chunks = [r for r in results if not r['is_adjacent']]
                adjacent_chunks = [r for r in results if r['is_adjacent']]
                similarities = [r['similarity'] for r in main_chunks]
                logger.info(f"📊 RAG: {len(main_chunks)} principales + {len(adjacent_chunks)} adyacentes")
                if similarities:
                    logger.info(f"📊 RAG Similitudes: min={min(similarities):.2%}, max={max(similarities):.2%}")
                logger.info(f"📊 RAG Orden: {[r['order_number'] for r in results]}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error en búsqueda de chunks relevantes: {e}", exc_info=True)
            return []
    
    def get_context_from_chunks(
        self, 
        chunks: List[Dict], 
        max_chars: int = 6000,
        include_metadata: bool = True
    ) -> str:
        """
        Construye el contexto a partir de los chunks recuperados.
        
        Formato simple con metadatos para ayudar al LLM a entender estructura.
        
        Args:
            chunks: Lista de chunks recuperados (ya ordenados por posición)
            max_chars: Máximo de caracteres para el contexto
            include_metadata: Si incluir indicadores de posición y tipo
            
        Returns:
            Texto del contexto formateado para el LLM
        """
        if not chunks:
            return ""
        
        context_parts = []
        current_length = 0
        
        for chunk in chunks:
            content = chunk['content']
            order = chunk.get('order_number', '?')
            similarity = chunk.get('similarity', 0)
            is_adjacent = chunk.get('is_adjacent', False)
            
            if include_metadata:
                # Metadatos útiles para el LLM
                if is_adjacent:
                    chunk_text = f"[Fragmento #{order} - Contexto adicional]:\n{content}"
                else:
                    chunk_text = f"[Fragmento #{order} - Relevancia: {similarity:.0%}]:\n{content}"
            else:
                chunk_text = content
            
            # Verificar si excede el límite
            if current_length + len(chunk_text) + 20 > max_chars:
                remaining = max_chars - current_length - 50
                if remaining > 300:
                    chunk_text = chunk_text[:remaining] + "..."
                    context_parts.append(chunk_text)
                break
            
            context_parts.append(chunk_text)
            current_length += len(chunk_text) + 20
        
        # Separadores claros
        context = "\n\n---\n\n".join(context_parts)
        
        main_count = sum(1 for c in chunks if not c.get('is_adjacent'))
        adj_count = sum(1 for c in chunks if c.get('is_adjacent'))
        logger.info(f"📝 Contexto: {len(context)} chars ({main_count} principales, {adj_count} adyacentes)")
        
        return context
    
    def check_document_has_chunks(self, document: Document) -> Dict:
        """
        Verifica si un documento tiene chunks y embeddings.
        
        Args:
            document: Documento a verificar
            
        Returns:
            Diccionario con estadísticas de chunks
        """
        total_chunks = DocumentChunk.objects.filter(document_id=document).count()
        chunks_with_embeddings = DocumentChunk.objects.filter(
            document_id=document,
            content_embedding__isnull=False
        ).count()
        
        has_rag = chunks_with_embeddings > 0
        
        logger.info(f"📊 RAG Check: Documento {document.document_id}")
        logger.info(f"   - Total chunks: {total_chunks}")
        logger.info(f"   - Chunks con embeddings: {chunks_with_embeddings}")
        logger.info(f"   - RAG habilitado: {'✅ SÍ' if has_rag else '❌ NO'}")
        
        return {
            'total_chunks': total_chunks,
            'chunks_with_embeddings': chunks_with_embeddings,
            'has_rag_capability': has_rag
        }


# Singleton instance para reutilizar
_rag_service_instance = None


def get_rag_service(top_k: int = 5, similarity_threshold: float = 0.3) -> RAGService:
    """
    Obtiene la instancia singleton del servicio RAG.
    
    Args:
        top_k: Número de chunks a recuperar
        similarity_threshold: Umbral de similitud
    """
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService(top_k=top_k, similarity_threshold=similarity_threshold)
    return _rag_service_instance
