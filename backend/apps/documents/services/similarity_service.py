# apps/documents/services/similarity_service.py
"""
Servicio de Similitud de Documentos

Proporciona búsqueda de documentos similares usando:
- Similitud semántica basada en embeddings (pgvector)
- Scoring híbrido con metadatos legales
- Penalizaciones configurables por inconsistencias
- Soporte para clean_embedding (768d) o enhanced_embedding (384d)

Versión: 3.1 - Soporte para clean_embedding
"""
import logging
from typing import List, Optional, Tuple, Dict, Any, Literal
from django.db.models import F, Q
from pgvector.django import CosineDistance

from apps.documents.models import Document

logger = logging.getLogger(__name__)

# Tipo para seleccionar el campo de embedding a usar
EmbeddingField = Literal['clean_embedding', 'enhanced_embedding']


class SimilarityReason:
    """Clase para representar las razones de similitud entre documentos"""
    
    def __init__(self):
        self.reasons = []
        self.score_breakdown = {}
        self.total_score = 0.0
        self.penalties = 0.0
    
    def add_reason(self, category: str, detail: str, weight: float, matched: bool = True):
        """Agrega una razón de similitud (o penalización si weight < 0)"""
        if matched:
            self.reasons.append({
                'category': category,
                'detail': detail,
                'weight': weight,
                'is_penalty': weight < 0
            })
            self.score_breakdown[category] = self.score_breakdown.get(category, 0) + weight
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte las razones a diccionario"""
        # Calcular boost y penalizaciones directamente del score_breakdown
        metadata_boost = sum(w for w in self.score_breakdown.values() if w > 0)
        penalties = sum(w for w in self.score_breakdown.values() if w < 0)
        
        return {
            'reasons': self.reasons,
            'score_breakdown': self.score_breakdown,
            'semantic_similarity': self.total_score,
            'metadata_boost': metadata_boost,
            'penalties': penalties,  # Calculado del score_breakdown, no de self.penalties
            'raw_hybrid_score': self.total_score + sum(self.score_breakdown.values())
        }


class DocumentSimilarityService:
    """
    Servicio para encontrar documentos jurisprudenciales similares.
    
    Optimizado para ayudar a jueces a encontrar:
    1. Casos análogos y precedentes relevantes
    2. Jurisprudencia comparable para redacción de resoluciones
    3. Decisiones en situaciones jurídicas similares
    
    Utiliza scoring híbrido CALIBRADO para evitar scores inflados:
    - Similitud semántica como base (con threshold estricto)
    - Boost moderado por coincidencias de metadatos jurídicos
    - Penalización por diferencias significativas
    
    Soporta dos tipos de embeddings:
    - clean_embedding (768d): Basado en texto limpio sin stopwords, recomendado
    - enhanced_embedding (384d): Embedding anterior basado en resumen
    """
    
    # V3: Sistema de similitud jurídica profunda
    # Enfocado en contenido único, no metadatos comunes
    
    # THRESHOLDS más estrictos
    MIN_SEMANTIC_THRESHOLD = 0.70  # Aumentado: contenido realmente similar (70%)
    HIGH_SIMILARITY_THRESHOLD = 0.88  # Similitud realmente alta
    
    # Embedding por defecto a usar
    DEFAULT_EMBEDDING_FIELD: EmbeddingField = 'clean_embedding'
    
    # Pesos V3: Priorizan especificidad sobre coincidencias genéricas
    WEIGHTS = {
        # Clasificación jurídica ESPECÍFICA (lo más importante)
        'same_legal_subject': 0.15,       # AUMENTADO: materia específica es crucial
        
        # Metadatos COMUNES (reducidos drásticamente)
        'same_legal_area': 0.03,          # REDUCIDO: área es muy común
        'same_doc_type': 0.02,            # REDUCIDO: tipo muy común (sentencias)
        'same_jurisdictional_body': 0.01, # REDUCIDO: órgano es genérico
        'same_issue_place': 0.01,         # REDUCIDO: ubicación irrelevante
        
        # Partes del proceso (indicador de relación real)
        'shared_person': 0.08,            # AUMENTADO: personas = caso relacionado
        
        # Mismo expediente (modo específico)
        'same_case_number': 0.25,         # Alto para documentos del mismo caso
        'related_resolution': 0.02,       # Reducido
    }
    
    # Penalizaciones V3: Incluyen coincidencias genéricas
    PENALTIES = {
        'different_legal_area': -0.15,        # Área legal diferente
        'different_doc_type_category': -0.08, # Tipos incompatibles
        'too_generic_match': -0.12,           # NUEVO: solo metadatos comunes
        'low_content_similarity': -0.10,      # NUEVO: baja similitud + metadatos = genérico
    }
    
    @staticmethod
    def _normalize_score(semantic_score: float, metadata_boost: float, penalties: float = 0.0) -> float:
        """
        Normaliza el score final para evitar inflación por metadatos comunes.
        
        Formula V3 optimizada para jurisprudencia:
        - Score base: similitud semántica (70% mínimo)
        - Boost LIMITADO de metadatos (máx 20% en V3)
        - Penalizaciones por incompatibilidades y coincidencias genéricas
        - Compresión agresiva para evitar scores > 0.90
        
        Args:
            semantic_score: Score semántico base (0-1)
            metadata_boost: Suma de boosts de metadatos
            penalties: Suma de penalizaciones
        
        Returns:
            Score normalizado entre 0 y 1
        """
        # V3: Limitar boost de metadatos a máximo 20% (reducido del 30%)
        max_boost = 0.20
        metadata_boost = min(metadata_boost, max_boost)
        
        # Calcular score híbrido
        hybrid = semantic_score + metadata_boost + penalties
        
        # V3: Compresión más agresiva para evitar scores > 0.90
        # Si hybrid > 0.82, aplicar compresión fuerte
        if hybrid > 0.82:
            # Compresión más agresiva del exceso
            excess = hybrid - 0.82
            compressed_excess = excess * 0.4  # Comprimir 60% del exceso (vs 50% en V2)
            hybrid = 0.82 + compressed_excess
        
        # V3: Hard cap en 0.92 para evitar scores irrealistas
        hybrid = min(hybrid, 0.92)
        
        # Limitar a rango válido
        return max(0.0, min(1.0, hybrid))
    
    @staticmethod
    def _categorize_document_type(doc_type_name: str) -> str:
        """
        Categoriza tipos de documentos para comparación inteligente.
        
        Returns:
            Categoría: 'sentencia', 'auto', 'resolucion', 'otro'
        """
        if not doc_type_name:
            return 'otro'
        
        name_lower = doc_type_name.lower()
        
        if 'sentencia' in name_lower:
            return 'sentencia'
        elif 'auto' in name_lower:
            return 'auto'
        elif 'resolución' in name_lower or 'resolucion' in name_lower:
            return 'resolucion'
        else:
            return 'otro'
    
    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normaliza texto para comparaciones"""
        if not text:
            return ""
        return text.strip().upper()
    
    @staticmethod
    def _get_embedding_field(
        doc: Document, 
        embedding_field: EmbeddingField = 'clean_embedding'
    ) -> Optional[list]:
        """
        Obtiene el embedding del documento según el campo especificado.
        
        Si el campo preferido no está disponible, intenta con el alternativo.
        
        Args:
            doc: Documento del cual obtener el embedding
            embedding_field: Campo de embedding a usar
        
        Returns:
            Lista con el embedding o None si no está disponible
        """
        # Intentar con el campo preferido
        embedding = getattr(doc, embedding_field, None)
        if embedding is not None and len(embedding) > 0:
            return embedding
        
        # Fallback al otro campo
        fallback_field = 'enhanced_embedding' if embedding_field == 'clean_embedding' else 'clean_embedding'
        fallback_embedding = getattr(doc, fallback_field, None)
        if fallback_embedding is not None and len(fallback_embedding) > 0:
            logger.info(
                f"Document {doc.document_id}: Using fallback embedding field '{fallback_field}' "
                f"(requested '{embedding_field}' not available)"
            )
            return fallback_embedding
        
        return None
    
    @staticmethod
    def _get_embedding_filter_and_field(
        doc: Document,
        embedding_field: EmbeddingField = 'clean_embedding'
    ) -> Tuple[str, Q, list]:
        """
        Determina el campo de embedding a usar y construye el filtro Q.
        
        Args:
            doc: Documento de referencia
            embedding_field: Campo de embedding preferido
        
        Returns:
            Tuple de (nombre_campo, filtro_Q, embedding)
        
        Raises:
            ValueError si no hay embedding disponible
        """
        # Verificar campo preferido
        embedding = getattr(doc, embedding_field, None)
        if embedding is not None and len(embedding) > 0:
            return (
                embedding_field,
                Q(**{f'{embedding_field}__isnull': False}),
                embedding
            )
        
        # Fallback al otro campo
        fallback_field = 'enhanced_embedding' if embedding_field == 'clean_embedding' else 'clean_embedding'
        fallback_embedding = getattr(doc, fallback_field, None)
        if fallback_embedding is not None and len(fallback_embedding) > 0:
            logger.info(
                f"Document {doc.document_id}: Using fallback '{fallback_field}' for similarity search"
            )
            return (
                fallback_field,
                Q(**{f'{fallback_field}__isnull': False}),
                fallback_embedding
            )
        
        raise ValueError(f"Document {doc.document_id} has no embedding available")
    
    @staticmethod
    def _calculate_similarity_reasons(
        reference_doc: Document,
        candidate_doc: Document,
        semantic_score: float
    ) -> SimilarityReason:
        """
        Calcula las razones específicas de por qué dos documentos son similares.
        
        NUEVO: Enfoque más estricto y jurisprudencial
        - Prioriza similitud de materia jurídica
        - Reduce peso de coincidencias administrativas
        - Aplica penalizaciones por incompatibilidades
        
        Args:
            reference_doc: Documento de referencia
            candidate_doc: Documento candidato
            semantic_score: Score de similitud semántica (0-1)
        
        Returns:
            SimilarityReason con detalles de la similitud
        """
        reasons = SimilarityReason()
        reasons.total_score = semantic_score
        
        total_penalties = 0.0
        
        # ===== VERIFICACIÓN DE COMPATIBILIDAD BÁSICA =====
        
        # 1. Área Legal - CRÍTICO para jurisprudencia
        ref_area = reference_doc.legal_area
        cand_area = candidate_doc.legal_area
        
        if ref_area and cand_area:
            if ref_area == cand_area:
                reasons.add_reason(
                    'legal_classification',
                    f'Misma área legal: {ref_area.name}',
                    DocumentSimilarityService.WEIGHTS['same_legal_area']
                )
            else:
                # PENALIZAR área legal diferente
                total_penalties += DocumentSimilarityService.PENALTIES['different_legal_area']
                reasons.add_reason(
                    'incompatibility',
                    f'Diferente área legal: {ref_area.name} vs {cand_area.name}',
                    DocumentSimilarityService.PENALTIES['different_legal_area']
                )
        
        # 2. Materia Legal - MUY IMPORTANTE para casos comparables
        if (reference_doc.legal_subject and candidate_doc.legal_subject):
            ref_subject = DocumentSimilarityService._normalize_text(reference_doc.legal_subject)
            cand_subject = DocumentSimilarityService._normalize_text(candidate_doc.legal_subject)
            
            if ref_subject == cand_subject:
                reasons.add_reason(
                    'legal_classification',
                    f'Misma materia jurídica: {reference_doc.legal_subject}',
                    DocumentSimilarityService.WEIGHTS['same_legal_subject']
                )
            elif ref_subject and cand_subject:
                # Similitud parcial de materia (contiene subcadena)
                if ref_subject in cand_subject or cand_subject in ref_subject:
                    reasons.add_reason(
                        'legal_classification',
                        f'Materia relacionada: {reference_doc.legal_subject} / {candidate_doc.legal_subject}',
                        DocumentSimilarityService.WEIGHTS['same_legal_subject'] * 0.5
                    )
        
        # 3. Tipo de Documento - Comparar categorías
        if reference_doc.doc_type and candidate_doc.doc_type:
            ref_type = reference_doc.doc_type.name
            cand_type = candidate_doc.doc_type.name
            
            ref_category = DocumentSimilarityService._categorize_document_type(ref_type)
            cand_category = DocumentSimilarityService._categorize_document_type(cand_type)
            
            if ref_category == cand_category:
                reasons.add_reason(
                    'document_type',
                    f'Mismo tipo de documento: {ref_type}',
                    DocumentSimilarityService.WEIGHTS['same_doc_type']
                )
            elif ref_category != 'otro' and cand_category != 'otro':
                # Categorías diferentes pero válidas - penalizar ligeramente
                total_penalties += DocumentSimilarityService.PENALTIES['different_doc_type_category']
                reasons.add_reason(
                    'incompatibility',
                    f'Diferente tipo: {ref_type} vs {cand_type}',
                    DocumentSimilarityService.PENALTIES['different_doc_type_category']
                )
        
        # ===== MISMO EXPEDIENTE (modo especial) =====
        # Solo dar boost si explícitamente se busca mismo expediente
        # Para jurisprudencia general, esto no es relevante
        if (reference_doc.case_number and candidate_doc.case_number and
            DocumentSimilarityService._normalize_text(reference_doc.case_number) ==
            DocumentSimilarityService._normalize_text(candidate_doc.case_number)):
            reasons.add_reason(
                'same_case',
                f'Mismo expediente: {reference_doc.case_number}',
                DocumentSimilarityService.WEIGHTS['same_case_number']
            )
        
        # ===== CONTEXTO JURÍDICO SECUNDARIO =====
        
        # 4. Órgano Jurisdiccional - Menos importante para jurisprudencia
        if (reference_doc.jurisdictional_body and candidate_doc.jurisdictional_body and
            DocumentSimilarityService._normalize_text(reference_doc.jurisdictional_body) ==
            DocumentSimilarityService._normalize_text(candidate_doc.jurisdictional_body)):
            reasons.add_reason(
                'jurisdiction',
                f'Mismo órgano: {reference_doc.jurisdictional_body}',
                DocumentSimilarityService.WEIGHTS['same_jurisdictional_body']
            )
        
        # 5. Lugar de Emisión - Mínima relevancia
        if (reference_doc.issue_place and candidate_doc.issue_place and
            DocumentSimilarityService._normalize_text(reference_doc.issue_place) ==
            DocumentSimilarityService._normalize_text(candidate_doc.issue_place)):
            reasons.add_reason(
                'location',
                f'Mismo lugar: {reference_doc.issue_place}',
                DocumentSimilarityService.WEIGHTS['same_issue_place']
            )
        
        # 6. Resoluciones relacionadas
        if (reference_doc.resolution_number and candidate_doc.resolution_number):
            ref_res = DocumentSimilarityService._normalize_text(reference_doc.resolution_number)
            cand_res = DocumentSimilarityService._normalize_text(candidate_doc.resolution_number)
            
            if ref_res in cand_res or cand_res in ref_res:
                reasons.add_reason(
                    'same_case',
                    f'Resoluciones relacionadas: {reference_doc.resolution_number} / {candidate_doc.resolution_number}',
                    DocumentSimilarityService.WEIGHTS['related_resolution']
                )
        
        # 7. Personas compartidas - Reducido significativamente
        ref_persons = set(
            dp.person.name.strip().upper() 
            for dp in reference_doc.document_persons.select_related('person').all()
        )
        cand_persons = set(
            dp.person.name.strip().upper()
            for dp in candidate_doc.document_persons.select_related('person').all()
        )
        
        shared_persons = ref_persons & cand_persons
        
        # Solo mencionar si hay personas compartidas (peso reducido)
        if shared_persons:
            person_count = len(shared_persons)
            # Limitar a máximo 2 personas para evitar inflar score
            person_count = min(person_count, 2)
            
            for i, person in enumerate(list(shared_persons)[:2]):
                reasons.add_reason(
                    'shared_entities',
                    f'Parte común: {person}',
                    DocumentSimilarityService.WEIGHTS['shared_person']
                )
        
        # ===== EVALUACIÓN DE SIMILITUD SEMÁNTICA =====
        
        # Clasificar nivel de similitud semántica
        if semantic_score >= DocumentSimilarityService.HIGH_SIMILARITY_THRESHOLD:
            reasons.add_reason(
                'semantic_similarity',
                f'Contenido muy similar ({semantic_score:.0%})',
                0.0
            )
        elif semantic_score >= 0.75:
            reasons.add_reason(
                'semantic_similarity',
                f'Contenido similar ({semantic_score:.0%})',
                0.0
            )
        elif semantic_score >= DocumentSimilarityService.MIN_SEMANTIC_THRESHOLD:
            reasons.add_reason(
                'semantic_similarity',
                f'Similitud moderada de contenido ({semantic_score:.0%})',
                0.0
            )
        else:
            reasons.add_reason(
                'semantic_similarity',
                f'Baja similitud de contenido ({semantic_score:.0%})',
                0.0
            )
        
        # ===== V3: DETECCIÓN DE COINCIDENCIAS GENÉRICAS =====
        # Penalizar cuando solo coinciden metadatos comunes pero el contenido es diferente
        
        # Contar cuántos metadatos comunes coinciden
        common_metadata_matches = 0
        if ref_area and cand_area and ref_area == cand_area:
            common_metadata_matches += 1
        if reference_doc.doc_type and candidate_doc.doc_type and reference_doc.doc_type == candidate_doc.doc_type:
            common_metadata_matches += 1
        if (reference_doc.jurisdictional_body and candidate_doc.jurisdictional_body and
            DocumentSimilarityService._normalize_text(reference_doc.jurisdictional_body) ==
            DocumentSimilarityService._normalize_text(candidate_doc.jurisdictional_body)):
            common_metadata_matches += 1
        
        # Si hay 2+ metadatos comunes PERO baja similitud de contenido → genérico
        if common_metadata_matches >= 2 and semantic_score < 0.75:
            total_penalties += DocumentSimilarityService.PENALTIES['too_generic_match']
            reasons.add_reason(
                'warning',
                f'Coincidencia genérica: metadatos comunes pero contenido diferente ({semantic_score:.0%})',
                DocumentSimilarityService.PENALTIES['too_generic_match']
            )
        
        # Si solo área + tipo coinciden pero contenido muy diferente → penalizar más
        if (common_metadata_matches >= 2 and 
            semantic_score < DocumentSimilarityService.MIN_SEMANTIC_THRESHOLD and
            not shared_persons):  # Sin personas compartidas
            total_penalties += DocumentSimilarityService.PENALTIES['low_content_similarity']
            reasons.add_reason(
                'warning',
                f'Baja similitud de contenido a pesar de metadatos comunes',
                DocumentSimilarityService.PENALTIES['low_content_similarity']
            )
        
        # Las penalizaciones ya están en score_breakdown, no necesitamos setear self.penalties
        
        return reasons
    
    @staticmethod
    def find_similar_documents(
        document_id: str,
        top_n: int = 3,
        min_similarity: float = 0.0,
        exclude_self: bool = True,
        use_hybrid_scoring: bool = True,
        embedding_field: EmbeddingField = None
    ) -> List[Tuple[Document, float, Dict[str, Any]]]:
        """
        Encuentra documentos similares a un documento dado usando cosine similarity.
        
        V3.1: Soporte para clean_embedding (768d) o enhanced_embedding (384d).
        
        Args:
            document_id: UUID del documento de referencia
            top_n: Número máximo de documentos similares a retornar
            min_similarity: Similitud mínima (0-1, donde 1 es idéntico)
            exclude_self: Si True, excluye el documento original de los resultados
            use_hybrid_scoring: Si True, usa scoring híbrido (semántico + metadatos)
            embedding_field: Campo de embedding a usar ('clean_embedding' o 'enhanced_embedding')
                           Si None, usa DEFAULT_EMBEDDING_FIELD con fallback automático
        
        Returns:
            Lista de tuplas (Document, hybrid_score, reasons_dict) ordenadas por score descendente
            donde hybrid_score combina similitud semántica con coincidencias de metadatos
            y reasons_dict contiene las razones detalladas de la similitud
        """
        try:
            # Usar campo por defecto si no se especifica
            if embedding_field is None:
                embedding_field = DocumentSimilarityService.DEFAULT_EMBEDDING_FIELD
            
            # Obtener el documento de referencia con relaciones
            reference_doc = Document.objects.prefetch_related(
                'document_persons__person',
                'legal_area',
                'doc_type'
            ).get(document_id=document_id)
            
            # Obtener el campo de embedding y filtro a usar
            try:
                field_name, embedding_filter, reference_embedding = \
                    DocumentSimilarityService._get_embedding_filter_and_field(
                        reference_doc, embedding_field
                    )
            except ValueError as e:
                logger.warning(str(e))
                return []
            
            logger.debug(f"Using embedding field '{field_name}' for similarity search")
            
            # Preparar el queryset base
            queryset = Document.objects.prefetch_related(
                'document_persons__person',
                'legal_area',
                'doc_type'
            ).filter(
                embedding_filter
            ).exclude(
                status='failed'
            )
            
            # Excluir el documento original si se solicita
            if exclude_self:
                queryset = queryset.exclude(document_id=document_id)
            
            # Calcular cosine distance y convertir a similarity
            queryset = queryset.annotate(
                distance=CosineDistance(field_name, reference_embedding)
            ).order_by('distance')
            
            # Obtener más candidatos si usamos hybrid scoring para reordenar
            fetch_limit = top_n * 3 if use_hybrid_scoring else top_n
            
            # Filtrar por similitud mínima básica
            if min_similarity > 0:
                max_distance = 1.0 - min_similarity
                queryset = queryset.filter(distance__lte=max_distance)
            
            queryset = queryset[:fetch_limit]
            
            # Calcular scores híbridos y razones
            results = []
            for doc in queryset:
                semantic_score = 1.0 - float(doc.distance)
                
                # Si min_similarity > 0, usarlo como threshold
                # Si min_similarity == 0.0, NO aplicar threshold (devolver todos)
                if min_similarity > 0 and semantic_score < min_similarity:
                    continue  # Saltar documentos por debajo del threshold especificado
                
                if use_hybrid_scoring:
                    # Calcular razones y score híbrido con penalizaciones
                    similarity_reasons = DocumentSimilarityService._calculate_similarity_reasons(
                        reference_doc, doc, semantic_score
                    )
                    
                    # Obtener boost y penalizaciones
                    metadata_boost = sum(w for w in similarity_reasons.score_breakdown.values() if w > 0)
                    penalties = sum(w for w in similarity_reasons.score_breakdown.values() if w < 0)
                    
                    # Usar normalización calibrada
                    hybrid_score = DocumentSimilarityService._normalize_score(
                        semantic_score, 
                        metadata_boost, 
                        penalties
                    )
                    
                    results.append((doc, hybrid_score, similarity_reasons.to_dict()))
                else:
                    # Solo similitud semántica, sin razones detalladas
                    results.append((doc, semantic_score, {'semantic_similarity': semantic_score}))
            
            # Reordenar por hybrid_score si se usa
            if use_hybrid_scoring:
                results.sort(key=lambda x: x[1], reverse=True)
            
            # Limitar a top_n resultados finales
            results = results[:top_n]
            
            logger.info(
                f"Found {len(results)} similar documents for document {document_id} "
                f"(hybrid_scoring={use_hybrid_scoring})"
            )
            
            return results
            
        except Document.DoesNotExist:
            logger.error(f"Document {document_id} not found")
            return []
        except Exception as e:
            logger.error(f"Error finding similar documents: {e}", exc_info=True)
            return []
    
    @staticmethod
    def find_similar_by_area(
        document_id: str,
        top_n: int = 3,
        min_similarity: float = 0.0,
        use_hybrid_scoring: bool = True,
        embedding_field: EmbeddingField = None
    ) -> List[Tuple[Document, float, Dict[str, Any]]]:
        """
        Encuentra documentos similares pero solo dentro de la misma área legal.
        
        Args:
            document_id: UUID del documento de referencia
            top_n: Número máximo de documentos similares a retornar
            min_similarity: Similitud mínima (0-1)
            use_hybrid_scoring: Si True, usa scoring híbrido
            embedding_field: Campo de embedding a usar ('clean_embedding' o 'enhanced_embedding')
        
        Returns:
            Lista de tuplas (Document, hybrid_score, reasons_dict)
        """
        try:
            # Usar campo por defecto si no se especifica
            if embedding_field is None:
                embedding_field = DocumentSimilarityService.DEFAULT_EMBEDDING_FIELD
            
            reference_doc = Document.objects.prefetch_related(
                'document_persons__person',
                'legal_area',
                'doc_type'
            ).get(document_id=document_id)
            
            # Obtener el campo de embedding y filtro a usar
            try:
                field_name, embedding_filter, reference_embedding = \
                    DocumentSimilarityService._get_embedding_filter_and_field(
                        reference_doc, embedding_field
                    )
            except ValueError as e:
                logger.warning(str(e))
                return []
            
            if not reference_doc.legal_area:
                logger.warning(f"Document {document_id} has no legal_area")
                # Retornar similar documents sin filtro de área
                return DocumentSimilarityService.find_similar_documents(
                    document_id, top_n, min_similarity, 
                    use_hybrid_scoring=use_hybrid_scoring,
                    embedding_field=embedding_field
                )
            
            # Filtrar por la misma área legal Y que tengan el embedding
            queryset = Document.objects.prefetch_related(
                'document_persons__person',
                'legal_area',
                'doc_type'
            ).filter(
                embedding_filter,
                legal_area=reference_doc.legal_area
            ).exclude(
                document_id=document_id
            ).exclude(
                status='failed'
            )
            
            # Calcular similitud
            queryset = queryset.annotate(
                distance=CosineDistance(field_name, reference_embedding)
            ).order_by('distance')
            
            # Obtener más candidatos si usamos hybrid scoring
            fetch_limit = top_n * 3 if use_hybrid_scoring else top_n
            
            # Filtrar por similitud mínima
            if min_similarity > 0:
                max_distance = 1.0 - min_similarity
                queryset = queryset.filter(distance__lte=max_distance)
            
            queryset = queryset[:fetch_limit]
            
            # Calcular scores híbridos y razones
            results = []
            for doc in queryset:
                semantic_score = 1.0 - float(doc.distance)
                
                # Si min_similarity > 0, usarlo como threshold
                # Si min_similarity == 0.0, NO aplicar threshold (devolver todos)
                if min_similarity > 0 and semantic_score < min_similarity:
                    continue
                
                if use_hybrid_scoring:
                    similarity_reasons = DocumentSimilarityService._calculate_similarity_reasons(
                        reference_doc, doc, semantic_score
                    )
                    metadata_boost = sum(w for w in similarity_reasons.score_breakdown.values() if w > 0)
                    penalties = sum(w for w in similarity_reasons.score_breakdown.values() if w < 0)
                    hybrid_score = DocumentSimilarityService._normalize_score(
                        semantic_score, metadata_boost, penalties
                    )
                    results.append((doc, hybrid_score, similarity_reasons.to_dict()))
                else:
                    results.append((doc, semantic_score, {'semantic_similarity': semantic_score}))
            
            # Reordenar por hybrid_score
            if use_hybrid_scoring:
                results.sort(key=lambda x: x[1], reverse=True)
            
            results = results[:top_n]
            
            logger.info(
                f"Found {len(results)} similar documents in same area for document {document_id}"
            )
            
            return results
            
        except Document.DoesNotExist:
            logger.error(f"Document {document_id} not found")
            return []
        except Exception as e:
            logger.error(f"Error finding similar documents by area: {e}", exc_info=True)
            return []
    
    @staticmethod
    def find_similar_by_document_type(
        document_id: str,
        top_n: int = 3,
        min_similarity: float = 0.0,
        use_hybrid_scoring: bool = True,
        embedding_field: EmbeddingField = None
    ) -> List[Tuple[Document, float, Dict[str, Any]]]:
        """
        Encuentra documentos similares pero solo del mismo tipo de documento.
        
        Args:
            document_id: UUID del documento de referencia
            top_n: Número máximo de documentos similares a retornar
            min_similarity: Similitud mínima (0-1)
            use_hybrid_scoring: Si True, usa scoring híbrido
            embedding_field: Campo de embedding a usar ('clean_embedding' o 'enhanced_embedding')
        
        Returns:
            Lista de tuplas (Document, hybrid_score, reasons_dict)
        """
        try:
            # Usar campo por defecto si no se especifica
            if embedding_field is None:
                embedding_field = DocumentSimilarityService.DEFAULT_EMBEDDING_FIELD
            
            reference_doc = Document.objects.prefetch_related(
                'document_persons__person',
                'legal_area',
                'doc_type'
            ).get(document_id=document_id)
            
            # Obtener el campo de embedding y filtro a usar
            try:
                field_name, embedding_filter, reference_embedding = \
                    DocumentSimilarityService._get_embedding_filter_and_field(
                        reference_doc, embedding_field
                    )
            except ValueError as e:
                logger.warning(str(e))
                return []
            
            if not reference_doc.doc_type:
                logger.warning(f"Document {document_id} has no doc_type")
                return DocumentSimilarityService.find_similar_documents(
                    document_id, top_n, min_similarity, 
                    use_hybrid_scoring=use_hybrid_scoring,
                    embedding_field=embedding_field
                )
            
            # Filtrar por el mismo tipo de documento Y que tengan el embedding
            queryset = Document.objects.prefetch_related(
                'document_persons__person',
                'legal_area',
                'doc_type'
            ).filter(
                embedding_filter,
                doc_type=reference_doc.doc_type
            ).exclude(
                document_id=document_id
            ).exclude(
                status='failed'
            )
            
            # Calcular similitud
            queryset = queryset.annotate(
                distance=CosineDistance(field_name, reference_embedding)
            ).order_by('distance')
            
            # Obtener más candidatos si usamos hybrid scoring
            fetch_limit = top_n * 3 if use_hybrid_scoring else top_n
            
            # Filtrar por similitud mínima
            if min_similarity > 0:
                max_distance = 1.0 - min_similarity
                queryset = queryset.filter(distance__lte=max_distance)
            
            queryset = queryset[:fetch_limit]
            
            # Calcular scores híbridos y razones
            results = []
            for doc in queryset:
                semantic_score = 1.0 - float(doc.distance)
                
                # Si min_similarity > 0, usarlo como threshold
                # Si min_similarity == 0.0, NO aplicar threshold (devolver todos)
                if min_similarity > 0 and semantic_score < min_similarity:
                    continue
                
                if use_hybrid_scoring:
                    similarity_reasons = DocumentSimilarityService._calculate_similarity_reasons(
                        reference_doc, doc, semantic_score
                    )
                    metadata_boost = sum(w for w in similarity_reasons.score_breakdown.values() if w > 0)
                    penalties = sum(w for w in similarity_reasons.score_breakdown.values() if w < 0)
                    hybrid_score = DocumentSimilarityService._normalize_score(
                        semantic_score, metadata_boost, penalties
                    )
                    results.append((doc, hybrid_score, similarity_reasons.to_dict()))
                else:
                    results.append((doc, semantic_score, {'semantic_similarity': semantic_score}))
            
            # Reordenar por hybrid_score
            if use_hybrid_scoring:
                results.sort(key=lambda x: x[1], reverse=True)
            
            results = results[:top_n]
            
            logger.info(
                f"Found {len(results)} similar documents of same type for document {document_id}"
            )
            
            return results
            
        except Document.DoesNotExist:
            logger.error(f"Document {document_id} not found")
            return []
        except Exception as e:
            logger.error(f"Error finding similar documents by type: {e}", exc_info=True)
            return []
    
    @staticmethod
    def _diversify_results(
        results: List[Tuple[Document, float, Dict[str, Any]]],
        max_per_category: int = 3,
        min_score_threshold: float = 0.75
    ) -> List[Tuple[Document, float, Dict[str, Any]]]:
        """
        V3: Diversifica resultados para evitar mostrar demasiados documentos genéricos similares.
        
        Aplica límites por categoría (área + tipo) para garantizar variedad jurisprudencial.
        
        Args:
            results: Lista de tuplas (Document, score, reasons)
            max_per_category: Máximo de documentos por combinación área+tipo
            min_score_threshold: Score mínimo para considerar (evita genéricos)
        
        Returns:
            Lista filtrada y diversificada manteniendo los mejores de cada categoría
        """
        if not results:
            return results
        
        # Agrupar por combinación de área legal + tipo de documento
        categories = {}
        for doc, score, reasons in results:
            # Solo incluir si supera threshold (evitar genéricos)
            if score < min_score_threshold:
                continue
            
            # Crear clave de categoría
            area_name = doc.legal_area.name if doc.legal_area else "sin_area"
            type_name = doc.doc_type.name if doc.doc_type else "sin_tipo"
            category_key = f"{area_name}_{type_name}"
            
            if category_key not in categories:
                categories[category_key] = []
            
            categories[category_key].append((doc, score, reasons))
        
        # Seleccionar los mejores de cada categoría (ya están ordenados por score)
        diversified = []
        for category_key, category_results in categories.items():
            # Ordenar por score descendente dentro de la categoría
            category_results.sort(key=lambda x: x[1], reverse=True)
            
            # Tomar máximo max_per_category de esta categoría
            diversified.extend(category_results[:max_per_category])
        
        # Re-ordenar por score global
        diversified.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(
            f"Diversificación: {len(results)} → {len(diversified)} documentos "
            f"({len(categories)} categorías, max {max_per_category} por categoría)"
        )
        
        return diversified
    
    @staticmethod
    def find_similar_by_text(
        query_text: str,
        top_n: int = 10,
        min_similarity: float = 0.0,
        embedding_field: EmbeddingField = None,
        legal_area_id: int = None,
        doc_type_id: int = None
    ) -> List[Tuple[Document, float]]:
        """
        Busca documentos similares a un texto dado (búsqueda semántica).
        
        Útil para búsqueda por consulta de texto libre.
        
        Args:
            query_text: Texto de consulta
            top_n: Número máximo de documentos a retornar
            min_similarity: Similitud mínima (0-1)
            embedding_field: Campo de embedding a usar
            legal_area_id: Filtrar por área legal específica
            doc_type_id: Filtrar por tipo de documento específico
        
        Returns:
            Lista de tuplas (Document, similarity_score)
        """
        try:
            # Usar campo por defecto si no se especifica
            if embedding_field is None:
                embedding_field = DocumentSimilarityService.DEFAULT_EMBEDDING_FIELD
            
            # Importar el servicio de embeddings aquí para evitar imports circulares
            from apps.documents.services.clean_embeddings_service import get_clean_embedding_service
            
            # Generar embedding del texto de consulta
            embedding_service = get_clean_embedding_service()
            query_embedding = embedding_service.generate_query_embedding(query_text)
            
            if query_embedding is None:
                logger.error("Failed to generate embedding for query text")
                return []
            
            # Construir filtro base
            field_filter = Q(**{f'{embedding_field}__isnull': False})
            queryset = Document.objects.filter(
                field_filter
            ).exclude(
                status='failed'
            )
            
            # Aplicar filtros opcionales
            if legal_area_id:
                queryset = queryset.filter(legal_area_id=legal_area_id)
            if doc_type_id:
                queryset = queryset.filter(doc_type_id=doc_type_id)
            
            # Calcular similitud
            queryset = queryset.annotate(
                distance=CosineDistance(embedding_field, list(query_embedding))
            ).order_by('distance')
            
            # Filtrar por similitud mínima
            if min_similarity > 0:
                max_distance = 1.0 - min_similarity
                queryset = queryset.filter(distance__lte=max_distance)
            
            queryset = queryset[:top_n]
            
            # Construir resultados
            results = []
            for doc in queryset:
                similarity_score = 1.0 - float(doc.distance)
                results.append((doc, similarity_score))
            
            logger.info(
                f"Found {len(results)} documents similar to query text "
                f"(embedding_field={embedding_field})"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error in find_similar_by_text: {e}", exc_info=True)
            return []

