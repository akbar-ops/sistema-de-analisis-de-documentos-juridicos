# """
# Servicio de clustering de documentos usando DBSCAN y otros algoritmos
# Agrupa documentos similares basándose en sus embeddings

# Versión: 2.1 - Soporte para clean_embedding (768d) + Keywords extraction via TF-IDF
# """
# import logging
# from typing import List, Dict, Any, Optional, Tuple, Literal
# import numpy as np
# from sklearn.cluster import DBSCAN, KMeans, AgglomerativeClustering
# from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances, manhattan_distances
# from sklearn.feature_extraction.text import TfidfVectorizer
# import re

# # Importar HDBSCAN si está disponible
# try:
#     import hdbscan
#     HDBSCAN_AVAILABLE = True
# except ImportError:
#     HDBSCAN_AVAILABLE = False

# # Importar UMAP si está disponible
# try:
#     import umap
#     UMAP_AVAILABLE = True
# except ImportError:
#     UMAP_AVAILABLE = False

# from apps.documents.models import Document

# logger = logging.getLogger(__name__)

# # Tipo para seleccionar el campo de embedding a usar
# EmbeddingField = Literal['clean_embedding', 'enhanced_embedding', 'summary_embedding']


# class ClusteringService:
#     """Servicio para clustering de documentos legales"""
    
#     # Embedding por defecto
#     DEFAULT_EMBEDDING_FIELD: EmbeddingField = 'clean_embedding'
    
#     def __init__(self):
#         self.default_eps = 0.242  # Distancia máxima entre documentos del mismo cluster (más permisivo)
#         self.default_min_samples = 2  # Mínimo de documentos para formar un cluster
    
#     def _get_embedding(
#         self,
#         doc: Document,
#         embedding_field: EmbeddingField = None
#     ) -> Optional[np.ndarray]:
#         """
#         Obtiene el embedding del documento con fallback automático.
        
#         Args:
#             doc: Documento del cual obtener el embedding
#             embedding_field: Campo de embedding preferido
        
#         Returns:
#             numpy array con el embedding o None
#         """
#         if embedding_field is None:
#             embedding_field = self.DEFAULT_EMBEDDING_FIELD
        
#         # Orden de preferencia para fallback
#         fields_to_try = [embedding_field]
#         if embedding_field != 'clean_embedding':
#             fields_to_try.append('clean_embedding')
#         if embedding_field != 'enhanced_embedding':
#             fields_to_try.append('enhanced_embedding')
#         if embedding_field != 'summary_embedding':
#             fields_to_try.append('summary_embedding')
        
#         for field in fields_to_try:
#             embedding = getattr(doc, field, None)
#             if embedding is not None and len(embedding) > 0:
#                 return np.array(embedding)
        
#         return None
    
#     def get_document_cluster(
#         self,
#         document_id: str,
#         max_neighbors: int = 20,
#         eps: float = 0.242,
#         min_samples: int = None,
#         embedding_field: EmbeddingField = None
#     ) -> Dict[str, Any]:
#         """
#         Obtiene el cluster del documento y sus vecinos más cercanos.
        
#         Args:
#             document_id: UUID del documento central
#             max_neighbors: Número máximo de vecinos a incluir
#             eps: Parámetro epsilon de DBSCAN (distancia máxima)
#             min_samples: Mínimo de muestras para formar cluster
#             embedding_field: Campo de embedding a usar ('clean_embedding', 'enhanced_embedding', 'summary_embedding')
            
#         Returns:
#             Diccionario con nodos, enlaces y metadatos del cluster
#         """
#         try:
#             if embedding_field is None:
#                 embedding_field = self.DEFAULT_EMBEDDING_FIELD
            
#             # Obtener documento central
#             central_doc = Document.objects.prefetch_related(
#                 'document_persons__person',
#                 'legal_area',
#                 'doc_type'
#             ).get(document_id=document_id)
            
#             central_embedding = self._get_embedding(central_doc, embedding_field)
#             if central_embedding is None:
#                 logger.warning(f"Document {document_id} has no embedding")
#                 return {
#                     'nodes': [],
#                     'links': [],
#                     'clusters': {},
#                     'error': 'Documento sin embedding'
#                 }
            
#             # Obtener documentos similares (solo procesados)
#             similar_docs = self._get_similar_documents(
#                 central_doc,
#                 max_neighbors,
#                 embedding_field=embedding_field
#             )
            
#             if not similar_docs:
#                 logger.warning(f"No similar documents found for {document_id}")
#                 return {
#                     'nodes': [self._create_node(central_doc, 0, True)],
#                     'links': [],
#                     'clusters': {0: [str(central_doc.document_id)]},
#                     'central_document_id': str(central_doc.document_id)
#                 }
            
#             # Incluir documento central
#             all_docs = [central_doc] + similar_docs
            
#             # Crear matriz de embeddings usando el campo apropiado
#             embeddings = np.array([
#                 self._get_embedding(doc, embedding_field)
#                 for doc in all_docs
#             ])
            
#             # Calcular matriz de similitud (coseno)
#             similarity_matrix = cosine_similarity(embeddings)
            
#             # Convertir similitud a distancia para DBSCAN
#             # Distancia = 1 - similitud
#             # Clip para evitar valores negativos por errores numéricos
#             distance_matrix = np.clip(1 - similarity_matrix, 0, 2)
            
#             # Asegurar simetría y valores no negativos
#             distance_matrix = np.maximum(distance_matrix, distance_matrix.T)
#             np.fill_diagonal(distance_matrix, 0)  # Distancia a sí mismo = 0
            
#             # Aplicar DBSCAN
#             eps_value = eps if eps is not None else self.default_eps
#             min_samples_value = min_samples if min_samples is not None else self.default_min_samples
            
#             clustering = DBSCAN(
#                 eps=eps_value,
#                 min_samples=min_samples_value,
#                 metric='precomputed'
#             )
            
#             cluster_labels = clustering.fit_predict(distance_matrix)
            
#             # Crear nodos
#             nodes = []
#             clusters = {}
            
#             for idx, (doc, cluster_label) in enumerate(zip(all_docs, cluster_labels)):
#                 is_central = (idx == 0)
#                 node = self._create_node(doc, int(cluster_label), is_central)
#                 nodes.append(node)
                
#                 # Agrupar por cluster
#                 if cluster_label not in clusters:
#                     clusters[cluster_label] = []
#                 clusters[cluster_label].append(str(doc.document_id))
            
#             # Crear enlaces solo entre documentos del mismo cluster con alta similitud
#             links = []
#             for i in range(len(all_docs)):
#                 for j in range(i + 1, len(all_docs)):
#                     # Solo enlazar si están en el mismo cluster (excepto -1 que es ruido)
#                     if cluster_labels[i] == cluster_labels[j] and cluster_labels[i] != -1:
#                         similarity = float(similarity_matrix[i][j])
#                         if similarity > 0.0:  # Umbral de similitud
#                             links.append({
#                                 'source': str(all_docs[i].document_id),
#                                 'target': str(all_docs[j].document_id),
#                                 'value': similarity,
#                                 'distance': 100 * (1 - similarity)  # Distancia visual
#                             })
            
#             # Convertir cluster_labels a formato serializable
#             clusters_serializable = {
#                 int(k): v for k, v in clusters.items()
#             }
            
#             # Extraer keywords por cluster
#             cluster_keywords = self._extract_cluster_keywords(
#                 all_docs,
#                 cluster_labels,
#                 clusters_serializable,
#                 top_n=8
#             )
            
#             # Calcular cluster_stats con keywords
#             cluster_stats = []
#             for label, doc_ids in clusters_serializable.items():
#                 if label == -1:
#                     continue
                    
#                 cluster_nodes = [n for n in nodes if n['cluster'] == label]
                
#                 # Contar por área
#                 areas = {}
#                 for node in cluster_nodes:
#                     area = node.get('legal_area', 'Sin área')
#                     areas[area] = areas.get(area, 0) + 1
                
#                 dominant_area = max(areas.items(), key=lambda x: x[1])[0] if areas else 'N/A'
#                 keywords = cluster_keywords.get(label, [])
                
#                 cluster_stats.append({
#                     'cluster_id': int(label),
#                     'size': len(doc_ids),
#                     'dominant_area': dominant_area,
#                     'area_distribution': areas,
#                     'keywords': keywords,
#                     'topic_label': ', '.join([kw['word'] for kw in keywords[:3]]) if keywords else dominant_area,
#                     'documents': doc_ids[:10]
#                 })
            
#             cluster_stats.sort(key=lambda x: x['size'], reverse=True)
            
#             return {
#                 'nodes': nodes,
#                 'links': links,
#                 'clusters': clusters_serializable,
#                 'cluster_stats': cluster_stats,
#                 'central_document_id': str(central_doc.document_id),
#                 'cluster_count': len([c for c in clusters_serializable.keys() if c != -1]),
#                 'noise_count': len(clusters_serializable.get(-1, []))
#             }
            
#         except Document.DoesNotExist:
#             logger.error(f"Document {document_id} not found")
#             return {
#                 'nodes': [],
#                 'links': [],
#                 'clusters': {},
#                 'error': 'Documento no encontrado'
#             }
#         except Exception as e:
#             logger.error(f"Error in get_document_cluster: {e}", exc_info=True)
#             return {
#                 'nodes': [],
#                 'links': [],
#                 'clusters': {},
#                 'error': str(e)
#             }
    
#     def _get_similar_documents(
#         self,
#         central_doc: Document,
#         max_neighbors: int,
#         embedding_field: EmbeddingField = None
#     ) -> List[Document]:
#         """
#         Obtiene documentos similares al documento central.
#         Solo incluye documentos con status='processed'.
        
#         Args:
#             central_doc: Documento de referencia
#             max_neighbors: Número máximo de vecinos
#             embedding_field: Campo de embedding a usar
#         """
#         from apps.documents.services.similarity_service import DocumentSimilarityService
        
#         if embedding_field is None:
#             embedding_field = self.DEFAULT_EMBEDDING_FIELD
        
#         try:
#             similar_results = DocumentSimilarityService.find_similar_documents(
#                 str(central_doc.document_id),
#                 top_n=max_neighbors,
#                 min_similarity=0.15,  # Umbral muy bajo para capturar más documentos
#                 exclude_self=True,
#                 use_hybrid_scoring=False,  # Solo similitud semántica
#                 embedding_field=embedding_field
#             )
            
#             # Extraer solo los documentos (primer elemento de la tupla)
#             # Filtrar solo documentos procesados
#             similar_docs = [
#                 doc for doc, score, reasons in similar_results
#                 if doc.status == 'processed'
#             ]
            
#             return similar_docs[:max_neighbors]
            
#         except Exception as e:
#             logger.error(f"Error getting similar documents: {e}")
#             return []
    
#     def _create_node(
#         self,
#         doc: Document,
#         cluster_label: int,
#         is_central: bool = False
#     ) -> Dict[str, Any]:
#         """
#         Crea un nodo para el grafo de fuerza.
        
#         Args:
#             doc: Documento
#             cluster_label: Label del cluster (-1 para ruido)
#             is_central: Si es el documento central
            
#         Returns:
#             Diccionario con datos del nodo
#         """
#         # Color por área legal / especialidad
#         area_colors = {
#             'Penal': '#D32F2F',                    # Rojo
#             'Laboral': '#1976D2',                  # Azul
#             'Familia Civil': '#E91E63',            # Rosa fuerte
#             'Civil': '#388E3C',                    # Verde
#             'Familia Tutelar': '#F06292',          # Rosa claro
#             'Comercial': '#0097A7',                # Cyan
#             'Derecho Constitucional': '#7B1FA2',   # Morado
#             'Contencioso Administrativo': '#F57C00', # Naranja
#             'Familia Penal': '#AD1457',            # Rosa oscuro
#             'Extension de Dominio': '#5E35B1',     # Violeta
#             'Otros': '#757575',                    # Gris
#             None: '#757575'                        # Gris para sin área
#         }
        
#         # Forma por tipo de documento
#         doc_shapes = {
#             'Sentencias': 'circle',
#             'Autos': 'triangle',
#             'Decretos': 'diamond',
#             'Otros': 'square',
#             None: 'circle'
#         }
        
#         area_name = doc.legal_area.name if doc.legal_area else None
#         doc_type_name = doc.doc_type.name if doc.doc_type else None
        
#         # Obtener personas principales
#         main_persons = doc.document_persons.filter(is_primary=True)[:2]
#         persons_text = ', '.join([
#             f"{dp.person.name} ({dp.get_role_display()})"
#             for dp in main_persons
#         ]) if main_persons.exists() else 'Sin personas registradas'
        
#         return {
#             'id': str(doc.document_id),
#             'label': doc.case_number or doc.title[:30] + '...',
#             'title': doc.title,
#             'summary': doc.summary or 'Sin resumen disponible',
#             'case_number': doc.case_number,
#             'resolution_number': doc.resolution_number,
#             'document_date': doc.document_date.isoformat() if doc.document_date else None,
#             'legal_area': area_name,
#             'doc_type': doc_type_name,
#             'color': area_colors.get(area_name, area_colors[None]),
#             'shape': doc_shapes.get(doc_type_name, doc_shapes[None]),
#             'cluster': cluster_label,
#             'is_central': is_central,
#             'is_noise': cluster_label == -1,
#             'persons': persons_text,
#             'val': 10 if is_central else 5  # Tamaño del nodo
#         }
    
#     def _extract_cluster_keywords(
#         self,
#         doc_list: List[Document],
#         cluster_labels: np.ndarray,
#         filtered_clusters: Dict[int, List[str]],
#         top_n: int = 8
#     ) -> Dict[int, List[Dict[str, Any]]]:
#         """
#         Extrae keywords representativas de cada cluster usando TF-IDF.
        
#         Combina título y resumen de cada documento, luego aplica TF-IDF
#         para encontrar los términos más distintivos de cada cluster.
        
#         Args:
#             doc_list: Lista de documentos
#             cluster_labels: Array con el label de cluster de cada documento
#             filtered_clusters: Diccionario de clusters filtrados {label: [doc_ids]}
#             top_n: Número de keywords por cluster
            
#         Returns:
#             Diccionario {cluster_id: [{'word': str, 'score': float}, ...]}
#         """
#         try:
#             # Stopwords en español comunes + términos legales genéricos
#             spanish_stopwords = [
#                 'el', 'la', 'los', 'las', 'de', 'del', 'en', 'y', 'a', 'que', 'es',
#                 'por', 'un', 'una', 'con', 'para', 'su', 'al', 'lo', 'como', 'más',
#                 'se', 'le', 'ya', 'o', 'pero', 'sus', 'este', 'ha', 'me', 'si',
#                 'no', 'ni', 'muy', 'sin', 'sobre', 'ser', 'tiene', 'también',
#                 'fue', 'había', 'todo', 'esta', 'son', 'entre', 'está', 'cuando',
#                 'hay', 'así', 'todos', 'nos', 'durante', 'estados', 'uno', 'dos',
#                 'fueron', 'ese', 'eso', 'ante', 'ellos', 'sido', 'parte', 'tiene',
#                 'forma', 'entonces', 'ir', 'ahora', 'puede', 'después', 'hacer',
#                 # Términos legales genéricos
#                 'artículo', 'articulo', 'numeral', 'código', 'codigo', 'ley',
#                 'expediente', 'resolución', 'resolucion', 'folio', 'folios',
#                 'mediante', 'conforme', 'señor', 'señora', 'doctor', 'doctora',
#                 'juez', 'fiscal', 'tribunal', 'juzgado', 'sala', 'corte',
#                 'demandante', 'demandado', 'acusado', 'imputado', 'parte',
#                 'proceso', 'caso', 'sentencia', 'auto', 'decreto',
#             ]
            
#             # Crear textos por cluster combinando título + resumen
#             cluster_texts = {}
#             for label in filtered_clusters.keys():
#                 if label == -1:  # Saltar ruido
#                     continue
                    
#                 texts = []
#                 for idx, (doc, doc_label) in enumerate(zip(doc_list, cluster_labels)):
#                     if doc_label == label:
#                         # Combinar título y resumen
#                         text_parts = []
#                         if doc.title:
#                             text_parts.append(doc.title)
#                         if doc.summary:
#                             text_parts.append(doc.summary)
#                         if text_parts:
#                             texts.append(' '.join(text_parts))
                
#                 if texts:
#                     # Unir todos los textos del cluster
#                     cluster_texts[label] = ' '.join(texts)
            
#             if not cluster_texts:
#                 return {}
            
#             # Preparar corpus: un documento por cluster
#             cluster_ids = list(cluster_texts.keys())
#             corpus = [cluster_texts[cid] for cid in cluster_ids]
            
#             # Preprocesar: limpiar texto
#             def clean_text(text):
#                 # Minúsculas
#                 text = text.lower()
#                 # Remover caracteres especiales excepto letras, números y espacios
#                 text = re.sub(r'[^\w\sáéíóúñü]', ' ', text)
#                 # Remover números solos
#                 text = re.sub(r'\b\d+\b', '', text)
#                 # Remover espacios múltiples
#                 text = re.sub(r'\s+', ' ', text).strip()
#                 return text
            
#             corpus = [clean_text(doc) for doc in corpus]
            
#             # TF-IDF Vectorizer
#             vectorizer = TfidfVectorizer(
#                 max_features=500,  # Limitar vocabulario
#                 min_df=1,          # Mínimo de documentos donde aparece
#                 max_df=0.95,       # Máximo porcentaje de documentos
#                 stop_words=spanish_stopwords,
#                 ngram_range=(1, 2),  # Unigramas y bigramas
#                 token_pattern=r'\b[a-záéíóúñü]{3,}\b'  # Palabras de al menos 3 caracteres
#             )
            
#             # Fit transform
#             tfidf_matrix = vectorizer.fit_transform(corpus)
#             feature_names = vectorizer.get_feature_names_out()
            
#             # Extraer top keywords por cluster
#             cluster_keywords = {}
#             for idx, cluster_id in enumerate(cluster_ids):
#                 # Obtener scores TF-IDF para este cluster
#                 row = tfidf_matrix[idx].toarray().flatten()
                
#                 # Obtener índices de los top_n scores más altos
#                 top_indices = row.argsort()[-top_n:][::-1]
                
#                 keywords = []
#                 for i in top_indices:
#                     score = float(row[i])
#                     if score > 0:  # Solo incluir si tiene score positivo
#                         keywords.append({
#                             'word': feature_names[i],
#                             'score': round(score, 4)
#                         })
                
#                 cluster_keywords[cluster_id] = keywords
            
#             return cluster_keywords
            
#         except Exception as e:
#             logger.error(f"Error extracting cluster keywords: {e}", exc_info=True)
#             return {}

#     def get_cluster_statistics(
#         self,
#         cluster_data: Dict[str, Any]
#     ) -> Dict[str, Any]:
#         """
#         Calcula estadísticas del clustering.
        
#         Args:
#             cluster_data: Resultado de get_document_cluster
            
#         Returns:
#             Diccionario con estadísticas
#         """
#         nodes = cluster_data.get('nodes', [])
#         clusters = cluster_data.get('clusters', {})
        
#         # Contar documentos por área legal
#         areas = {}
#         doc_types = {}
        
#         for node in nodes:
#             area = node.get('legal_area', 'Sin área')
#             doc_type = node.get('doc_type', 'Sin tipo')
            
#             areas[area] = areas.get(area, 0) + 1
#             doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
        
#         return {
#             'total_nodes': len(nodes),
#             'total_clusters': len([c for c in clusters.keys() if c != -1]),
#             'noise_nodes': len(clusters.get(-1, [])),
#             'areas_distribution': areas,
#             'doc_types_distribution': doc_types,
#             'avg_cluster_size': np.mean([
#                 len(docs) for label, docs in clusters.items() if label != -1
#             ]) if len([c for c in clusters.keys() if c != -1]) > 0 else 0
#         }
    
#     def get_all_clusters(
#         self,
#         algorithm: str = 'dbscan',
#         metric: str = 'cosine',
#         n_clusters: int = 5,
#         eps: float = None,
#         min_samples: int = None,
#         min_cluster_size: int = 2,
#         max_documents: int = 200,
#         embedding_field: EmbeddingField = None,
#         use_umap: bool = True,
#         umap_n_components: int = 2,
#         umap_n_neighbors: int = 15,
#         umap_min_dist: float = 0.1,
#         top_k_links: int = 3,
#         link_threshold: float = 0.3,
#     ) -> Dict[str, Any]:
#         """
#         Obtiene todos los clusters de documentos usando diferentes algoritmos.
        
#         Args:
#             algorithm: Algoritmo a usar ('dbscan', 'hdbscan', 'kmeans', 'agglomerative')
#             metric: Métrica de distancia ('cosine', 'euclidean', 'manhattan')
#             n_clusters: Número de clusters para kmeans/agglomerative
#             eps: Parámetro epsilon de DBSCAN
#             min_samples: Mínimo de muestras para formar cluster (DBSCAN/HDBSCAN)
#             min_cluster_size: Tamaño mínimo de cluster a retornar
#             max_documents: Número máximo de documentos a procesar
#             embedding_field: Campo de embedding ('clean_embedding', 'enhanced_embedding', 'summary_embedding')
#             use_umap: Si True aplica UMAP para reducción de dimensionalidad antes de clustering
#             umap_n_components: Número de dimensiones para UMAP (2 o 3 para visualización)
#             umap_n_neighbors: Balance estructura local vs global (5-50, más alto = más global)
#             umap_min_dist: Distancia mínima entre puntos (0.0-0.99, más bajo = clusters más compactos)
            
#         Returns:
#             Diccionario con nodos, enlaces, clusters y estadísticas
#         """
#         try:
#             # Usar campo por defecto si no se especifica
#             if embedding_field is None:
#                 embedding_field = self.DEFAULT_EMBEDDING_FIELD
            
#             # Obtener documentos procesados con embeddings
#             filter_kwargs = {
#                 'status': 'processed',
#                 f'{embedding_field}__isnull': False
#             }
            
#             documents = Document.objects.filter(
#                 **filter_kwargs
#             ).prefetch_related(
#                 'document_persons__person',
#                 'legal_area',
#                 'doc_type'
#             ).order_by('-created_at')[:max_documents]
            
#             if not documents.exists():
#                 return {
#                     'nodes': [],
#                     'links': [],
#                     'clusters': {},
#                     'cluster_stats': [],
#                     'total_documents': 0,
#                     'cluster_count': 0,
#                     'noise_count': 0
#                 }
            
#             doc_list = list(documents)
            
#             # Crear matriz de embeddings con fallback automático
#             embeddings_list = []
#             valid_docs = []
#             for doc in doc_list:
#                 emb = self._get_embedding(doc, embedding_field)
#                 if emb is not None:
#                     embeddings_list.append(emb)
#                     valid_docs.append(doc)
#                 else:
#                     logger.warning(f"Document {doc.document_id} has no valid embedding, skipping")
            
#             if len(embeddings_list) < 3:
#                 return {
#                     'nodes': [],
#                     'links': [],
#                     'clusters': {},
#                     'cluster_stats': [],
#                     'total_documents': len(doc_list),
#                     'cluster_count': 0,
#                     'noise_count': 0,
#                     'error': 'Not enough documents with valid embeddings'
#                 }
            
#             doc_list = valid_docs
#             embeddings_original = np.array(embeddings_list, dtype=np.float64)
            
#             logger.info(f"Original embeddings shape: {embeddings_original.shape} (embedding_field={embedding_field})")
            
#             # IMPORTANTE: Calcular similitud SIEMPRE sobre embeddings originales
#             # para obtener valores reales de similitud semántica
#             if metric == 'cosine':
#                 similarity_matrix_original = cosine_similarity(embeddings_original)
#             elif metric == 'euclidean':
#                 distance_matrix_temp = euclidean_distances(embeddings_original)
#                 similarity_matrix_original = 1 / (1 + distance_matrix_temp)
#             elif metric == 'manhattan':
#                 distance_matrix_temp = manhattan_distances(embeddings_original)
#                 similarity_matrix_original = 1 / (1 + distance_matrix_temp)
#             else:
#                 similarity_matrix_original = cosine_similarity(embeddings_original)
            
#             # Aplicar UMAP para reducción de dimensionalidad si está habilitado
#             # UMAP solo se usa para VISUALIZACIÓN, no para clustering
#             if use_umap and UMAP_AVAILABLE and len(doc_list) > umap_n_neighbors:
#                 logger.info(f"Applying UMAP dimensionality reduction: {embeddings_original.shape[1]}D -> {umap_n_components}D")
                
#                 # Configurar UMAP
#                 reducer = umap.UMAP(
#                     n_components=umap_n_components,  # 2D o 3D para visualización
#                     n_neighbors=umap_n_neighbors,    # Balance local/global
#                     min_dist=umap_min_dist,          # Compactación de clusters
#                     metric=metric,                    # Usar la misma métrica
#                     random_state=42,
#                     n_jobs=-1  # Usar todos los cores
#                 )
                
#                 # Reducir dimensionalidad
#                 embeddings_reduced = reducer.fit_transform(embeddings_original)
#                 logger.info(f"UMAP reduced embeddings shape: {embeddings_reduced.shape}")
                
#                 # Para la visualización, guardar las coordenadas UMAP
#                 umap_coords = embeddings_reduced.copy()
                
#                 # Para clustering, usar embeddings UMAP reducidos
#                 embeddings = embeddings_reduced
#             else:
#                 if use_umap and not UMAP_AVAILABLE:
#                     logger.warning("UMAP requested but not available, using original embeddings")
#                 elif use_umap and len(doc_list) <= umap_n_neighbors:
#                     logger.warning(f"Not enough documents ({len(doc_list)}) for UMAP with n_neighbors={umap_n_neighbors}, using original embeddings")
                
#                 embeddings = embeddings_original
#                 umap_coords = None
            
#             # Calcular matriz de distancia para clustering (puede ser sobre UMAP o original)
#             if metric == 'cosine':
#                 similarity_matrix = cosine_similarity(embeddings)
#                 distance_matrix = np.clip(1 - similarity_matrix, 0, 2)
#             elif metric == 'euclidean':
#                 distance_matrix = euclidean_distances(embeddings)
#                 similarity_matrix = 1 / (1 + distance_matrix)
#             elif metric == 'manhattan':
#                 distance_matrix = manhattan_distances(embeddings)
#                 similarity_matrix = 1 / (1 + distance_matrix)
#             else:
#                 # Default a coseno
#                 similarity_matrix = cosine_similarity(embeddings)
#                 distance_matrix = np.clip(1 - similarity_matrix, 0, 2)
            
#             # Asegurar que la matriz sea simétrica y float64 para HDBSCAN
#             distance_matrix = np.maximum(distance_matrix, distance_matrix.T)
#             np.fill_diagonal(distance_matrix, 0)
#             distance_matrix = distance_matrix.astype(np.float64)
            
#             # Inicializar variables de parámetros para el return
#             eps_value = eps if eps is not None else self.default_eps
#             min_samples_value = min_samples if min_samples is not None else self.default_min_samples
            
#             # Aplicar algoritmo de clustering seleccionado
#             if algorithm == 'dbscan':
#                 clustering = DBSCAN(
#                     eps=eps_value,
#                     min_samples=min_samples_value,
#                     metric='precomputed'
#                 )
#                 cluster_labels = clustering.fit_predict(distance_matrix)
                
#             elif algorithm == 'hdbscan':
#                 # HDBSCAN - Hierarchical DBSCAN
#                 if not HDBSCAN_AVAILABLE:
#                     logger.warning("HDBSCAN not available, falling back to DBSCAN")
#                     clustering = DBSCAN(
#                         eps=eps_value,
#                         min_samples=min_samples_value,
#                         metric='precomputed'
#                     )
#                     cluster_labels = clustering.fit_predict(distance_matrix)
#                 else:
#                     # HDBSCAN con métrica precomputada
#                     clustering = hdbscan.HDBSCAN(
#                         min_cluster_size=max(2, min_samples_value),
#                         min_samples=min_samples_value,
#                         metric='precomputed',
#                         cluster_selection_method='eom'
#                     )
#                     cluster_labels = clustering.fit_predict(distance_matrix)
                
#             elif algorithm == 'kmeans':
#                 # K-Means necesita los embeddings originales, no la matriz de distancia
#                 clustering = KMeans(
#                     n_clusters=min(n_clusters, len(doc_list)),
#                     random_state=42,
#                     n_init=10
#                 )
#                 cluster_labels = clustering.fit_predict(embeddings)
                
#             elif algorithm == 'agglomerative':
#                 clustering = AgglomerativeClustering(
#                     n_clusters=min(n_clusters, len(doc_list)),
#                     metric='precomputed',
#                     linkage='average'
#                 )
#                 cluster_labels = clustering.fit_predict(distance_matrix)
                
#             else:
#                 # Default a DBSCAN
#                 clustering = DBSCAN(
#                     eps=eps_value,
#                     min_samples=min_samples_value,
#                     metric='precomputed'
#                 )
#                 cluster_labels = clustering.fit_predict(distance_matrix)
            
#             # Crear nodos y agrupar por cluster
#             nodes = []
#             clusters = {}
            
#             for idx, (doc, cluster_label) in enumerate(zip(doc_list, cluster_labels)):
#                 node = self._create_node(doc, int(cluster_label), is_central=False)
                
#                 # Si tenemos coordenadas UMAP, agregarlas para mejor visualización
#                 if umap_coords is not None:
#                     node['x'] = float(umap_coords[idx, 0])
#                     node['y'] = float(umap_coords[idx, 1])
#                     if umap_n_components == 3:
#                         node['z'] = float(umap_coords[idx, 2])
                
#                 nodes.append(node)
                
#                 if cluster_label not in clusters:
#                     clusters[cluster_label] = []
#                 clusters[cluster_label].append(str(doc.document_id))
            
#             # Filtrar clusters por tamaño mínimo
#             # Nota: DBSCAN usa -1 para ruido, otros algoritmos no
#             has_noise = -1 in clusters
#             filtered_clusters = {
#                 label: docs for label, docs in clusters.items()
#                 if (label == -1 and has_noise) or (label != -1 and len(docs) >= min_cluster_size)
#             }
            
#             # Crear enlaces controlados por top-k para reducir el ruido visual
#             # Se construyen links solo entre los vecinos más cercanos dentro del mismo cluster
#             # IMPORTANTE: Usar similarity_matrix_original para valores reales de similitud
#             links = []
#             added_pairs = set()

#             for i in range(len(doc_list)):
#                 cluster_i = cluster_labels[i]
#                 # Saltar ruido si aplica
#                 if has_noise and cluster_i == -1:
#                     continue
#                 if cluster_i not in filtered_clusters:
#                     continue

#                 # Recolectar vecinos dentro del mismo cluster que superen el umbral
#                 neighbors = []
#                 for j in range(len(doc_list)):
#                     if i == j:
#                         continue
#                     cluster_j = cluster_labels[j]
#                     if cluster_j != cluster_i:
#                         continue
#                     if has_noise and cluster_j == -1:
#                         continue

#                     # Usar similitud de embeddings ORIGINALES para valores reales
#                     similarity = float(similarity_matrix_original[i][j])
#                     if similarity >= link_threshold:
#                         neighbors.append((j, similarity))

#                 # Ordenar por similitud descendente y tomar top-k
#                 neighbors.sort(key=lambda x: x[1], reverse=True)
#                 for neighbor_idx, sim in neighbors[:max(0, min(top_k_links, len(neighbors)))]:
#                     a, b = sorted((i, neighbor_idx))
#                     if (a, b) in added_pairs:
#                         continue
#                     added_pairs.add((a, b))
#                     links.append({
#                         'source': str(doc_list[a].document_id),
#                         'target': str(doc_list[b].document_id),
#                         'value': float(sim),
#                         'distance': 100 * (1 - float(sim)),
#                         'cluster': int(cluster_i)
#                     })
            
#             # Filtrar nodos
#             filtered_nodes = [
#                 node for node in nodes
#                 if node['cluster'] in filtered_clusters
#             ]
            
#             # Extraer keywords por cluster usando TF-IDF
#             cluster_keywords = self._extract_cluster_keywords(
#                 doc_list,
#                 cluster_labels,
#                 filtered_clusters,
#                 top_n=8
#             )
            
#             # Calcular estadísticas por cluster
#             cluster_stats = []
#             for label, doc_ids in filtered_clusters.items():
#                 if label == -1:
#                     continue
                    
#                 cluster_nodes = [n for n in filtered_nodes if n['cluster'] == label]
                
#                 # Contar por área
#                 areas = {}
#                 for node in cluster_nodes:
#                     area = node.get('legal_area', 'Sin área')
#                     areas[area] = areas.get(area, 0) + 1
                
#                 dominant_area = max(areas.items(), key=lambda x: x[1])[0] if areas else 'N/A'
                
#                 # Obtener keywords para este cluster
#                 keywords = cluster_keywords.get(label, [])
                
#                 cluster_stats.append({
#                     'cluster_id': int(label),
#                     'size': len(doc_ids),
#                     'dominant_area': dominant_area,
#                     'area_distribution': areas,
#                     'keywords': keywords,  # Añadir keywords TF-IDF
#                     'topic_label': ', '.join([kw['word'] for kw in keywords[:3]]) if keywords else dominant_area,  # Etiqueta corta
#                     'documents': doc_ids[:10]  # Solo primeros 10 para preview
#                 })
            
#             # Ordenar por tamaño
#             cluster_stats.sort(key=lambda x: x['size'], reverse=True)
            
#             # Construir parámetros del response según el algoritmo
#             response_params = {
#                 'algorithm': algorithm,
#                 'metric': metric,
#                 'min_cluster_size': min_cluster_size
#             }
            
#             if algorithm in ['dbscan', 'hdbscan']:
#                 if algorithm == 'dbscan':
#                     response_params['eps'] = eps_value
#                 response_params['min_samples'] = min_samples_value
#             else:
#                 response_params['n_clusters'] = n_clusters
            
#             return {
#                 'nodes': filtered_nodes,
#                 'links': links,
#                 'clusters': {int(k): v for k, v in filtered_clusters.items()},
#                 'cluster_stats': cluster_stats,
#                 'total_documents': len(doc_list),
#                 'cluster_count': len([c for c in filtered_clusters.keys() if c != -1]),
#                 'noise_count': len(filtered_clusters.get(-1, [])),
#                 'parameters': response_params
#             }
            
#         except Exception as e:
#             logger.error(f"Error in get_all_clusters: {e}", exc_info=True)
#             return {
#                 'nodes': [],
#                 'links': [],
#                 'clusters': {},
#                 'cluster_stats': [],
#                 'error': str(e)
#             }
