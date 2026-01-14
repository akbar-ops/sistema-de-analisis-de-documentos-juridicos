# apps/documents/tasks.py
"""
Tareas Celery para procesamiento asíncrono de documentos.
"""
import logging
from celery import shared_task, current_task
from django.utils import timezone
from django.db import transaction

from .models import Document, DocumentTask, TaskStatus, TaskType, DocumentChunk
from .services.modular_processing import ModularDocumentProcessor
from .services.parsers.text_extraction import TextExtractionService
from .services.chunking_service import ChunkingService
from .services.embedding_service import get_embedding_service
from .services.clean_embeddings_service import get_clean_embedding_service
from .services.chunk_embedding_service import ChunkEmbeddingService

logger = logging.getLogger(__name__)


def update_task_progress(task_obj, percent, message, status=TaskStatus.PROGRESS):
    """
    Actualiza el progreso de una tarea en la base de datos.
    """
    task_obj.progress_percent = percent
    task_obj.progress_message = message
    task_obj.status = status
    if status == TaskStatus.STARTED and not task_obj.started_at:
        task_obj.started_at = timezone.now()
    task_obj.save(update_fields=['progress_percent', 'progress_message', 'status', 'started_at'])
    
    # También actualizar el estado de Celery para que se pueda consultar (solo en contexto Celery)
    if current_task and hasattr(current_task, 'request') and current_task.request.id:
        try:
            current_task.update_state(
                state=status.upper(),
                meta={
                    'progress': percent,
                    'message': message,
                    'document_id': str(task_obj.document.document_id)
                }
            )
        except Exception as e:
            logger.warning(f"Could not update Celery state: {e}")


@shared_task(bind=True, name='apps.documents.tasks.process_document_upload')
def process_document_upload(self, document_id: str, task_id: str):
    """
    Procesa un documento recién subido: extrae texto, crea chunks, genera embeddings.
    Esta tarea tiene ALTA PRIORIDAD (queue: high_priority).
    
    Args:
        document_id: UUID del documento
        task_id: ID de la tarea en DocumentTask
    """
    logger.info(f"Starting upload processing for document {document_id}")
    
    try:
        # Obtener documento y tarea
        document = Document.objects.get(document_id=document_id)
        task_obj = DocumentTask.objects.get(task_id=task_id)
        
        # Marcar como iniciada
        update_task_progress(task_obj, 0, "Iniciando procesamiento...", TaskStatus.STARTED)
        
        # PASO 1: Extraer texto (30%)
        update_task_progress(task_obj, 10, "Extrayendo texto del documento...")
        
        text_extractor = TextExtractionService()
        with document.file_path.open('rb') as f:
            file_content = f.read()
        
        extracted_text, metadata = text_extractor.extract_text(
            file_content,
            document.file_path.name,
        )
        
        if not extracted_text:
            raise ValueError("No se pudo extraer texto del documento")
        
        document.content = extracted_text
        document.pages = metadata.get('n_hojas', 0)
        document.file_size = document.file_path.size
        document.save()
        
        update_task_progress(task_obj, 30, f"Texto extraído: {len(extracted_text)} caracteres")
        
        # PASO 2: Crear chunks (60%)
        update_task_progress(task_obj, 40, "Creando chunks del documento...")
        
        chunking_service = ChunkingService(chunk_size=1000, chunk_overlap=200)
        num_chunks = chunking_service.create_chunks_for_document(
            document,
            method='contextual'
        )
        
        update_task_progress(task_obj, 60, f"Creados {num_chunks} chunks")
        
        # PASO 3a: Generar embeddings LEGACY para chunks (384d) - Mantener compatibilidad
        update_task_progress(task_obj, 65, "Generando embeddings legacy (384d)...")
        
        embedding_service = get_embedding_service()
        chunks = DocumentChunk.objects.filter(document_id=document).order_by('order_number')
        
        if chunks.exists():
            chunk_contents = [chunk.content for chunk in chunks]
            chunk_embeddings = embedding_service.encode_chunks_batch(
                chunk_contents,
                batch_size=32
            )
            
            for chunk, embedding in zip(chunks, chunk_embeddings):
                chunk.content_embedding = embedding.tolist()
                chunk.save(update_fields=['content_embedding'])
        
        update_task_progress(task_obj, 70, f"Embeddings legacy generados")
        
        # PASO 3b: Generar clean_content_embedding para chunks (768d) - NUEVO para RAG v4.0
        update_task_progress(task_obj, 75, "Generando embeddings limpios para chunks (768d)...")
        
        chunk_embedding_service = ChunkEmbeddingService(clean_chunks=True)
        chunks = DocumentChunk.objects.filter(document_id=document).order_by('order_number')
        
        if chunks.exists():
            chunk_contents = [chunk.content for chunk in chunks]
            clean_embeddings = chunk_embedding_service.generate_batch_embeddings(
                chunk_contents,
                normalize=True,
                apply_cleaning=True,
                batch_size=32
            )
            
            for chunk, clean_emb in zip(chunks, clean_embeddings):
                if clean_emb is not None:
                    chunk.clean_content_embedding = clean_emb.tolist()
                    chunk.save(update_fields=['clean_content_embedding'])
        
        update_task_progress(task_obj, 85, f"Embeddings limpios generados para {num_chunks} chunks")
        
        # PASO 4: Generar clean_embedding (ALWAYS - does NOT require Ollama)
        update_task_progress(task_obj, 90, "Generando clean embedding (similaridad/clustering)...")
        
        clean_embedding_service = get_clean_embedding_service()
        clean_embedding = clean_embedding_service.generate_document_embedding(
            extracted_text,
            clean_text=True,
            pooling_strategy='weighted_start'
        )
        
        if clean_embedding is not None:
            document.clean_embedding = clean_embedding.tolist()
            document.save(update_fields=['clean_embedding'])
            
            stats = clean_embedding_service.get_text_statistics(extracted_text)
            logger.info(
                f"Clean embedding generated: {stats['original_words']} → {stats['cleaned_words']} words "
                f"({stats['reduction_percent']}% reduction)"
            )
        
        update_task_progress(task_obj, 95, "Clean embedding generado")

        # PASO 5: Finalizar (100%)
        document.refresh_from_db()
        task_obj.status = TaskStatus.SUCCESS
        task_obj.progress_percent = 100
        task_obj.progress_message = "Documento procesado correctamente"
        task_obj.completed_at = timezone.now()
        task_obj.result = {
            'num_chunks': num_chunks,
            'text_length': len(extracted_text),
            'pages': document.pages
        }
        task_obj.save()
        
        logger.info(f"Successfully processed document {document_id} with {num_chunks} chunks")
        return {
            'status': 'success',
            'document_id': str(document_id),
            'num_chunks': num_chunks
        }
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}", exc_info=True)
        
        # Marcar tarea como fallida
        task_obj = DocumentTask.objects.get(task_id=task_id)
        task_obj.status = TaskStatus.FAILURE
        task_obj.error_message = str(e)
        task_obj.completed_at = timezone.now()
        task_obj.save()
        
        # Marcar documento como fallido
        document = Document.objects.get(document_id=document_id)
        document.status = 'failed'
        document.error_message = str(e)
        document.save()
        
        raise


@shared_task(bind=True, name='apps.documents.tasks.process_document_analysis')
def process_document_analysis(self, document_id: str, task_id: str, parts: list, summarizer_type: str = None):
    """
    Procesa análisis de partes específicas de un documento.
    Esta tarea tiene PRIORIDAD NORMAL (queue: default).
    
    IMPORTANTE: El clean_embedding SIEMPRE se genera/actualiza si no existe,
    independientemente de las partes solicitadas. NO requiere Ollama.
    
    Args:
        document_id: UUID del documento
        task_id: ID de la tarea en DocumentTask
        parts: Lista de partes a analizar ['metadata', 'summary', 'persons', 'clean_embedding']
        summarizer_type: Tipo de generador de resumen ('ollama' o 'bart'), default: 'ollama'
    """
    # Default a ollama si no se especifica
    if summarizer_type is None:
        summarizer_type = 'ollama'
    
    logger.info(f"Starting analysis for document {document_id}, parts: {parts}, summarizer: {summarizer_type}")
    
    try:
        # Obtener documento y tarea
        document = Document.objects.get(document_id=document_id)
        task_obj = DocumentTask.objects.get(task_id=task_id)
        
        # Verificar que el documento tenga contenido
        if not document.content:
            raise ValueError("El documento no tiene contenido extraído")
        
        # Marcar como iniciada
        update_task_progress(task_obj, 0, "Iniciando análisis...", TaskStatus.STARTED)
        
        # SIEMPRE generar clean_embedding primero si no existe (NO requiere Ollama)
        processor = ModularDocumentProcessor()
        results = {}
        
        if document.clean_embedding is None:
            update_task_progress(task_obj, 5, "Generando clean embedding (similaridad/clustering)...")
            results['clean_embedding'] = processor.generate_clean_embedding(document)
            logger.info(f"Clean embedding generated for document {document_id}")
        
        total_parts = len(parts)
        for i, part in enumerate(parts):
            progress = int((i / total_parts) * 80) + 10  # 10% - 90%
            
            if part == 'metadata':
                update_task_progress(task_obj, progress, "Analizando metadatos...")
                results['metadata'] = processor.process_metadata(document)
                
            elif part == 'title':
                update_task_progress(task_obj, progress, "Generando título específico...")
                results['title'] = processor.process_title(document)
                
            elif part == 'summary':
                update_task_progress(
                    task_obj, progress, 
                    f"Generando resumen con {summarizer_type.upper()}..."
                )
                results['summary'] = processor.process_summary(document, summarizer_type)
                
            elif part == 'persons':
                update_task_progress(task_obj, progress, "Extrayendo personas...")
                results['persons'] = processor.process_persons(document)
            
            elif part == 'clean_embedding':
                update_task_progress(task_obj, progress, "Regenerando clean embedding...")
                results['clean_embedding'] = processor.generate_clean_embedding(document)
        
        # Actualizar estado del documento
        update_task_progress(task_obj, 95, "Actualizando estado del documento...")
        processor._update_document_status(document)
        
        # Finalizar
        task_obj.status = TaskStatus.SUCCESS
        task_obj.progress_percent = 100
        task_obj.progress_message = "Análisis completado correctamente"
        task_obj.completed_at = timezone.now()
        task_obj.result = results
        task_obj.save()
        
        # NOTE: Cluster rebuild is now MANUAL only (via frontend button)
        # No longer auto-triggered after document analysis
        
        logger.info(f"Successfully analyzed document {document_id}: {results}")
        return {
            'status': 'success',
            'document_id': str(document_id),
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Error analyzing document {document_id}: {e}", exc_info=True)
        
        # Marcar tarea como fallida
        task_obj = DocumentTask.objects.get(task_id=task_id)
        task_obj.status = TaskStatus.FAILURE
        task_obj.error_message = str(e)
        task_obj.completed_at = timezone.now()
        task_obj.save()
        
        raise


@shared_task(bind=True, name='apps.documents.tasks.compute_cluster_graph')
def compute_cluster_graph(
    self,
    max_documents: int = 1000,
    use_enhanced_embedding: bool = False,
    use_clean_embedding: bool = True,
    algorithm: str = 'hdbscan',
    knn_k: int = 20,
    knn_min_similarity: float = 0.3
):
    """
    Tarea periódica para computar el grafo global de clusters.
    
    Esta tarea se ejecuta:
    - Nightly (batch nocturno automático)
    - Manualmente desde comando de Django
    - Desde el botón "Recargar" del frontend
    
    Args:
        max_documents: Máximo de documentos a incluir
        use_enhanced_embedding: Si True usa enhanced_embedding (384D)
        use_clean_embedding: Si True usa clean_embedding (768D) - RECOMENDADO
        algorithm: 'hdbscan' o 'dbscan'
        knn_k: Número de vecinos para KNN graph
        knn_min_similarity: Similitud mínima para KNN edges
    """
    from apps.documents.services.clustering_service_new import ClusteringService
    
    logger.info("=" * 80)
    logger.info("🚀 STARTING CLUSTER GRAPH COMPUTATION (BATCH JOB)")
    logger.info("=" * 80)
    logger.info(f"Parameters:")
    logger.info(f"  - max_documents: {max_documents}")
    logger.info(f"  - use_clean_embedding: {use_clean_embedding}")
    logger.info(f"  - use_enhanced_embedding: {use_enhanced_embedding}")
    logger.info(f"  - algorithm: {algorithm}")
    
    try:
        # Actualizar estado de Celery (solo si estamos en contexto de Celery)
        if current_task and hasattr(current_task, 'request') and current_task.request.id:
            try:
                current_task.update_state(
                    state='PROGRESS',
                    meta={
                        'progress': 0,
                        'message': 'Starting cluster computation...',
                        'stage': 'initialization'
                    }
                )
            except Exception as e:
                logger.warning(f"Could not update Celery state: {e}")
        
        # Crear servicio de clustering
        clustering_service = ClusteringService()
        
        # Computar grafo (esto puede tomar varios minutos)
        cluster_graph = clustering_service.compute_global_clusters(
            max_documents=max_documents,
            use_enhanced_embedding=use_enhanced_embedding,
            use_clean_embedding=use_clean_embedding,
            algorithm=algorithm,
            knn_params={
                'k': knn_k,
                'min_similarity': knn_min_similarity
            }
        )
        
        # Activar el nuevo grafo
        logger.info(f"✅ Activating new cluster graph {cluster_graph.graph_id}...")
        cluster_graph.activate()
        
        # Resultado
        result = {
            'status': 'success',
            'graph_id': cluster_graph.graph_id,
            'document_count': cluster_graph.document_count,
            'cluster_count': cluster_graph.cluster_count,
            'noise_count': cluster_graph.noise_count,
            'computation_time': cluster_graph.computation_time_seconds,
            'created_at': cluster_graph.created_at.isoformat()
        }
        
        logger.info("=" * 80)
        logger.info("✅ CLUSTER GRAPH COMPUTATION COMPLETED")
        logger.info("=" * 80)
        logger.info(f"Graph ID: {result['graph_id']}")
        logger.info(f"Documents: {result['document_count']}")
        logger.info(f"Clusters: {result['cluster_count']}")
        logger.info(f"Noise: {result['noise_count']}")
        logger.info(f"Time: {result['computation_time']:.2f}s")
        
        return result
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error("❌ CLUSTER GRAPH COMPUTATION FAILED")
        logger.error("=" * 80)
        logger.error(f"Error: {e}", exc_info=True)
        
        if current_task and hasattr(current_task, 'request') and current_task.request.id:
            try:
                current_task.update_state(
                    state='FAILURE',
                    meta={
                        'error': str(e),
                        'stage': 'failed'
                    }
                )
            except Exception as update_error:
                logger.warning(f"Could not update Celery state: {update_error}")
        
        raise


# ============================================================================
# BERTOPIC TASK
# ============================================================================

@shared_task(bind=True, name='apps.documents.tasks.compute_bertopic_model')
def compute_bertopic_model(
    self,
    max_documents: int = 1000,
    min_topic_size: int = 4,  # 🔥 Optimizado: 4 en lugar de 5
    nr_topics: int = None,
    embedding_field: str = 'clean_embedding'
):
    """
    Tarea para computar modelo BERTopic OPTIMIZADO.
    
    BERTopic combina:
    - Embeddings de documentos (SentenceTransformers)
    - UMAP para reducción de dimensionalidad (15D, optimizado)
    - HDBSCAN para clustering (min_cluster=4, min_samples=2)
    - c-TF-IDF para extracción de keywords representativos
    
    Args:
        max_documents: Máximo de documentos a incluir
        min_topic_size: Mínimo de documentos por tópico (default: 4 optimizado)
        nr_topics: Número deseado de tópicos (None = auto)
        embedding_field: Campo de embedding a usar (default: clean_embedding 768D)
    """
    # 🔥 Usar el servicio OPTIMIZADO
    from apps.documents.services.bertopic_service_optimized import BERTopicServiceOptimized
    
    logger.info("=" * 80)
    logger.info("🎯 STARTING BERTOPIC MODEL COMPUTATION")
    logger.info("=" * 80)
    logger.info(f"Parameters:")
    logger.info(f"  - max_documents: {max_documents}")
    logger.info(f"  - min_topic_size: {min_topic_size}")
    logger.info(f"  - nr_topics: {nr_topics or 'auto'}")
    logger.info(f"  - embedding_field: {embedding_field}")
    
    try:
        # Update Celery state
        if current_task and hasattr(current_task, 'request') and current_task.request.id:
            try:
                current_task.update_state(
                    state='PROGRESS',
                    meta={
                        'progress': 0,
                        'message': 'Starting BERTopic OPTIMIZED computation...',
                        'stage': 'initialization'
                    }
                )
            except Exception as e:
                logger.warning(f"Could not update Celery state: {e}")
        
        # 🔥 Create OPTIMIZED service and compute topics
        service = BERTopicServiceOptimized(require_bertopic=True)
        bertopic_model = service.compute_topics(
            max_documents=max_documents,
            min_topic_size=min_topic_size,
            nr_topics=nr_topics,
            embedding_field=embedding_field,
            calculate_probabilities=True,
            compute_metrics=True  # 🔥 Calcular métricas de calidad
        )
        
        # Activate the new model
        logger.info(f"✅ Activating new BERTopic model {bertopic_model.model_id}...")
        bertopic_model.activate()
        
        # Result
        result = {
            'status': 'success',
            'model_id': bertopic_model.model_id,
            'document_count': bertopic_model.document_count,
            'topic_count': bertopic_model.topic_count,
            'outlier_count': bertopic_model.outlier_count,
            'computation_time': bertopic_model.computation_time,
            'created_at': bertopic_model.created_at.isoformat()
        }
        
        logger.info("=" * 80)
        logger.info("✅ BERTOPIC MODEL COMPUTATION COMPLETED")
        logger.info("=" * 80)
        logger.info(f"Model ID: {result['model_id']}")
        logger.info(f"Documents: {result['document_count']}")
        logger.info(f"Topics: {result['topic_count']}")
        logger.info(f"Outliers: {result['outlier_count']}")
        logger.info(f"Time: {result['computation_time']:.2f}s")
        
        return result
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error("❌ BERTOPIC MODEL COMPUTATION FAILED")
        logger.error("=" * 80)
        logger.error(f"Error: {e}", exc_info=True)
        
        if current_task and hasattr(current_task, 'request') and current_task.request.id:
            try:
                current_task.update_state(
                    state='FAILURE',
                    meta={
                        'error': str(e),
                        'stage': 'failed'
                    }
                )
            except Exception as update_error:
                logger.warning(f"Could not update Celery state: {update_error}")
        
        raise
