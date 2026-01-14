# documents/models.py
from django.db import models
from pgvector.django import VectorField
import uuid

class DocumentStatus(models.TextChoices):
    UPLOADED = 'uploaded', 'Subido'
    PROCESSING = 'processing', 'Procesando'
    PROCESSED = 'processed', 'Procesado'
    PARTIAL = 'partial', 'Parcialmente Procesado'
    FAILED = 'failed', 'Falló'

class AnalysisStatus(models.TextChoices):
    """Estado de cada parte del análisis"""
    PENDING = 'pending', 'Pendiente'
    PROCESSING = 'processing', 'Procesando'
    COMPLETED = 'completed', 'Completado'
    FAILED = 'failed', 'Falló'

class DocumentFileType(models.TextChoices):
    PDF = 'pdf', 'PDF'
    DOCX = 'docx', 'Word (DOCX)'
    DOC = 'doc', 'Word (DOC)'
    TXT = 'txt', 'Texto plano'
    OTHER = 'other', 'Otro'

class SummarizerType(models.TextChoices):
    """Tipos de generadores de resumen"""
    OLLAMA = 'ollama', 'Ollama (LLM)'
    OLLAMA_HIERARCHICAL = 'ollama_hierarchical', 'Ollama Jerárquico (Documento Completo)'
    BART = 'bart', 'BART (Hugging Face)'

# ============== TABLAS DE CATÁLOGO ==============

class LegalArea(models.Model):
    """Áreas legales del sistema judicial peruano"""
    area_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True, verbose_name="Nombre")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'documents_legal_area'
        ordering = ['name']
        verbose_name = 'Área Legal'
        verbose_name_plural = 'Áreas Legales'
    
    def __str__(self):
        return self.name

class DocumentType(models.Model):
    """Tipos de documentos legales"""
    type_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True, verbose_name="Nombre")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'documents_document_type'
        ordering = ['name']
        verbose_name = 'Tipo de Documento'
        verbose_name_plural = 'Tipos de Documento'
    
    def __str__(self):
        return self.name

class Person(models.Model):
    """Personas o entidades mencionadas en documentos legales (demandantes, demandados, jueces, etc.)"""
    person_id = models.AutoField(primary_key=True)
    name = models.CharField(
        max_length=255, 
        db_index=True,
        verbose_name="Nombre",
        help_text="Nombre de persona o entidad en mayúsculas sin tildes"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'documents_person'
        ordering = ['name']
        verbose_name = 'Persona/Entidad'
        verbose_name_plural = 'Personas/Entidades'
        indexes = [
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return self.name

class PersonRole(models.TextChoices):
    """Roles de personas en documentos legales"""
    PLAINTIFF = 'demandante', 'Demandante'
    DEFENDANT = 'demandado', 'Demandado'
    JUDGE = 'juez', 'Juez'
    PROSECUTOR = 'fiscal', 'Fiscal'
    LAWYER = 'abogado', 'Abogado'
    WITNESS = 'testigo', 'Testigo'
    EXPERT = 'perito', 'Perito'
    THIRD_PARTY = 'tercero', 'Tercero'
    OTHER = 'otro', 'Otro'

# ============== TABLA PRINCIPAL ==============

class Document(models.Model):
    """Documento legal principal"""
    document_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Información básica (generada por Ollama)
    title = models.CharField(max_length=255, verbose_name="Título")
    content = models.TextField(blank=True, null=True, verbose_name="Contenido Completo")
    summary = models.TextField(blank=True, null=True, verbose_name="Resumen")
    summary_embedding = VectorField(dimensions=384, blank=True, null=True)
    
    # Enhanced embedding: combina múltiples campos para mejor similitud
    # Incluye: title, legal_area, legal_subject, summary, issue_place, 
    # case_number, resolution_number, personas relacionadas
    enhanced_embedding = VectorField(
        dimensions=384, 
        blank=True, 
        null=True,
        help_text="Embedding mejorado que combina múltiples campos del documento"
    )
    
    # Clean embedding: vector representativo sobre texto LIMPIO (sin stopwords)
    # Generado con SentenceTransformers SIN depender de Ollama
    # Usado para: similaridad, clustering, búsqueda semántica
    clean_embedding = VectorField(
        dimensions=768,
        blank=True,
        null=True,
        help_text="Embedding sobre texto limpio (sin stopwords) para similaridad y clustering. Generado con SentenceTransformers sin depender de Ollama."
    )
    
    # Clasificación (ForeignKeys a tablas de catálogo)
    doc_type = models.ForeignKey(
        DocumentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents',
        verbose_name="Tipo de Documento"
    )
    legal_area = models.ForeignKey(
        LegalArea,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents',
        verbose_name="Área Legal"
    )
    
    # Campos estructurados extraídos por Ollama
    case_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Número de Expediente",
        help_text="Número de expediente o caso judicial"
    )
    resolution_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Número de Resolución",
        help_text="Número de resolución judicial (ej: 23-2025, TRES, DOSCIENTOS SETENTA Y NUEVE)"
    )
    issue_place = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Lugar de Emisión",
        help_text="Ciudad o lugar donde se emitió el documento (ej: Lima, Puno, Santa Anita)"
    )
    document_date = models.DateField(
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Fecha del Documento",
        help_text="Fecha de emisión del documento judicial"
    )
    legal_subject = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Materia del Área Legal",
        help_text="Materia específica dentro del área legal (ej: Robo Agravado, Despido Arbitrario, etc.)"
    )
    jurisdictional_body = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Órgano Jurisdiccional",
        help_text="Órgano jurisdiccional que emite o tramita el documento"
    )
    
    # Metadatos del archivo
    file_path = models.FileField(upload_to='documentos/', verbose_name="Archivo")
    file_type = models.CharField(
        max_length=10,
        choices=DocumentFileType.choices,
        default=DocumentFileType.PDF,
        verbose_name="Tipo de Archivo"
    )
    file_size = models.BigIntegerField(
        default=0,
        verbose_name="Tamaño del Archivo (bytes)"
    )
    pages = models.IntegerField(blank=True, null=True, verbose_name="Número de Páginas")
    
    # Estado del procesamiento
    status = models.CharField(
        max_length=20, 
        choices=DocumentStatus.choices, 
        default=DocumentStatus.UPLOADED,
        verbose_name="Estado"
    )
    
    # Estados de análisis modular (cada parte puede procesarse independientemente)
    metadata_analysis_status = models.CharField(
        max_length=20,
        choices=AnalysisStatus.choices,
        default=AnalysisStatus.PENDING,
        verbose_name="Estado Análisis de Metadatos"
    )
    summary_analysis_status = models.CharField(
        max_length=20,
        choices=AnalysisStatus.choices,
        default=AnalysisStatus.PENDING,
        verbose_name="Estado Análisis de Resumen"
    )
    persons_analysis_status = models.CharField(
        max_length=20,
        choices=AnalysisStatus.choices,
        default=AnalysisStatus.PENDING,
        verbose_name="Estado Análisis de Personas"
    )
    
    # Tipo de generador de resumen utilizado
    summarizer_type = models.CharField(
        max_length=20,
        choices=SummarizerType.choices,
        default=SummarizerType.OLLAMA,
        verbose_name="Tipo de Generador de Resumen",
        help_text="Motor utilizado para generar el resumen del documento"
    )
    
    error_message = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Mensaje de Error"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    processed_at = models.DateTimeField(
        blank=True, 
        null=True,
        verbose_name="Fecha de Procesamiento"
    )

    class Meta:
        db_table = 'documents_document'
        ordering = ['-created_at']
        verbose_name = 'Documento'
        verbose_name_plural = 'Documentos'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['jurisdictional_body']),
            models.Index(fields=['file_type']),
        ]
    
    def __str__(self):
        return self.title

# ============== TABLA INTERMEDIA N:N ==============

class DocumentPerson(models.Model):
    """Relación entre documentos y personas con roles"""
    id = models.AutoField(primary_key=True)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='document_persons',
        verbose_name="Documento"
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name='person_documents',
        verbose_name="Persona"
    )
    role = models.CharField(
        max_length=20,
        choices=PersonRole.choices,
        verbose_name="Rol"
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name="Es Principal",
        help_text="Marca si es demandante/demandado principal"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'documents_document_person'
        unique_together = [['document', 'person', 'role']]
        ordering = ['-is_primary', 'role', 'person__name']
        verbose_name = 'Persona en Documento'
        verbose_name_plural = 'Personas en Documentos'
        indexes = [
            models.Index(fields=['document', 'role']),
            models.Index(fields=['person', 'role']),
            models.Index(fields=['is_primary']),
        ]
    
    def __str__(self):
        return f"{self.person.name} - {self.get_role_display()} en {self.document.title}"

class DocumentChunk(models.Model):
    """
    Chunks de documentos para RAG (Retrieval Augmented Generation).
    
    Campos de embedding:
    - content_embedding (384d): Embedding legacy con modelo MiniLM
    - clean_content_embedding (768d): Embedding mejorado con modelo mpnet + texto limpio
    
    El RAG debería usar preferentemente clean_content_embedding.
    """
    document_id = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    chunk_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.IntegerField()
    content = models.TextField()
    
    # Embedding legacy (384 dimensiones) - Modelo MiniLM
    content_embedding = VectorField(dimensions=384, blank=True, null=True)
    
    # Embedding mejorado (768 dimensiones) - Modelo mpnet + texto limpio
    # Este es el preferido para RAG
    clean_content_embedding = VectorField(
        dimensions=768, 
        blank=True, 
        null=True,
        help_text='Embedding de 768d del contenido limpio (sin encabezados)'
    )

    created_at = models.DateTimeField(auto_now_add=True)
        
    class Meta:
        unique_together = ['document_id', 'order_number']
        indexes = [
            models.Index(fields=['document_id', 'order_number']),
        ]
        db_table = 'documents_documentchunk'


# ============== SISTEMA DE TAREAS ASÍNCRONAS ==============

class TaskStatus(models.TextChoices):
    """Estados de tareas Celery"""
    PENDING = 'pending', 'Pendiente'
    STARTED = 'started', 'Iniciada'
    PROGRESS = 'progress', 'En Progreso'
    SUCCESS = 'success', 'Completada'
    FAILURE = 'failure', 'Fallida'
    REVOKED = 'revoked', 'Cancelada'

class TaskType(models.TextChoices):
    """Tipos de tareas de procesamiento"""
    UPLOAD = 'upload', 'Subida y Extracción'
    ANALYSIS_METADATA = 'analysis_metadata', 'Análisis de Metadatos'
    ANALYSIS_TITLE = 'analysis_title', 'Generación de Título'
    ANALYSIS_SUMMARY = 'analysis_summary', 'Análisis de Resumen'
    ANALYSIS_PERSONS = 'analysis_persons', 'Análisis de Personas'
    ANALYSIS_FULL = 'analysis_full', 'Análisis Completo'

class DocumentTask(models.Model):
    """
    Modelo para tracking de tareas Celery relacionadas con documentos.
    Permite visualizar el estado y progreso de procesamiento en tiempo real.
    """
    task_id = models.CharField(
        max_length=255,
        primary_key=True,
        verbose_name="ID de Tarea Celery"
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name="Documento"
    )
    task_type = models.CharField(
        max_length=50,
        choices=TaskType.choices,
        verbose_name="Tipo de Tarea"
    )
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.PENDING,
        verbose_name="Estado"
    )
    priority = models.IntegerField(
        default=5,
        verbose_name="Prioridad",
        help_text="1 = Alta prioridad, 10 = Baja prioridad"
    )
    
    # Información de progreso
    progress_percent = models.IntegerField(
        default=0,
        verbose_name="Progreso (%)"
    )
    progress_message = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Mensaje de Progreso"
    )
    
    # Partes a analizar (para tareas de análisis)
    analysis_parts = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Partes a Analizar",
        help_text="Lista de partes: ['metadata', 'summary', 'persons']"
    )
    
    # Configuración de análisis
    summarizer_type = models.CharField(
        max_length=20,
        choices=SummarizerType.choices,
        blank=True,
        null=True,
        verbose_name="Tipo de Generador de Resumen",
        help_text="Motor a utilizar para generar resumen: ollama o bart"
    )
    
    # Resultados y errores
    result = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Resultado"
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name="Mensaje de Error"
    )
    traceback = models.TextField(
        blank=True,
        null=True,
        verbose_name="Traceback"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creada"
    )
    started_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Iniciada"
    )
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Completada"
    )
    
    # Worker info
    worker_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Worker"
    )
    
    class Meta:
        db_table = 'documents_task'
        ordering = ['-created_at']
        verbose_name = 'Tarea de Documento'
        verbose_name_plural = 'Tareas de Documentos'
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['document', 'status']),
            models.Index(fields=['task_type', 'status']),
            models.Index(fields=['priority', 'status']),
        ]
    
    def __str__(self):
        return f"{self.get_task_type_display()} - {self.document.title} ({self.get_status_display()})"
    
    @property
    def duration_seconds(self):
        """Calcula la duración de la tarea en segundos"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            from django.utils import timezone
            return (timezone.now() - self.started_at).total_seconds()
        return None
    
    @property
    def is_active(self):
        """Indica si la tarea está activa (pendiente o en progreso)"""
        return self.status in [TaskStatus.PENDING, TaskStatus.STARTED, TaskStatus.PROGRESS]
    
    @property
    def is_completed(self):
        """Indica si la tarea está completada (éxito o fallo)"""
        return self.status in [TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED]


# ============== SISTEMA DE CLUSTERING PRECOMPUTADO ==============

class ClusterGraph(models.Model):
    """
    Modelo para almacenar el grafo de clusters precomputado.
    Esto se calcula una vez (en batch nocturno) y se sirve rápidamente a los clientes.
    
    Arquitectura:
    1. UMAP 30D → preserva estructura global semántica
    2. HDBSCAN en 30D → clusters semánticos estables
    3. UMAP 2D → solo para visualización (x, y)
    4. KNN graph → edges para "documentos relacionados"
    """
    graph_id = models.AutoField(primary_key=True)
    
    # Metadata del grafo
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creado")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Actualizado")
    is_active = models.BooleanField(
        default=True, 
        verbose_name="Activo",
        help_text="Solo un grafo debe estar activo a la vez"
    )
    document_count = models.IntegerField(
        verbose_name="Cantidad de Documentos",
        help_text="Número de documentos incluidos en este grafo"
    )
    cluster_count = models.IntegerField(
        verbose_name="Cantidad de Clusters",
        help_text="Número de clusters encontrados (sin contar ruido)"
    )
    noise_count = models.IntegerField(
        default=0,
        verbose_name="Documentos de Ruido",
        help_text="Documentos que no pertenecen a ningún cluster"
    )
    
    # Parámetros usados en la computación
    algorithm = models.CharField(
        max_length=50,
        default='hdbscan',
        verbose_name="Algoritmo",
        help_text="Algoritmo de clustering usado (hdbscan, dbscan)"
    )
    metric = models.CharField(
        max_length=50,
        default='cosine',
        verbose_name="Métrica",
        help_text="Métrica de distancia usada"
    )
    umap_30d_params = models.JSONField(
        verbose_name="Parámetros UMAP 30D",
        help_text="Parámetros para reducción 384D → 30D"
    )
    umap_2d_params = models.JSONField(
        verbose_name="Parámetros UMAP 2D",
        help_text="Parámetros para reducción 30D → 2D (visualización)"
    )
    clustering_params = models.JSONField(
        verbose_name="Parámetros de Clustering",
        help_text="Parámetros del algoritmo de clustering"
    )
    knn_params = models.JSONField(
        verbose_name="Parámetros KNN",
        help_text="Parámetros para construcción del grafo KNN"
    )
    
    # Estadísticas
    computation_time_seconds = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Tiempo de Computación (seg)"
    )
    
    # Métricas de calidad del clustering
    silhouette_score = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Silhouette Score",
        help_text="Mide cohesión y separación de clusters (-1 a 1, mayor es mejor)"
    )
    calinski_harabasz_score = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Calinski-Harabasz Score",
        help_text="Ratio de dispersión inter/intra cluster (mayor es mejor)"
    )
    davies_bouldin_score = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Davies-Bouldin Score",
        help_text="Promedio de similitud entre clusters (menor es mejor)"
    )
    
    class Meta:
        db_table = 'documents_cluster_graph'
        ordering = ['-created_at']
        verbose_name = 'Grafo de Clusters'
        verbose_name_plural = 'Grafos de Clusters'
        indexes = [
            models.Index(fields=['is_active', '-created_at']),
        ]
    
    def __str__(self):
        return f"ClusterGraph {self.graph_id} - {self.document_count} docs, {self.cluster_count} clusters"
    
    @classmethod
    def get_active_graph(cls):
        """Obtiene el grafo activo más reciente"""
        return cls.objects.filter(is_active=True).order_by('-created_at').first()
    
    def activate(self):
        """Activa este grafo y desactiva todos los demás"""
        # Desactivar todos
        ClusterGraph.objects.update(is_active=False)
        # Activar este
        self.is_active = True
        self.save()


class ClusterGraphNode(models.Model):
    """
    Nodo individual en el grafo de clusters.
    Representa un documento con sus coordenadas de visualización y cluster asignado.
    """
    node_id = models.AutoField(primary_key=True)
    graph = models.ForeignKey(
        ClusterGraph,
        on_delete=models.CASCADE,
        related_name='nodes',
        verbose_name="Grafo"
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='cluster_nodes',
        verbose_name="Documento"
    )
    
    # Embeddings reducidos
    umap_30d_embedding = VectorField(
        dimensions=30,
        verbose_name="Embedding UMAP 30D",
        help_text="Embedding reducido para clustering semántico"
    )
    
    # Coordenadas de visualización 2D
    x = models.FloatField(verbose_name="Coordenada X (UMAP 2D)")
    y = models.FloatField(verbose_name="Coordenada Y (UMAP 2D)")
    
    # Cluster asignado
    cluster_label = models.IntegerField(
        verbose_name="Label del Cluster",
        help_text="-1 significa ruido (sin cluster)"
    )
    is_noise = models.BooleanField(
        default=False,
        verbose_name="Es Ruido",
        help_text="True si cluster_label == -1"
    )
    
    # Metadata adicional para visualización rápida
    # (denormalizado para evitar joins en renderizado)
    doc_title = models.CharField(max_length=255, verbose_name="Título")
    doc_case_number = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name="Número de Expediente"
    )
    doc_legal_area_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Área Legal"
    )
    doc_type_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Tipo de Documento"
    )
    doc_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha del Documento"
    )
    
    class Meta:
        db_table = 'documents_cluster_graph_node'
        unique_together = [['graph', 'document']]
        ordering = ['cluster_label', 'document__title']
        verbose_name = 'Nodo del Grafo'
        verbose_name_plural = 'Nodos del Grafo'
        indexes = [
            models.Index(fields=['graph', 'cluster_label']),
            models.Index(fields=['graph', 'document']),
            models.Index(fields=['cluster_label']),
        ]
    
    def __str__(self):
        return f"{self.doc_title} (Cluster {self.cluster_label})"


class ClusterGraphEdge(models.Model):
    """
    Edge (arista) en el grafo KNN.
    Representa la relación de "vecino más cercano" entre dos documentos.
    Estas aristas se muestran opcionalmente en el frontend para exploración local.
    """
    edge_id = models.AutoField(primary_key=True)
    graph = models.ForeignKey(
        ClusterGraph,
        on_delete=models.CASCADE,
        related_name='edges',
        verbose_name="Grafo"
    )
    
    # Nodos conectados
    source_node = models.ForeignKey(
        ClusterGraphNode,
        on_delete=models.CASCADE,
        related_name='outgoing_edges',
        verbose_name="Nodo Origen"
    )
    target_node = models.ForeignKey(
        ClusterGraphNode,
        on_delete=models.CASCADE,
        related_name='incoming_edges',
        verbose_name="Nodo Destino"
    )
    
    # Peso/similitud de la arista
    similarity = models.FloatField(
        verbose_name="Similitud",
        help_text="Similitud semántica entre los documentos (0-1)"
    )
    
    # Tipo de edge
    edge_type = models.CharField(
        max_length=20,
        default='knn',
        verbose_name="Tipo de Arista",
        help_text="knn = K-Nearest Neighbor"
    )
    
    class Meta:
        db_table = 'documents_cluster_graph_edge'
        unique_together = [['graph', 'source_node', 'target_node']]
        ordering = ['-similarity']
        verbose_name = 'Arista del Grafo'
        verbose_name_plural = 'Aristas del Grafo'
        indexes = [
            models.Index(fields=['graph', 'source_node']),
            models.Index(fields=['graph', 'target_node']),
            models.Index(fields=['-similarity']),
        ]
    
    def __str__(self):
        return f"{self.source_node.doc_title} → {self.target_node.doc_title} ({self.similarity:.3f})"


# ============== BERTOPIC MODELS ==============

class BERTopicModel(models.Model):
    """
    Modelo BERTopic precomputado.
    Almacena los resultados de topic modeling para visualización rápida.
    
    BERTopic combina:
    - Embeddings de documentos (SentenceTransformers)
    - UMAP para reducción de dimensionalidad
    - HDBSCAN para clustering
    - c-TF-IDF para extracción de keywords representativos
    """
    model_id = models.AutoField(primary_key=True)
    
    # Estadísticas generales
    document_count = models.IntegerField(verbose_name="Número de Documentos")
    topic_count = models.IntegerField(verbose_name="Número de Tópicos")
    outlier_count = models.IntegerField(
        default=0,
        verbose_name="Documentos sin Tópico",
        help_text="Documentos clasificados como outliers (-1)"
    )
    
    # Tiempo de computación
    computation_time = models.FloatField(
        verbose_name="Tiempo de Computación (s)",
        help_text="Segundos que tomó generar el modelo"
    )
    
    # Parámetros utilizados
    parameters = models.JSONField(
        default=dict,
        verbose_name="Parámetros del Modelo",
        help_text="UMAP, HDBSCAN, embedding field, etc."
    )
    
    # Estado
    is_active = models.BooleanField(
        default=False,
        verbose_name="Modelo Activo",
        help_text="Solo un modelo puede estar activo a la vez"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'documents_bertopic_model'
        ordering = ['-created_at']
        verbose_name = 'Modelo BERTopic'
        verbose_name_plural = 'Modelos BERTopic'
    
    def __str__(self):
        return f"BERTopic Model {self.model_id} ({self.topic_count} topics, {self.document_count} docs)"
    
    def activate(self):
        """Activar este modelo y desactivar los demás."""
        BERTopicModel.objects.filter(is_active=True).update(is_active=False)
        self.is_active = True
        self.save(update_fields=['is_active', 'updated_at'])


class BERTopicTopic(models.Model):
    """
    Un tópico individual de un modelo BERTopic.
    Contiene keywords representativos y estadísticas.
    """
    topic_db_id = models.AutoField(primary_key=True)
    model = models.ForeignKey(
        BERTopicModel,
        on_delete=models.CASCADE,
        related_name='topics',
        verbose_name="Modelo"
    )
    
    # Identificador del tópico (asignado por BERTopic)
    topic_id = models.IntegerField(
        verbose_name="ID del Tópico",
        help_text="-1 = outliers/sin tópico"
    )
    
    # Label descriptivo (generado desde keywords)
    label = models.CharField(
        max_length=255,
        verbose_name="Etiqueta del Tópico",
        help_text="Label generado desde top keywords"
    )
    
    # Keywords representativos (c-TF-IDF)
    keywords = models.JSONField(
        default=list,
        verbose_name="Keywords",
        help_text="Lista de palabras clave ordenadas por relevancia"
    )
    
    # Pesos de keywords (para visualización de barchart)
    keyword_weights = models.JSONField(
        default=dict,
        verbose_name="Pesos de Keywords",
        help_text="Dict {keyword: weight}"
    )
    
    # Estadísticas
    document_count = models.IntegerField(
        verbose_name="Número de Documentos",
        help_text="Documentos en este tópico"
    )
    
    # Flags
    is_outlier = models.BooleanField(
        default=False,
        verbose_name="Es Outlier",
        help_text="True si topic_id == -1"
    )
    
    class Meta:
        db_table = 'documents_bertopic_topic'
        unique_together = [['model', 'topic_id']]
        ordering = ['topic_id']
        verbose_name = 'Tópico BERTopic'
        verbose_name_plural = 'Tópicos BERTopic'
        indexes = [
            models.Index(fields=['model', 'topic_id']),
            models.Index(fields=['model', '-document_count']),
        ]
    
    def __str__(self):
        return f"Topic {self.topic_id}: {self.label[:50]}"


class BERTopicDocument(models.Model):
    """
    Asignación de un documento a un tópico BERTopic.
    Incluye coordenadas 2D para visualización y probabilidad.
    """
    bertopic_doc_id = models.AutoField(primary_key=True)
    model = models.ForeignKey(
        BERTopicModel,
        on_delete=models.CASCADE,
        related_name='document_assignments',
        verbose_name="Modelo"
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='bertopic_assignments',
        verbose_name="Documento"
    )
    topic = models.ForeignKey(
        BERTopicTopic,
        on_delete=models.CASCADE,
        related_name='documents',
        null=True,
        verbose_name="Tópico Asignado"
    )
    
    # Topic ID raw (para queries rápidos)
    topic_id_raw = models.IntegerField(
        verbose_name="Topic ID",
        help_text="-1 = outlier"
    )
    
    # Probabilidad de pertenencia al tópico
    probability = models.FloatField(
        null=True,
        verbose_name="Probabilidad",
        help_text="Probabilidad de pertenencia al tópico asignado"
    )
    
    # Coordenadas 2D para visualización
    x = models.FloatField(verbose_name="Coordenada X")
    y = models.FloatField(verbose_name="Coordenada Y")
    
    class Meta:
        db_table = 'documents_bertopic_document'
        unique_together = [['model', 'document']]
        ordering = ['topic_id_raw']
        verbose_name = 'Documento BERTopic'
        verbose_name_plural = 'Documentos BERTopic'
        indexes = [
            models.Index(fields=['model', 'topic_id_raw']),
            models.Index(fields=['model', 'document']),
        ]
    
    def __str__(self):
        return f"{self.document.title[:50]} → Topic {self.topic_id_raw}"
