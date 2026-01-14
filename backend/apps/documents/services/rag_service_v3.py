# apps/documents/services/rag_service_v3.py
"""
RAG (Retrieval Augmented Generation) Service - Versión 3.0

Sistema de recuperación semántica mejorado para documentos jurídicos peruanos.

MEJORAS SOBRE V2.0:
=====================
1. RE-RANKING: Combina similitud semántica + BM25 léxico
2. QUERY EXPANSION: Expansión semántica inteligente para términos legales
3. MMR (Maximal Marginal Relevance): Diversidad en resultados
4. CONTEXT WINDOWS: Recupera chunks adyacentes inteligentemente
5. MULTI-STAGE RETRIEVAL: Busca más, filtra mejor
6. ADAPTIVE THRESHOLD: Umbral dinámico según calidad de resultados

PROBLEMAS QUE RESUELVE:
=======================
- Query "qué decidieron" no encontraba chunks de "decisión/fallo"
- Pocos chunks relevantes (top_k=3 era insuficiente)  
- Threshold muy bajo (0.25) incluía ruido
- Sin diversidad (chunks muy similares entre sí)
- Query expansion limitada (solo sinónimos directos)
"""

import logging
import re
import math
from typing import List, Dict, Optional, Tuple, Set
from collections import defaultdict
import numpy as np

from django.db.models import F
from pgvector.django import CosineDistance

from apps.documents.models import Document, DocumentChunk
from apps.documents.services.chunk_embedding_service import get_chunk_embedding_service

logger = logging.getLogger(__name__)


class RAGServiceV3:
    """
    Servicio RAG v3.0 con recuperación multi-etapa y re-ranking.
    
    Pipeline:
    1. EXPAND: Expande query con sinónimos y variantes semánticas
    2. RETRIEVE: Recupera top-N chunks por similitud semántica
    3. RERANK: Re-ordena combinando similitud + BM25 + posición
    4. DIVERSIFY: Aplica MMR para evitar redundancia
    5. CONTEXTUALIZE: Agrega chunks adyacentes
    6. FORMAT: Formatea contexto para LLM
    """
    
    # =========================================================================
    # EXPANSIONES SEMÁNTICAS PARA DOMINIOS LEGALES PERUANOS
    # =========================================================================
    LEGAL_EXPANSIONS = {
        # Decisiones y fallos
        'decidieron': ['resolvieron', 'ordenaron', 'declararon', 'fallaron', 'dispusieron', 'confirmaron', 'revocaron'],
        'decisión': ['fallo', 'resolución', 'pronunciamiento', 'sentencia', 'determinación', 'disposición'],
        'resolvió': ['falló', 'declaró', 'ordenó', 'dispuso', 'determinó', 'sentenció'],
        'resultado': ['fallo', 'decisión', 'resolución', 'conclusión', 'determinación'],
        
        # Partes procesales
        'demandante': ['actor', 'recurrente', 'solicitante', 'peticionante', 'accionante', 'impugnante'],
        'demandado': ['emplazado', 'requerido', 'accionado', 'recurrido', 'apelado'],
        'partes': ['litigantes', 'intervinientes', 'procesados', 'involucrados', 'sujetos procesales'],
        
        # Jueces y autoridades  
        'juez': ['magistrado', 'juzgador', 'vocal', 'ponente', 'relator'],
        'sala': ['tribunal', 'colegiado', 'órgano jurisdiccional', 'instancia'],
        'fiscal': ['ministerio público', 'representante del estado', 'acusador'],
        
        # Tipos de resolución
        'sentencia': ['fallo', 'resolución', 'decisión', 'pronunciamiento', 'auto definitivo'],
        'apelación': ['recurso', 'impugnación', 'alzada', 'segunda instancia'],
        'casación': ['recurso extraordinario', 'nulidad', 'revisión'],
        
        # Estados del fallo
        'fundada': ['procedente', 'amparada', 'estimada', 'acogida', 'con lugar'],
        'infundada': ['improcedente', 'desestimada', 'rechazada', 'sin lugar', 'no ha lugar'],
        'confirmar': ['ratificar', 'mantener', 'sostener', 'validar'],
        'revocar': ['anular', 'dejar sin efecto', 'modificar', 'revertir'],
        
        # Conceptos legales
        'prueba': ['evidencia', 'medio probatorio', 'acreditación', 'elemento probatorio'],
        'derecho': ['pretensión', 'facultad', 'beneficio', 'interés legítimo'],
        'obligación': ['deber', 'responsabilidad', 'compromiso', 'carga'],
        'indemnización': ['reparación', 'compensación', 'resarcimiento', 'pago de daños'],
        'despido': ['cese', 'terminación', 'extinción del vínculo laboral', 'destitución'],
        
        # Materia laboral específica
        'cts': ['compensación por tiempo de servicios', 'beneficios sociales'],
        'gratificaciones': ['beneficios', 'bonificaciones', 'asignaciones'],
        'remuneración': ['sueldo', 'salario', 'haberes', 'retribución'],
        'trabajador': ['empleado', 'servidor', 'colaborador', 'obrero'],
        'empleador': ['patrono', 'empresa', 'entidad empleadora', 'patrón'],
        
        # Materia penal específica
        'imputado': ['acusado', 'procesado', 'inculpado', 'encausado'],
        'agraviado': ['víctima', 'perjudicado', 'afectado'],
        'pena': ['sanción', 'condena', 'castigo', 'sentencia condenatoria'],
        'absolución': ['liberación', 'exoneración', 'declaración de inocencia'],
    }
    
    # Patrones para identificar tipo de pregunta
    QUESTION_PATTERNS = {
        'decision': [
            r'qu[ée]\s+(decidieron|resolvieron|fallaron|ordenaron)',
            r'cu[áa]l\s+(fue|es)\s+(la|el)\s+(decisi[óo]n|fallo|resultado|sentencia)',
            r'c[óo]mo\s+(terminó|concluyó|resolvió)',
            r'(confirmaron|revocaron|declararon)',
        ],
        'parties': [
            r'qui[ée]n(es)?\s+(es|son|era|fueron)',
            r'partes\s+(involucradas|del proceso)',
            r'(demandante|demandado|actor|accionante)',
        ],
        'facts': [
            r'qu[ée]\s+(pas[óo]|ocurri[óo]|sucedi[óo])',
            r'(hechos|circunstancias|antecedentes)',
            r'c[óo]mo\s+(pas[óo]|ocurrieron)',
        ],
        'legal_basis': [
            r'(fundamento|base|argumento)\s+legal',
            r'qu[ée]\s+(ley|norma|artículo)',
            r'(principio|derecho)\s+(aplicado|vulnerado)',
        ],
        'amount': [
            r'(cu[áa]nto|monto|suma|cantidad)',
            r'(indemnizaci[óo]n|pago|compensaci[óo]n)',
        ],
    }
    
    def __init__(
        self, 
        top_k: int = 8,  # Aumentado de 5
        initial_candidates: int = 20,  # Candidatos iniciales antes de re-ranking
        similarity_threshold: float = 0.35,  # Más estricto que 0.25
        mmr_lambda: float = 0.7,  # Balance similitud/diversidad
        use_bm25_rerank: bool = True,
        include_adjacent: bool = True,
        max_context_chars: int = 8000  # Más contexto para LLM
    ):
        """
        Inicializa RAGService v3.0.
        
        Args:
            top_k: Chunks finales a retornar
            initial_candidates: Candidatos iniciales para re-ranking
            similarity_threshold: Umbral mínimo de similitud (0-1)
            mmr_lambda: 0=max diversidad, 1=max similitud
            use_bm25_rerank: Si usar BM25 para re-ranking
            include_adjacent: Si incluir chunks adyacentes
            max_context_chars: Máximo de caracteres para contexto
        """
        self.top_k = top_k
        self.initial_candidates = initial_candidates
        self.similarity_threshold = similarity_threshold
        self.mmr_lambda = mmr_lambda
        self.use_bm25_rerank = use_bm25_rerank
        self.include_adjacent = include_adjacent
        self.max_context_chars = max_context_chars
        
        self.embedding_service = get_chunk_embedding_service()
        
        # Compilar patrones de preguntas
        self._compiled_patterns = {
            q_type: [re.compile(p, re.IGNORECASE) for p in patterns]
            for q_type, patterns in self.QUESTION_PATTERNS.items()
        }
        
        logger.info(
            f"RAGService v3.0 initialized: "
            f"top_k={top_k}, candidates={initial_candidates}, "
            f"threshold={similarity_threshold}, mmr_lambda={mmr_lambda}"
        )
    
    # =========================================================================
    # STAGE 1: QUERY EXPANSION
    # =========================================================================
    
    def _detect_question_type(self, question: str) -> List[str]:
        """Detecta el tipo de pregunta para expansión dirigida."""
        question_lower = question.lower()
        detected_types = []
        
        for q_type, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(question_lower):
                    detected_types.append(q_type)
                    break
        
        return detected_types or ['general']
    
    def _expand_query(self, question: str) -> Tuple[str, List[str]]:
        """
        Expande la consulta con sinónimos y variantes semánticas.
        
        Retorna:
            Tuple de (query expandida, lista de términos agregados)
        """
        question_lower = question.lower()
        additions = []
        
        # Detectar tipo de pregunta para expansión dirigida
        q_types = self._detect_question_type(question)
        
        # Si pregunta sobre decisión, agregar términos de fallo
        if 'decision' in q_types:
            additions.extend(['fallo', 'resolvió', 'declaró', 'confirmó', 'revocó', 'dispuso'])
        
        # Expansión basada en términos encontrados
        for term, synonyms in self.LEGAL_EXPANSIONS.items():
            if term in question_lower:
                # Agregar top 3 sinónimos más relevantes
                additions.extend(synonyms[:3])
        
        # Eliminar duplicados manteniendo orden
        seen = set()
        unique_additions = []
        for term in additions:
            if term not in seen and term not in question_lower:
                seen.add(term)
                unique_additions.append(term)
        
        if unique_additions:
            expanded_query = f"{question} {' '.join(unique_additions[:10])}"
            logger.info(f"🔄 Query expansion: +{len(unique_additions)} terms: {unique_additions[:5]}...")
            return expanded_query, unique_additions
        
        return question, []
    
    # =========================================================================
    # STAGE 2: EMBEDDING Y RETRIEVAL INICIAL
    # =========================================================================
    
    def encode_question(self, question: str, expand: bool = True) -> Optional[np.ndarray]:
        """Genera embedding para la pregunta."""
        if not question or not question.strip():
            return None
        
        try:
            query_to_encode = question
            if expand:
                query_to_encode, _ = self._expand_query(question)
            
            embedding = self.embedding_service.encode_query(query_to_encode, normalize=True)
            
            if embedding is not None:
                logger.info(f"✅ Query embedding: shape={embedding.shape}")
            return embedding
            
        except Exception as e:
            logger.error(f"❌ Error generating query embedding: {e}")
            return None
    
    def _retrieve_initial_candidates(
        self, 
        document: Document, 
        question_embedding: np.ndarray,
        num_candidates: int
    ) -> List[Dict]:
        """
        Recupera candidatos iniciales por similitud semántica.
        
        Busca más chunks de los necesarios para luego filtrar con re-ranking.
        """
        # Determinar qué campo de embedding usar
        chunks_with_clean = DocumentChunk.objects.filter(
            document_id=document,
            clean_content_embedding__isnull=False
        )
        
        use_clean = chunks_with_clean.exists()
        
        if use_clean:
            embedding_field = 'clean_content_embedding'
            chunks_query = chunks_with_clean
            logger.info(f"🔵 Using clean_content_embedding (768d)")
        else:
            # Fallback a embedding legacy
            chunks_query = DocumentChunk.objects.filter(
                document_id=document,
                content_embedding__isnull=False
            )
            embedding_field = 'content_embedding'
            
            # Regenerar embedding con modelo de 384d
            from apps.documents.services.embedding_service import get_embedding_service
            legacy_service = get_embedding_service()
            question_embedding = legacy_service.encode_text(
                self._expand_query(document.title or "documento legal")[0],
                normalize=True
            )
            logger.warning(f"⚠️ Using legacy content_embedding (384d)")
        
        if not chunks_query.exists():
            logger.warning(f"❌ Document has no chunks with embeddings")
            return []
        
        total_chunks = chunks_query.count()
        logger.info(f"🔍 Searching {total_chunks} chunks (field: {embedding_field})")
        
        # Buscar por similitud
        try:
            embedding_list = question_embedding.tolist()
            
            candidates = chunks_query.annotate(
                distance=CosineDistance(embedding_field, embedding_list)
            ).order_by('distance')[:num_candidates]
            
            results = []
            for chunk in candidates:
                # Convertir distancia a similitud
                similarity = 1 - (chunk.distance / 2)
                
                results.append({
                    'chunk_id': str(chunk.chunk_id),
                    'content': chunk.content,
                    'order_number': chunk.order_number,
                    'semantic_similarity': round(similarity, 4),
                    'embedding_type': '768d' if use_clean else '384d',
                })
            
            logger.info(f"📊 Retrieved {len(results)} initial candidates")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error in initial retrieval: {e}", exc_info=True)
            return []
    
    # =========================================================================
    # STAGE 3: RE-RANKING CON BM25
    # =========================================================================
    
    def _compute_bm25_scores(
        self, 
        query: str, 
        chunks: List[Dict],
        k1: float = 1.5,
        b: float = 0.75
    ) -> List[float]:
        """
        Calcula scores BM25 para re-ranking léxico.
        
        BM25 complementa la similitud semántica al capturar matches exactos
        de términos que el embedding puede perder.
        """
        # Tokenizar query
        query_terms = set(re.findall(r'\b\w+\b', query.lower()))
        
        # Calcular estadísticas del corpus
        doc_lengths = [len(c['content'].split()) for c in chunks]
        avg_doc_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 1
        
        # IDF: calcular frecuencia de documentos para cada término
        df = defaultdict(int)
        for chunk in chunks:
            chunk_terms = set(re.findall(r'\b\w+\b', chunk['content'].lower()))
            for term in query_terms:
                if term in chunk_terms:
                    df[term] += 1
        
        n_docs = len(chunks)
        
        # Calcular BM25 para cada chunk
        scores = []
        for i, chunk in enumerate(chunks):
            chunk_content = chunk['content'].lower()
            chunk_terms = re.findall(r'\b\w+\b', chunk_content)
            chunk_length = len(chunk_terms)
            
            # Contar frecuencia de términos
            tf = defaultdict(int)
            for term in chunk_terms:
                tf[term] += 1
            
            score = 0.0
            for term in query_terms:
                if df[term] == 0:
                    continue
                
                # IDF
                idf = math.log((n_docs - df[term] + 0.5) / (df[term] + 0.5) + 1)
                
                # TF normalizado
                term_freq = tf.get(term, 0)
                tf_norm = (term_freq * (k1 + 1)) / (
                    term_freq + k1 * (1 - b + b * chunk_length / avg_doc_length)
                )
                
                score += idf * tf_norm
            
            scores.append(score)
        
        # Normalizar scores a [0, 1]
        max_score = max(scores) if scores else 1
        if max_score > 0:
            scores = [s / max_score for s in scores]
        
        return scores
    
    def _rerank_chunks(
        self, 
        query: str, 
        chunks: List[Dict],
        semantic_weight: float = 0.7,
        bm25_weight: float = 0.2,
        position_weight: float = 0.1
    ) -> List[Dict]:
        """
        Re-rankea chunks combinando múltiples señales:
        - Similitud semántica (embedding)
        - Score BM25 (matching léxico)
        - Posición en documento (chunks finales para decisiones)
        """
        if not chunks:
            return []
        
        # Calcular BM25 scores
        bm25_scores = self._compute_bm25_scores(query, chunks) if self.use_bm25_rerank else [0] * len(chunks)
        
        # Calcular position scores (chunks más altos = más importantes para intro,
        # chunks más bajos = más importantes para conclusión/fallo)
        total_chunks_approx = max(c['order_number'] for c in chunks)
        
        # Detectar si pregunta sobre decisión (chunks finales más importantes)
        q_types = self._detect_question_type(query)
        prefer_final = 'decision' in q_types
        
        for i, chunk in enumerate(chunks):
            order = chunk['order_number']
            
            if prefer_final:
                # Para preguntas de decisión, preferir chunks finales
                position_score = order / total_chunks_approx
            else:
                # Para otras preguntas, sin preferencia de posición
                position_score = 0.5
            
            # Score combinado
            combined_score = (
                semantic_weight * chunk['semantic_similarity'] +
                bm25_weight * bm25_scores[i] +
                position_weight * position_score
            )
            
            chunk['bm25_score'] = round(bm25_scores[i], 4)
            chunk['position_score'] = round(position_score, 4)
            chunk['combined_score'] = round(combined_score, 4)
        
        # Ordenar por score combinado
        chunks.sort(key=lambda x: x['combined_score'], reverse=True)
        
        logger.info(f"📊 Re-ranked {len(chunks)} chunks (prefer_final={prefer_final})")
        
        return chunks
    
    # =========================================================================
    # STAGE 4: MMR (MAXIMAL MARGINAL RELEVANCE) PARA DIVERSIDAD
    # =========================================================================
    
    def _apply_mmr(
        self, 
        chunks: List[Dict], 
        top_k: int,
        lambda_param: float
    ) -> List[Dict]:
        """
        Aplica MMR para seleccionar chunks diversos.
        
        MMR = λ * Sim(chunk, query) - (1-λ) * max(Sim(chunk, selected))
        
        Esto evita seleccionar chunks muy similares entre sí,
        aumentando la cobertura de información.
        """
        if len(chunks) <= top_k:
            return chunks
        
        selected = []
        candidates = chunks.copy()
        
        # Primer chunk: el de mayor score
        selected.append(candidates.pop(0))
        
        while len(selected) < top_k and candidates:
            best_mmr = -float('inf')
            best_idx = 0
            
            for i, candidate in enumerate(candidates):
                # Similitud con query (ya calculada)
                sim_query = candidate['combined_score']
                
                # Máxima similitud con chunks ya seleccionados
                # Usamos una heurística basada en overlap de contenido
                max_sim_selected = 0
                for sel in selected:
                    # Similitud aproximada por palabras compartidas
                    cand_words = set(candidate['content'].lower().split())
                    sel_words = set(sel['content'].lower().split())
                    if cand_words and sel_words:
                        overlap = len(cand_words & sel_words) / len(cand_words | sel_words)
                        max_sim_selected = max(max_sim_selected, overlap)
                
                # Score MMR
                mmr = lambda_param * sim_query - (1 - lambda_param) * max_sim_selected
                
                if mmr > best_mmr:
                    best_mmr = mmr
                    best_idx = i
            
            selected.append(candidates.pop(best_idx))
        
        logger.info(f"📊 MMR selection: {len(selected)} diverse chunks")
        
        return selected
    
    # =========================================================================
    # STAGE 5: CONTEXTUALIZACIÓN (CHUNKS ADYACENTES)
    # =========================================================================
    
    def _add_adjacent_chunks(
        self, 
        document: Document,
        selected_chunks: List[Dict],
        max_adjacent: int = 2
    ) -> List[Dict]:
        """
        Agrega chunks adyacentes para contexto narrativo.
        
        Limita el número de adyacentes para no diluir la relevancia.
        """
        if not selected_chunks or not self.include_adjacent:
            return selected_chunks
        
        selected_orders = {c['order_number'] for c in selected_chunks}
        adjacent_orders = set()
        
        for order in selected_orders:
            adjacent_orders.add(order - 1)  # Anterior
            adjacent_orders.add(order + 1)  # Siguiente
        
        # Remover ya seleccionados e inválidos
        adjacent_orders -= selected_orders
        adjacent_orders = {o for o in adjacent_orders if o >= 1}
        
        if not adjacent_orders:
            return selected_chunks
        
        # Limitar adyacentes
        adjacent_orders = sorted(adjacent_orders)[:max_adjacent * 2]
        
        # Buscar chunks adyacentes
        adjacent_chunks = DocumentChunk.objects.filter(
            document_id=document,
            order_number__in=adjacent_orders
        )
        
        for chunk in adjacent_chunks:
            selected_chunks.append({
                'chunk_id': str(chunk.chunk_id),
                'content': chunk.content,
                'order_number': chunk.order_number,
                'semantic_similarity': 0.0,
                'combined_score': 0.0,
                'is_adjacent': True,
            })
        
        logger.info(f"📎 Added {adjacent_chunks.count()} adjacent chunks for context")
        
        return selected_chunks
    
    # =========================================================================
    # LIMPIEZA DE CONTENIDO
    # =========================================================================
    
    def _clean_chunk_content(self, content: str) -> str:
        """Limpia contenido del chunk para presentación."""
        cleaned = content
        
        # Remover marcadores de página
        cleaned = re.sub(r'\[Página \d+\]\s*', '', cleaned)
        cleaned = re.sub(r'\n*## PÁGINA \d+\n*', '\n', cleaned)
        cleaned = re.sub(r'Página\s+\d+\s+de\s+\d+', '', cleaned)
        
        # Remover artefactos OCR
        cleaned = re.sub(r'/g\d+', '', cleaned)
        
        # Normalizar espacios
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r' {2,}', ' ', cleaned)
        
        return cleaned.strip()
    
    # =========================================================================
    # MÉTODO PRINCIPAL: RETRIEVE RELEVANT CHUNKS
    # =========================================================================
    
    def retrieve_relevant_chunks(
        self, 
        document: Document, 
        question: str,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        include_adjacent: Optional[bool] = None
    ) -> List[Dict]:
        """
        Pipeline completo de recuperación RAG v3.0.
        
        1. Expande query con sinónimos legales
        2. Recupera N candidatos iniciales por similitud semántica
        3. Re-rankea con BM25 + posición
        4. Aplica MMR para diversidad
        5. Agrega chunks adyacentes
        6. Filtra por threshold y retorna
        """
        top_k = top_k or self.top_k
        threshold = similarity_threshold or self.similarity_threshold
        include_adj = include_adjacent if include_adjacent is not None else self.include_adjacent
        
        logger.info(f"{'='*60}")
        logger.info(f"🚀 RAG v3.0 PIPELINE START")
        logger.info(f"{'='*60}")
        logger.info(f"📝 Question: '{question[:100]}...'")
        logger.info(f"📊 Params: top_k={top_k}, threshold={threshold}")
        
        # STAGE 1: Query expansion
        expanded_query, added_terms = self._expand_query(question)
        
        # STAGE 2: Generate embedding y retrieve inicial
        question_embedding = self.encode_question(expanded_query, expand=False)
        if question_embedding is None:
            logger.error("❌ Could not generate question embedding")
            return []
        
        # STAGE 3: Retrieve initial candidates
        candidates = self._retrieve_initial_candidates(
            document, 
            question_embedding,
            self.initial_candidates
        )
        
        if not candidates:
            logger.warning("❌ No candidates found")
            return []
        
        # STAGE 4: Re-rank with BM25 + position
        reranked = self._rerank_chunks(question, candidates)
        
        # STAGE 5: Apply MMR for diversity
        diverse = self._apply_mmr(reranked, top_k, self.mmr_lambda)
        
        # STAGE 6: Filter by threshold
        filtered = [
            c for c in diverse 
            if c['combined_score'] >= threshold or c.get('is_adjacent')
        ]
        
        # Si muy pocos resultados, bajar threshold adaptativamente
        if len(filtered) < 3 and diverse:
            adaptive_threshold = threshold * 0.7
            filtered = [
                c for c in diverse 
                if c['combined_score'] >= adaptive_threshold or c.get('is_adjacent')
            ]
            logger.info(f"⚠️ Adaptive threshold: {threshold} → {adaptive_threshold}")
        
        # STAGE 7: Add adjacent chunks
        if include_adj:
            filtered = self._add_adjacent_chunks(document, filtered)
        
        # STAGE 8: Clean content
        for chunk in filtered:
            chunk['content'] = self._clean_chunk_content(chunk['content'])
            chunk['is_adjacent'] = chunk.get('is_adjacent', False)
        
        # STAGE 9: Sort by relevance (NOT by document order)
        # Chunks más relevantes primero para que el LLM los vea primero
        # Los adyacentes van al final con score 0
        filtered.sort(key=lambda x: (-x.get('combined_score', 0), x['order_number']))
        
        # Log final results
        logger.info(f"{'='*60}")
        logger.info(f"✅ RAG v3.0 RESULTS: {len(filtered)} chunks")
        logger.info(f"{'='*60}")
        
        main_chunks = [c for c in filtered if not c.get('is_adjacent')]
        adj_chunks = [c for c in filtered if c.get('is_adjacent')]
        
        if main_chunks:
            scores = [c['combined_score'] for c in main_chunks]
            logger.info(f"📊 Main chunks: {len(main_chunks)}")
            logger.info(f"📊 Scores: min={min(scores):.2%}, max={max(scores):.2%}, avg={sum(scores)/len(scores):.2%}")
            logger.info(f"📊 Orders: {[c['order_number'] for c in main_chunks]}")
        
        if adj_chunks:
            logger.info(f"📎 Adjacent chunks: {len(adj_chunks)}, orders: {[c['order_number'] for c in adj_chunks]}")
        
        return filtered
    
    # =========================================================================
    # FORMATEO DE CONTEXTO PARA LLM
    # =========================================================================
    
    def get_context_from_chunks(
        self, 
        chunks: List[Dict], 
        max_chars: Optional[int] = None,
        include_metadata: bool = True,
        sort_by_relevance: bool = True
    ) -> str:
        """
        Construye contexto optimizado para el LLM.
        
        Los chunks ya vienen ordenados por relevancia (más relevantes primero).
        El LLM verá primero los fragmentos más importantes.
        
        Args:
            chunks: Lista de chunks (ya ordenados por relevancia)
            max_chars: Máximo de caracteres
            include_metadata: Si incluir headers con relevancia
            sort_by_relevance: Si True, mantiene orden por relevancia;
                               Si False, ordena por posición en documento
        """
        if not chunks:
            return ""
        
        max_chars = max_chars or self.max_context_chars
        
        # Opcionalmente reordenar por posición para narrativa coherente
        display_chunks = chunks.copy()
        if not sort_by_relevance:
            display_chunks.sort(key=lambda x: x['order_number'])
        
        context_parts = []
        current_length = 0
        
        # Separar principales de adyacentes
        main_chunks = [c for c in display_chunks if not c.get('is_adjacent')]
        adj_chunks = [c for c in display_chunks if c.get('is_adjacent')]
        
        # Agregar chunks principales primero (ordenados por relevancia)
        for chunk in main_chunks:
            content = chunk['content']
            order = chunk.get('order_number', '?')
            score = chunk.get('combined_score', 0)
            
            if include_metadata:
                relevance_label = "MUY ALTA" if score >= 0.8 else "Alta" if score >= 0.6 else "Media" if score >= 0.4 else "Baja"
                header = f"[Fragmento #{order} - Relevancia: {relevance_label} ({score:.0%})]"
                chunk_text = f"{header}\n{content}"
            else:
                chunk_text = content
            
            # Verificar límite
            if current_length + len(chunk_text) + 30 > max_chars:
                remaining = max_chars - current_length - 50
                if remaining > 300:
                    chunk_text = chunk_text[:remaining] + "..."
                    context_parts.append(chunk_text)
                break
            
            context_parts.append(chunk_text)
            current_length += len(chunk_text) + 30
        
        # Agregar chunks adyacentes al final (si hay espacio)
        for chunk in adj_chunks:
            content = chunk['content']
            order = chunk.get('order_number', '?')
            
            if include_metadata:
                header = f"[Fragmento #{order} - Contexto adicional]"
                chunk_text = f"{header}\n{content}"
            else:
                chunk_text = content
            
            if current_length + len(chunk_text) + 30 > max_chars:
                break
            
            context_parts.append(chunk_text)
            current_length += len(chunk_text) + 30
        
        context = "\n\n---\n\n".join(context_parts)
        
        main_count = len(main_chunks)
        adj_count = len(adj_chunks)
        logger.info(f"📝 Context: {len(context)} chars ({main_count} main, {adj_count} adjacent)")
        
        return context
    
    def check_document_has_chunks(self, document: Document) -> Dict:
        """Verifica capacidad RAG del documento."""
        total_chunks = DocumentChunk.objects.filter(document_id=document).count()
        
        chunks_with_clean = DocumentChunk.objects.filter(
            document_id=document,
            clean_content_embedding__isnull=False
        ).count()
        
        chunks_with_legacy = DocumentChunk.objects.filter(
            document_id=document,
            content_embedding__isnull=False
        ).count()
        
        has_rag = chunks_with_clean > 0 or chunks_with_legacy > 0
        
        logger.info(f"📊 RAG Check: Document {document.document_id}")
        logger.info(f"   - Total chunks: {total_chunks}")
        logger.info(f"   - Clean embeddings (768d): {chunks_with_clean}")
        logger.info(f"   - Legacy embeddings (384d): {chunks_with_legacy}")
        logger.info(f"   - RAG enabled: {'✅' if has_rag else '❌'}")
        
        return {
            'total_chunks': total_chunks,
            'chunks_with_clean_embedding': chunks_with_clean,
            'chunks_with_legacy_embedding': chunks_with_legacy,
            'has_rag_capability': has_rag,
            'recommended_action': None if chunks_with_clean > 0 else 
                'Run: python manage.py regenerate_chunk_embeddings --document-id ' + str(document.document_id)
        }


# =============================================================================
# FACTORY (NO SINGLETON para evitar problemas de caché)
# =============================================================================

def get_rag_service_v3(
    top_k: int = 8,
    similarity_threshold: float = 0.35,
    **kwargs
) -> RAGServiceV3:
    """
    Crea una instancia de RAGService v3.0.
    
    Nota: Ya no es singleton para evitar problemas de configuración cached.
    El modelo de embeddings se comparte mediante el ChunkEmbeddingService singleton.
    """
    return RAGServiceV3(
        top_k=top_k,
        similarity_threshold=similarity_threshold,
        **kwargs
    )


# Alias para retrocompatibilidad
def get_rag_service(top_k: int = 8, similarity_threshold: float = 0.35) -> RAGServiceV3:
    """Alias para obtener RAGService v3.0 (reemplaza v2.0)."""
    return get_rag_service_v3(top_k=top_k, similarity_threshold=similarity_threshold)
