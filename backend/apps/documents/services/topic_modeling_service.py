# apps/documents/services/topic_modeling_service.py
"""
Servicio de Topic Modeling con BERTopic

Proporciona modelado de tópicos semántico usando:
- Embeddings precomputados (clean_embedding o enhanced_embedding)
- UMAP para reducción de dimensionalidad
- HDBSCAN para clustering jerárquico
- c-TF-IDF para representación de tópicos
- KeyBERT para extracción de palabras clave

Versión: 1.0
"""
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TopicInfo:
    """Información de un tópico descubierto"""
    topic_id: int
    name: str
    keywords: List[Tuple[str, float]]  # (palabra, score)
    document_count: int
    representative_docs: List[str] = field(default_factory=list)
    coherence_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'topic_id': self.topic_id,
            'name': self.name,
            'keywords': [{'word': w, 'score': s} for w, s in self.keywords],
            'document_count': self.document_count,
            'representative_docs': self.representative_docs,
            'coherence_score': self.coherence_score
        }


@dataclass
class DocumentTopicAssignment:
    """Asignación de documento a tópico"""
    document_id: str
    topic_id: int
    topic_name: str
    probability: float
    keywords: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'document_id': self.document_id,
            'topic_id': self.topic_id,
            'topic_name': self.topic_name,
            'probability': self.probability,
            'keywords': self.keywords
        }


class TopicModelingService:
    """
    Servicio para modelado de tópicos en documentos legales.
    
    Usa BERTopic para descubrir tópicos semánticos en la colección
    de documentos, ideal para:
    - Exploración de jurisprudencia por temas
    - Descubrimiento de patrones en resoluciones
    - Organización automática de documentos
    """
    
    # Configuración por defecto
    DEFAULT_MIN_CLUSTER_SIZE = 5
    DEFAULT_N_NEIGHBORS = 15
    DEFAULT_MIN_SAMPLES = 3
    DEFAULT_TOP_N_WORDS = 10
    
    # Stopwords adicionales para dominio legal (complementan las del modelo)
    LEGAL_STOPWORDS = {
        'artículo', 'articulo', 'ley', 'código', 'codigo', 'decreto',
        'número', 'numero', 'fecha', 'señor', 'señora', 'juez', 'tribunal',
        'sala', 'corte', 'juzgado', 'expediente', 'fojas', 'fs', 'foja',
        'considerando', 'resuelve', 'vistos', 'oídos', 'oidos',
        'demandante', 'demandado', 'parte', 'partes', 'actor', 'actora',
        'proceso', 'causa', 'autos', 'auto', 'sentencia', 'resolución',
        'resolucion', 'primero', 'segundo', 'tercero', 'cuarto', 'quinto'
    }
    
    def __init__(
        self,
        min_cluster_size: int = None,
        n_neighbors: int = None,
        min_samples: int = None,
        top_n_words: int = None
    ):
        """
        Inicializa el servicio de topic modeling.
        
        Args:
            min_cluster_size: Tamaño mínimo de cluster para HDBSCAN
            n_neighbors: Número de vecinos para UMAP
            min_samples: Muestras mínimas para considerar un cluster
            top_n_words: Número de palabras clave por tópico
        """
        self.min_cluster_size = min_cluster_size or self.DEFAULT_MIN_CLUSTER_SIZE
        self.n_neighbors = n_neighbors or self.DEFAULT_N_NEIGHBORS
        self.min_samples = min_samples or self.DEFAULT_MIN_SAMPLES
        self.top_n_words = top_n_words or self.DEFAULT_TOP_N_WORDS
        
        self._topic_model = None
        self._is_fitted = False
        
    def _initialize_model(self, n_documents: int) -> 'BERTopic':
        """
        Inicializa el modelo BERTopic con configuración optimizada.
        
        Args:
            n_documents: Número de documentos para ajustar parámetros
        
        Returns:
            Instancia de BERTopic configurada
        """
        try:
            from bertopic import BERTopic
            from umap import UMAP
            from hdbscan import HDBSCAN
            from sklearn.feature_extraction.text import CountVectorizer
        except ImportError as e:
            logger.error(f"Missing required package: {e}")
            raise ImportError(
                "Please install required packages: pip install bertopic umap-learn hdbscan"
            )
        
        # Ajustar parámetros según tamaño del dataset
        min_cluster = max(2, min(self.min_cluster_size, n_documents // 10))
        n_neighbors = max(2, min(self.n_neighbors, n_documents - 1))
        
        # UMAP para reducción de dimensionalidad
        umap_model = UMAP(
            n_neighbors=n_neighbors,
            n_components=5,  # Reducir a 5D antes de clustering
            min_dist=0.0,
            metric='cosine',
            random_state=42
        )
        
        # HDBSCAN para clustering
        hdbscan_model = HDBSCAN(
            min_cluster_size=min_cluster,
            min_samples=self.min_samples,
            metric='euclidean',
            cluster_selection_method='eom',
            prediction_data=True
        )
        
        # Vectorizer con stopwords en español
        vectorizer_model = CountVectorizer(
            stop_words=list(self.LEGAL_STOPWORDS),
            min_df=2,
            max_df=0.95,
            ngram_range=(1, 2)
        )
        
        # Crear modelo BERTopic
        # No usamos embedding_model porque pasaremos embeddings precalculados
        topic_model = BERTopic(
            language='spanish',
            umap_model=umap_model,
            hdbscan_model=hdbscan_model,
            vectorizer_model=vectorizer_model,
            top_n_words=self.top_n_words,
            nr_topics='auto',  # Detectar automáticamente
            calculate_probabilities=True,
            verbose=False
        )
        
        logger.info(
            f"Initialized BERTopic model with min_cluster={min_cluster}, "
            f"n_neighbors={n_neighbors}"
        )
        
        return topic_model
    
    def fit_transform(
        self,
        documents: List[str],
        embeddings: np.ndarray,
        document_ids: List[str] = None
    ) -> Tuple[List[int], List[float]]:
        """
        Ajusta el modelo a los documentos y retorna asignaciones de tópicos.
        
        Args:
            documents: Lista de textos de documentos
            embeddings: Array de embeddings (n_docs, embedding_dim)
            document_ids: IDs opcionales de documentos
        
        Returns:
            Tuple de (topics, probabilities) donde:
            - topics: Lista de IDs de tópico asignados (-1 = outlier)
            - probabilities: Lista de probabilidades de pertenencia
        """
        if len(documents) < 3:
            logger.warning("Not enough documents for topic modeling (min 3)")
            return [-1] * len(documents), [0.0] * len(documents)
        
        # Convertir embeddings si es necesario
        if not isinstance(embeddings, np.ndarray):
            embeddings = np.array(embeddings)
        
        # Inicializar modelo
        self._topic_model = self._initialize_model(len(documents))
        
        try:
            # Fit y transform
            topics, probs = self._topic_model.fit_transform(
                documents, 
                embeddings=embeddings
            )
            
            self._is_fitted = True
            
            logger.info(
                f"Topic modeling complete: {len(set(topics))} topics found "
                f"from {len(documents)} documents"
            )
            
            return topics, probs.tolist() if isinstance(probs, np.ndarray) else probs
            
        except Exception as e:
            logger.error(f"Error in topic modeling: {e}", exc_info=True)
            return [-1] * len(documents), [0.0] * len(documents)
    
    def get_topic_info(self) -> List[TopicInfo]:
        """
        Obtiene información detallada de todos los tópicos descubiertos.
        
        Returns:
            Lista de TopicInfo con detalles de cada tópico
        """
        if not self._is_fitted or self._topic_model is None:
            logger.warning("Model not fitted yet")
            return []
        
        try:
            topic_info_df = self._topic_model.get_topic_info()
            results = []
            
            for _, row in topic_info_df.iterrows():
                topic_id = row['Topic']
                
                # Obtener palabras clave con scores
                topic_words = self._topic_model.get_topic(topic_id)
                if topic_words:
                    keywords = [(word, score) for word, score in topic_words[:self.top_n_words]]
                else:
                    keywords = []
                
                # Generar nombre basado en top keywords
                if keywords:
                    name = "_".join([w for w, _ in keywords[:3]])
                else:
                    name = f"topic_{topic_id}"
                
                topic_info = TopicInfo(
                    topic_id=topic_id,
                    name=name,
                    keywords=keywords,
                    document_count=row.get('Count', 0),
                    representative_docs=row.get('Representative_Docs', [])[:3]
                )
                
                results.append(topic_info)
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting topic info: {e}", exc_info=True)
            return []
    
    def get_document_topics(
        self,
        documents: List[str],
        document_ids: List[str],
        embeddings: np.ndarray = None
    ) -> List[DocumentTopicAssignment]:
        """
        Obtiene las asignaciones de tópicos para cada documento.
        
        Args:
            documents: Textos de documentos
            document_ids: IDs de documentos
            embeddings: Embeddings opcionales (usa los del fit si no se proveen)
        
        Returns:
            Lista de DocumentTopicAssignment
        """
        if not self._is_fitted:
            logger.warning("Model not fitted. Call fit_transform first.")
            return []
        
        try:
            # Si tenemos embeddings, hacer transform
            if embeddings is not None:
                topics, probs = self._topic_model.transform(documents, embeddings)
            else:
                # Usar los topics del fit
                topics = self._topic_model.topics_
                probs = self._topic_model.probabilities_
            
            results = []
            for i, (doc_id, topic_id) in enumerate(zip(document_ids, topics)):
                # Obtener keywords del tópico
                topic_words = self._topic_model.get_topic(topic_id)
                keywords = [w for w, _ in (topic_words or [])[:5]]
                
                # Generar nombre
                topic_name = "_".join(keywords[:3]) if keywords else f"topic_{topic_id}"
                
                # Probabilidad
                prob = float(probs[i]) if isinstance(probs[i], (int, float)) else float(probs[i].max())
                
                assignment = DocumentTopicAssignment(
                    document_id=doc_id,
                    topic_id=topic_id,
                    topic_name=topic_name,
                    probability=prob,
                    keywords=keywords
                )
                results.append(assignment)
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting document topics: {e}", exc_info=True)
            return []
    
    def find_topics(self, search_term: str, top_n: int = 5) -> List[Tuple[int, float]]:
        """
        Busca tópicos relacionados con un término de búsqueda.
        
        Args:
            search_term: Término a buscar
            top_n: Número de tópicos a retornar
        
        Returns:
            Lista de (topic_id, similarity_score)
        """
        if not self._is_fitted:
            return []
        
        try:
            topics, similarities = self._topic_model.find_topics(search_term, top_n=top_n)
            return list(zip(topics, similarities))
        except Exception as e:
            logger.error(f"Error finding topics: {e}")
            return []
    
    def visualize_topics(self) -> Optional[str]:
        """
        Genera una visualización interactiva de los tópicos.
        
        Returns:
            HTML string con la visualización o None si falla
        """
        if not self._is_fitted:
            return None
        
        try:
            fig = self._topic_model.visualize_topics()
            return fig.to_html()
        except Exception as e:
            logger.error(f"Error visualizing topics: {e}")
            return None
    
    def visualize_documents(
        self,
        docs: List[str],
        embeddings: np.ndarray,
        topics: List[int]
    ) -> Optional[str]:
        """
        Genera visualización 2D de documentos coloreados por tópico.
        
        Returns:
            HTML string con la visualización
        """
        if not self._is_fitted:
            return None
        
        try:
            fig = self._topic_model.visualize_documents(
                docs, 
                embeddings=embeddings,
                topics=topics
            )
            return fig.to_html()
        except Exception as e:
            logger.error(f"Error visualizing documents: {e}")
            return None


def run_topic_modeling_on_documents(
    embedding_field: str = 'clean_embedding',
    min_documents: int = 10,
    **kwargs
) -> Dict[str, Any]:
    """
    Ejecuta topic modeling sobre todos los documentos con embeddings.
    
    Args:
        embedding_field: Campo de embedding a usar
        min_documents: Número mínimo de documentos requeridos
        **kwargs: Argumentos adicionales para TopicModelingService
    
    Returns:
        Dict con topics, document_assignments, y topic_info
    """
    from apps.documents.models import Document
    
    # Obtener documentos con embeddings
    filter_kwargs = {f'{embedding_field}__isnull': False}
    documents = Document.objects.filter(**filter_kwargs).exclude(status='failed')
    
    if documents.count() < min_documents:
        logger.warning(
            f"Not enough documents for topic modeling "
            f"({documents.count()} < {min_documents})"
        )
        return {
            'success': False,
            'error': f'Insufficient documents ({documents.count()} < {min_documents})',
            'topics': [],
            'assignments': []
        }
    
    # Preparar datos
    doc_texts = []
    doc_ids = []
    embeddings_list = []
    
    for doc in documents:
        # Usar resumen si existe, sino texto limpio del contenido
        text = doc.summary if doc.summary else (doc.extracted_text or '')[:2000]
        if not text.strip():
            continue
        
        embedding = getattr(doc, embedding_field)
        if embedding is None or len(embedding) == 0:
            continue
        
        doc_texts.append(text)
        doc_ids.append(str(doc.document_id))
        embeddings_list.append(embedding)
    
    if len(doc_texts) < min_documents:
        return {
            'success': False,
            'error': f'Not enough valid documents ({len(doc_texts)})',
            'topics': [],
            'assignments': []
        }
    
    # Convertir a numpy array
    embeddings_array = np.array(embeddings_list)
    
    # Ejecutar topic modeling
    service = TopicModelingService(**kwargs)
    topics, probabilities = service.fit_transform(
        documents=doc_texts,
        embeddings=embeddings_array,
        document_ids=doc_ids
    )
    
    # Obtener información de tópicos
    topic_info = service.get_topic_info()
    
    # Obtener asignaciones de documentos
    assignments = service.get_document_topics(doc_texts, doc_ids)
    
    return {
        'success': True,
        'n_topics': len(set(topics)) - (1 if -1 in topics else 0),  # -1 son outliers
        'n_documents': len(doc_texts),
        'topics': [t.to_dict() for t in topic_info],
        'assignments': [a.to_dict() for a in assignments],
        'outliers_count': topics.count(-1) if isinstance(topics, list) else sum(1 for t in topics if t == -1)
    }
