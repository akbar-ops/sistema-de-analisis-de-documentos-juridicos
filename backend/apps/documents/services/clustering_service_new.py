"""
Servicio de clustering de documentos - Nueva Arquitectura
=========================================================

Arquitectura correcta:
1. Backend (batch nocturno):
   - Cargar embeddings originales (384D)
   - UMAP 30D → reducción para preservar estructura global
   - HDBSCAN en 30D → obtener clusters semánticos estables
   - UMAP 2D → solo para coordenadas de visualización (x, y)
   - KNN graph → edges para "documentos relacionados"
   - Guardar todo en ClusterGraph, ClusterGraphNode, ClusterGraphEdge

2. Frontend (instantáneo):
   - Cargar nodos (x, y, cluster, metadata)
   - Dibujar scatter plot
   - Color = cluster
   - On click → mostrar vecinos (edges)
   - Toggle: show/hide KNN edges

Beneficios:
- Exploración visual completa del espacio de conocimiento
- Saltar entre documentos relacionados (KNN edges)
- Clusters claramente separados
- Detección de anomalías
- Modos: Clusters vs Connected
- Mapa reutilizable y estable
"""

import logging
import numpy as np
import re
import time
from typing import List, Dict, Any, Optional, Tuple
from django.db import transaction
from django.utils import timezone
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors
from sklearn.feature_extraction.text import TfidfVectorizer

# Importar métricas de calidad de clustering
try:
    from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    print("⚠️  Clustering metrics not available. Install sklearn.")

# Importar UMAP si está disponible
try:
    import umap
    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False
    print("⚠️  UMAP not available. Install with: pip install umap-learn")

# Importar HDBSCAN si está disponible
try:
    import hdbscan
    HDBSCAN_AVAILABLE = True
except ImportError:
    HDBSCAN_AVAILABLE = False
    print("⚠️  HDBSCAN not available. Install with: pip install hdbscan")

from apps.documents.models import (
    Document, 
    ClusterGraph, 
    ClusterGraphNode, 
    ClusterGraphEdge
)

logger = logging.getLogger(__name__)


class ClusteringService:
    """
    Servicio para clustering de documentos legales.
    Soporta dos modos:
    1. compute_global_clusters() - Batch job que precomputa todo el grafo
    2. get_cached_clusters() - API que sirve el grafo precomputado
    """
    
    def __init__(self):
        # Parámetros por defecto para UMAP 30D (preservar estructura global)
        self.umap_30d_defaults = {
            'n_components': 30,
            'n_neighbors': 15,
            'min_dist': 0.0,
            'metric': 'cosine',
            'random_state': 42
        }
        
        # Parámetros por defecto para UMAP 2D (solo visualización)
        self.umap_2d_defaults = {
            'n_components': 2,
            'n_neighbors': 10,
            'min_dist': 0.99,
            'metric': 'cosine',
            'random_state': 42
        }
        
        # Parámetros por defecto para HDBSCAN
        self.hdbscan_defaults = {
            'min_cluster_size': 4,  # Sweet spot between 3 (too many) and 5 (too few)
            'min_samples': 2,  # Reduced from 3 for more sensitivity
            'metric': 'euclidean',
            'cluster_selection_method': 'eom',
            'prediction_data': True  # Necesario para soft clustering
        }
        
        # Parámetros por defecto para KNN graph
        self.knn_defaults = {
            'k': 3,  # Número de vecinos más cercanos
            'min_similarity': 0.6  # Umbral mínimo de similitud para crear edge
        }
    
    def compute_global_clusters(
        self,
        max_documents: int = 1000,
        use_enhanced_embedding: bool = False,
        use_clean_embedding: bool = True,
        umap_30d_params: Optional[Dict[str, Any]] = None,
        umap_2d_params: Optional[Dict[str, Any]] = None,
        clustering_params: Optional[Dict[str, Any]] = None,
        knn_params: Optional[Dict[str, Any]] = None,
        algorithm: str = 'hdbscan'
    ) -> ClusterGraph:
        """
        Computa el grafo global de clusters (BATCH JOB).
        
        Este es el método principal que se ejecuta periódicamente
        para recalcular el grafo completo de documentos.
        
        Args:
            max_documents: Máximo de documentos a incluir
            use_enhanced_embedding: Si True usa enhanced_embedding
            use_clean_embedding: Si True usa clean_embedding (768D) - RECOMENDADO
            umap_30d_params: Parámetros para UMAP XD→30D
            umap_2d_params: Parámetros para UMAP 30D→2D
            clustering_params: Parámetros para HDBSCAN/DBSCAN
            knn_params: Parámetros para KNN graph
            algorithm: 'hdbscan' o 'dbscan'
            
        Returns:
            ClusterGraph creado
        """
        start_time = time.time()
        
        logger.info("🚀 Starting global cluster computation...")
        
        # Verificar dependencias
        if not UMAP_AVAILABLE:
            raise ImportError("UMAP is required for clustering. Install with: pip install umap-learn")
        
        if algorithm == 'hdbscan' and not HDBSCAN_AVAILABLE:
            raise ImportError("HDBSCAN is required. Install with: pip install hdbscan")
        
        # Merge parámetros con defaults
        umap_30d_params = {**self.umap_30d_defaults, **(umap_30d_params or {})}
        umap_2d_params = {**self.umap_2d_defaults, **(umap_2d_params or {})}
        clustering_params = {**self.hdbscan_defaults, **(clustering_params or {})}
        knn_params = {**self.knn_defaults, **(knn_params or {})}
        
        # 1. Cargar documentos con embeddings
        # Prioridad: clean_embedding (768D) > enhanced_embedding (384D) > summary_embedding
        if use_clean_embedding:
            embedding_field = 'clean_embedding'
            logger.info("📦 Using clean_embedding (768D) for clustering")
        elif use_enhanced_embedding:
            embedding_field = 'enhanced_embedding'
            logger.info("📦 Using enhanced_embedding (384D) for clustering")
        else:
            embedding_field = 'summary_embedding'
            logger.info("📦 Using summary_embedding for clustering")
        
        documents = Document.objects.filter(
            status='processed',
            **{f'{embedding_field}__isnull': False}
        ).prefetch_related(
            'legal_area',
            'doc_type'
        ).order_by('-created_at')[:max_documents]
        
        if not documents.exists():
            logger.warning(f"No documents found with {embedding_field}")
            raise ValueError(f"No documents available for clustering (no {embedding_field})")
        
        doc_list = list(documents)
        logger.info(f"📊 Loaded {len(doc_list)} documents with {embedding_field}")
        
        # 2. Extraer embeddings originales (384D)
        embeddings_384d = np.array([
            np.array(getattr(doc, embedding_field))
            for doc in doc_list
        ], dtype=np.float64)
        
        logger.info(f"📐 Original embeddings shape: {embeddings_384d.shape}")
        
        # 3. UMAP 384D → 30D (preservar estructura global)
        logger.info("🔄 Applying UMAP 384D → 30D (preserve global structure)...")
        reducer_30d = umap.UMAP(**umap_30d_params, n_jobs=-1)
        embeddings_30d = reducer_30d.fit_transform(embeddings_384d)
        logger.info(f"✅ UMAP 30D shape: {embeddings_30d.shape}")
        
        # 4. HDBSCAN clustering en 30D
        logger.info(f"🎯 Applying {algorithm.upper()} clustering on 30D embeddings...")
        
        if algorithm == 'hdbscan':
            clusterer = hdbscan.HDBSCAN(**clustering_params)
            cluster_labels = clusterer.fit_predict(embeddings_30d)
        else:
            # DBSCAN fallback
            from sklearn.cluster import DBSCAN
            eps = clustering_params.get('eps', 0.5)
            min_samples = clustering_params.get('min_samples', 3)
            clusterer = DBSCAN(eps=eps, min_samples=min_samples, metric='euclidean')
            cluster_labels = clusterer.fit_predict(embeddings_30d)
        
        unique_clusters = np.unique(cluster_labels)
        n_clusters = len([c for c in unique_clusters if c != -1])
        n_noise = np.sum(cluster_labels == -1)
        
        logger.info(f"✅ Found {n_clusters} clusters, {n_noise} noise points")
        
        # 5. UMAP 30D → 2D (solo para visualización)
        logger.info("🔄 Applying UMAP 30D → 2D (visualization only)...")
        reducer_2d = umap.UMAP(**umap_2d_params, n_jobs=-1)
        embeddings_2d = reducer_2d.fit_transform(embeddings_30d)
        logger.info(f"✅ UMAP 2D shape: {embeddings_2d.shape}")
        
        # 6. Construir KNN graph sobre embeddings originales (384D)
        # Esto asegura que las similitudes sean semánticamente correctas
        logger.info(f"🔗 Building KNN graph (k={knn_params['k']})...")
        knn_edges = self._build_knn_graph(
            embeddings_384d,
            k=knn_params['k'],
            min_similarity=knn_params['min_similarity']
        )
        logger.info(f"✅ Created {len(knn_edges)} KNN edges")
        
        # 7. Guardar todo en la base de datos
        logger.info("💾 Saving cluster graph to database...")
        
        with transaction.atomic():
            # Crear ClusterGraph
            cluster_graph = ClusterGraph.objects.create(
                document_count=len(doc_list),
                cluster_count=n_clusters,
                noise_count=n_noise,
                algorithm=algorithm,
                metric='cosine',
                umap_30d_params=umap_30d_params,
                umap_2d_params=umap_2d_params,
                clustering_params=clustering_params,
                knn_params=knn_params,
                computation_time_seconds=time.time() - start_time,
                is_active=False  # No activar automáticamente
            )
            
            # Crear nodos
            nodes = []
            doc_to_node = {}  # Mapeo para crear edges después
            
            for idx, doc in enumerate(doc_list):
                node = ClusterGraphNode(
                    graph=cluster_graph,
                    document=doc,
                    umap_30d_embedding=embeddings_30d[idx].tolist(),
                    x=float(embeddings_2d[idx][0]),
                    y=float(embeddings_2d[idx][1]),
                    cluster_label=int(cluster_labels[idx]),
                    is_noise=(cluster_labels[idx] == -1),
                    doc_title=doc.title,
                    doc_case_number=doc.case_number,
                    doc_legal_area_name=doc.legal_area.name if doc.legal_area else None,
                    doc_type_name=doc.doc_type.name if doc.doc_type else None,
                    doc_date=doc.document_date
                )
                nodes.append(node)
            
            # Bulk create nodes
            created_nodes = ClusterGraphNode.objects.bulk_create(nodes, batch_size=500)
            
            # Crear mapeo doc_idx → node
            for idx, node in enumerate(created_nodes):
                doc_to_node[idx] = node
            
            logger.info(f"✅ Created {len(created_nodes)} nodes")
            
            # Crear edges
            edges = []
            for source_idx, target_idx, similarity in knn_edges:
                edge = ClusterGraphEdge(
                    graph=cluster_graph,
                    source_node=doc_to_node[source_idx],
                    target_node=doc_to_node[target_idx],
                    similarity=float(similarity),
                    edge_type='knn'
                )
                edges.append(edge)
            
            # Bulk create edges
            if edges:
                ClusterGraphEdge.objects.bulk_create(edges, batch_size=1000)
                logger.info(f"✅ Created {len(edges)} edges")
            
            # Calcular y guardar métricas de calidad del clustering
            logger.info("📊 Computing clustering quality metrics...")
            try:
                # Solo calcular si hay al menos 2 clusters
                non_noise_mask = cluster_labels != -1
                non_noise_labels = cluster_labels[non_noise_mask]
                non_noise_embeddings = embeddings_30d[non_noise_mask]
                
                if len(np.unique(non_noise_labels)) >= 2 and len(non_noise_embeddings) >= 2:
                    sil_score = silhouette_score(non_noise_embeddings, non_noise_labels)
                    ch_score = calinski_harabasz_score(non_noise_embeddings, non_noise_labels)
                    db_score = davies_bouldin_score(non_noise_embeddings, non_noise_labels)
                    
                    cluster_graph.silhouette_score = round(sil_score, 4)
                    cluster_graph.calinski_harabasz_score = round(ch_score, 2)
                    cluster_graph.davies_bouldin_score = round(db_score, 4)
                    cluster_graph.save()
                    
                    logger.info(f"✅ Quality metrics: Silhouette={sil_score:.4f}, CH={ch_score:.2f}, DB={db_score:.4f}")
                else:
                    logger.warning("⚠️ Not enough clusters for quality metrics calculation")
            except Exception as e:
                logger.error(f"❌ Error computing quality metrics: {e}")
        
        elapsed_time = time.time() - start_time
        logger.info(f"✅ Global cluster computation completed in {elapsed_time:.2f} seconds")
        logger.info(f"📊 Graph ID: {cluster_graph.graph_id}")
        logger.info(f"📊 Documents: {cluster_graph.document_count}")
        logger.info(f"📊 Clusters: {cluster_graph.cluster_count}")
        logger.info(f"📊 Noise: {cluster_graph.noise_count}")
        
        return cluster_graph
    
    def _build_knn_graph(
        self,
        embeddings: np.ndarray,
        k: int = 5,
        min_similarity: float = 0.3
    ) -> List[Tuple[int, int, float]]:
        """
        Construye un grafo KNN sobre los embeddings.
        
        Args:
            embeddings: Array de embeddings (N x D)
            k: Número de vecinos más cercanos
            min_similarity: Umbral mínimo de similitud para crear edge
            
        Returns:
            Lista de tuplas (source_idx, target_idx, similarity)
        """
        # Calcular matriz de similitud completa
        similarity_matrix = cosine_similarity(embeddings)
        
        # Para cada documento, encontrar sus k vecinos más cercanos
        edges = []
        
        for i in range(len(embeddings)):
            # Obtener similitudes de este documento con todos los demás
            similarities = similarity_matrix[i]
            
            # Obtener índices de los k+1 vecinos más cercanos (incluyendo a sí mismo)
            # Excluir el documento mismo (índice 0 después de ordenar)
            top_k_indices = np.argsort(similarities)[::-1][1:k+1]
            
            for j in top_k_indices:
                sim = similarities[j]
                if sim >= min_similarity:
                    # Agregar edge bidireccional (evitamos duplicados después)
                    edges.append((i, int(j), sim))
        
        # Eliminar duplicados (a→b y b→a se consideran el mismo edge)
        unique_edges = set()
        for source, target, sim in edges:
            if source < target:
                unique_edges.add((source, target, sim))
            else:
                unique_edges.add((target, source, sim))
        
        return list(unique_edges)
    
    def get_cached_clusters(
        self,
        graph_id: Optional[int] = None,
        include_edges: bool = False,
        cluster_filter: Optional[List[int]] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Obtiene el grafo de clusters precomputado (API RÁPIDA).
        
        Este método NO computa nada, solo sirve los datos ya calculados.
        
        Args:
            graph_id: ID del grafo a obtener (None = grafo activo)
            include_edges: Si True incluye las aristas KNN
            cluster_filter: Lista de cluster_labels a incluir (None = todos)
            top_k: Mantener solo las top-k aristas más fuertes por nodo (default: 5)
            
        Returns:
            Diccionario con nodes, links (opcional), clusters, statistics
        """
        # Obtener grafo
        if graph_id is not None:
            cluster_graph = ClusterGraph.objects.filter(graph_id=graph_id).first()
        else:
            cluster_graph = ClusterGraph.get_active_graph()
        
        if not cluster_graph:
            return {
                'nodes': [],
                'links': [],
                'clusters': {},
                'cluster_stats': [],
                'metadata': {
                    'error': 'No cluster graph available'
                }
            }
        
        # Obtener nodos
        nodes_query = cluster_graph.nodes.all()
        
        if cluster_filter:
            nodes_query = nodes_query.filter(cluster_label__in=cluster_filter)
        
        nodes = []
        clusters = {}
        
        for node in nodes_query:
            # Crear nodo para el frontend
            node_data = {
                'id': str(node.document_id),
                'x': node.x,
                'y': node.y,
                'cluster': node.cluster_label,
                'is_noise': node.is_noise,
                'title': node.doc_title,
                'case_number': node.doc_case_number,
                'legal_area': node.doc_legal_area_name,
                'doc_type': node.doc_type_name,
                'document_date': node.doc_date.isoformat() if node.doc_date else None,
                # Color y forma se asignan en el frontend
            }
            nodes.append(node_data)
            
            # Agrupar por cluster
            label = node.cluster_label
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(str(node.document_id))
        
        # Obtener edges si se solicita
        links = []
        if include_edges:
            edges_query = cluster_graph.edges.all()
            
            # Filtrar edges para que solo conecten nodos visibles
            if cluster_filter:
                visible_node_ids = set([node.node_id for node in nodes_query])
                edges_query = edges_query.filter(
                    source_node_id__in=visible_node_ids,
                    target_node_id__in=visible_node_ids
                )
            
            # Convert to list for processing
            all_edges = list(edges_query)
            
            # Apply top-k pruning: keep only the strongest k edges per node
            if top_k > 0:
                from collections import defaultdict
                
                # Group edges by source node
                node_edges = defaultdict(list)
                for edge in all_edges:
                    source_id = str(edge.source_node.document_id)
                    target_id = str(edge.target_node.document_id)
                    
                    # Add to both source and target (undirected graph)
                    node_edges[source_id].append((edge, target_id))
                    node_edges[target_id].append((edge, source_id))
                
                # Keep only top-k edges per node
                pruned_edges = set()  # Use set to avoid duplicates
                for node_id, edges_list in node_edges.items():
                    # Sort by similarity (descending) and keep top-k
                    top_edges = sorted(edges_list, key=lambda x: x[0].similarity, reverse=True)[:top_k]
                    for edge, _ in top_edges:
                        pruned_edges.add(edge.edge_id)
                
                # Filter edges
                all_edges = [e for e in all_edges if e.edge_id in pruned_edges]
            
            # Convert to link format
            for edge in all_edges:
                link = {
                    'source': str(edge.source_node.document_id),
                    'target': str(edge.target_node.document_id),
                    'similarity': edge.similarity,
                    'type': edge.edge_type
                }
                links.append(link)
        
        # Calcular estadísticas por cluster
        cluster_stats = []
        for label, doc_ids in clusters.items():
            if label == -1:
                continue  # Skip noise
            
            # Obtener nodos de este cluster
            cluster_nodes = [n for n in nodes if n['cluster'] == label]
            
            # Contar documentos por área legal
            area_counts = {}
            for n in cluster_nodes:
                area = n.get('legal_area', 'Sin área')
                area_counts[area] = area_counts.get(area, 0) + 1
            
            # Extraer keywords del cluster
            keywords = self._extract_cluster_keywords(cluster_nodes)
            
            cluster_stats.append({
                'cluster_label': label,
                'cluster_id': label,  # Alias para compatibilidad
                'size': len(doc_ids),
                'main_area': max(area_counts.items(), key=lambda x: x[1])[0] if area_counts else 'Mixto',
                'dominant_area': max(area_counts.items(), key=lambda x: x[1])[0] if area_counts else 'Mixto',  # Alias
                'area_distribution': area_counts,
                'keywords': keywords,
                'topic_label': ', '.join([kw['word'] for kw in keywords[:3]]) if keywords else (max(area_counts.items(), key=lambda x: x[1])[0] if area_counts else 'Mixto'),
                'documents': doc_ids[:10]  # Preview de IDs
            })
        
        # Ordenar por tamaño
        cluster_stats.sort(key=lambda x: x['size'], reverse=True)
        
        # Obtener métricas de calidad almacenadas en el modelo
        quality_metrics = self._get_quality_metrics(cluster_graph)
        
        return {
            'nodes': nodes,
            'links': links,
            'clusters': clusters,
            'cluster_stats': cluster_stats,
            'quality_metrics': quality_metrics,
            'metadata': {
                'graph_id': cluster_graph.graph_id,
                'created_at': cluster_graph.created_at.isoformat(),
                'document_count': cluster_graph.document_count,
                'cluster_count': cluster_graph.cluster_count,
                'noise_count': cluster_graph.noise_count,
                'algorithm': cluster_graph.algorithm,
                'computation_time': cluster_graph.computation_time_seconds
            }
        }
    
    def _get_quality_metrics(self, cluster_graph) -> Dict[str, Any]:
        """
        Obtiene las métricas de calidad almacenadas en el modelo ClusterGraph.
        Las métricas se calculan durante compute_global_clusters() y se guardan.
        """
        # Interpretaciones
        def interpret_silhouette(score):
            if score is None:
                return {'level': 'unknown', 'message': 'Métrica no disponible'}
            if score >= 0.7:
                return {'level': 'excellent', 'message': 'Estructura de clusters muy fuerte'}
            elif score >= 0.5:
                return {'level': 'good', 'message': 'Estructura de clusters razonable'}
            elif score >= 0.25:
                return {'level': 'fair', 'message': 'Estructura débil, clusters posiblemente superpuestos'}
            else:
                return {'level': 'poor', 'message': 'No hay estructura sustancial de clusters'}
        
        def interpret_davies_bouldin(score):
            if score is None:
                return {'level': 'unknown', 'message': 'Métrica no disponible'}
            if score < 0.5:
                return {'level': 'excellent', 'message': 'Clusters muy bien separados'}
            elif score < 1.0:
                return {'level': 'good', 'message': 'Clusters razonablemente separados'}
            elif score < 2.0:
                return {'level': 'fair', 'message': 'Clusters moderadamente superpuestos'}
            else:
                return {'level': 'poor', 'message': 'Clusters muy superpuestos'}
        
        return {
            'silhouette_score': cluster_graph.silhouette_score,
            'calinski_harabasz_score': cluster_graph.calinski_harabasz_score,
            'davies_bouldin_score': cluster_graph.davies_bouldin_score,
            'error': None if cluster_graph.silhouette_score is not None else 'Metrics not computed',
            'interpretation': {
                'silhouette': interpret_silhouette(cluster_graph.silhouette_score),
                'calinski_harabasz': {
                    'level': 'info',
                    'message': 'Mayor valor indica clusters más densos y separados'
                },
                'davies_bouldin': interpret_davies_bouldin(cluster_graph.davies_bouldin_score)
            }
        }
    
    def _extract_cluster_keywords(
        self,
        cluster_nodes: List[Dict[str, Any]],
        top_n: int = 8
    ) -> List[Dict[str, Any]]:
        """
        Extrae keywords representativas de un cluster usando TF-IDF.
        
        Args:
            cluster_nodes: Lista de nodos del cluster con doc_title
            top_n: Número de keywords a retornar
            
        Returns:
            Lista de {word: str, score: float}
        """
        try:
            # Stopwords en español comunes + términos legales genéricos
            spanish_stopwords = [
                'el', 'la', 'los', 'las', 'de', 'del', 'en', 'y', 'a', 'que', 'es',
                'por', 'un', 'una', 'con', 'para', 'su', 'al', 'lo', 'como', 'más',
                'se', 'le', 'ya', 'o', 'pero', 'sus', 'este', 'ha', 'me', 'si',
                'no', 'ni', 'muy', 'sin', 'sobre', 'ser', 'tiene', 'también',
                'fue', 'había', 'todo', 'esta', 'son', 'entre', 'está', 'cuando',
                'hay', 'así', 'todos', 'nos', 'durante', 'estados', 'uno', 'dos',
                # Términos legales genéricos
                'artículo', 'articulo', 'numeral', 'código', 'codigo', 'ley',
                'expediente', 'resolución', 'resolucion', 'folio', 'folios',
                'mediante', 'conforme', 'señor', 'señora', 'doctor', 'doctora',
                'juez', 'fiscal', 'tribunal', 'juzgado', 'sala', 'corte',
            ]
            
            if not cluster_nodes:
                return []
            
            # Obtener títulos y summaries de los documentos del cluster
            doc_ids = [n.get('document_id') for n in cluster_nodes if n.get('document_id')]
            
            if not doc_ids:
                return []
            
            # Fetch documents with summaries
            documents = Document.objects.filter(document_id__in=doc_ids).values('title', 'summary')
            
            # Combinar título + summary
            texts = []
            for doc in documents:
                text_parts = []
                if doc.get('title'):
                    text_parts.append(doc['title'])
                if doc.get('summary'):
                    text_parts.append(doc['summary'])
                if text_parts:
                    texts.append(' '.join(text_parts))
            
            if not texts:
                return []
            
            # Unir todos los textos
            combined_text = ' '.join(texts)
            
            # Preprocesar
            def clean_text(text):
                text = text.lower()
                text = re.sub(r'[^\w\sáéíóúñü]', ' ', text)
                text = re.sub(r'\b\d+\b', '', text)
                text = re.sub(r'\s+', ' ', text).strip()
                return text
            
            combined_text = clean_text(combined_text)
            
            # TF-IDF con un solo documento (todo el cluster)
            vectorizer = TfidfVectorizer(
                max_features=200,
                stop_words=spanish_stopwords,
                ngram_range=(1, 2),
                token_pattern=r'\b[a-záéíóúñü]{3,}\b'
            )
            
            # Fit y transform
            tfidf_matrix = vectorizer.fit_transform([combined_text])
            feature_names = vectorizer.get_feature_names_out()
            
            # Obtener scores
            row = tfidf_matrix.toarray().flatten()
            top_indices = row.argsort()[-top_n:][::-1]
            
            keywords = []
            for i in top_indices:
                score = float(row[i])
                if score > 0:
                    keywords.append({
                        'word': feature_names[i],
                        'score': round(score, 4)
                    })
            
            return keywords
            
        except Exception as e:
            logger.error(f"Error extracting cluster keywords: {e}")
            return []
    
    def get_document_neighbors(
        self,
        document_id: str,
        graph_id: Optional[int] = None,
        max_neighbors: int = 10
    ) -> Dict[str, Any]:
        """
        Obtiene los vecinos KNN de un documento específico.
        
        Útil para el modo "Connected" del frontend:
        - Click en nodo → mostrar sus vecinos
        
        Args:
            document_id: UUID del documento
            graph_id: ID del grafo (None = grafo activo)
            max_neighbors: Máximo número de vecinos a retornar
            
        Returns:
            Diccionario con el nodo central y sus vecinos conectados
        """
        # Obtener grafo
        if graph_id is not None:
            cluster_graph = ClusterGraph.objects.filter(graph_id=graph_id).first()
        else:
            cluster_graph = ClusterGraph.get_active_graph()
        
        if not cluster_graph:
            return {
                'central_node': None,
                'neighbors': [],
                'edges': [],
                'error': 'No cluster graph available'
            }
        
        # Obtener nodo central
        try:
            central_node = cluster_graph.nodes.get(document_id=document_id)
        except ClusterGraphNode.DoesNotExist:
            return {
                'central_node': None,
                'neighbors': [],
                'edges': [],
                'error': f'Document {document_id} not found in graph'
            }
        
        # Obtener edges salientes del nodo central
        outgoing_edges = central_node.outgoing_edges.order_by('-similarity')[:max_neighbors]
        
        # Obtener edges entrantes del nodo central
        incoming_edges = central_node.incoming_edges.order_by('-similarity')[:max_neighbors]
        
        # Combinar y ordenar por similitud
        all_edges = list(outgoing_edges) + list(incoming_edges)
        all_edges.sort(key=lambda e: e.similarity, reverse=True)
        all_edges = all_edges[:max_neighbors]
        
        # Obtener nodos vecinos
        neighbor_nodes = []
        edges_data = []
        
        for edge in all_edges:
            # Determinar cuál es el vecino
            if edge.source_node == central_node:
                neighbor = edge.target_node
            else:
                neighbor = edge.source_node
            
            neighbor_data = {
                'id': str(neighbor.document_id),
                'x': neighbor.x,
                'y': neighbor.y,
                'cluster': neighbor.cluster_label,
                'title': neighbor.doc_title,
                'case_number': neighbor.doc_case_number,
                'legal_area': neighbor.doc_legal_area_name,
                'similarity': edge.similarity
            }
            neighbor_nodes.append(neighbor_data)
            
            edges_data.append({
                'source': str(central_node.document_id),
                'target': str(neighbor.document_id),
                'similarity': edge.similarity
            })
        
        central_data = {
            'id': str(central_node.document_id),
            'x': central_node.x,
            'y': central_node.y,
            'cluster': central_node.cluster_label,
            'title': central_node.doc_title,
            'case_number': central_node.doc_case_number,
            'legal_area': central_node.doc_legal_area_name
        }
        
        return {
            'central_node': central_data,
            'neighbors': neighbor_nodes,
            'edges': edges_data
        }
