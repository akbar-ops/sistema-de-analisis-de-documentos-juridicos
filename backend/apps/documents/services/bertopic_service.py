"""
Servicio de Topic Modeling con BERTopic
=======================================

BERTopic es una técnica de topic modeling que:
1. Usa embeddings de documentos (BERT/Sentence-Transformers)
2. Reduce dimensionalidad con UMAP
3. Agrupa con HDBSCAN
4. Extrae representaciones de tópicos con c-TF-IDF
5. Genera keywords representativos por tópico

Ventajas sobre clustering simple:
- Keywords interpretables por tópico
- Representación jerárquica de tópicos
- Visualizaciones ricas (barchart, heatmap, hierarchy)
- Probabilidades de pertenencia a tópico
- Tópicos dinámicos (evolución temporal)

Arquitectura:
1. compute_topics() - Batch job que computa tópicos
2. get_cached_topics() - API que sirve tópicos precomputados
"""

import logging
import numpy as np
import time
from typing import List, Dict, Any, Optional, Tuple
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# Verificar disponibilidad de BERTopic
try:
    from bertopic import BERTopic
    from bertopic.representation import KeyBERTInspired, MaximalMarginalRelevance
    BERTOPIC_AVAILABLE = True
except ImportError:
    BERTOPIC_AVAILABLE = False
    logger.warning("⚠️ BERTopic not available. Install with: pip install bertopic")

# Verificar UMAP
try:
    import umap
    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False

# Verificar HDBSCAN
try:
    import hdbscan
    HDBSCAN_AVAILABLE = True
except ImportError:
    HDBSCAN_AVAILABLE = False

# Verificar sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# Verificar sklearn
try:
    from sklearn.feature_extraction.text import CountVectorizer
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from apps.documents.models import (
    Document,
    BERTopicModel,
    BERTopicTopic,
    BERTopicDocument
)


class BERTopicService:
    """
    Servicio para topic modeling con BERTopic.
    
    Flujo:
    1. Cargar documentos con embeddings (clean_embedding 768D)
    2. Configurar BERTopic con UMAP + HDBSCAN + c-TF-IDF
    3. Fit del modelo sobre embeddings
    4. Extraer tópicos, keywords, probabilidades
    5. Guardar en base de datos
    6. Servir desde caché para el frontend
    """
    
    def __init__(self, require_bertopic: bool = False):
        """
        Inicializa el servicio de BERTopic.
        
        Args:
            require_bertopic: Si True, lanza excepción si BERTopic no está disponible.
                             Si False, permite servir datos cacheados sin BERTopic.
        """
        self._bertopic_available = BERTOPIC_AVAILABLE
        
        if require_bertopic and not BERTOPIC_AVAILABLE:
            raise ImportError(
                "BERTopic is required for this operation. Install with: pip install bertopic"
            )
        
        # Parámetros por defecto para UMAP
        self.umap_params = {
            'n_components': 5,  # BERTopic recomienda 5 para clustering
            'n_neighbors': 15,
            'min_dist': 0.0,
            'metric': 'cosine',
            'random_state': 42
        }
        
        # Parámetros por defecto para HDBSCAN
        self.hdbscan_params = {
            'min_cluster_size': 5,
            'min_samples': 3,
            'metric': 'euclidean',
            'cluster_selection_method': 'eom',
            'prediction_data': True
        }
        
        # Parámetros para vectorización de texto (c-TF-IDF)
        self.vectorizer_params = {
            'stop_words': self._get_spanish_stopwords(),
            'ngram_range': (1, 2),  # Unigrams y bigrams
            'min_df': 2,
            'max_df': 0.95
        }
        
        # Parámetros para representación de tópicos
        self.representation_params = {
            'top_n_words': 10,  # Keywords por tópico
            'diversity': 0.3    # Diversidad de keywords (MMR)
        }
    
    def _get_spanish_stopwords(self) -> List[str]:
        """Obtener stopwords en español para mejor extracción de keywords."""
        # Stopwords básicas en español
        stopwords = [
            'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
            'de', 'del', 'al', 'a', 'ante', 'bajo', 'con', 'contra',
            'desde', 'en', 'entre', 'hacia', 'hasta', 'para', 'por',
            'según', 'sin', 'sobre', 'tras', 'durante', 'mediante',
            'que', 'cual', 'cuyo', 'cuya', 'cuyos', 'cuyas',
            'quien', 'quienes', 'donde', 'cuando', 'como', 'cuanto',
            'este', 'esta', 'estos', 'estas', 'ese', 'esa', 'esos', 'esas',
            'aquel', 'aquella', 'aquellos', 'aquellas',
            'yo', 'tú', 'él', 'ella', 'nosotros', 'vosotros', 'ellos', 'ellas',
            'me', 'te', 'se', 'nos', 'os', 'le', 'les', 'lo', 'la', 'los', 'las',
            'mi', 'tu', 'su', 'nuestro', 'vuestro', 'suyo',
            'ser', 'estar', 'haber', 'tener', 'hacer', 'poder', 'deber',
            'es', 'son', 'está', 'están', 'fue', 'fueron', 'ha', 'han', 'había',
            'y', 'o', 'pero', 'sino', 'ni', 'que', 'si', 'porque', 'aunque',
            'más', 'menos', 'muy', 'mucho', 'poco', 'tanto', 'tan',
            'no', 'sí', 'también', 'además', 'solo', 'ya', 'aún', 'todavía',
            'así', 'entonces', 'luego', 'después', 'antes', 'ahora',
            # Términos legales genéricos
            'artículo', 'artículos', 'inciso', 'numeral', 'párrafo',
            'folio', 'folios', 'página', 'páginas', 'documento', 'documentos',
            'presente', 'señor', 'señora', 'señores', 'señoras',
            'dicho', 'dicha', 'dichos', 'dichas', 'mismo', 'misma', 'mismos', 'mismas',
        ]
        return stopwords
    
    def compute_topics(
        self,
        max_documents: int = 1000,
        min_topic_size: int = 5,
        nr_topics: Optional[int] = None,  # None = auto
        embedding_field: str = 'clean_embedding',
        calculate_probabilities: bool = True,
        umap_params: Optional[Dict] = None,
        hdbscan_params: Optional[Dict] = None
    ) -> 'BERTopicModel':
        """
        Computa tópicos con BERTopic (BATCH JOB).
        
        Requires BERTopic to be installed.
        
        Args:
            max_documents: Máximo de documentos a procesar
            min_topic_size: Tamaño mínimo de tópico (min_cluster_size)
            nr_topics: Número de tópicos deseado (None = automático)
            embedding_field: Campo de embedding a usar
            calculate_probabilities: Calcular probabilidades por documento
            umap_params: Parámetros personalizados para UMAP
            hdbscan_params: Parámetros personalizados para HDBSCAN
            
        Returns:
            BERTopicModel creado
            
        Raises:
            ImportError: Si BERTopic no está instalado
        """
        # Verificar que BERTopic esté disponible
        if not self._bertopic_available:
            raise ImportError(
                "BERTopic is required to compute topics. Install with: pip install bertopic"
            )
        
        start_time = time.time()
        logger.info("🚀 Starting BERTopic computation...")
        
        # Merge parámetros con defaults
        umap_config = {**self.umap_params, **(umap_params or {})}
        hdbscan_config = {**self.hdbscan_params, **(hdbscan_params or {})}
        hdbscan_config['min_cluster_size'] = min_topic_size
        
        # 1. Cargar documentos con embeddings
        logger.info(f"📊 Loading documents with {embedding_field}...")
        documents = Document.objects.filter(
            status='processed',
            **{f'{embedding_field}__isnull': False}
        ).prefetch_related(
            'legal_area',
            'doc_type'
        ).order_by('-created_at')[:max_documents]
        
        if not documents.exists():
            raise ValueError(f"No documents found with {embedding_field}")
        
        doc_list = list(documents)
        logger.info(f"✅ Loaded {len(doc_list)} documents")
        
        # 2. Extraer embeddings y textos
        embeddings = np.array([
            np.array(getattr(doc, embedding_field))
            for doc in doc_list
        ], dtype=np.float64)
        
        # Para BERTopic necesitamos el texto para c-TF-IDF
        # Usamos título + contenido truncado
        texts = []
        for doc in doc_list:
            text = f"{doc.title or ''} {(doc.content or '')[:2000]}"
            texts.append(text.strip())
        
        logger.info(f"📐 Embeddings shape: {embeddings.shape}")
        
        # 3. Configurar componentes de BERTopic
        logger.info("⚙️ Configuring BERTopic components...")
        
        # UMAP para reducción de dimensionalidad
        umap_model = umap.UMAP(**umap_config)
        
        # HDBSCAN para clustering
        hdbscan_model = hdbscan.HDBSCAN(**hdbscan_config)
        
        # Vectorizador para c-TF-IDF
        vectorizer_model = CountVectorizer(**self.vectorizer_params)
        
        # Cargar el modelo de embeddings para KeyBERTInspired
        # Usamos el mismo modelo que genera clean_embedding
        logger.info("📦 Loading embedding model for representation...")
        embedding_model = SentenceTransformer(
            'sentence-transformers/paraphrase-multilingual-mpnet-base-v2'
        )
        
        # Modelos de representación para mejores keywords
        # KeyBERTInspired requiere el embedding model
        representation_models = [
            KeyBERTInspired(top_n_words=self.representation_params['top_n_words']),
            MaximalMarginalRelevance(diversity=self.representation_params['diversity'])
        ]
        
        # 4. Crear modelo BERTopic
        logger.info("🎯 Creating BERTopic model...")
        topic_model = BERTopic(
            embedding_model=embedding_model,  # Necesario para KeyBERTInspired
            umap_model=umap_model,
            hdbscan_model=hdbscan_model,
            vectorizer_model=vectorizer_model,
            representation_model=representation_models,
            nr_topics=nr_topics,  # None = auto
            calculate_probabilities=calculate_probabilities,
            verbose=True
        )
        
        # 5. Fit del modelo
        logger.info("🔄 Fitting BERTopic model...")
        topics, probs = topic_model.fit_transform(texts, embeddings)
        
        # 6. Obtener información de tópicos
        topic_info = topic_model.get_topic_info()
        logger.info(f"✅ Found {len(topic_info) - 1} topics (excluding outliers)")
        
        # 7. Reducir embeddings a 2D para visualización
        logger.info("🔄 Reducing to 2D for visualization...")
        umap_2d = umap.UMAP(
            n_components=2,
            n_neighbors=15,
            min_dist=0.1,
            metric='cosine',
            random_state=42
        )
        embeddings_2d = umap_2d.fit_transform(embeddings)
        
        # 8. Guardar en base de datos
        logger.info("💾 Saving BERTopic model to database...")
        bertopic_model = self._save_to_database(
            doc_list=doc_list,
            texts=texts,
            topics=topics,
            probs=probs if calculate_probabilities else None,
            topic_model=topic_model,
            topic_info=topic_info,
            embeddings_2d=embeddings_2d,
            computation_time=time.time() - start_time,
            params={
                'max_documents': max_documents,
                'min_topic_size': min_topic_size,
                'nr_topics': nr_topics,
                'embedding_field': embedding_field,
                'umap_params': umap_config,
                'hdbscan_params': hdbscan_config
            }
        )
        
        logger.info("=" * 60)
        logger.info("✅ BERTopic computation completed!")
        logger.info(f"   Model ID: {bertopic_model.model_id}")
        logger.info(f"   Documents: {bertopic_model.document_count}")
        logger.info(f"   Topics: {bertopic_model.topic_count}")
        logger.info(f"   Outliers: {bertopic_model.outlier_count}")
        logger.info(f"   Time: {bertopic_model.computation_time:.2f}s")
        logger.info("=" * 60)
        
        return bertopic_model
    
    def _save_to_database(
        self,
        doc_list: List[Document],
        texts: List[str],
        topics: List[int],
        probs: Optional[np.ndarray],
        topic_model: 'BERTopic',
        topic_info,
        embeddings_2d: np.ndarray,
        computation_time: float,
        params: Dict
    ) -> 'BERTopicModel':
        """Guardar modelo BERTopic en la base de datos."""
        
        with transaction.atomic():
            # Contar tópicos (excluyendo -1 outliers)
            unique_topics = set(topics)
            topic_count = len([t for t in unique_topics if t != -1])
            outlier_count = sum(1 for t in topics if t == -1)
            
            # Crear modelo principal
            bertopic_model = BERTopicModel.objects.create(
                document_count=len(doc_list),
                topic_count=topic_count,
                outlier_count=outlier_count,
                computation_time=computation_time,
                parameters=params,
                is_active=False
            )
            
            # Crear tópicos
            topic_objects = {}
            for _, row in topic_info.iterrows():
                topic_id = row['Topic']
                
                # Obtener keywords del tópico
                topic_words = topic_model.get_topic(topic_id)
                if topic_words:
                    keywords = [word for word, _ in topic_words[:10]]
                    keyword_weights = {word: float(weight) for word, weight in topic_words[:10]}
                else:
                    keywords = []
                    keyword_weights = {}
                
                # Generar label representativo
                if topic_id == -1:
                    label = "Outliers (sin tópico)"
                elif keywords:
                    label = ", ".join(keywords[:3])
                else:
                    label = f"Tópico {topic_id}"
                
                topic_obj = BERTopicTopic.objects.create(
                    model=bertopic_model,
                    topic_id=topic_id,
                    label=label,
                    keywords=keywords,
                    keyword_weights=keyword_weights,
                    document_count=int(row['Count']),
                    is_outlier=(topic_id == -1)
                )
                topic_objects[topic_id] = topic_obj
            
            # Crear documentos con sus tópicos
            doc_records = []
            for i, (doc, topic_id) in enumerate(zip(doc_list, topics)):
                prob = float(probs[i].max()) if probs is not None else None
                
                doc_records.append(BERTopicDocument(
                    model=bertopic_model,
                    document=doc,
                    topic=topic_objects.get(topic_id),
                    topic_id_raw=topic_id,
                    probability=prob,
                    x=float(embeddings_2d[i, 0]),
                    y=float(embeddings_2d[i, 1])
                ))
            
            BERTopicDocument.objects.bulk_create(doc_records)
            
            # Activar este modelo y desactivar los anteriores
            BERTopicModel.objects.exclude(model_id=bertopic_model.model_id).update(is_active=False)
            bertopic_model.is_active = True
            bertopic_model.save(update_fields=['is_active'])
            
            return bertopic_model
    
    def get_cached_topics(
        self,
        model_id: Optional[int] = None,
        include_outliers: bool = True,
        topic_filter: Optional[List[int]] = None,
        include_edges: bool = False,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Obtener tópicos precomputados para el frontend.
        
        Args:
            model_id: ID del modelo (None = modelo activo)
            include_outliers: Incluir documentos sin tópico
            topic_filter: Lista de topic_ids a incluir
            include_edges: Si True, calcular y devolver edges KNN entre documentos
            top_k: Número de edges KNN más fuertes a mantener por nodo
            
        Returns:
            Dict con nodes, topics, links (opcional), metadata
        """
        # Obtener modelo
        if model_id:
            model = BERTopicModel.objects.get(model_id=model_id)
        else:
            model = BERTopicModel.objects.filter(is_active=True).first()
        
        if not model:
            return {
                'error': 'No BERTopic model available',
                'nodes': [],
                'topics': [],
                'links': [],
                'topic_stats': [],
                'metadata': None
            }
        
        # Obtener tópicos
        topics_qs = BERTopicTopic.objects.filter(model=model)
        if topic_filter:
            topics_qs = topics_qs.filter(topic_id__in=topic_filter)
        if not include_outliers:
            topics_qs = topics_qs.exclude(is_outlier=True)
        
        topics_data = []
        topic_stats = []
        for topic in topics_qs.order_by('topic_id'):
            topic_dict = {
                'topic_id': topic.topic_id,
                'label': topic.label,
                'keywords': topic.keywords,
                'keyword_weights': topic.keyword_weights,
                'document_count': topic.document_count,
                'is_outlier': topic.is_outlier
            }
            topics_data.append(topic_dict)
            
            # Crear topic_stats con formato compatible con cluster_stats
            if not topic.is_outlier:
                topic_stats.append({
                    'cluster_id': topic.topic_id,  # Alias for compatibility
                    'cluster_label': topic.topic_id,
                    'topic_id': topic.topic_id,
                    'label': topic.label,
                    'topic_label': topic.label,
                    'size': topic.document_count,
                    'document_count': topic.document_count,
                    'keywords': topic.keywords,
                    'keyword_weights': topic.keyword_weights,
                    'is_outlier': False
                })
        
        # Obtener documentos
        docs_qs = BERTopicDocument.objects.filter(
            model=model
        ).select_related('document', 'topic', 'document__legal_area', 'document__doc_type')
        
        if topic_filter:
            docs_qs = docs_qs.filter(topic_id_raw__in=topic_filter)
        if not include_outliers:
            docs_qs = docs_qs.exclude(topic_id_raw=-1)
        
        nodes_data = []
        doc_ids_for_edges = []  # Para calcular edges si se solicita
        
        for doc in docs_qs:
            node = {
                'id': str(doc.document.document_id),
                'x': doc.x,
                'y': doc.y,
                # BERTopic fields
                'topic_id': doc.topic_id_raw,
                'topic_label': doc.topic.label if doc.topic else None,
                'probability': doc.probability,
                'is_outlier': doc.topic_id_raw == -1,
                # Cluster compatibility fields
                'cluster': doc.topic_id_raw,  # Alias para compatibilidad con cluster view
                'is_noise': doc.topic_id_raw == -1,
                # Document fields
                'title': doc.document.title,
                'case_number': doc.document.case_number,
                'legal_area': doc.document.legal_area.name if doc.document.legal_area else None,
                'doc_type': doc.document.doc_type.name if doc.document.doc_type else None,
                'document_date': doc.document.document_date.isoformat() if doc.document.document_date else None
            }
            nodes_data.append(node)
            doc_ids_for_edges.append(str(doc.document.document_id))
        
        # Calcular edges KNN si se solicita
        links_data = []
        if include_edges and len(nodes_data) > 1:
            links_data = self._compute_knn_edges(doc_ids_for_edges, top_k=top_k)
        
        # Metadata
        metadata = {
            'model_id': model.model_id,
            'created_at': model.created_at.isoformat(),
            'document_count': model.document_count,
            'topic_count': model.topic_count,
            'cluster_count': model.topic_count,  # Alias para compatibilidad
            'outlier_count': model.outlier_count,
            'noise_count': model.outlier_count,  # Alias para compatibilidad
            'computation_time': model.computation_time,
            'algorithm': 'bertopic',
            'parameters': model.parameters
        }
        
        return {
            'nodes': nodes_data,
            'topics': topics_data,
            'topic_stats': topic_stats,  # Formato compatible con cluster_stats
            'cluster_stats': topic_stats,  # Alias para compatibilidad
            'links': links_data,
            'metadata': metadata
        }
    
    def _compute_knn_edges(
        self,
        doc_ids: List[str],
        top_k: int = 5,
        min_similarity: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Calcular edges KNN entre documentos usando clean_embedding.
        
        Args:
            doc_ids: Lista de document_ids a incluir
            top_k: Número de vecinos más cercanos por documento
            min_similarity: Similitud mínima para incluir edge
            
        Returns:
            Lista de edges con source, target, similarity
        """
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        
        try:
            # Obtener documentos con embeddings
            documents = Document.objects.filter(
                document_id__in=doc_ids,
                clean_embedding__isnull=False
            )
            
            if documents.count() < 2:
                return []
            
            # Crear mapeo id -> index y extraer embeddings
            id_to_idx = {}
            idx_to_id = {}
            embeddings_list = []
            
            for idx, doc in enumerate(documents):
                doc_id = str(doc.document_id)
                id_to_idx[doc_id] = idx
                idx_to_id[idx] = doc_id
                embeddings_list.append(np.array(doc.clean_embedding))
            
            if len(embeddings_list) < 2:
                return []
            
            embeddings = np.array(embeddings_list, dtype=np.float64)
            
            # Calcular similitud coseno
            similarity_matrix = cosine_similarity(embeddings)
            
            # Extraer top-k edges por cada nodo
            edges = []
            seen_pairs = set()  # Evitar duplicados
            
            n_docs = len(embeddings)
            actual_k = min(top_k, n_docs - 1)
            
            for i in range(n_docs):
                # Obtener similitudes ordenadas (excluyendo self)
                similarities = similarity_matrix[i].copy()
                similarities[i] = -1  # Excluir self
                
                # Top-k índices
                top_indices = np.argsort(similarities)[-actual_k:][::-1]
                
                for j in top_indices:
                    if similarities[j] < min_similarity:
                        continue
                    
                    # Crear par ordenado para evitar duplicados
                    pair = tuple(sorted([i, j]))
                    if pair in seen_pairs:
                        continue
                    seen_pairs.add(pair)
                    
                    edges.append({
                        'source': idx_to_id[i],
                        'target': idx_to_id[j],
                        'similarity': float(similarities[j]),
                        'type': 'knn'
                    })
            
            logger.info(f"✅ Computed {len(edges)} KNN edges for {n_docs} documents")
            return edges
            
        except Exception as e:
            logger.error(f"Error computing KNN edges: {e}")
            return []
    
    def get_topic_hierarchy(self, model_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Obtener jerarquía de tópicos (para visualización de árbol).
        
        Returns:
            Dict con estructura jerárquica de tópicos
        """
        # Obtener modelo
        if model_id:
            model = BERTopicModel.objects.get(model_id=model_id)
        else:
            model = BERTopicModel.objects.filter(is_active=True).first()
        
        if not model:
            return {'error': 'No BERTopic model available'}
        
        # Obtener tópicos ordenados por tamaño
        topics = BERTopicTopic.objects.filter(
            model=model,
            is_outlier=False
        ).order_by('-document_count')
        
        hierarchy = {
            'name': 'All Topics',
            'children': []
        }
        
        for topic in topics:
            hierarchy['children'].append({
                'name': topic.label,
                'topic_id': topic.topic_id,
                'value': topic.document_count,
                'keywords': topic.keywords[:5]
            })
        
        return hierarchy
    
    def get_topic_similarity_matrix(self, model_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Calcular matriz de similitud entre tópicos basada en keywords.
        
        Returns:
            Dict con matriz de similitud y labels
        """
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        
        # Obtener modelo
        if model_id:
            model = BERTopicModel.objects.get(model_id=model_id)
        else:
            model = BERTopicModel.objects.filter(is_active=True).first()
        
        if not model:
            return {'error': 'No BERTopic model available'}
        
        # Obtener tópicos (sin outliers)
        topics = list(BERTopicTopic.objects.filter(
            model=model,
            is_outlier=False
        ).order_by('topic_id'))
        
        if len(topics) < 2:
            return {'error': 'Not enough topics for similarity matrix'}
        
        # Crear textos de keywords por tópico
        topic_texts = [' '.join(t.keywords) for t in topics]
        
        # Calcular TF-IDF y similitud
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(topic_texts)
        similarity_matrix = cosine_similarity(tfidf_matrix)
        
        return {
            'matrix': similarity_matrix.tolist(),
            'labels': [t.label for t in topics],
            'topic_ids': [t.topic_id for t in topics]
        }
