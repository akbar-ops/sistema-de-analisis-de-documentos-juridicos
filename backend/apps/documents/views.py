from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import transaction
from django.db.models import Q
from celery import current_app, chain
import logging
import uuid

from .models import Document, DocumentStatus, DocumentTask, TaskType, TaskStatus, AnalysisStatus
from .serializers import (
    DocumentSerializer, DocumentCreateSerializer, 
    DocumentListSerializer, DocumentChunkSerializer,
    DocumentSimilaritySerializer, DocumentSearchResultSerializer,
    BulkUploadSerializer, DocumentAnalysisSerializer,
    DocumentTaskSerializer, DocumentTaskListSerializer
)
from .pagination import DocumentPagination
from .services.document_processing import DocumentProcessingService
from .services.modular_processing import ModularDocumentProcessor
from .services.similarity_service import DocumentSimilarityService
from .services.search_service import DocumentSearchService
from .services.parsers.text_extraction import TextExtractionService
from .services.chunking_service import ChunkingService
from .services.embedding_service import get_embedding_service
from .tasks import process_document_upload, process_document_analysis

logger = logging.getLogger(__name__)

class DocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing legal documents"""
    
    queryset = Document.objects.all()
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    pagination_class = DocumentPagination

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return DocumentCreateSerializer
        elif self.action == 'bulk_upload':
            return BulkUploadSerializer
        elif self.action == 'analyze':
            return DocumentAnalysisSerializer
        elif self.action == 'list':
            return DocumentListSerializer
        return DocumentSerializer

    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = Document.objects.all().order_by('-created_at')
        
        # Filter by document type
        doc_type = self.request.query_params.get('doc_type', None)
        if doc_type:
            queryset = queryset.filter(doc_type=doc_type)
        
        # Filter by legal area
        legal_area = self.request.query_params.get('legal_area', None)
        if legal_area:
            queryset = queryset.filter(legal_area=legal_area)
        
        # Filter by status
        doc_status = self.request.query_params.get('status', None)
        if doc_status:
            queryset = queryset.filter(status=doc_status)
        
        # Search in title and content
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(content__icontains=search)
            )
        
        return queryset

    def create(self, request, *args, **kwargs):
        """
        Create a new document and send it to Celery queue for processing.
        HIGH PRIORITY: Documents without analysis requests
        NORMAL PRIORITY: Documents with analysis requests
        """
        # Debug logging
        logger.info(f"📥 Received POST /api/documents/")
        logger.info(f"   Content-Type: {request.content_type}")
        logger.info(f"   request.data keys: {list(request.data.keys())}")
        logger.info(f"   request.FILES keys: {list(request.FILES.keys())}")
        if 'file' in request.data:
            logger.info(f"   file in request.data: {type(request.data['file'])}")
        if 'file' in request.FILES:
            logger.info(f"   file in request.FILES: {type(request.FILES['file'])}")
        
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            logger.error(f"❌ Serializer validation failed: {serializer.errors}")
        
        serializer.is_valid(raise_exception=True)
        
        # Get analysis options
        analyze_metadata = serializer.validated_data.get('analyze_metadata', False)
        analyze_title = serializer.validated_data.get('analyze_title', False)
        analyze_summary = serializer.validated_data.get('analyze_summary', False)
        analyze_persons = serializer.validated_data.get('analyze_persons', False)
        summarizer_type = serializer.validated_data.get('summarizer_type', 'ollama')
        
        has_analysis_request = analyze_metadata or analyze_title or analyze_summary or analyze_persons
        
        try:
            # Create document
            document = serializer.save()
            document.status = DocumentStatus.PROCESSING
            document.save()
            
            logger.info(f"Document created: {document.document_id}")
            
            # Create task for upload processing (ALWAYS HIGH PRIORITY)
            # El upload básico (extracción de texto, páginas, tamaño) siempre va primero con alta prioridad
            task_id = str(uuid.uuid4())
            upload_task = DocumentTask.objects.create(
                task_id=task_id,
                document=document,
                task_type=TaskType.UPLOAD,
                status=TaskStatus.PENDING,
                priority=1,  # SIEMPRE alta prioridad para metadatos básicos
                progress_message="En cola para procesamiento..."
            )
            
            # Send to Celery HIGH PRIORITY queue (basic metadata extraction)
            celery_task = process_document_upload.apply_async(
                args=[str(document.document_id), task_id],
                task_id=task_id,
                queue='high_priority'  # SIEMPRE alta prioridad
            )
            
            logger.info(f"Upload task queued: {task_id} (HIGH PRIORITY)")
            
            # If analysis is requested, queue it to run AFTER upload completes
            analysis_task_data = None
            if has_analysis_request:
                parts = []
                if analyze_metadata:
                    parts.append('metadata')
                if analyze_title:
                    parts.append('title')
                if analyze_summary:
                    parts.append('summary')
                if analyze_persons:
                    parts.append('persons')
                
                analysis_task_id = str(uuid.uuid4())
                analysis_task = DocumentTask.objects.create(
                    task_id=analysis_task_id,
                    document=document,
                    task_type=TaskType.ANALYSIS_FULL if len(parts) == 4 else (
                        TaskType.ANALYSIS_METADATA if parts == ['metadata'] else
                        TaskType.ANALYSIS_TITLE if parts == ['title'] else
                        TaskType.ANALYSIS_SUMMARY if parts == ['summary'] else
                        TaskType.ANALYSIS_PERSONS if parts == ['persons'] else
                        TaskType.ANALYSIS_FULL
                    ),
                    status=TaskStatus.PENDING,
                    priority=5,  # Prioridad normal para análisis
                    analysis_parts=parts,
                    summarizer_type=summarizer_type if analyze_summary else None,
                    progress_message="Esperando a que termine la carga básica..."
                )
                
                # Queue analysis task to run AFTER upload completes (using Celery chain)
                # Esto asegura que primero se procese el upload con alta prioridad
                # y luego el análisis con prioridad normal
                
                # Create a chain: upload -> analysis
                # Usamos .si() (immutable signature) para que no pase el resultado
                chain_result = chain(
                    process_document_upload.si(
                        str(document.document_id), 
                        task_id
                    ).set(task_id=task_id, queue='high_priority'),
                    process_document_analysis.si(
                        str(document.document_id), 
                        analysis_task_id, 
                        parts,
                        summarizer_type
                    ).set(task_id=analysis_task_id, queue='default')
                ).apply_async()
                
                logger.info(f"Analysis task queued to run after upload: {analysis_task_id}")
                
                analysis_task_data = DocumentTaskSerializer(analysis_task).data
            else:
                # No analysis requested, just run upload task
                celery_task = process_document_upload.apply_async(
                    args=[str(document.document_id), task_id],
                    task_id=task_id,
                    queue='high_priority'
                )
            
            # Return document and task info
            document.refresh_from_db()
            output_serializer = DocumentSerializer(document)
            
            return Response({
                'document': output_serializer.data,
                'upload_task': DocumentTaskSerializer(upload_task).data,
                'analysis_task': analysis_task_data,
                'message': 'Documento en cola para procesamiento'
            }, status=status.HTTP_202_ACCEPTED)  # 202 = Accepted (async)
                
        except Exception as e:
            logger.error(f"Error creating document: {e}", exc_info=True)
            return Response(
                {'error': f'Error creating document: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def bulk_upload(self, request):
        """
        Upload multiple documents at once and queue them for processing.
        
        Body parameters:
        - files: List of files to upload (max 10)
        - analyze_metadata: Boolean (default: False)
        - analyze_title: Boolean (default: False)
        - analyze_summary: Boolean (default: False)
        - analyze_persons: Boolean (default: False)
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        files = serializer.validated_data['files']
        analyze_metadata = serializer.validated_data.get('analyze_metadata', False)
        analyze_title = serializer.validated_data.get('analyze_title', False)
        analyze_summary = serializer.validated_data.get('analyze_summary', False)
        analyze_persons = serializer.validated_data.get('analyze_persons', False)
        summarizer_type = serializer.validated_data.get('summarizer_type', 'ollama')
        
        has_analysis_request = analyze_metadata or analyze_title or analyze_summary or analyze_persons
        
        # Prepare analysis parts
        parts = []
        if analyze_metadata:
            parts.append('metadata')
        if analyze_title:
            parts.append('title')
        if analyze_summary:
            parts.append('summary')
        if analyze_persons:
            parts.append('persons')
        
        # Create documents and queue tasks
        results = []
        errors = []
        upload_tasks = []
        analysis_tasks = []
        
        for file in files:
            try:
                # Create document
                document = Document.objects.create(
                    file_path=file,
                    title=file.name,
                    status=DocumentStatus.PROCESSING
                )
                
                logger.info(f"Document created: {document.document_id} ({file.name})")
                
                # Create upload task (ALWAYS HIGH PRIORITY for basic metadata)
                task_id = str(uuid.uuid4())
                upload_task = DocumentTask.objects.create(
                    task_id=task_id,
                    document=document,
                    task_type=TaskType.UPLOAD,
                    status=TaskStatus.PENDING,
                    priority=1,  # SIEMPRE alta prioridad para metadatos básicos
                    progress_message="En cola para procesamiento..."
                )
                
                upload_tasks.append(DocumentTaskSerializer(upload_task).data)
                
                # If analysis requested, create analysis task to run AFTER upload
                if has_analysis_request:
                    analysis_task_id = str(uuid.uuid4())
                    analysis_task = DocumentTask.objects.create(
                        task_id=analysis_task_id,
                        document=document,
                        task_type=TaskType.ANALYSIS_FULL if len(parts) == 4 else (
                            TaskType.ANALYSIS_METADATA if parts == ['metadata'] else
                            TaskType.ANALYSIS_TITLE if parts == ['title'] else
                            TaskType.ANALYSIS_SUMMARY if parts == ['summary'] else
                            TaskType.ANALYSIS_PERSONS if parts == ['persons'] else
                            TaskType.ANALYSIS_FULL
                        ),
                        status=TaskStatus.PENDING,
                        priority=5,  # Prioridad normal para análisis
                        analysis_parts=parts,
                        summarizer_type=summarizer_type if analyze_summary else None,
                        progress_message="Esperando a que termine la carga básica..."
                    )
                    
                    # Queue tasks in chain: upload (high priority) -> analysis (normal priority)
                    # Usamos .si() (immutable signature) para que no pase el resultado
                    
                    chain_result = chain(
                        process_document_upload.si(
                            str(document.document_id), 
                            task_id
                        ).set(task_id=task_id, queue='high_priority'),
                        process_document_analysis.si(
                            str(document.document_id), 
                            analysis_task_id, 
                            parts,
                            summarizer_type
                        ).set(task_id=analysis_task_id, queue='default')
                    ).apply_async()
                    
                    logger.info(f"Chained tasks queued for {file.name}: upload ({task_id}) -> analysis ({analysis_task_id})")
                    
                    analysis_tasks.append(DocumentTaskSerializer(analysis_task).data)
                else:
                    # No analysis, just queue upload task with high priority
                    celery_task = process_document_upload.apply_async(
                        args=[str(document.document_id), task_id],
                        task_id=task_id,
                        queue='high_priority'
                    )
                    
                    logger.info(f"Upload task queued: {task_id} for {file.name} (HIGH PRIORITY)")
                
                # Add document to results
                serializer = DocumentSerializer(document)
                results.append(serializer.data)
                
            except Exception as e:
                logger.error(f"Error creating document for {file.name}: {e}", exc_info=True)
                errors.append({
                    'file': file.name,
                    'error': str(e)
                })
        
        return Response({
            'total_uploaded': len(results),
            'total_errors': len(errors),
            'documents': results,
            'upload_tasks': upload_tasks,
            'analysis_tasks': analysis_tasks,
            'errors': errors,
            'message': f'{len(results)} documentos en cola para procesamiento'
        }, status=status.HTTP_202_ACCEPTED if results else status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def analyze(self, request, pk=None):
        """
        Queue analysis of specific parts of a document.
        
        Body parameters:
        - parts: List of parts to analyze ['metadata', 'title', 'summary', 'persons']
        - summarizer_type: 'ollama' (default) or 'bart' (only used if 'summary' in parts)
        
        Example:
        POST /api/documents/{id}/analyze/
        {
            "parts": ["metadata", "title", "summary"],
            "summarizer_type": "bart"
        }
        """
        document = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        parts = serializer.validated_data['parts']
        summarizer_type = serializer.validated_data.get('summarizer_type', 'ollama')
        
        if not document.content:
            return Response(
                {'error': 'El documento no tiene contenido extraído'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Create analysis task
            analysis_task_id = str(uuid.uuid4())
            analysis_task = DocumentTask.objects.create(
                task_id=analysis_task_id,
                document=document,
                task_type=TaskType.ANALYSIS_FULL if len(parts) == 4 else (
                    TaskType.ANALYSIS_METADATA if parts == ['metadata'] else
                    TaskType.ANALYSIS_TITLE if parts == ['title'] else
                    TaskType.ANALYSIS_SUMMARY if parts == ['summary'] else
                    TaskType.ANALYSIS_PERSONS if parts == ['persons'] else
                    TaskType.ANALYSIS_FULL
                ),
                status=TaskStatus.PENDING,
                priority=5,
                analysis_parts=parts,
                summarizer_type=summarizer_type if 'summary' in parts else None,
                progress_message="En cola para análisis..."
            )
            
            # Queue analysis task with summarizer_type
            celery_task = process_document_analysis.apply_async(
                args=[str(document.document_id), analysis_task_id, parts, summarizer_type],
                task_id=analysis_task_id,
                queue='default'
            )
            
            logger.info(
                f"Analysis task queued: {analysis_task_id} for document {document.document_id} "
                f"(summarizer: {summarizer_type})"
            )
            
            # Refresh document
            document.refresh_from_db()
            output_serializer = DocumentSerializer(document)
            
            return Response({
                'message': f'Análisis en cola para procesamiento (resumen: {summarizer_type})',
                'analysis_task': DocumentTaskSerializer(analysis_task).data,
                'document': output_serializer.data
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            logger.error(f"Error queuing analysis for document {pk}: {e}", exc_info=True)
            return Response(
                {'error': f'Error al encolar análisis: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        """Reprocess a document to update classification"""
        document = self.get_object()
        
        if document.status == DocumentStatus.PROCESSING:
            return Response(
                {'error': 'Document is already being processed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        processor = DocumentProcessingService()
        success = processor.process_document(document)
        
        if success:
            serializer = DocumentSerializer(document)
            return Response({
                'message': 'Document reprocessed successfully',
                'document': serializer.data
            })
        else:
            return Response(
                {'error': 'Reprocessing failed'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def chunks(self, request, pk=None):
        """Get all chunks for a document"""
        document = self.get_object()
        
        # Get chunks ordered by their position in the document
        chunks = document.chunks.all().order_by('order_number')
        
        serializer = DocumentChunkSerializer(chunks, many=True)
        return Response({
            'document_id': str(document.document_id),
            'total_chunks': chunks.count(),
            'chunks': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def similar(self, request, pk=None):
        """
        Find similar documents using embeddings and cosine similarity.
        
        Query parameters:
        - top_n: Number of similar documents to return (default: 3)
        - min_similarity: Minimum similarity score 0-1 (default: 0.0)
        - filter_by: 'area' or 'type' to filter by same legal area or document type
        - use_hybrid: 'true' or 'false' to use hybrid scoring (default: true)
        - embedding_field: 'clean_embedding' or 'enhanced_embedding' (default: clean_embedding)
        """
        document = self.get_object()
        
        # Get query parameters
        top_n = int(request.query_params.get('top_n', 3))
        min_similarity = float(request.query_params.get('min_similarity', 0.0))
        filter_by = request.query_params.get('filter_by', None)
        use_hybrid = request.query_params.get('use_hybrid', 'true').lower() == 'true'
        embedding_field = request.query_params.get('embedding_field', 'clean_embedding')
        
        # Validate parameters
        top_n = max(1, min(top_n, 10))  # Limit between 1 and 10
        min_similarity = max(0.0, min(min_similarity, 1.0))  # Between 0 and 1
        if embedding_field not in ('clean_embedding', 'enhanced_embedding'):
            embedding_field = 'clean_embedding'
        
        # Find similar documents
        if filter_by == 'area':
            similar_docs = DocumentSimilarityService.find_similar_by_area(
                document_id=str(document.document_id),
                top_n=top_n,
                min_similarity=min_similarity,
                use_hybrid_scoring=use_hybrid,
                embedding_field=embedding_field
            )
        elif filter_by == 'type':
            similar_docs = DocumentSimilarityService.find_similar_by_document_type(
                document_id=str(document.document_id),
                top_n=top_n,
                min_similarity=min_similarity,
                use_hybrid_scoring=use_hybrid,
                embedding_field=embedding_field
            )
        else:
            similar_docs = DocumentSimilarityService.find_similar_documents(
                document_id=str(document.document_id),
                top_n=top_n,
                min_similarity=min_similarity,
                use_hybrid_scoring=use_hybrid,
                embedding_field=embedding_field
            )
        
        # Serialize results with similarity scores and reasons
        results = []
        for doc, hybrid_score, reasons in similar_docs:
            # Agregar atributos dinámicos al documento
            doc.similarity_score = reasons.get('semantic_similarity', 0.0)
            doc.semantic_score = reasons.get('semantic_similarity', 0.0)
            doc.hybrid_score = hybrid_score
            doc.raw_hybrid_score = reasons.get('raw_hybrid_score', hybrid_score)
            doc.bm25_score = reasons.get('bm25_score', 0.0)
            doc.metadata_boost = reasons.get('metadata_boost', 0.0)
            doc.penalties = reasons.get('penalties', 0.0)
            doc.similarity_reasons = reasons.get('reasons', [])
            doc.score_breakdown = reasons.get('score_breakdown', {})
            
            serializer = DocumentSimilaritySerializer(doc)
            results.append(serializer.data)
        
        return Response({
            'document_id': str(document.document_id),
            'total_similar': len(results),
            'use_hybrid_scoring': use_hybrid,
            'embedding_field': embedding_field,
            'min_semantic_threshold': 0.65,  # Informar threshold aplicado
            'similar_documents': results
        })
    
    @action(detail=True, methods=['get'])
    def cluster(self, request, pk=None):
        """
        Get document cluster using DBSCAN algorithm.
        Returns force-directed graph data with nodes and links.
        
        Query parameters:
        - max_neighbors: Maximum number of neighbors to include (default: 20)
        - eps: DBSCAN epsilon parameter - max distance (default: 0.3)
        - min_samples: DBSCAN min_samples parameter (default: 2)
        - embedding_field: 'clean_embedding' or 'enhanced_embedding' (default: clean_embedding)
        """
        from apps.documents.services.clustering_service import ClusteringService
        
        document = self.get_object()
        
        # Get query parameters
        max_neighbors = int(request.query_params.get('max_neighbors', 20))
        eps = request.query_params.get('eps', None)
        min_samples = request.query_params.get('min_samples', None)
        embedding_field = request.query_params.get('embedding_field', 'clean_embedding')
        
        # Validate parameters
        max_neighbors = max(5, min(max_neighbors, 50))
        if eps is not None:
            eps = float(eps)
            eps = max(0.1, min(eps, 0.9))
        if min_samples is not None:
            min_samples = int(min_samples)
            min_samples = max(2, min(min_samples, 10))
        
        # Validate embedding field
        if embedding_field not in ('clean_embedding', 'enhanced_embedding'):
            embedding_field = 'clean_embedding'
        
        # Get cluster data
        clustering_service = ClusteringService()
        cluster_data = clustering_service.get_document_cluster(
            document_id=str(document.document_id),
            max_neighbors=max_neighbors,
            eps=eps,
            min_samples=min_samples,
            embedding_field=embedding_field
        )
        
        # Get statistics
        if cluster_data.get('nodes'):
            stats = clustering_service.get_cluster_statistics(cluster_data)
        else:
            stats = {}
        
        return Response({
            **cluster_data,
            'statistics': stats,
            'parameters': {
                'max_neighbors': max_neighbors,
                'eps': eps,
                'min_samples': min_samples,
                'embedding_field': embedding_field
            }
        })
    
    @action(detail=False, methods=['get'])
    def all_clusters(self, request):
        """
        Get all document clusters from the precomputed cluster graph.
        Returns force-directed graph data with all nodes, links and cluster statistics.
        
        ⚡ NEW ARCHITECTURE: This endpoint serves PRECOMPUTED data for instant loading.
        The cluster graph is computed nightly by a batch job.
        
        Query parameters:
        - graph_id: Specific graph to load (default: active graph)
        - include_edges: Include KNN edges for "Connected Mode" (default: false)
        - cluster_filter: Comma-separated list of cluster IDs to show (default: all)
        - top_k: Keep only top-k strongest edges per node (default: 5, range: 1-20)
        
        Example:
        - /api/documents/all_clusters/
        - /api/documents/all_clusters/?include_edges=true
        - /api/documents/all_clusters/?cluster_filter=0,1,2
        - /api/documents/all_clusters/?include_edges=true&top_k=3
        """
        from apps.documents.services.clustering_service_new import ClusteringService
        
        # Get query parameters
        graph_id = request.query_params.get('graph_id', None)
        include_edges = request.query_params.get('include_edges', 'true').lower() == 'true'  # Changed default to 'true'
        cluster_filter_str = request.query_params.get('cluster_filter', None)
        top_k = int(request.query_params.get('top_k', 5))  # Default: keep 5 strongest edges per node
        
        # Validate top_k
        top_k = max(1, min(top_k, 20))  # Clamp between 1 and 20
        
        # Parse cluster filter
        cluster_filter = None
        if cluster_filter_str:
            try:
                cluster_filter = [int(c.strip()) for c in cluster_filter_str.split(',')]
            except ValueError:
                return Response(
                    {'error': 'cluster_filter must be comma-separated integers'},
                    status=400
                )
        
        # Convert graph_id to int
        if graph_id:
            try:
                graph_id = int(graph_id)
            except ValueError:
                return Response(
                    {'error': 'graph_id must be an integer'},
                    status=400
                )
        
        # Get cached clusters
        clustering_service = ClusteringService()
        cluster_data = clustering_service.get_cached_clusters(
            graph_id=graph_id,
            include_edges=include_edges,
            cluster_filter=cluster_filter,
            top_k=top_k  # Pass top_k to service
        )
        
        return Response(cluster_data)
    
    @action(detail=False, methods=['post'])
    def regenerate_clusters(self, request):
        """
        Manually trigger cluster graph regeneration.
        
        🔄 This is triggered by the "Recargar" button in the frontend.
        The clustering is now MANUAL only - no longer auto-triggered on document upload.
        
        Request body (all optional):
        - max_documents: Maximum documents to include (default: 1000)
        - use_clean_embedding: Use clean_embedding field (768D) - RECOMENDADO (default: true)
        - use_enhanced_embedding: Use enhanced_embedding field (384D) (default: false)
        - algorithm: 'hdbscan' or 'dbscan' (default: 'hdbscan')
        
        Returns:
        - task_id: Celery task ID to track progress
        - estimated_time: Estimated computation time in seconds
        
        Example:
        POST /api/documents/regenerate_clusters/
        {
            "max_documents": 1000,
            "use_clean_embedding": true,
            "algorithm": "hdbscan"
        }
        """
        from apps.documents.tasks import compute_cluster_graph
        
        # Get parameters from request body
        max_documents = request.data.get('max_documents', 1000)
        use_clean_embedding = request.data.get('use_clean_embedding', True)
        use_enhanced_embedding = request.data.get('use_enhanced_embedding', False)
        algorithm = request.data.get('algorithm', 'hdbscan').lower()
        
        # Validate parameters
        try:
            max_documents = int(max_documents)
            if max_documents < 1:
                return Response(
                    {'error': 'max_documents must be >= 1'},
                    status=400
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'max_documents must be an integer'},
                status=400
            )
        
        if algorithm not in ['hdbscan', 'dbscan']:
            return Response(
                {'error': 'algorithm must be "hdbscan" or "dbscan"'},
                status=400
            )
        
        # Queue the cluster computation task with proper KNN parameters
        task = compute_cluster_graph.apply_async(
            kwargs={
                'max_documents': max_documents,
                'use_clean_embedding': use_clean_embedding,
                'use_enhanced_embedding': use_enhanced_embedding,
                'algorithm': algorithm,
                'knn_k': 20,  # Use k=20 to match current active graph
                'knn_min_similarity': 0.3
            },
            priority=5  # High priority - user-initiated
        )
        
        # Estimate computation time based on document count
        from apps.documents.models import Document
        # Use clean_embedding count if that's what we're using
        if use_clean_embedding:
            doc_count = Document.objects.exclude(clean_embedding__isnull=True).count()
        else:
            doc_count = Document.objects.exclude(enhanced_embedding__isnull=True).count()
        doc_count = min(doc_count, max_documents)
        estimated_time = max(10, int(doc_count * 0.03))  # ~0.03 seconds per doc
        
        embedding_type = 'clean_embedding (768D)' if use_clean_embedding else 'enhanced_embedding (384D)'
        logger.info(f"🔄 Manual cluster regeneration triggered: task_id={task.id}, docs={doc_count}, algorithm={algorithm}, embedding={embedding_type}")
        
        return Response({
            'status': 'queued',
            'task_id': task.id,
            'estimated_time_seconds': estimated_time,
            'document_count': doc_count,
            'algorithm': algorithm,
            'message': f'Cluster regeneration queued. Estimated time: {estimated_time}s for {doc_count} documents.'
        })
    
    @action(detail=True, methods=['get'])
    def neighbors(self, request, pk=None):
        """
        Get KNN neighbors of a specific document from the precomputed graph.
        
        ⚡ For "Connected Mode" in the frontend: click a node → see its neighbors.
        
        Query parameters:
        - max_neighbors: Maximum neighbors to return (default: 10)
        - graph_id: Specific graph to use (default: active graph)
        
        Example:
        - /api/documents/{doc_id}/neighbors/
        - /api/documents/{doc_id}/neighbors/?max_neighbors=5
        """
        from apps.documents.services.clustering_service_new import ClusteringService
        
        document = self.get_object()
        
        # Get query parameters
        max_neighbors = int(request.query_params.get('max_neighbors', 10))
        graph_id = request.query_params.get('graph_id', None)
        
        # Validate
        max_neighbors = max(1, min(max_neighbors, 50))
        
        if graph_id:
            try:
                graph_id = int(graph_id)
            except ValueError:
                return Response(
                    {'error': 'graph_id must be an integer'},
                    status=400
                )
        
        # Get neighbors
        clustering_service = ClusteringService()
        neighbors_data = clustering_service.get_document_neighbors(
            document_id=str(document.document_id),
            graph_id=graph_id,
            max_neighbors=max_neighbors
        )
        
        return Response(neighbors_data)
    
    @action(detail=False, methods=['get'])
    def cluster_documents(self, request):
        """
        Get detailed documents from a specific cluster.
        
        Query parameters:
        - cluster_id: ID of the cluster (required)
        - algorithm: Clustering algorithm used (default: 'dbscan')
        - metric: Distance metric used (default: 'cosine')
        - n_clusters: Number of clusters for kmeans/agglomerative (default: 5)
        - eps: DBSCAN epsilon parameter (default: 0.05)
        - min_samples: DBSCAN/HDBSCAN min_samples parameter (default: 2)
        - min_cluster_size: Minimum cluster size (default: 2)
        - max_documents: Maximum documents to process (default: 200)
        
        Returns:
        - List of documents in the specified cluster with full details
        """
        from apps.documents.services.clustering_service import ClusteringService
        
        # Get cluster_id from query params
        cluster_id = request.query_params.get('cluster_id', None)
        
        if cluster_id is None:
            return Response(
                {'error': 'cluster_id is required'},
                status=400
            )
        
        try:
            cluster_id = int(cluster_id)
        except ValueError:
            return Response(
                {'error': 'cluster_id must be an integer'},
                status=400
            )
        
        # Get other parameters (same as all_clusters)
        algorithm = request.query_params.get('algorithm', 'dbscan').lower()
        metric = request.query_params.get('metric', 'cosine').lower()
        n_clusters = request.query_params.get('n_clusters', None)
        eps = request.query_params.get('eps', None)
        min_samples = request.query_params.get('min_samples', None)
        min_cluster_size = int(request.query_params.get('min_cluster_size', 2))
        max_documents = int(request.query_params.get('max_documents', 200))
        use_enhanced_embedding = request.query_params.get('use_enhanced_embedding', 'false').lower() == 'true'
        
        # Validate parameters
        if algorithm not in ['dbscan', 'hdbscan', 'kmeans', 'agglomerative']:
            algorithm = 'dbscan'
        
        if metric not in ['cosine', 'euclidean', 'manhattan']:
            metric = 'cosine'
        
        if n_clusters is not None:
            n_clusters = int(n_clusters)
            n_clusters = max(2, min(n_clusters, 20))
        else:
            n_clusters = 5
        
        if eps is not None:
            eps = float(eps)
            eps = max(0.001, min(eps, 0.9))
        if min_samples is not None:
            min_samples = int(min_samples)
            min_samples = max(1, min(min_samples, 20))
        
        min_cluster_size = max(1, min(min_cluster_size, 20))
        max_documents = max(10, min(max_documents, 1000))
        
        # Get all clusters with the same parameters
        clustering_service = ClusteringService()
        cluster_data = clustering_service.get_all_clusters(
            algorithm=algorithm,
            metric=metric,
            n_clusters=n_clusters,
            eps=eps,
            min_samples=min_samples,
            min_cluster_size=min_cluster_size,
            max_documents=max_documents,
            use_enhanced_embedding=use_enhanced_embedding
        )
        
        # Get document IDs for the specified cluster
        clusters = cluster_data.get('clusters', {})
        document_ids = clusters.get(cluster_id, [])
        
        if not document_ids:
            return Response({
                'cluster_id': cluster_id,
                'documents': [],
                'count': 0,
                'message': 'No documents found in this cluster'
            })
        
        # Fetch full document details
        documents = Document.objects.filter(
            document_id__in=document_ids
        ).prefetch_related(
            'document_persons__person',
            'legal_area',
            'doc_type'
        ).order_by('-created_at')
        
        # Serialize documents
        from apps.documents.serializers import DocumentSerializer
        serializer = DocumentSerializer(documents, many=True)
        
        # Calculate similarity if a reference document is provided
        reference_doc_id = request.query_params.get('reference_doc_id', None)
        # Convert to list of dicts (mutable) to add similarity field
        documents_with_similarity = list(serializer.data)
        
        if reference_doc_id:
            logger.info(f"Calculating similarity for reference document: {reference_doc_id}")
            try:
                # Get reference document
                reference_doc = Document.objects.get(document_id=reference_doc_id)
                logger.info(f"Found reference document: {reference_doc.title}")
                
                # Determine which embedding to use
                embedding_field = 'enhanced_embedding' if use_enhanced_embedding else 'summary_embedding'
                reference_embedding = getattr(reference_doc, embedding_field)
                
                logger.info(f"Using embedding field: {embedding_field}")
                logger.info(f"Reference embedding exists: {reference_embedding is not None}")
                
                if reference_embedding is not None and len(reference_embedding) > 0:
                    import numpy as np
                    from sklearn.metrics.pairwise import cosine_similarity
                    
                    reference_emb = np.array(reference_embedding).reshape(1, -1)
                    logger.info(f"Reference embedding shape: {reference_emb.shape}")
                    
                    # Create a dict for quick lookup
                    docs_dict = {str(doc.document_id): doc for doc in documents}
                    logger.info(f"Created docs dict with {len(docs_dict)} documents")
                    
                    # Calculate similarity for each document
                    similarities_calculated = 0
                    for idx, doc_data in enumerate(documents_with_similarity):
                        # El serializer usa 'document_id' no 'id'
                        doc_id = str(doc_data.get('document_id') or doc_data.get('id', ''))
                        
                        if doc_id and doc_id in docs_dict:
                            doc = docs_dict[doc_id]
                            doc_embedding = getattr(doc, embedding_field)
                            
                            if doc_embedding is not None and len(doc_embedding) > 0 and doc_id != str(reference_doc_id):
                                doc_emb = np.array(doc_embedding).reshape(1, -1)
                                similarity = cosine_similarity(reference_emb, doc_emb)[0][0]
                                # Ensure we're modifying the dict directly
                                documents_with_similarity[idx]['similarity'] = float(similarity)
                                similarities_calculated += 1
                            elif doc_id == str(reference_doc_id):
                                documents_with_similarity[idx]['similarity'] = 1.0
                                similarities_calculated += 1
                            else:
                                documents_with_similarity[idx]['similarity'] = 0.0
                        else:
                            documents_with_similarity[idx]['similarity'] = 0.0
                    
                    logger.info(f"Calculated similarity for {similarities_calculated} documents")
                else:
                    logger.warning(f"Reference document has no {embedding_field}")
                            
            except Document.DoesNotExist:
                logger.error(f"Reference document not found: {reference_doc_id}")
                pass  # Reference document not found, return without similarity
            except Exception as e:
                # Log the error but continue without similarity
                logger.error(f"Error calculating similarity: {e}", exc_info=True)
        
        # Log a sample document to verify similarity was added
        if documents_with_similarity and len(documents_with_similarity) > 0:
            logger.info(f"Sample document before response: {documents_with_similarity[0]}")
            logger.info(f"Has 'similarity' key: {'similarity' in documents_with_similarity[0]}")
        
        return Response({
            'cluster_id': cluster_id,
            'documents': documents_with_similarity,
            'count': len(documents_with_similarity),
            'parameters': cluster_data.get('parameters', {}),
            'has_similarity': reference_doc_id is not None
        })
    
    @action(detail=False, methods=['post'])
    def advanced_search(self, request):
        """
        Advanced search combining filters and semantic search.
        
        Body parameters:
        - query: Text query for semantic search (optional)
        - case_number: Filter by case number (optional)
        - resolution_number: Filter by resolution number (optional)
        - legal_area_id: Filter by legal area ID (optional)
        - doc_type_id: Filter by document type ID (optional)
        - issue_place: Filter by issue place (optional)
        - date_from: Filter from date YYYY-MM-DD (optional)
        - date_to: Filter to date YYYY-MM-DD (optional)
        - semantic_search: Enable semantic search (default: true)
        - top_n: Maximum number of results (default: 20)
        - min_similarity: Minimum similarity for semantic search (default: 0.3)
        """
        # Get search parameters
        query = request.data.get('query', None)
        case_number = request.data.get('case_number', None)
        resolution_number = request.data.get('resolution_number', None)
        legal_area_id = request.data.get('legal_area_id', None)
        doc_type_id = request.data.get('doc_type_id', None)
        issue_place = request.data.get('issue_place', None)
        date_from = request.data.get('date_from', None)
        date_to = request.data.get('date_to', None)
        semantic_search = request.data.get('semantic_search', True)
        top_n = int(request.data.get('top_n', 20))
        min_similarity = float(request.data.get('min_similarity', 0.3))
        
        # Validate parameters
        top_n = max(1, min(top_n, 100))  # Limit between 1 and 100
        min_similarity = max(0.0, min(min_similarity, 1.0))
        
        # Perform search
        search_service = DocumentSearchService()
        results = search_service.search(
            query=query,
            case_number=case_number,
            resolution_number=resolution_number,
            legal_area_id=legal_area_id,
            doc_type_id=doc_type_id,
            issue_place=issue_place,
            date_from=date_from,
            date_to=date_to,
            semantic_search=semantic_search,
            top_n=top_n,
            min_similarity=min_similarity
        )
        
        # Serialize results with similarity scores
        serialized_results = []
        for doc, score in results:
            doc.similarity_score = score  # Add score as attribute
            serializer = DocumentSearchResultSerializer(doc)
            serialized_results.append(serializer.data)
        
        return Response({
            'total_results': len(serialized_results),
            'results': serialized_results,
            'search_params': {
                'query': query,
                'semantic_search': semantic_search,
                'filters_applied': {
                    'case_number': case_number,
                    'resolution_number': resolution_number,
                    'legal_area_id': legal_area_id,
                    'doc_type_id': doc_type_id,
                    'issue_place': issue_place,
                    'date_from': date_from,
                    'date_to': date_to,
                }
            }
        })
    
    @action(detail=False, methods=['post'])
    def semantic_search(self, request):
        """
        Pure semantic search using embeddings.
        
        Searches for documents similar to a text query using clean_embedding.
        
        Body parameters:
        - query: Text query to search for (required)
        - top_n: Maximum number of results (default: 10, max: 50)
        - min_similarity: Minimum similarity score 0-1 (default: 0.0)
        - embedding_field: 'clean_embedding' or 'enhanced_embedding' (default: clean_embedding)
        - legal_area_id: Filter by legal area (optional)
        - doc_type_id: Filter by document type (optional)
        """
        query = request.data.get('query', '').strip()
        if not query:
            return Response(
                {'error': 'Query text is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get parameters
        top_n = int(request.data.get('top_n', 10))
        min_similarity = float(request.data.get('min_similarity', 0.0))
        embedding_field = request.data.get('embedding_field', 'clean_embedding')
        legal_area_id = request.data.get('legal_area_id')
        doc_type_id = request.data.get('doc_type_id')
        
        # Validate parameters
        top_n = max(1, min(top_n, 50))
        min_similarity = max(0.0, min(min_similarity, 1.0))
        if embedding_field not in ('clean_embedding', 'enhanced_embedding'):
            embedding_field = 'clean_embedding'
        
        try:
            # Use the similarity service for text-based search
            results = DocumentSimilarityService.find_similar_by_text(
                query_text=query,
                top_n=top_n,
                min_similarity=min_similarity,
                embedding_field=embedding_field,
                legal_area_id=legal_area_id,
                doc_type_id=doc_type_id
            )
            
            # Serialize results
            serialized_results = []
            for doc, score in results:
                doc.similarity_score = score
                serializer = DocumentSearchResultSerializer(doc)
                serialized_results.append(serializer.data)
            
            return Response({
                'total_results': len(serialized_results),
                'results': serialized_results,
                'search_params': {
                    'query': query,
                    'top_n': top_n,
                    'min_similarity': min_similarity,
                    'embedding_field': embedding_field,
                    'legal_area_id': legal_area_id,
                    'doc_type_id': doc_type_id
                }
            })
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def search_filters(self, request):
        """
        Get available filter options for advanced search.
        
        Returns:
        - legal_areas: List of available legal areas
        - doc_types: List of available document types
        """
        search_service = DocumentSearchService()
        filters = search_service.get_available_filters()
        
        return Response(filters)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get comprehensive statistics about documents.
        
        Example: GET /api/documents/statistics/
        """
        from django.db.models import Count, Avg, Sum, Q, Max, Min
        from django.db.models.functions import TruncDate, TruncMonth
        from datetime import timedelta
        from django.utils import timezone
        
        # Total documents
        total_docs = self.queryset.count()
        
        # Documents by status
        by_status = {
            'uploaded': self.queryset.filter(status=DocumentStatus.UPLOADED).count(),
            'processing': self.queryset.filter(status=DocumentStatus.PROCESSING).count(),
            'processed': self.queryset.filter(status=DocumentStatus.PROCESSED).count(),
            'partial': self.queryset.filter(status=DocumentStatus.PARTIAL).count(),
            'failed': self.queryset.filter(status=DocumentStatus.FAILED).count(),
        }
        
        # Documents by analysis status
        by_analysis = {
            'metadata_completed': self.queryset.filter(metadata_analysis_status=AnalysisStatus.COMPLETED).count(),
            'summary_completed': self.queryset.filter(summary_analysis_status=AnalysisStatus.COMPLETED).count(),
            'persons_completed': self.queryset.filter(persons_analysis_status=AnalysisStatus.COMPLETED).count(),
        }
        
        # Documents uploaded in last 7 days
        last_7days = timezone.now() - timedelta(days=7)
        docs_last_7days = self.queryset.filter(created_at__gte=last_7days)
        
        by_day = list(docs_last_7days.annotate(
            day=TruncDate('created_at')
        ).values('day').annotate(
            count=Count('document_id')
        ).order_by('day'))
        
        # Documents by month (last 6 months)
        last_6months = timezone.now() - timedelta(days=180)
        docs_last_6months = self.queryset.filter(created_at__gte=last_6months)
        
        by_month = list(docs_last_6months.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('document_id')
        ).order_by('month'))
        
        # Documents by legal area
        by_legal_area = list(self.queryset.exclude(
            legal_area__isnull=True
        ).values(
            'legal_area__name'
        ).annotate(
            count=Count('document_id')
        ).order_by('-count')[:10])
        
        # Documents by doc type
        by_doc_type = list(self.queryset.exclude(
            doc_type__isnull=True
        ).values(
            'doc_type__name'
        ).annotate(
            count=Count('document_id')
        ).order_by('-count')[:10])
        
        # Average pages
        avg_pages = self.queryset.exclude(
            pages__isnull=True
        ).aggregate(avg=Avg('pages'))['avg']
        
        # Total pages
        total_pages = self.queryset.exclude(
            pages__isnull=True
        ).aggregate(total=Sum('pages'))['total']
        
        # Average file size (in MB)
        avg_size = self.queryset.exclude(
            file_size__isnull=True
        ).aggregate(avg=Avg('file_size'))['avg']
        
        if avg_size:
            avg_size = avg_size / (1024 * 1024)  # Convert to MB
        
        # Total file size (in MB)
        total_size = self.queryset.exclude(
            file_size__isnull=True
        ).aggregate(total=Sum('file_size'))['total']
        
        if total_size:
            total_size = total_size / (1024 * 1024)  # Convert to MB
        
        # Documents with persons extracted
        docs_with_persons = self.queryset.filter(
            document_persons__isnull=False
        ).distinct().count()
        
        # Top 10 most common persons
        from .models import DocumentPerson
        top_persons = list(DocumentPerson.objects.values(
            'person__name', 'role'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:10])
        
        # Documents by issue place (top 10)
        by_place = list(self.queryset.exclude(
            issue_place__isnull=True
        ).exclude(
            issue_place__exact=''
        ).values(
            'issue_place'
        ).annotate(
            count=Count('document_id')
        ).order_by('-count')[:10])
        
        # Recent activity (last 24 hours)
        last_24h = timezone.now() - timedelta(hours=24)
        recent_uploads = self.queryset.filter(created_at__gte=last_24h).count()
        
        return Response({
            'total_documents': total_docs,
            'by_status': by_status,
            'by_analysis': by_analysis,
            'by_day': by_day,
            'by_month': by_month,
            'by_legal_area': by_legal_area,
            'by_doc_type': by_doc_type,
            'by_place': by_place,
            'avg_pages': round(avg_pages, 2) if avg_pages else 0,
            'total_pages': total_pages or 0,
            'avg_size_mb': round(avg_size, 2) if avg_size else 0,
            'total_size_mb': round(total_size, 2) if total_size else 0,
            'docs_with_persons': docs_with_persons,
            'top_persons': top_persons,
            'recent_uploads_24h': recent_uploads,
        })

    # ============================================================================
    # BERTOPIC ENDPOINTS
    # ============================================================================
    
    @action(detail=False, methods=['get'])
    def bertopic_topics(self, request):
        """
        Get BERTopic topics from the active model.
        
        Returns topic modeling results with:
        - nodes: Documents with 2D coordinates and topic assignments
        - topics: Topic info with keywords and document counts
        - links: KNN edges between documents (if include_edges=true)
        - topic_stats: Statistics per topic (compatible with cluster_stats)
        - metadata: Model info (document count, topic count, etc.)
        
        Query parameters:
        - model_id: Specific model to use (default: active model)
        - include_outliers: Include documents without topic (default: true)
        - include_edges: Include KNN edges between documents (default: true)
        - top_k: Keep top-k strongest edges per node (default: 5, range: 1-20)
        - topic_filter: Comma-separated list of topic IDs to include
        
        Example:
        - /api/documents/bertopic_topics/
        - /api/documents/bertopic_topics/?include_outliers=false
        - /api/documents/bertopic_topics/?include_edges=true&top_k=5
        - /api/documents/bertopic_topics/?topic_filter=0,1,2,3
        """
        try:
            # 🔥 Usar servicio OPTIMIZADO
            from apps.documents.services.bertopic_service_optimized import BERTopicServiceOptimized
            
            # Get query parameters
            model_id = request.query_params.get('model_id', None)
            include_outliers = request.query_params.get('include_outliers', 'true').lower() == 'true'
            include_edges = request.query_params.get('include_edges', 'true').lower() == 'true'
            top_k = int(request.query_params.get('top_k', 5))
            topic_filter_str = request.query_params.get('topic_filter', None)
            
            # Validate top_k
            top_k = max(1, min(top_k, 20))  # Clamp between 1 and 20
            
            # Parse topic filter
            topic_filter = None
            if topic_filter_str:
                try:
                    topic_filter = [int(t.strip()) for t in topic_filter_str.split(',')]
                except ValueError:
                    return Response(
                        {'error': 'topic_filter must be comma-separated integers'},
                        status=400
                    )
            
            # Convert model_id to int
            if model_id:
                try:
                    model_id = int(model_id)
                except ValueError:
                    return Response(
                        {'error': 'model_id must be an integer'},
                        status=400
                    )
            
            # Get cached topics with optional KNN edges
            service = BERTopicServiceOptimized(require_bertopic=False)
            topics_data = service.get_cached_topics(
                model_id=model_id,
                include_outliers=include_outliers,
                topic_filter=topic_filter,
                include_edges=include_edges,
                top_k=top_k
            )
            
            return Response(topics_data)
            
        except Exception as e:
            logger.error(f"Error getting BERTopic topics: {e}", exc_info=True)
            return Response(
                {'error': str(e), 'nodes': [], 'topics': [], 'links': [], 'metadata': None},
                status=500
            )
    
    @action(detail=False, methods=['post'])
    def regenerate_bertopic(self, request):
        """
        Trigger BERTopic model regeneration.
        
        Request body (all optional):
        - max_documents: Maximum documents to include (default: 1000)
        - min_topic_size: Minimum documents per topic (default: 5)
        - nr_topics: Desired number of topics (default: auto)
        - embedding_field: Which embedding to use (default: 'clean_embedding')
        
        Returns:
        - task_id: Celery task ID to track progress
        - estimated_time: Estimated computation time
        
        Example:
        POST /api/documents/regenerate_bertopic/
        {
            "max_documents": 1000,
            "min_topic_size": 4
        }
        """
        from apps.documents.tasks import compute_bertopic_model
        from apps.documents.models import Document
        
        # Get parameters (🔥 defaults optimizados)
        max_documents = request.data.get('max_documents', 1000)
        min_topic_size = request.data.get('min_topic_size', 4)  # 🔥 Optimizado: 4 en lugar de 5
        nr_topics = request.data.get('nr_topics', None)
        embedding_field = request.data.get('embedding_field', 'clean_embedding')
        
        # Validate parameters
        try:
            max_documents = int(max_documents)
            min_topic_size = int(min_topic_size)
            if nr_topics:
                nr_topics = int(nr_topics)
        except (ValueError, TypeError) as e:
            return Response(
                {'error': f'Invalid parameter type: {e}'},
                status=400
            )
        
        if max_documents < 1:
            return Response({'error': 'max_documents must be >= 1'}, status=400)
        if min_topic_size < 2:
            return Response({'error': 'min_topic_size must be >= 2'}, status=400)
        
        # Queue the task
        task = compute_bertopic_model.apply_async(
            kwargs={
                'max_documents': max_documents,
                'min_topic_size': min_topic_size,
                'nr_topics': nr_topics,
                'embedding_field': embedding_field
            },
            priority=5
        )
        
        # Estimate time
        doc_count = Document.objects.exclude(clean_embedding__isnull=True).count()
        doc_count = min(doc_count, max_documents)
        estimated_time = max(15, int(doc_count * 0.05))  # ~0.05s per doc
        
        logger.info(f"🎯 BERTopic regeneration triggered: task_id={task.id}, docs={doc_count}")
        
        return Response({
            'status': 'queued',
            'task_id': task.id,
            'estimated_time_seconds': estimated_time,
            'document_count': doc_count,
            'message': f'BERTopic model generation queued. Estimated time: {estimated_time}s for {doc_count} documents.'
        })
    
    @action(detail=False, methods=['get'])
    def bertopic_hierarchy(self, request):
        """
        Get topic hierarchy for tree visualization.
        
        Returns hierarchical structure of topics sorted by size.
        """
        try:
            # 🔥 Usar servicio OPTIMIZADO
            from apps.documents.services.bertopic_service_optimized import BERTopicServiceOptimized
            
            model_id = request.query_params.get('model_id', None)
            if model_id:
                model_id = int(model_id)
            
            service = BERTopicServiceOptimized()
            hierarchy = service.get_topic_hierarchy(model_id=model_id)
            
            return Response(hierarchy)
            
        except Exception as e:
            logger.error(f"Error getting BERTopic hierarchy: {e}", exc_info=True)
            return Response({'error': str(e)}, status=500)
    
    @action(detail=False, methods=['get'])
    def bertopic_similarity(self, request):
        """
        Get topic similarity matrix for heatmap visualization.
        
        Returns similarity matrix between topics based on keyword overlap.
        """
        try:
            # 🔥 Usar servicio OPTIMIZADO
            from apps.documents.services.bertopic_service_optimized import BERTopicServiceOptimized
            
            model_id = request.query_params.get('model_id', None)
            if model_id:
                model_id = int(model_id)
            
            service = BERTopicServiceOptimized()
            similarity = service.get_topic_similarity_matrix(model_id=model_id)
            
            return Response(similarity)
            
        except Exception as e:
            logger.error(f"Error getting BERTopic similarity: {e}", exc_info=True)
            return Response({'error': str(e)}, status=500)
    
    @action(detail=True, methods=['get'])
    def keywords(self, request, pk=None):
        """
        Get BERTopic keywords for a specific document.
        
        Returns the topic keywords assigned to this document from the active
        BERTopic model. Keywords are extracted via c-TF-IDF and represent
        the most distinctive terms for the document's topic.
        
        Returns:
        - keywords: List of keywords for the document's topic
        - topic_id: The topic ID assigned to this document
        - topic_label: Human-readable topic label
        - probability: Confidence score for topic assignment
        - has_topic: Boolean indicating if document has a topic (not outlier)
        
        Example:
        GET /api/documents/{document_id}/keywords/
        """
        try:
            from apps.documents.models import BERTopicModel, BERTopicDocument, BERTopicTopic
            
            document = self.get_object()
            
            # Get active model
            active_model = BERTopicModel.objects.filter(is_active=True).first()
            if not active_model:
                return Response({
                    'keywords': [],
                    'topic_id': None,
                    'topic_label': None,
                    'probability': None,
                    'has_topic': False,
                    'message': 'No active BERTopic model'
                })
            
            # Get document assignment
            doc_assignment = BERTopicDocument.objects.filter(
                model=active_model,
                document=document
            ).select_related('topic').first()
            
            if not doc_assignment:
                return Response({
                    'keywords': [],
                    'topic_id': None,
                    'topic_label': None,
                    'probability': None,
                    'has_topic': False,
                    'message': 'Document not in BERTopic model'
                })
            
            # Check if outlier
            if doc_assignment.topic_id_raw == -1 or not doc_assignment.topic:
                return Response({
                    'keywords': [],
                    'topic_id': -1,
                    'topic_label': 'Sin clasificar',
                    'probability': doc_assignment.probability,
                    'has_topic': False,
                    'message': 'Document is an outlier (no specific topic)'
                })
            
            # Get topic keywords
            topic = doc_assignment.topic
            
            return Response({
                'keywords': topic.keywords[:10],  # Top 10 keywords
                'keyword_weights': topic.keyword_weights,
                'topic_id': topic.topic_id,
                'topic_label': topic.label,
                'probability': doc_assignment.probability,
                'document_count': topic.document_count,
                'has_topic': True
            })
            
        except Exception as e:
            logger.error(f"Error getting document keywords: {e}", exc_info=True)
            return Response({
                'keywords': [],
                'topic_id': None,
                'topic_label': None,
                'probability': None,
                'has_topic': False,
                'error': str(e)
            }, status=500)



