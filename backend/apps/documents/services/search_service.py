# apps/documents/services/search_service.py
import logging
from typing import List, Optional, Dict, Any, Tuple
from django.db.models import Q, QuerySet
from pgvector.django import CosineDistance

from apps.documents.models import Document, LegalArea, DocumentType
from apps.documents.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class DocumentSearchService:
    """
    Servicio para búsqueda avanzada de documentos.
    
    Combina:
    - Filtros tradicionales (case_number, resolution_number, legal_area, doc_type, etc.)
    - Búsqueda semántica usando embeddings y pgvector
    """
    
    def __init__(self):
        self.embedding_service = get_embedding_service()
    
    def search(
        self,
        query: Optional[str] = None,
        case_number: Optional[str] = None,
        resolution_number: Optional[str] = None,
        legal_area_id: Optional[int] = None,
        doc_type_id: Optional[int] = None,
        issue_place: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        semantic_search: bool = True,
        top_n: int = 20,
        min_similarity: float = 0.3
    ) -> List[Tuple[Document, Optional[float]]]:
        """
        Búsqueda avanzada de documentos combinando filtros y búsqueda semántica.
        
        Args:
            query: Texto libre para búsqueda semántica
            case_number: Filtro por número de expediente (búsqueda parcial)
            resolution_number: Filtro por número de resolución (búsqueda parcial)
            legal_area_id: Filtro por ID de área legal
            doc_type_id: Filtro por ID de tipo de documento
            issue_place: Filtro por lugar de emisión (búsqueda parcial)
            date_from: Fecha desde (YYYY-MM-DD)
            date_to: Fecha hasta (YYYY-MM-DD)
            semantic_search: Si True, usa búsqueda semántica con embeddings
            top_n: Número máximo de resultados para búsqueda semántica
            min_similarity: Similitud mínima para búsqueda semántica (0-1)
        
        Returns:
            Lista de tuplas (Document, similarity_score)
            similarity_score es None si no se usó búsqueda semántica
        """
        try:
            # Iniciar con todos los documentos procesados
            queryset = Document.objects.filter(
                status='processed'
            ).select_related('doc_type', 'legal_area')
            
            # Aplicar filtros tradicionales
            queryset = self._apply_filters(
                queryset,
                case_number=case_number,
                resolution_number=resolution_number,
                legal_area_id=legal_area_id,
                doc_type_id=doc_type_id,
                issue_place=issue_place,
                date_from=date_from,
                date_to=date_to
            )
            
            # Si hay query y búsqueda semántica está activada
            if query and semantic_search:
                return self._semantic_search(
                    query=query,
                    base_queryset=queryset,
                    top_n=top_n,
                    min_similarity=min_similarity
                )
            
            # Si hay query pero no búsqueda semántica, hacer búsqueda textual
            elif query:
                queryset = queryset.filter(
                    Q(title__icontains=query) |
                    Q(summary__icontains=query) |
                    Q(content__icontains=query) |
                    Q(legal_subject__icontains=query)
                )
            
            # Ordenar por fecha de creación descendente
            queryset = queryset.order_by('-created_at')[:top_n]
            
            # Retornar sin scores de similitud
            return [(doc, None) for doc in queryset]
            
        except Exception as e:
            logger.error(f"Error in search: {e}", exc_info=True)
            return []
    
    def _apply_filters(
        self,
        queryset: QuerySet,
        case_number: Optional[str] = None,
        resolution_number: Optional[str] = None,
        legal_area_id: Optional[int] = None,
        doc_type_id: Optional[int] = None,
        issue_place: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> QuerySet:
        """
        Aplica filtros tradicionales al queryset.
        
        Args:
            queryset: QuerySet base
            case_number: Número de expediente (parcial)
            resolution_number: Número de resolución (parcial)
            legal_area_id: ID de área legal
            doc_type_id: ID de tipo de documento
            issue_place: Lugar de emisión (parcial)
            date_from: Fecha desde
            date_to: Fecha hasta
        
        Returns:
            QuerySet filtrado
        """
        # Filtro por número de expediente
        if case_number:
            queryset = queryset.filter(
                case_number__icontains=case_number
            )
        
        # Filtro por número de resolución
        if resolution_number:
            queryset = queryset.filter(
                resolution_number__icontains=resolution_number
            )
        
        # Filtro por área legal
        if legal_area_id:
            queryset = queryset.filter(legal_area_id=legal_area_id)
        
        # Filtro por tipo de documento
        if doc_type_id:
            queryset = queryset.filter(doc_type_id=doc_type_id)
        
        # Filtro por lugar de emisión
        if issue_place:
            queryset = queryset.filter(
                issue_place__icontains=issue_place
            )
        
        # Filtro por rango de fechas
        if date_from:
            queryset = queryset.filter(document_date__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(document_date__lte=date_to)
        
        return queryset
    
    def _semantic_search(
        self,
        query: str,
        base_queryset: QuerySet,
        top_n: int = 20,
        min_similarity: float = 0.3
    ) -> List[Tuple[Document, float]]:
        """
        Realiza búsqueda semántica usando embeddings.
        
        Args:
            query: Texto de búsqueda
            base_queryset: QuerySet base con filtros ya aplicados
            top_n: Número máximo de resultados
            min_similarity: Similitud mínima (0-1)
        
        Returns:
            Lista de tuplas (Document, similarity_score)
        """
        try:
            # Generar embedding para la query
            query_embedding = self.embedding_service.encode_text(query, normalize=True)
            
            if query_embedding is None:
                logger.warning("Could not generate embedding for query")
                return [(doc, None) for doc in base_queryset[:top_n]]
            
            # Filtrar solo documentos con enhanced_embedding
            queryset = base_queryset.filter(
                enhanced_embedding__isnull=False
            )
            
            # Calcular cosine distance y ordenar
            queryset = queryset.annotate(
                distance=CosineDistance('enhanced_embedding', query_embedding.tolist())
            ).order_by('distance')
            
            # Filtrar por similitud mínima
            if min_similarity > 0:
                max_distance = 1.0 - min_similarity
                queryset = queryset.filter(distance__lte=max_distance)
            
            # Limitar resultados
            queryset = queryset[:top_n]
            
            # Convertir a lista de tuplas con similarity score
            results = []
            for doc in queryset:
                similarity_score = 1.0 - float(doc.distance)
                results.append((doc, similarity_score))
            
            logger.info(
                f"Semantic search returned {len(results)} results for query: '{query[:50]}...'"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}", exc_info=True)
            # Fallback a búsqueda sin semántica
            return [(doc, None) for doc in base_queryset[:top_n]]
    
    def search_by_text(
        self,
        query: str,
        top_n: int = 10,
        min_similarity: float = 0.4
    ) -> List[Tuple[Document, float]]:
        """
        Búsqueda semántica simple solo con texto.
        Útil para autocompletado o sugerencias.
        
        Args:
            query: Texto de búsqueda
            top_n: Número máximo de resultados
            min_similarity: Similitud mínima (0-1)
        
        Returns:
            Lista de tuplas (Document, similarity_score)
        """
        return self.search(
            query=query,
            semantic_search=True,
            top_n=top_n,
            min_similarity=min_similarity
        )
    
    def get_available_filters(self) -> Dict[str, Any]:
        """
        Retorna los valores disponibles para filtros.
        
        Returns:
            Diccionario con legal_areas y doc_types disponibles
        """
        try:
            legal_areas = list(
                LegalArea.objects.filter(is_active=True)
                .values('area_id', 'name')
                .order_by('name')
            )
            
            doc_types = list(
                DocumentType.objects.filter(is_active=True)
                .values('type_id', 'name')
                .order_by('name')
            )
            
            return {
                'legal_areas': legal_areas,
                'doc_types': doc_types
            }
        except Exception as e:
            logger.error(f"Error getting available filters: {e}")
            return {
                'legal_areas': [],
                'doc_types': []
            }
