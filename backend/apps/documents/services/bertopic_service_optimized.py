"""
Servicio de Topic Modeling con BERTopic - OPTIMIZADO
====================================================

OPTIMIZACIONES APLICADAS para igualar el rendimiento de HDBSCAN:

1. ✅ UMAP intermedio aumentado de 5D a 15D (más información preservada)
2. ✅ min_cluster_size reducido de 5 a 4 (igual que HDBSCAN optimizado)
3. ✅ min_samples reducido de 3 a 2 (igual que HDBSCAN optimizado)
4. ✅ UMAP 2D optimizado para mejor separación visual
5. ✅ Vectorizador mejorado con trigramas y filtros más estrictos
6. ✅ Soporte para enhanced_embedding (384D) para comparación directa
7. ✅ Múltiples modelos de representación para keywords más diversos
8. ✅ Métricas de calidad de clustering

Basado en análisis comparativo con clustering_service_new.py
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
    from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from apps.documents.models import (
    Document,
    BERTopicModel,
    BERTopicTopic,
    BERTopicDocument
)


class BERTopicServiceOptimized:
    """
    Servicio OPTIMIZADO para topic modeling con BERTopic.
    
    Mejoras clave sobre la versión anterior:
    - UMAP intermedio 15D (vs 5D) para preservar más información
    - Parámetros HDBSCAN alineados con clustering standalone (4/2 vs 5/3)
    - UMAP 2D optimizado para mejor separación visual
    - Vectorizador con trigramas y filtros más robustos
    - Soporte para enhanced_embedding para comparación directa
    """
    
    def __init__(self, require_bertopic: bool = False):
        """
        Inicializa el servicio de BERTopic optimizado.
        
        Args:
            require_bertopic: Si True, lanza excepción si BERTopic no está disponible.
        """
        self._bertopic_available = BERTOPIC_AVAILABLE
        
        if require_bertopic and not BERTOPIC_AVAILABLE:
            raise ImportError(
                "BERTopic is required for this operation. Install with: pip install bertopic"
            )
        
        # ✨ OPTIMIZACIÓN 1: UMAP Intermedio - ALINEADO CON HDBSCAN STANDALONE
        # Usar 30D igual que clustering_service_new.py para preservar estructura
        self.umap_params = {
            'n_components': 30,     # 🔥 Igual que HDBSCAN standalone (30D)
            'n_neighbors': 15,      # Igual que HDBSCAN standalone
            'min_dist': 0.0,        # Igual que HDBSCAN standalone
            'metric': 'cosine',     # Igual que HDBSCAN standalone
            'random_state': 42
        }
        
        # ✨ OPTIMIZACIÓN 2: HDBSCAN alineado con clustering standalone
        # Parámetros más permisivos para más clusters y menos outliers
        self.hdbscan_params = {
            'min_cluster_size': 4,  # 🔥 Reducido de 5 → 4
            'min_samples': 2,        # 🔥 Reducido de 3 → 2
            'metric': 'euclidean',
            'cluster_selection_method': 'eom',
            'prediction_data': True
        }
        
        # ✨ OPTIMIZACIÓN 3: Vectorizador mejorado
        # Trigramas + filtros más estrictos para keywords más relevantes
        self.vectorizer_params = {
            'stop_words': self._get_spanish_stopwords(),
            'ngram_range': (1, 3),      # 🔥 Ampliado de (1,2) → (1,3) para frases legales
            'min_df': 3,                 # 🔥 Aumentado de 2 → 3 para filtrar raros
            'max_df': 0.90,              # 🔥 Reducido de 0.95 → 0.90 para filtrar comunes
            'max_features': 5000,        # 🔥 NUEVO: limitar vocabulario
            'token_pattern': r'\b[a-záéíóúñü]{3,}\b',  # 🔥 NUEVO: min 3 chars, español
        }
        
        # ✨ OPTIMIZACIÓN 4: Representación con mayor diversidad
        self.representation_params = {
            'top_n_words': 15,      # 🔥 Aumentado de 10 → 15 para más contexto
            'diversity': 0.5        # 🔥 Aumentado de 0.3 → 0.5 para keywords más diversos
        }
        
        # ✨ OPTIMIZACIÓN 5: UMAP 2D - ALINEADO CON HDBSCAN STANDALONE
        # Parámetros idénticos a clustering_service_new.py para mejor separación visual
        self.umap_2d_params = {
            'n_components': 2,
            'n_neighbors': 10,      # Igual que HDBSCAN standalone
            'min_dist': 0.99,       # 🔥 CLAVE: igual que HDBSCAN (0.99 vs 0.3 anterior)
            'metric': 'cosine',     # Igual que HDBSCAN standalone
            'random_state': 42
            # Removido 'spread' para consistencia con HDBSCAN standalone
        }
    
    def _get_spanish_stopwords(self) -> List[str]:
        """Obtener stopwords en español ampliadas para documentos legales."""
        # Stopwords básicas en español
        stopwords = [
            # Artículos
            'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
            # Preposiciones
            'de', 'del', 'al', 'a', 'ante', 'bajo', 'con', 'contra',
            'desde', 'en', 'entre', 'hacia', 'hasta', 'para', 'por',
            'según', 'sin', 'sobre', 'tras', 'durante', 'mediante',
            # Pronombres
            'que', 'cual', 'cuyo', 'cuya', 'cuyos', 'cuyas',
            'quien', 'quienes', 'donde', 'cuando', 'como', 'cuanto',
            # Demostrativos
            'este', 'esta', 'estos', 'estas', 'ese', 'esa', 'esos', 'esas',
            'aquel', 'aquella', 'aquellos', 'aquellas',
            # Personales
            'yo', 'tú', 'él', 'ella', 'nosotros', 'vosotros', 'ellos', 'ellas',
            'me', 'te', 'se', 'nos', 'os', 'le', 'les', 'lo', 'la', 'los', 'las',
            'mi', 'tu', 'su', 'nuestro', 'vuestro', 'suyo',
            # Verbos auxiliares comunes
            'ser', 'estar', 'haber', 'tener', 'hacer', 'poder', 'deber',
            'es', 'son', 'está', 'están', 'fue', 'fueron', 'ha', 'han', 'había',
            'será', 'serán', 'sea', 'sean', 'sido',
            # Conjunciones
            'y', 'e', 'o', 'u', 'pero', 'sino', 'ni', 'que', 'si', 'porque', 'aunque',
            # Adverbios
            'más', 'menos', 'muy', 'mucho', 'poco', 'tanto', 'tan',
            'no', 'sí', 'también', 'además', 'solo', 'ya', 'aún', 'todavía',
            'así', 'entonces', 'luego', 'después', 'antes', 'ahora',
            # 🔥 Términos legales genéricos (ampliado)
            'artículo', 'artículos', 'inciso', 'incisos', 'numeral', 'numerales',
            'párrafo', 'párrafos', 'folio', 'folios', 'página', 'páginas',
            'documento', 'documentos', 'presente', 'presentes',
            'señor', 'señora', 'señores', 'señoras', 'señorita',
            'dicho', 'dicha', 'dichos', 'dichas', 
            'mismo', 'misma', 'mismos', 'mismas',
            'siguiente', 'siguientes', 'anterior', 'anteriores',
            'respectivo', 'respectiva', 'respectivos', 'respectivas',
            'mediante', 'conforme', 'relativo', 'relativa',
            'expediente', 'expedientes', 'proceso', 'procesos',
            'vista', 'visto', 'vistas', 'vistos',
            'resulta', 'resultando', 'considerando', 'considerandos',
        ]
        return stopwords
    
    def compute_topics(
        self,
        max_documents: int = 1000,
        min_topic_size: int = 4,      # 🔥 Default cambiado de 5 → 4
        nr_topics: Optional[int] = None,
        embedding_field: str = 'clean_embedding',  # 🔥 Usar clean_embedding (768D) por consistencia con el proyecto
        calculate_probabilities: bool = True,
        umap_params: Optional[Dict] = None,
        hdbscan_params: Optional[Dict] = None,
        compute_metrics: bool = True   # 🔥 NUEVO: calcular métricas de calidad
    ) -> 'BERTopicModel':
        """
        Computa tópicos con BERTopic OPTIMIZADO.
        
        Args:
            max_documents: Máximo de documentos a procesar
            min_topic_size: Tamaño mínimo de tópico (min_cluster_size)
            nr_topics: Número de tópicos deseado (None = automático)
            embedding_field: 'enhanced_embedding' (384D) o 'clean_embedding' (768D)
            calculate_probabilities: Calcular probabilidades por documento
            umap_params: Parámetros personalizados para UMAP
            hdbscan_params: Parámetros personalizados para HDBSCAN
            compute_metrics: Si True, calcula métricas de calidad de clustering
            
        Returns:
            BERTopicModel creado con métricas de calidad
        """
        if not self._bertopic_available:
            raise ImportError(
                "BERTopic is required to compute topics. Install with: pip install bertopic"
            )
        
        start_time = time.time()
        logger.info("=" * 80)
        logger.info("🚀 Starting OPTIMIZED BERTopic computation...")
        logger.info("=" * 80)
        
        # Merge parámetros con defaults optimizados
        umap_config = {**self.umap_params, **(umap_params or {})}
        hdbscan_config = {**self.hdbscan_params, **(hdbscan_params or {})}
        hdbscan_config['min_cluster_size'] = min_topic_size
        
        logger.info(f"📋 Configuration:")
        logger.info(f"   Embedding field: {embedding_field}")
        logger.info(f"   UMAP components: {umap_config['n_components']}D")
        logger.info(f"   HDBSCAN min_cluster_size: {hdbscan_config['min_cluster_size']}")
        logger.info(f"   HDBSCAN min_samples: {hdbscan_config['min_samples']}")
        logger.info("")
        
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
        texts = []
        for doc in doc_list:
            # Combinar título + contenido para mejor contexto
            text = f"{doc.title or ''} {(doc.content or '')[:3000]}"  # 🔥 Aumentado de 2000
            texts.append(text.strip())
        
        logger.info(f"📐 Embeddings shape: {embeddings.shape}")
        
        # 3. Configurar componentes de BERTopic
        logger.info("⚙️ Configuring BERTopic components...")
        
        # UMAP para reducción de dimensionalidad (XD → 15D)
        logger.info(f"   - UMAP {embeddings.shape[1]}D → {umap_config['n_components']}D")
        umap_model = umap.UMAP(**umap_config)
        
        # HDBSCAN para clustering
        logger.info(f"   - HDBSCAN (min_cluster={hdbscan_config['min_cluster_size']}, "
                   f"min_samples={hdbscan_config['min_samples']})")
        hdbscan_model = hdbscan.HDBSCAN(**hdbscan_config)
        
        # Vectorizador para c-TF-IDF
        logger.info(f"   - Vectorizer (ngrams={self.vectorizer_params['ngram_range']}, "
                   f"max_features={self.vectorizer_params['max_features']})")
        vectorizer_model = CountVectorizer(**self.vectorizer_params)
        
        # Cargar el modelo de embeddings para KeyBERTInspired
        # Usar el modelo apropiado según el embedding_field
        logger.info("📦 Loading embedding model for representation...")
        if embedding_field == 'clean_embedding':
            # clean_embedding usa paraphrase-multilingual-mpnet-base-v2
            embedding_model = SentenceTransformer(
                'sentence-transformers/paraphrase-multilingual-mpnet-base-v2'
            )
        else:
            # enhanced_embedding usa paraphrase-multilingual-MiniLM-L12-v2
            embedding_model = SentenceTransformer(
                'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
            )
        
        # Modelos de representación para mejores keywords
        representation_models = [
            KeyBERTInspired(top_n_words=self.representation_params['top_n_words']),
            MaximalMarginalRelevance(diversity=self.representation_params['diversity'])
        ]
        
        # 4. Crear modelo BERTopic
        logger.info("🎯 Creating BERTopic model...")
        topic_model = BERTopic(
            embedding_model=embedding_model,
            umap_model=umap_model,
            hdbscan_model=hdbscan_model,
            vectorizer_model=vectorizer_model,
            representation_model=representation_models,
            nr_topics=nr_topics,
            calculate_probabilities=calculate_probabilities,
            verbose=True
        )
        
        # 5. Fit del modelo
        logger.info("🔄 Fitting BERTopic model...")
        topics, probs = topic_model.fit_transform(texts, embeddings)
        
        # 6. Obtener información de tópicos
        topic_info = topic_model.get_topic_info()
        unique_topics = set(topics)
        n_topics = len([t for t in unique_topics if t != -1])
        n_outliers = sum(1 for t in topics if t == -1)
        
        logger.info("")
        logger.info(f"📊 Clustering Results:")
        logger.info(f"   Topics found: {n_topics}")
        logger.info(f"   Outliers: {n_outliers} ({n_outliers/len(doc_list)*100:.1f}%)")
        logger.info("")
        
        # 🔥 7. Calcular métricas de calidad de clustering
        quality_metrics = {}
        if compute_metrics and SKLEARN_AVAILABLE and n_topics > 1:
            logger.info("📈 Computing clustering quality metrics...")
            try:
                # Filtrar embeddings para reducción dimensional (excluir outliers)
                non_outlier_mask = np.array(topics) != -1
                if non_outlier_mask.sum() > 10:  # Mínimo 10 documentos no-outliers
                    # Reducir embeddings para métricas (usar UMAP result)
                    embeddings_reduced = umap_model.embedding_
                    
                    # Silhouette Score (rango -1 a 1, más alto = mejor)
                    silhouette = silhouette_score(
                        embeddings_reduced[non_outlier_mask],
                        np.array(topics)[non_outlier_mask]
                    )
                    
                    # Calinski-Harabasz Score (más alto = mejor)
                    calinski = calinski_harabasz_score(
                        embeddings_reduced[non_outlier_mask],
                        np.array(topics)[non_outlier_mask]
                    )
                    
                    # Davies-Bouldin Score (más bajo = mejor)
                    davies = davies_bouldin_score(
                        embeddings_reduced[non_outlier_mask],
                        np.array(topics)[non_outlier_mask]
                    )
                    
                    quality_metrics = {
                        'silhouette_score': float(silhouette),
                        'calinski_harabasz_score': float(calinski),
                        'davies_bouldin_score': float(davies)
                    }
                    
                    logger.info(f"   Silhouette Score: {silhouette:.3f}")
                    logger.info(f"   Calinski-Harabasz: {calinski:.1f}")
                    logger.info(f"   Davies-Bouldin: {davies:.3f}")
                    logger.info("")
            except Exception as e:
                logger.warning(f"   Could not compute quality metrics: {e}")
        
        # 8. Reducir embeddings a 2D para visualización
        logger.info("🔄 Reducing to 2D for visualization...")
        logger.info(f"   UMAP 2D params: n_neighbors={self.umap_2d_params['n_neighbors']}, "
                   f"min_dist={self.umap_2d_params['min_dist']}")
        umap_2d = umap.UMAP(**self.umap_2d_params)
        embeddings_2d = umap_2d.fit_transform(embeddings)
        logger.info(f"✅ 2D embeddings shape: {embeddings_2d.shape}")
        
        # 9. Guardar en base de datos
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
                'hdbscan_params': hdbscan_config,
                'quality_metrics': quality_metrics,  # 🔥 NUEVO
                'optimized': True,  # 🔥 Flag para indicar versión optimizada
                'version': '2.0'    # 🔥 Versión del servicio
            }
        )
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ OPTIMIZED BERTopic computation completed!")
        logger.info("=" * 80)
        logger.info(f"📊 Final Results:")
        logger.info(f"   Model ID: {bertopic_model.model_id}")
        logger.info(f"   Documents: {bertopic_model.document_count}")
        logger.info(f"   Topics: {bertopic_model.topic_count}")
        logger.info(f"   Outliers: {bertopic_model.outlier_count} "
                   f"({bertopic_model.outlier_count/bertopic_model.document_count*100:.1f}%)")
        logger.info(f"   Computation Time: {bertopic_model.computation_time:.2f}s")
        if quality_metrics:
            logger.info(f"   Silhouette Score: {quality_metrics['silhouette_score']:.3f}")
        logger.info("=" * 80)
        logger.info("")
        
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
                    keywords = [word for word, _ in topic_words[:15]]  # 🔥 Aumentado de 10 a 15
                    keyword_weights = {word: float(weight) for word, weight in topic_words[:15]}
                else:
                    keywords = []
                    keyword_weights = {}
                
                # Generar label representativo
                if topic_id == -1:
                    label = "Outliers (sin tópico)"
                elif keywords:
                    # 🔥 Usar top 4 keywords para label más descriptivo
                    label = ", ".join(keywords[:4])
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
            
            BERTopicDocument.objects.bulk_create(doc_records, batch_size=500)
            
            logger.info(f"✅ Saved {len(topic_objects)} topics and {len(doc_records)} document assignments")
            
            return bertopic_model
    
    def compare_with_hdbscan(
        self,
        bertopic_model_id: int,
        hdbscan_graph_id: int
    ) -> Dict[str, Any]:
        """
        Comparar resultados de BERTopic con HDBSCAN standalone.
        
        Args:
            bertopic_model_id: ID del modelo BERTopic
            hdbscan_graph_id: ID del grafo HDBSCAN
            
        Returns:
            Dict con comparación de métricas
        """
        from apps.documents.models import ClusterGraph
        
        bertopic_model = BERTopicModel.objects.get(model_id=bertopic_model_id)
        hdbscan_graph = ClusterGraph.objects.get(graph_id=hdbscan_graph_id)
        
        # Extraer métricas
        bertopic_params = bertopic_model.parameters
        hdbscan_params = hdbscan_graph.parameters
        
        comparison = {
            'bertopic': {
                'model_id': bertopic_model.model_id,
                'document_count': bertopic_model.document_count,
                'cluster_count': bertopic_model.topic_count,
                'outlier_count': bertopic_model.outlier_count,
                'outlier_percentage': bertopic_model.outlier_count / bertopic_model.document_count * 100,
                'computation_time': bertopic_model.computation_time,
                'quality_metrics': bertopic_params.get('quality_metrics', {}),
                'umap_components': bertopic_params.get('umap_params', {}).get('n_components'),
                'min_cluster_size': bertopic_params.get('hdbscan_params', {}).get('min_cluster_size'),
                'min_samples': bertopic_params.get('hdbscan_params', {}).get('min_samples'),
            },
            'hdbscan': {
                'graph_id': hdbscan_graph.graph_id,
                'document_count': hdbscan_graph.document_count,
                'cluster_count': hdbscan_graph.cluster_count,
                'noise_count': hdbscan_graph.noise_count,
                'noise_percentage': hdbscan_graph.noise_count / hdbscan_graph.document_count * 100,
                'computation_time': hdbscan_graph.computation_time,
                'quality_metrics': hdbscan_params.get('quality_metrics', {}),
                'umap_components': hdbscan_params.get('umap_30d_params', {}).get('n_components'),
                'min_cluster_size': hdbscan_params.get('clustering_params', {}).get('min_cluster_size'),
                'min_samples': hdbscan_params.get('clustering_params', {}).get('min_samples'),
            }
        }
        
        # Calcular diferencias
        comparison['differences'] = {
            'cluster_count_diff': bertopic_model.topic_count - hdbscan_graph.cluster_count,
            'outlier_diff': bertopic_model.outlier_count - hdbscan_graph.noise_count,
            'outlier_percentage_diff': comparison['bertopic']['outlier_percentage'] - comparison['hdbscan']['noise_percentage']
        }
        
        logger.info("=" * 80)
        logger.info("📊 BERTopic vs HDBSCAN Comparison")
        logger.info("=" * 80)
        logger.info(f"Clusters: BERTopic={bertopic_model.topic_count}, HDBSCAN={hdbscan_graph.cluster_count} "
                   f"(diff={comparison['differences']['cluster_count_diff']:+d})")
        logger.info(f"Outliers: BERTopic={bertopic_model.outlier_count} ({comparison['bertopic']['outlier_percentage']:.1f}%), "
                   f"HDBSCAN={hdbscan_graph.noise_count} ({comparison['hdbscan']['noise_percentage']:.1f}%) "
                   f"(diff={comparison['differences']['outlier_percentage_diff']:+.1f}%)")
        logger.info("=" * 80)
        
        return comparison

    # ============================================================================
    # MÉTODOS PARA SERVIR DATOS AL FRONTEND (compatibles con bertopic_service.py)
    # ============================================================================

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
        
        # Metadata con información de optimización
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
            'parameters': model.parameters,
            'is_optimized': model.parameters.get('optimized', False),
            'quality_metrics': model.parameters.get('quality_metrics', {})
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


# ============================================================================
# ALIAS PARA COMPATIBILIDAD: Mantener el nombre BERTopicService para que
# las vistas y tasks existentes funcionen sin cambios
# ============================================================================
BERTopicService = BERTopicServiceOptimized
