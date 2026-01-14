# documents/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Document, LegalArea, DocumentType, Person, 
    DocumentPerson, PersonRole, ClusterGraph,
    ClusterGraphNode, ClusterGraphEdge
)

@admin.register(LegalArea)
class LegalAreaAdmin(admin.ModelAdmin):
    """Admin for Legal Areas"""
    list_display = ['area_id', 'name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']

@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    """Admin for Document Types"""
    list_display = ['type_id', 'name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']

@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    """Admin for Persons and Entities"""
    list_display = ['person_id', 'name', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']

class DocumentPersonInline(admin.TabularInline):
    """Inline for persons in document"""
    model = DocumentPerson
    extra = 0
    readonly_fields = ['person', 'role', 'is_primary']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Enhanced admin interface for Document model"""
    
    list_display = [
        'document_id_short',
        'title', 
        'doc_type_name',
        'legal_area_name',
        'case_number',
        'jurisdictional_body',
        'status_colored',
        'file_type',
        'pages',
        'created_at',
    ]
    
    list_filter = [
        'status', 
        'doc_type',
        'legal_area', 
        'file_type',
        'jurisdictional_body',
        'created_at',
    ]
    
    search_fields = [
        'title', 
        'content',
        'document_id',
        'summary',
        'case_number',
    ]
    
    readonly_fields = [
        'document_id',
        'created_at',
        'updated_at',
        'processed_at',
        'content',
        'summary',
        'doc_type',
        'legal_area',
        'legal_subject',
        'jurisdictional_body',
        'case_number',
        'pages',
        'file_type',
        'file_size',
        'status',
        'error_message',
    ]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('document_id', 'title', 'file_path', 'status', 'error_message')
        }),
        ('Clasificación Automática', {
            'fields': ('doc_type', 'legal_area', 'legal_subject', 'jurisdictional_body', 'case_number'),
            'description': 'Clasificación generada por IA'
        }),
        ('Metadatos del Archivo', {
            'fields': ('file_type', 'file_size', 'pages'),
        }),
        ('Contenido', {
            'fields': ('summary', 'content'),
            'classes': ('collapse',),
        }),
        ('Sistema', {
            'fields': ('created_at', 'updated_at', 'processed_at'),
            'classes': ('collapse',),
        }),
    )

    inlines = [DocumentPersonInline]
    ordering = ['-created_at']
    actions = ['reprocess_documents']

    def document_id_short(self, obj):
        """Display shortened document ID"""
        return str(obj.document_id)[:8] + '...'
    document_id_short.short_description = 'ID'

    def doc_type_name(self, obj):
        """Display document type name"""
        return obj.doc_type.name if obj.doc_type else '-'
    doc_type_name.short_description = 'Tipo'
    doc_type_name.admin_order_field = 'doc_type__name'

    def legal_area_name(self, obj):
        """Display legal area name"""
        return obj.legal_area.name if obj.legal_area else '-'
    legal_area_name.short_description = 'Área Legal'
    legal_area_name.admin_order_field = 'legal_area__name'

    def status_colored(self, obj):
        """Display status with color coding"""
        colors = {
            'uploaded': 'gray',
            'processing': 'blue',
            'processed': 'green',
            'failed': 'red',
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = 'Estado'
    status_colored.admin_order_field = 'status'

    def reprocess_documents(self, request, queryset):
        """Admin action to reprocess selected documents"""
        from .services.document_processing import DocumentProcessingService
        
        processor = DocumentProcessingService()
        success_count = 0
        
        for document in queryset:
            if processor.process_document(document):
                success_count += 1
        
        self.message_user(
            request,
            f'{success_count} de {queryset.count()} documentos reprocesados exitosamente.'
        )
    reprocess_documents.short_description = 'Reprocesar documentos seleccionados'

@admin.register(DocumentPerson)
class DocumentPersonAdmin(admin.ModelAdmin):
    """Admin for Document-Person relationships"""
    list_display = ['document_title', 'person_name', 'role', 'is_primary']
    list_filter = ['role', 'is_primary']
    search_fields = ['document__title', 'person__name']
    readonly_fields = ['document', 'person', 'role', 'is_primary', 'created_at']
    
    def document_title(self, obj):
        return obj.document.title[:50]
    document_title.short_description = 'Documento'
    
    def person_name(self, obj):
        return obj.person.name
    person_name.short_description = 'Persona'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


# ============== CLUSTER GRAPH ADMIN ==============

@admin.register(ClusterGraph)
class ClusterGraphAdmin(admin.ModelAdmin):
    """Admin for precomputed cluster graphs"""
    
    list_display = [
        'graph_id',
        'is_active_colored',
        'document_count',
        'cluster_count',
        'noise_count',
        'algorithm',
        'computation_time_formatted',
        'created_at',
    ]
    
    list_filter = [
        'is_active',
        'algorithm',
        'created_at',
    ]
    
    readonly_fields = [
        'graph_id',
        'created_at',
        'updated_at',
        'document_count',
        'cluster_count',
        'noise_count',
        'algorithm',
        'metric',
        'umap_30d_params',
        'umap_2d_params',
        'clustering_params',
        'knn_params',
        'computation_time_seconds',
    ]
    
    fieldsets = (
        ('Estado', {
            'fields': ('graph_id', 'is_active', 'created_at', 'updated_at')
        }),
        ('Estadísticas', {
            'fields': ('document_count', 'cluster_count', 'noise_count', 'computation_time_seconds')
        }),
        ('Parámetros', {
            'fields': ('algorithm', 'metric', 'umap_30d_params', 'umap_2d_params', 'clustering_params', 'knn_params'),
            'classes': ('collapse',),
        }),
    )
    
    ordering = ['-created_at']
    actions = ['activate_graph', 'rebuild_graph']
    
    def is_active_colored(self, obj):
        """Display active status with color"""
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ ACTIVO</span>'
            )
        else:
            return format_html(
                '<span style="color: gray;">○ Inactivo</span>'
            )
    is_active_colored.short_description = 'Estado'
    is_active_colored.admin_order_field = 'is_active'
    
    def computation_time_formatted(self, obj):
        """Display computation time in readable format"""
        if obj.computation_time_seconds:
            minutes = int(obj.computation_time_seconds // 60)
            seconds = int(obj.computation_time_seconds % 60)
            if minutes > 0:
                return f"{minutes}m {seconds}s"
            return f"{seconds}s"
        return "-"
    computation_time_formatted.short_description = 'Tiempo'
    computation_time_formatted.admin_order_field = 'computation_time_seconds'
    
    def activate_graph(self, request, queryset):
        """Admin action to activate a graph"""
        if queryset.count() != 1:
            self.message_user(
                request,
                'Seleccione exactamente un grafo para activar.',
                level='error'
            )
            return
        
        graph = queryset.first()
        graph.activate()
        
        self.message_user(
            request,
            f'Grafo {graph.graph_id} activado exitosamente.',
            level='success'
        )
    activate_graph.short_description = 'Activar grafo seleccionado'
    
    def rebuild_graph(self, request, queryset):
        """Admin action to rebuild cluster graph"""
        from apps.documents.tasks import compute_cluster_graph
        
        # Queue task
        task = compute_cluster_graph.delay(
            max_documents=1000,
            use_enhanced_embedding=True,
            algorithm='hdbscan'
        )
        
        self.message_user(
            request,
            f'Tarea de reconstrucción de grafo encolada: {task.id}',
            level='success'
        )
    rebuild_graph.short_description = 'Reconstruir grafo de clusters (async)'
    
    def has_add_permission(self, request):
        """No se pueden crear grafos manualmente"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Solo se pueden eliminar grafos inactivos"""
        if obj and obj.is_active:
            return False
        return True


@admin.register(ClusterGraphNode)
class ClusterGraphNodeAdmin(admin.ModelAdmin):
    """Admin for cluster graph nodes"""
    
    list_display = [
        'node_id',
        'graph_id',
        'document_title_short',
        'cluster_label',
        'is_noise',
        'legal_area_name',
        'position',
    ]
    
    list_filter = [
        'graph',
        'cluster_label',
        'is_noise',
        'doc_legal_area_name',
    ]
    
    search_fields = [
        'doc_title',
        'doc_case_number',
        'document__document_id',
    ]
    
    readonly_fields = [
        'node_id',
        'graph',
        'document',
        'umap_30d_embedding',
        'x',
        'y',
        'cluster_label',
        'is_noise',
        'doc_title',
        'doc_case_number',
        'doc_legal_area_name',
        'doc_type_name',
        'doc_date',
    ]
    
    ordering = ['graph', 'cluster_label', 'doc_title']
    
    def document_title_short(self, obj):
        return obj.doc_title[:50] + '...' if len(obj.doc_title) > 50 else obj.doc_title
    document_title_short.short_description = 'Documento'
    
    def legal_area_name(self, obj):
        return obj.doc_legal_area_name or '-'
    legal_area_name.short_description = 'Área Legal'
    
    def position(self, obj):
        return f"({obj.x:.2f}, {obj.y:.2f})"
    position.short_description = 'Posición (x, y)'
    
    def graph_id(self, obj):
        return obj.graph.graph_id
    graph_id.short_description = 'Grafo ID'
    graph_id.admin_order_field = 'graph__graph_id'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ClusterGraphEdge)
class ClusterGraphEdgeAdmin(admin.ModelAdmin):
    """Admin for cluster graph edges (KNN)"""
    
    list_display = [
        'edge_id',
        'graph_id',
        'source_title_short',
        'target_title_short',
        'similarity_formatted',
        'edge_type',
    ]
    
    list_filter = [
        'graph',
        'edge_type',
    ]
    
    search_fields = [
        'source_node__doc_title',
        'target_node__doc_title',
    ]
    
    readonly_fields = [
        'edge_id',
        'graph',
        'source_node',
        'target_node',
        'similarity',
        'edge_type',
    ]
    
    ordering = ['graph', '-similarity']
    
    def graph_id(self, obj):
        return obj.graph.graph_id
    graph_id.short_description = 'Grafo ID'
    graph_id.admin_order_field = 'graph__graph_id'
    
    def source_title_short(self, obj):
        title = obj.source_node.doc_title
        return title[:30] + '...' if len(title) > 30 else title
    source_title_short.short_description = 'Origen'
    
    def target_title_short(self, obj):
        title = obj.target_node.doc_title
        return title[:30] + '...' if len(title) > 30 else title
    target_title_short.short_description = 'Destino'
    
    def similarity_formatted(self, obj):
        return f"{obj.similarity:.3f}"
    similarity_formatted.short_description = 'Similitud'
    similarity_formatted.admin_order_field = 'similarity'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
