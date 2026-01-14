# apps/documents/services/rag_service_v4.py
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    RAG SERVICE v4.0 - DOCUMENTACIÓN COMPLETA                  ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  PROBLEMA QUE RESUELVE:                                                       ║
║  ─────────────────────                                                        ║
║  Los documentos legales son extensos (10,000+ palabras). Los LLMs tienen      ║
║  ventanas de contexto limitadas (~4096 tokens). No podemos enviar todo el     ║
║  documento al LLM, debemos seleccionar las partes más relevantes.             ║
║                                                                               ║
║  SOLUCIÓN - RAG (Retrieval Augmented Generation):                             ║
║  ────────────────────────────────────────────────                             ║
║  1. El documento se divide en "chunks" (fragmentos de ~500 palabras)          ║
║  2. Cada chunk se convierte en un vector (embedding) de 768 dimensiones       ║
║  3. La pregunta del usuario también se convierte en un vector                 ║
║  4. Buscamos los chunks cuyo vector sea más SIMILAR al de la pregunta         ║
║  5. Enviamos solo esos chunks al LLM como contexto                            ║
║                                                                               ║
║  ¿POR QUÉ FUNCIONA LA SIMILITUD SEMÁNTICA?                                    ║
║  ─────────────────────────────────────────                                    ║
║  Los embeddings capturan el SIGNIFICADO, no solo las palabras. Por ejemplo:   ║
║                                                                               ║
║    Pregunta: "¿Cuál fue la decisión del tribunal?"                            ║
║    Chunks relevantes encontrados:                                             ║
║      - "...RESOLVIERON: Declarar FUNDADA la demanda..."  (similitud: 78%)     ║
║      - "...SE DISPUSO: Confirmar la sentencia..."        (similitud: 75%)     ║
║                                                                               ║
║  El embedding entiende que "decisión", "resolvieron", "dispuso", "fallo"      ║
║  tienen significados relacionados aunque sean palabras diferentes.            ║
║                                                                               ║
║  NO NECESITAMOS DETECTAR TIPOS DE PREGUNTAS:                                  ║
║  ───────────────────────────────────────────                                  ║
║  La similitud semántica es AGNÓSTICA al tipo de pregunta. Funciona para:      ║
║    - "¿Cuáles son los antecedentes?"                                          ║
║    - "Explica los hechos"                                                     ║
║    - "¿Qué decidieron?"                                                       ║
║    - "Resumen del caso"                                                       ║
║    - "¿Quiénes son las partes?"                                               ║
║    - Cualquier otra pregunta...                                               ║
║                                                                               ║
║  El modelo de embeddings (paraphrase-multilingual-mpnet-base-v2) fue          ║
║  entrenado con millones de pares de oraciones en múltiples idiomas.           ║
║  Entiende sinónimos, paráfrasis y relaciones semánticas automáticamente.      ║
║                                                                               ║
║  FILOSOFÍA v4.0: "MENOS CHUNKS, MÁS CONTEXTO"                                 ║
║  ─────────────────────────────────────────────                                ║
║  Versiones anteriores: Traían 10-15 chunks dispersos por el documento.        ║
║  Problema: Fragmentos sin contexto, información incompleta.                   ║
║                                                                               ║
║  v4.0: Traemos solo 3 chunks principales PERO los expandimos con sus          ║
║  chunks adyacentes (±2 antes y después). Resultado: menos fragmentos          ║
║  pero cada uno con contexto completo.                                         ║
║                                                                               ║
║  EJEMPLO VISUAL:                                                              ║
║  ───────────────                                                              ║
║  Documento: [1][2][3][4][5][6][7][8][9][10][11][12]                           ║
║                                                                               ║
║  Si el chunk #5 es el más relevante a la pregunta:                            ║
║    - Versión anterior: Solo devolvía [5]                                      ║
║    - v4.0: Devuelve [3][4][5][6][7] (ventana de contexto)                     ║
║                                                                               ║
║  PIPELINE DE BÚSQUEDA:                                                        ║
║  ─────────────────────                                                        ║
║  1. ENCODE: Convertir pregunta a vector 768d                                  ║
║  2. SEARCH: Buscar chunks similares (distancia coseno en PostgreSQL)          ║
║  3. RERANK: Combinar similitud semántica + coincidencia de palabras (BM25)    ║
║  4. EXPAND: Agregar chunks adyacentes para contexto completo                  ║
║  5. MERGE: Fusionar ventanas que se solapan                                   ║
║  6. FORMAT: Generar texto estructurado para el LLM                            ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝

MÉTRICAS DE SIMILITUD:
======================

1. SIMILITUD SEMÁNTICA (Cosine Similarity):
   - Mide qué tan "alineados" están dos vectores en el espacio 768d
   - Rango: 0.0 (sin relación) a 1.0 (idénticos)
   - Captura significado, sinónimos, conceptos relacionados
   - Fórmula: cos(θ) = (A · B) / (||A|| × ||B||)

2. BM25 (Best Matching 25):
   - Mide coincidencia de palabras exactas
   - Útil cuando el usuario usa términos específicos del documento
   - Considera frecuencia de términos y longitud del documento

3. SCORE COMBINADO:
   - combined_score = 0.7 × semantic + 0.3 × bm25
   - Prioriza significado pero también considera coincidencias exactas

USO:
====
    from apps.documents.services.rag_service_v4 import get_rag_service
    
    # Crear servicio
    rag = get_rag_service()
    
    # Buscar contexto relevante (FUNCIONA CON CUALQUIER PREGUNTA)
    result = rag.retrieve_with_context(document, "¿Cuál fue el fallo?")
    result = rag.retrieve_with_context(document, "Explica los antecedentes")
    result = rag.retrieve_with_context(document, "¿Quiénes son las partes?")
    
    # Obtener texto formateado para LLM
    context = result.get_context_for_llm()
"""

import logging
import re
import math
from typing import List, Dict, Optional, Tuple, Set
from collections import defaultdict
from dataclasses import dataclass, field
import numpy as np

from django.db.models import F
from pgvector.django import CosineDistance

from apps.documents.models import Document, DocumentChunk
from apps.documents.services.chunk_embedding_service import get_chunk_embedding_service

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES - Estructuras para organizar resultados
# =============================================================================

@dataclass
class ChunkResult:
    """
    Representa un fragmento del documento con sus scores de relevancia.
    
    Attributes:
        chunk_id: Identificador único del chunk
        order_number: Posición en el documento (1 = primero, N = último)
        content: Texto del fragmento
        semantic_score: Similitud semántica con la pregunta (0.0 - 1.0)
        bm25_score: Coincidencia de palabras exactas (0.0 - 1.0) 
        combined_score: Score final ponderado
        is_anchor: True si es chunk principal, False si es contexto adyacente
    """
    chunk_id: str
    order_number: int
    content: str
    semantic_score: float
    bm25_score: float
    combined_score: float
    is_anchor: bool = True


@dataclass  
class ContextWindow:
    """
    Ventana de contexto: un chunk principal rodeado de sus adyacentes.
    
    Ejemplo: Si el anchor es chunk #5 con ventana de ±2:
        before = [chunk #3, chunk #4]
        anchor = chunk #5
        after = [chunk #6, chunk #7]
    """
    anchor: ChunkResult
    before: List[ChunkResult] = field(default_factory=list)
    after: List[ChunkResult] = field(default_factory=list)
    
    @property
    def all_chunks(self) -> List[ChunkResult]:
        """Todos los chunks en orden de lectura."""
        return self.before + [self.anchor] + self.after
    
    @property
    def combined_content(self) -> str:
        """Texto combinado de toda la ventana."""
        return "\n\n".join([c.content for c in self.all_chunks])
    
    @property
    def start_order(self) -> int:
        """Número del primer chunk en la ventana."""
        return self.before[0].order_number if self.before else self.anchor.order_number
    
    @property
    def end_order(self) -> int:
        """Número del último chunk en la ventana."""
        return self.after[-1].order_number if self.after else self.anchor.order_number


@dataclass
class RAGResult:
    """
    Resultado completo del proceso RAG.
    
    Contiene las ventanas de contexto encontradas y metadata del proceso.
    """
    question: str
    windows: List[ContextWindow]
    total_chunks_searched: int
    embedding_dimension: int
    processing_time_ms: float = 0
    
    @property
    def main_chunks_count(self) -> int:
        """Cantidad de chunks principales (anclas)."""
        return len(self.windows)
    
    @property
    def context_chunks_count(self) -> int:
        """Cantidad de chunks de contexto adicional."""
        return sum(len(w.before) + len(w.after) for w in self.windows)
    
    @property
    def total_chunks_used(self) -> int:
        """Total de chunks en el resultado."""
        return sum(len(w.all_chunks) for w in self.windows)
    
    def get_context_for_llm(self, max_chars: int = 10000) -> str:
        """
        Genera el texto de contexto formateado para enviar al LLM.
        
        El formato es claro y estructurado para que el LLM pueda
        identificar fácilmente las secciones relevantes.
        
        Args:
            max_chars: Límite de caracteres (para no exceder contexto del LLM)
            
        Returns:
            Texto formateado con las secciones relevantes del documento
        """
        if not self.windows:
            return "[No se encontraron fragmentos relevantes]"
        
        parts = []
        current_length = 0
        
        for i, window in enumerate(self.windows, 1):
            # Calcular nivel de relevancia para mostrar al usuario
            relevance = window.anchor.combined_score
            if relevance >= 0.7:
                rel_label = "MUY ALTA"
            elif relevance >= 0.5:
                rel_label = "ALTA"
            elif relevance >= 0.35:
                rel_label = "MEDIA"
            else:
                rel_label = "BAJA"
            
            # Header de la sección
            header = f"{'═' * 60}\n"
            header += f"📄 SECCIÓN {i} | Relevancia: {rel_label} ({relevance:.0%})\n"
            header += f"   Fragmentos #{window.start_order} al #{window.end_order}\n"
            header += f"{'═' * 60}\n"
            
            content = f"{header}\n{window.combined_content}"
            
            # Verificar límite de caracteres
            if current_length + len(content) > max_chars:
                remaining = max_chars - current_length - 100
                if remaining > 500:
                    content = content[:remaining] + "\n\n[...contenido truncado por límite...]"
                    parts.append(content)
                break
            
            parts.append(content)
            current_length += len(content) + 50
        
        return "\n\n".join(parts)


# =============================================================================
# RAG SERVICE v4.0 - Servicio Principal
# =============================================================================

class RAGServiceV4:
    """
    Servicio RAG (Retrieval Augmented Generation) versión 4.0.
    
    Este servicio encuentra los fragmentos más relevantes de un documento
    para responder una pregunta específica del usuario.
    
    IMPORTANTE: Este servicio es AGNÓSTICO al tipo de pregunta.
    ══════════════════════════════════════════════════════════
    No intentamos detectar si el usuario pregunta por "antecedentes",
    "decisión", "partes", etc. La similitud semántica se encarga de
    encontrar los chunks relevantes automáticamente.
    
    ¿Por qué? Porque el modelo de embeddings fue entrenado para entender
    el SIGNIFICADO de las oraciones, no solo las palabras. Si el usuario
    pregunta "¿Cuál fue el fallo?", el modelo encontrará chunks que 
    contengan "resolvieron", "decidieron", "sentenciaron", etc.
    
    Características principales:
    - Búsqueda por similitud semántica (embeddings 768d)
    - Re-ranking con BM25 para mejorar precisión
    - Expansión de contexto (chunks adyacentes)
    - Fusión de ventanas solapadas
    - Logging detallado para debugging
    
    Attributes:
        top_k_anchors: Número de chunks principales a recuperar (default: 3)
        context_window_size: Chunks adyacentes a incluir (default: 2)
        similarity_threshold: Umbral mínimo de similitud (default: 0.35)
    """
    
    def __init__(
        self,
        top_k_anchors: int = 3,
        context_window_size: int = 2,
        similarity_threshold: float = 0.35,
    ):
        """
        Inicializa el servicio RAG.
        
        Args:
            top_k_anchors: Cuántos chunks principales recuperar.
                          Más = más información pero más ruido.
                          Menos = más enfocado pero puede perder info.
                          Recomendado: 3-5
            
            context_window_size: Cuántos chunks adyacentes incluir.
                                ±2 significa 2 antes y 2 después del anchor.
                                Recomendado: 2-3
            
            similarity_threshold: Umbral mínimo de similitud.
                                 Chunks con score menor se descartan.
                                 Recomendado: 0.30-0.45
        """
        self.top_k_anchors = top_k_anchors
        self.context_window_size = context_window_size
        self.similarity_threshold = similarity_threshold
        
        # Servicio de embeddings para convertir texto a vectores
        self.embedding_service = get_chunk_embedding_service()
    
    # =========================================================================
    # MÉTODO PRINCIPAL
    # =========================================================================
    
    def retrieve_with_context(
        self,
        document: Document,
        question: str,
        top_k: Optional[int] = None,
        context_size: Optional[int] = None,
    ) -> RAGResult:
        """
        Recupera fragmentos relevantes del documento para la pregunta dada.
        
        Este es el método principal del servicio. Ejecuta el pipeline completo:
        1. Genera embedding de la pregunta
        2. Busca chunks similares en la base de datos
        3. Aplica re-ranking con BM25
        4. Expande con contexto adyacente
        5. Fusiona ventanas solapadas
        
        NOTA: Este método es agnóstico al tipo de pregunta. Funciona igual
        para "¿Cuáles son los antecedentes?" que para "¿Qué decidieron?".
        La similitud semántica encuentra los chunks relevantes automáticamente.
        
        Args:
            document: Documento donde buscar
            question: Pregunta del usuario (cualquier pregunta)
            top_k: Override para top_k_anchors
            context_size: Override para context_window_size
            
        Returns:
            RAGResult con las ventanas de contexto encontradas
            
        Example:
            >>> rag = get_rag_service()
            >>> result = rag.retrieve_with_context(doc, "¿Cuál fue el fallo?")
            >>> result = rag.retrieve_with_context(doc, "Explica los antecedentes")
            >>> print(result.get_context_for_llm())
        """
        import time
        start_time = time.time()
        
        top_k = top_k or self.top_k_anchors
        context_size = context_size or self.context_window_size
        
        # ═══════════════════════════════════════════════════════════════════
        # LOGGING - Inicio del proceso
        # ═══════════════════════════════════════════════════════════════════
        self._log_header("RAG v4.0 - BÚSQUEDA SEMÁNTICA")
        self._log_section("ENTRADA")
        self._log_item("Documento", f"{document.title[:50]}...")
        self._log_item("Pregunta", f'"{question}"')
        self._log_item("Configuración", f"top_k={top_k}, contexto=±{context_size}")
        
        # ═══════════════════════════════════════════════════════════════════
        # PASO 1: Generar embedding de la pregunta
        # ═══════════════════════════════════════════════════════════════════
        self._log_section("PASO 1: GENERAR EMBEDDING DE LA PREGUNTA")
        
        query_embedding = self.embedding_service.encode_query(question, normalize=True)
        
        if query_embedding is None:
            self._log_item("Estado", "❌ Error al generar embedding")
            return RAGResult(
                question=question,
                windows=[],
                total_chunks_searched=0,
                embedding_dimension=0,
            )
        
        self._log_item("Vector generado", f"{query_embedding.shape[0]} dimensiones ✓")
        self._log_item("Nota", "Este vector captura el SIGNIFICADO de la pregunta")
        
        # ═══════════════════════════════════════════════════════════════════
        # PASO 2: Buscar chunks similares en base de datos
        # ═══════════════════════════════════════════════════════════════════
        self._log_section("PASO 2: BUSCAR CHUNKS SIMILARES")
        
        # Determinar qué campo de embedding usar
        chunks_with_clean = DocumentChunk.objects.filter(
            document_id=document,
            clean_content_embedding__isnull=False
        )
        
        use_clean = chunks_with_clean.exists()
        embedding_field = 'clean_content_embedding' if use_clean else 'content_embedding'
        embedding_dim = 768 if use_clean else 384
        
        if use_clean:
            chunks_query = chunks_with_clean
        else:
            # Fallback a embeddings legacy 384d
            chunks_query = DocumentChunk.objects.filter(
                document_id=document,
                content_embedding__isnull=False
            )
            # Regenerar embedding de query con modelo correcto
            from apps.documents.services.embedding_service import get_embedding_service
            query_embedding = get_embedding_service().encode_text(question, normalize=True)
        
        total_chunks = chunks_query.count()
        self._log_item("Total chunks en documento", str(total_chunks))
        self._log_item("Campo embedding", f"{embedding_field} ({embedding_dim}d)")
        
        if total_chunks == 0:
            self._log_item("Estado", "⚠️ Sin chunks disponibles")
            return RAGResult(
                question=question,
                windows=[],
                total_chunks_searched=0,
                embedding_dimension=embedding_dim,
            )
        
        # Buscar por similitud coseno - traer más candidatos para filtrar después
        search_limit = min(top_k * 4, total_chunks)
        
        # PostgreSQL calcula distancia coseno entre vectores
        candidates = chunks_query.annotate(
            distance=CosineDistance(embedding_field, query_embedding.tolist())
        ).order_by('distance')[:search_limit]
        
        self._log_item("Candidatos recuperados", str(len(candidates)))
        self._log_item("Método", "Distancia coseno en PostgreSQL (pgvector)")
        
        # ═══════════════════════════════════════════════════════════════════
        # PASO 3: Calcular scores y re-rankear
        # ═══════════════════════════════════════════════════════════════════
        self._log_section("PASO 3: RE-RANKING (Semántico + BM25)")
        
        chunk_results = []
        
        for chunk in candidates:
            # Similitud semántica = 1 - distancia coseno
            # (distancia 0 = idénticos, distancia 2 = opuestos)
            semantic_score = 1 - chunk.distance
            
            # BM25: coincidencia de palabras exactas
            bm25_score = self._calculate_bm25(question, chunk.content)
            
            # Score combinado: 70% semántico + 30% BM25
            # Priorizamos semántico porque captura significado
            # BM25 ayuda cuando hay términos específicos
            combined_score = (0.4 * semantic_score) + (0.6 * bm25_score)
            
            chunk_results.append(ChunkResult(
                chunk_id=str(chunk.chunk_id),
                order_number=chunk.order_number,
                content=chunk.content,
                semantic_score=semantic_score,
                bm25_score=bm25_score,
                combined_score=combined_score,
                is_anchor=True,
            ))
        
        # Ordenar por score combinado (mayor = más relevante)
        chunk_results.sort(key=lambda x: x.combined_score, reverse=True)
        
        # Filtrar por umbral de similitud
        filtered_results = [
            c for c in chunk_results 
            if c.combined_score >= self.similarity_threshold
        ]
        
        self._log_item("Fórmula", "combined = 0.4 × semántico + 0.6 × BM25")
        self._log_item("Umbral", f"{self.similarity_threshold:.0%}")
        self._log_item("Chunks sobre umbral", f"{len(filtered_results)}/{len(chunk_results)}")
        
        # Seleccionar top-k chunks principales
        anchors = filtered_results[:top_k]
        
        # Mostrar chunks seleccionados
        self._log_item("", "")
        self._log_item("📊 CHUNKS SELECCIONADOS (ordenados por relevancia)", "")
        for i, chunk in enumerate(anchors, 1):
            preview = chunk.content[:60].replace('\n', ' ')
            self._log_item(
                f"   {i}. Chunk #{chunk.order_number:3d}",
                f"Score: {chunk.combined_score:.0%} (Sem: {chunk.semantic_score:.0%}, BM25: {chunk.bm25_score:.0%})"
            )
            self._log_item("", f'      "{preview}..."')
        
        if not anchors:
            self._log_item("Estado", "⚠️ No hay chunks suficientemente relevantes")
            return RAGResult(
                question=question,
                windows=[],
                total_chunks_searched=total_chunks,
                embedding_dimension=embedding_dim,
            )
        
        # ═══════════════════════════════════════════════════════════════════
        # PASO 4: Expandir con contexto adyacente
        # ═══════════════════════════════════════════════════════════════════
        self._log_section("PASO 4: EXPANDIR CON CONTEXTO ADYACENTE")
        self._log_item("Estrategia", f"Agregar ±{context_size} chunks alrededor de cada ancla")
        
        windows = self._expand_with_context(
            document=document,
            anchors=anchors,
            context_size=context_size,
            chunks_query=chunks_query,
        )
















        
        
        # ═══════════════════════════════════════════════════════════════════
        # PASO 5: Fusionar ventanas solapadas
        # ═══════════════════════════════════════════════════════════════════
        self._log_section("PASO 5: FUSIONAR VENTANAS SOLAPADAS")
        
        merged_windows = self._merge_overlapping_windows(windows)
        
        self._log_item("Ventanas originales", str(len(windows)))
        self._log_item("Ventanas después de fusión", str(len(merged_windows)))
        
        # ═══════════════════════════════════════════════════════════════════
        # RESULTADO FINAL
        # ═══════════════════════════════════════════════════════════════════
        processing_time = (time.time() - start_time) * 1000
        
        result = RAGResult(
            question=question,
            windows=merged_windows,
            total_chunks_searched=total_chunks,
            embedding_dimension=embedding_dim,
            processing_time_ms=processing_time,
        )
        
        # Log del resultado
        self._log_result_summary(result)
        
        return result
    
    # =========================================================================
    # MÉTODOS AUXILIARES
    # =========================================================================
    
    def _calculate_bm25(
        self,
        query: str,
        document: str,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> float:
        """
        Calcula score BM25 simplificado.
        
        BM25 es un algoritmo clásico de Information Retrieval que mide
        qué tan bien un documento coincide con una query basándose en
        la frecuencia de términos.
        
        Complementa la similitud semántica porque detecta coincidencias
        de palabras exactas que podrían ser importantes.
        
        Args:
            query: Texto de la pregunta
            document: Texto del chunk
            k1: Parámetro de saturación de frecuencia (default: 1.5)
            b: Parámetro de normalización por longitud (default: 0.75)
            
        Returns:
            Score BM25 normalizado entre 0 y 1
        """
        # Tokenizar (simplificado - solo palabras alfanuméricas)
        query_terms = set(re.findall(r'\w+', query.lower()))
        doc_terms = re.findall(r'\w+', document.lower())
        
        if not query_terms or not doc_terms:
            return 0.0
        
        doc_len = len(doc_terms)
        avg_doc_len = 500  # Aproximación para chunks de ~500 palabras
        
        score = 0.0
        doc_term_freq = defaultdict(int)
        for term in doc_terms:
            doc_term_freq[term] += 1
        
        for term in query_terms:
            if term in doc_term_freq:
                tf = doc_term_freq[term]
                idf = 1.0  # Simplificado (sin corpus completo)
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * (doc_len / avg_doc_len))
                score += idf * (numerator / denominator)
        
        # Normalizar a [0, 1]
        max_possible = len(query_terms) * (k1 + 1) / (1 + k1 * (1 - b))
        return min(score / max_possible, 1.0) if max_possible > 0 else 0.0
    
    def _expand_with_context(
        self,
        document: Document,
        anchors: List[ChunkResult],
        context_size: int,
        chunks_query,
    ) -> List[ContextWindow]:
        """
        Expande cada chunk anchor con sus chunks adyacentes.
        
        Para cada anchor, recuperamos los chunks que están inmediatamente
        antes y después en el documento para proporcionar contexto completo.
        
        Ejemplo: Si anchor es chunk #5 y context_size es 2:
            - Recuperamos chunks #3, #4, #5, #6, #7
            - #5 es el anchor, #3-4 son before, #6-7 son after
        
        Args:
            document: Documento fuente
            anchors: Lista de chunks principales
            context_size: Cantidad de chunks adyacentes (antes y después)
            chunks_query: QuerySet de chunks para buscar adyacentes
            
        Returns:
            Lista de ContextWindow, una por cada anchor
        """
        windows = []
        
        for anchor in anchors:
            # Determinar rango de chunks a recuperar
            start_order = max(1, anchor.order_number - context_size)
            end_order = anchor.order_number + context_size
            
            # Recuperar chunks adyacentes
            adjacent_chunks = chunks_query.filter(
                order_number__gte=start_order,
                order_number__lte=end_order,
            ).exclude(
                order_number=anchor.order_number
            ).order_by('order_number')
            
            before = []
            after = []
            
            for chunk in adjacent_chunks:
                chunk_result = ChunkResult(
                    chunk_id=str(chunk.chunk_id),
                    order_number=chunk.order_number,
                    content=chunk.content,
                    semantic_score=0.0,  # No calculado para adyacentes
                    bm25_score=0.0,
                    combined_score=0.0,
                    is_anchor=False,  # Marcar como contexto, no ancla
                )
                
                if chunk.order_number < anchor.order_number:
                    before.append(chunk_result)
                else:
                    after.append(chunk_result)
            
            window = ContextWindow(
                anchor=anchor,
                before=before,
                after=after,
            )
            windows.append(window)
            
            self._log_item(
                f"📦 Ventana",
                f"Chunks #{window.start_order}-#{window.end_order} ({len(window.all_chunks)} chunks)"
            )
        
        return windows
    
    def _merge_overlapping_windows(
        self,
        windows: List[ContextWindow],
    ) -> List[ContextWindow]:
        """
        Fusiona ventanas que se solapan en una sola.
        
        Si dos ventanas comparten chunks (porque sus anchors están cerca),
        las fusionamos en una sola ventana más grande para evitar repetición.
        
        Ejemplo:
            - Ventana 1: chunks #1-#5 (anchor en #3)
            - Ventana 2: chunks #4-#8 (anchor en #6)
            - Se solapan en #4-#5
            - Resultado: una ventana #1-#8 (anchor con mayor score)
        
        Args:
            windows: Lista de ventanas a procesar
            
        Returns:
            Lista de ventanas fusionadas (sin solapamiento)
        """
        if len(windows) <= 1:
            return windows
        
        # Ordenar por posición de inicio
        sorted_windows = sorted(windows, key=lambda w: w.start_order)
        
        merged = [sorted_windows[0]]
        
        for current in sorted_windows[1:]:
            last = merged[-1]
            
            # Verificar si hay solapamiento (o son adyacentes)
            if current.start_order <= last.end_order + 1:
                # Fusionar: mantener el anchor con mayor score
                if current.anchor.combined_score > last.anchor.combined_score:
                    new_anchor = current.anchor
                else:
                    new_anchor = last.anchor
                
                # Combinar todos los chunks únicos
                all_orders = set()
                all_chunks = {}
                
                for chunk in last.all_chunks + current.all_chunks:
                    if chunk.order_number not in all_orders:
                        all_orders.add(chunk.order_number)
                        all_chunks[chunk.order_number] = chunk
                
                # Reconstruir before/after alrededor del nuevo anchor
                before = []
                after = []
                
                for order in sorted(all_chunks.keys()):
                    chunk = all_chunks[order]
                    if order < new_anchor.order_number:
                        chunk.is_anchor = False
                        before.append(chunk)
                    elif order > new_anchor.order_number:
                        chunk.is_anchor = False
                        after.append(chunk)
                
                merged[-1] = ContextWindow(
                    anchor=new_anchor,
                    before=before,
                    after=after,
                )
            else:
                # No hay solapamiento, agregar como nueva ventana
                merged.append(current)
        
        return merged
    
    def check_document_has_chunks(self, document: Document) -> Dict:
        """
        Verifica si un documento tiene chunks con embeddings.
        
        Útil para saber si podemos usar RAG o debemos usar fallback
        (enviar texto plano del documento).
        
        Args:
            document: Documento a verificar
            
        Returns:
            Dict con:
                - total_chunks: Total de chunks del documento
                - chunks_with_embeddings: Chunks con vector generado
                - has_rag_capability: True si podemos usar RAG
                - embedding_coverage: Porcentaje de cobertura
        """
        total = DocumentChunk.objects.filter(document_id=document).count()
        with_embeddings = DocumentChunk.objects.filter(
            document_id=document,
            clean_content_embedding__isnull=False
        ).count()
        
        return {
            'total_chunks': total,
            'chunks_with_embeddings': with_embeddings,
            'has_rag_capability': with_embeddings > 0,
            'embedding_coverage': with_embeddings / total if total > 0 else 0,
        }
    
    # =========================================================================
    # LOGGING - Métodos para logs claros y estructurados
    # =========================================================================
    
    def _log_header(self, title: str):
        """Imprime header principal del proceso."""
        border = "═" * 68
        logger.info(f"\n╔{border}╗")
        logger.info(f"║{title:^68}║")
        logger.info(f"╚{border}╝\n")
    
    def _log_section(self, title: str):
        """Imprime header de sección."""
        logger.info(f"\n┌─── {title} {'─' * max(0, 50 - len(title))}")
    
    def _log_item(self, key: str, value: str):
        """Imprime item de log."""
        if key:
            logger.info(f"│  • {key}: {value}")
        else:
            logger.info(f"│    {value}")
    
    def _log_result_summary(self, result: RAGResult):
        """Imprime resumen final del resultado."""
        border = "═" * 68
        logger.info(f"\n╔{border}╗")
        logger.info(f"║{'RESULTADO RAG v4.0':^68}║")
        logger.info(f"╠{border}╣")
        logger.info(f"║  Ventanas de contexto: {result.main_chunks_count:<44}║")
        logger.info(f"║  Chunks principales (anclas): {result.main_chunks_count:<37}║")
        logger.info(f"║  Chunks de contexto (adyacentes): {result.context_chunks_count:<33}║")
        logger.info(f"║  Total chunks en resultado: {result.total_chunks_used:<39}║")
        logger.info(f"║  Tiempo de procesamiento: {result.processing_time_ms:.0f}ms{' ' * 39}║")
        logger.info(f"╚{border}╝\n")


# =============================================================================
# FACTORY - Función para crear instancias del servicio
# =============================================================================

def get_rag_service(
    top_k_anchors: int = 3,
    context_window_size: int = 2,
    similarity_threshold: float = 0.35,
    **kwargs
) -> RAGServiceV4:
    """
    Crea una instancia de RAG Service v4.0.
    
    Esta es la función principal para obtener el servicio RAG.
    El servicio es AGNÓSTICO al tipo de pregunta - funciona con cualquier
    pregunta gracias a la similitud semántica.
    
    Args:
        top_k_anchors: Chunks principales a recuperar (default: 3)
                      - 3: Más enfocado, menos ruido
                      - 5: Más cobertura, más información
        context_window_size: Chunks de contexto ±N (default: 2)
                            - 2: Contexto moderado
                            - 3: Más contexto por ventana
        similarity_threshold: Umbral mínimo de similitud (default: 0.35)
                             - 0.30: Más resultados, posible ruido
                             - 0.45: Menos resultados, más precisos
        
    Returns:
        Instancia configurada de RAGServiceV4
        
    Example:
        >>> rag = get_rag_service()
        >>> result = rag.retrieve_with_context(doc, "¿Qué decidieron?")
        >>> result = rag.retrieve_with_context(doc, "Explica los antecedentes")
        >>> context = result.get_context_for_llm()
    """
    return RAGServiceV4(
        top_k_anchors=top_k_anchors,
        context_window_size=context_window_size,
        similarity_threshold=similarity_threshold,
        **kwargs
    )


# Aliases para compatibilidad con código existente
def get_rag_service_v3(*args, **kwargs) -> RAGServiceV4:
    """Alias para compatibilidad - retorna v4."""
    return get_rag_service(*args, **kwargs)


def get_rag_service_v4(*args, **kwargs) -> RAGServiceV4:
    """Alias explícito para v4."""
    return get_rag_service(*args, **kwargs)
