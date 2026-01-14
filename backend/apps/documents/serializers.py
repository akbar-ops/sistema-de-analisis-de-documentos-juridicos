# apps/documents/serializers.py
from rest_framework import serializers
from .models import (
    Document, LegalArea, DocumentType, Person, 
    DocumentPerson, PersonRole, DocumentChunk, DocumentTask
)

class LegalAreaSerializer(serializers.ModelSerializer):
    """Serializer for legal areas"""
    class Meta:
        model = LegalArea
        fields = ['area_id', 'name', 'description']

class DocumentTypeSerializer(serializers.ModelSerializer):
    """Serializer for document types"""
    class Meta:
        model = DocumentType
        fields = ['type_id', 'name', 'description']

class PersonSerializer(serializers.ModelSerializer):
    """Serializer for persons and entities"""
    class Meta:
        model = Person
        fields = ['person_id', 'name']

class DocumentPersonSerializer(serializers.ModelSerializer):
    """Serializer for document-person relationships"""
    person = PersonSerializer(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = DocumentPerson
        fields = ['person', 'role', 'role_display', 'is_primary']

class DocumentChunkSerializer(serializers.ModelSerializer):
    """Serializer for document chunks"""
    class Meta:
        model = DocumentChunk
        fields = ['chunk_id', 'order_number', 'content', 'created_at']
        read_only_fields = ['chunk_id', 'created_at']

class DocumentSimilaritySerializer(serializers.ModelSerializer):
    """
    Optimized serializer for similar documents (GET /api/documents/{id}/similar/)
    Incluye solo información esencial + preview + similarity score + razones
    
    NUEVO: Incluye scoring calibrado para jurisprudencia con penalizaciones
    """
    doc_type = DocumentTypeSerializer(read_only=True)
    legal_area = LegalAreaSerializer(read_only=True)
    file_type = serializers.CharField(source='get_file_type_display', read_only=True)
    file_path = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    summary_preview = serializers.SerializerMethodField()
    persons_preview = serializers.SerializerMethodField()
    
    # Campos completos para el diálogo de comparación
    summary = serializers.CharField(read_only=True)
    persons = serializers.SerializerMethodField()
    
    # Campos de scoring mejorado
    similarity_score = serializers.FloatField(read_only=True)  # Semántico puro
    hybrid_score = serializers.FloatField(read_only=True, required=False)  # Normalizado
    raw_hybrid_score = serializers.FloatField(read_only=True, required=False)  # Sin normalizar
    metadata_boost = serializers.FloatField(read_only=True, required=False)  # Boost positivo
    penalties = serializers.FloatField(read_only=True, required=False)  # Penalizaciones
    similarity_reasons = serializers.ListField(read_only=True, required=False)
    score_breakdown = serializers.DictField(read_only=True, required=False)
    bm25_score = serializers.FloatField(read_only=True, required=False)
    semantic_score = serializers.FloatField(read_only=True, required=False)
    
    class Meta:
        model = Document
        fields = [
            'document_id',
            'title',
            'case_number',
            'resolution_number',
            'issue_place',
            'document_date',
            'legal_subject',
            'jurisdictional_body',
            'pages',
            'status',
            'created_at',
            'doc_type',
            'legal_area',
            'file_type',
            'file_size_mb',
            'file_path',
            'file_name',
            'summary',           # Resumen completo
            'summary_preview',   # Preview de 150 caracteres
            'persons',           # Todas las personas
            'persons_preview',   # Solo primeras 3 personas
            'similarity_score',  # Score semántico (0-1)
            'hybrid_score',      # Score normalizado final
            'raw_hybrid_score',  # Score sin normalización
            'bm25_score',        # Score BM25
            'semantic_score',    # Score semántico separado
            'metadata_boost',    # Boost por metadatos
            'penalties',         # Penalizaciones aplicadas
            'similarity_reasons', # Lista de razones
            'score_breakdown',   # Desglose por categoría
        ]
        read_only_fields = fields
    
    def get_file_path(self, obj):
        """Return the file URL path"""
        if obj.file_path:
            return obj.file_path.url
        return None
    
    def get_file_size_mb(self, obj):
        """Convert file size to MB"""
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return 0
    
    def get_file_name(self, obj):
        """Return the file name"""
        if obj.file_path:
            return obj.file_path.name.split('/')[-1]
        return None
    
    def get_summary_preview(self, obj):
        """Return first 150 characters of summary"""
        if obj.summary:
            preview = obj.summary[:150]
            if len(obj.summary) > 150:
                preview += "..."
            return preview
        return None
    
    def get_persons_preview(self, obj):
        """Return first 3 persons with their roles"""
        doc_persons = obj.document_persons.select_related('person').all()[:3]
        return [
            {
                'name': dp.person.name,
                'role': dp.get_role_display() if dp.role else None
            }
            for dp in doc_persons
        ]
    
    def get_persons(self, obj):
        """Return all persons with their roles"""
        doc_persons = obj.document_persons.select_related('person').all()
        return [
            {
                'name': dp.person.name,
                'role': dp.get_role_display() if dp.role else None
            }
            for dp in doc_persons
        ]

class DocumentSearchResultSerializer(serializers.ModelSerializer):
    """
    Optimized serializer for search results (POST /api/documents/advanced_search/)
    Incluye solo información esencial + preview + similarity score
    """
    doc_type = DocumentTypeSerializer(read_only=True)
    legal_area = LegalAreaSerializer(read_only=True)
    file_type = serializers.CharField(source='get_file_type_display', read_only=True)
    file_path = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()
    summary_preview = serializers.SerializerMethodField()
    persons_preview = serializers.SerializerMethodField()
    similarity_score = serializers.FloatField(read_only=True, required=False, allow_null=True)
    cluster = serializers.IntegerField(source='hdbscan_cluster', read_only=True, allow_null=True)
    
    class Meta:
        model = Document
        fields = [
            'document_id',
            'title',
            'case_number',
            'resolution_number',
            'issue_place',
            'document_date',
            'legal_subject',
            'jurisdictional_body',
            'pages',
            'status',
            'created_at',
            'doc_type',
            'legal_area',
            'file_type',
            'file_size_mb',
            'file_path',
            'summary_preview',   # Preview de 150 caracteres
            'persons_preview',   # Solo primeras 3 personas
            'similarity_score',  # Score de similitud para búsqueda semántica
            'cluster',           # HDBSCAN cluster for visualization
        ]
        read_only_fields = fields
    
    def get_file_path(self, obj):
        """Return the file URL path"""
        if obj.file_path:
            return obj.file_path.url
        return None
    
    def get_file_size_mb(self, obj):
        """Convert file size to MB"""
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return 0
    
    def get_summary_preview(self, obj):
        """Return first 150 characters of summary"""
        if obj.summary:
            preview = obj.summary[:150]
            if len(obj.summary) > 150:
                preview += "..."
            return preview
        return None
    
    def get_persons_preview(self, obj):
        """Return first 3 persons with their roles"""
        doc_persons = obj.document_persons.select_related('person').all()[:3]
        return [
            {
                'name': dp.person.name,
                'role': dp.get_role_display() if dp.role else None
            }
            for dp in doc_persons
        ]

class DocumentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new documents (POST /api/documents/)"""
    file = serializers.FileField(write_only=True, source='file_path')
    
    # Campos opcionales para análisis modular
    # Usar CharField en lugar de BooleanField porque FormData envía strings
    analyze_metadata = serializers.CharField(default='false', write_only=True, required=False)
    analyze_title = serializers.CharField(default='false', write_only=True, required=False)
    analyze_summary = serializers.CharField(default='false', write_only=True, required=False)
    analyze_persons = serializers.CharField(default='false', write_only=True, required=False)
    summarizer_type = serializers.ChoiceField(
        choices=['ollama', 'ollama_hierarchical', 'bart'],
        default='ollama',  # Direct method (6000 chars) - faster
        write_only=True,
        required=False,
        help_text="Tipo de generador de resumen: 'ollama' (6000 chars, rápido), 'ollama_hierarchical' (documento completo, lento), 'bart' (Hugging Face)"
    )
    
    class Meta:
        model = Document
        fields = ['file', 'analyze_metadata', 'analyze_title', 'analyze_summary', 'analyze_persons', 'summarizer_type']
    
    def to_internal_value(self, data):
        """
        Override to convert string booleans from FormData to actual booleans
        """
        # Llamar al método padre primero
        result = super().to_internal_value(data)
        
        # Convertir strings de booleanos a valores booleanos reales en validated_data
        for field in ['analyze_metadata', 'analyze_title', 'analyze_summary', 'analyze_persons']:
            if field in result:
                value = result[field]
                if isinstance(value, str):
                    result[field] = value.lower() in ('true', '1', 'yes')
        
        return result
    
    def validate_file(self, value):
        """Validate uploaded file"""
        max_size = 50 * 1024 * 1024  # 50MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f"El archivo es demasiado grande. Tamaño máximo: 50MB"
            )
        
        allowed_extensions = ['.pdf', '.docx', '.doc', '.txt']
        file_name = value.name.lower()
        if not any(file_name.endswith(ext) for ext in allowed_extensions):
            raise serializers.ValidationError(
                f"Formato de archivo no permitido. Formatos válidos: {', '.join(allowed_extensions)}"
            )
        
        return value
    
    def create(self, validated_data):
        """Create document with initial status"""
        # Remover campos de análisis antes de crear el documento
        validated_data.pop('analyze_metadata', None)
        validated_data.pop('analyze_title', None)
        validated_data.pop('analyze_summary', None)
        validated_data.pop('analyze_persons', None)
        validated_data.pop('summarizer_type', None)
        
        file_path = validated_data.get('file_path')
        if file_path:
            validated_data['title'] = file_path.name
        
        return super().create(validated_data)


class BulkUploadSerializer(serializers.Serializer):
    """Serializer for bulk document upload (POST /api/documents/bulk_upload/)"""
    files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        help_text="Lista de archivos a subir"
    )
    
    # Opciones de análisis que se aplicarán a todos los documentos
    # Usar CharField en lugar de BooleanField porque FormData envía strings
    analyze_metadata = serializers.CharField(default='false', required=False)
    analyze_title = serializers.CharField(default='false', required=False)
    analyze_summary = serializers.CharField(default='false', required=False)
    analyze_persons = serializers.CharField(default='false', required=False)
    summarizer_type = serializers.ChoiceField(
        choices=['ollama', 'ollama_hierarchical', 'bart'],
        default='ollama',  # Direct method (6000 chars) - faster
        required=False,
        help_text="Tipo de generador de resumen: 'ollama' (6000 chars, rápido), 'ollama_hierarchical' (documento completo, lento), 'bart' (Hugging Face)"
    )
    
    def to_internal_value(self, data):
        """
        Override to convert string booleans from FormData to actual booleans
        """
        # Llamar al método padre primero
        result = super().to_internal_value(data)
        
        # Convertir strings de booleanos a valores booleanos reales en validated_data
        for field in ['analyze_metadata', 'analyze_title', 'analyze_summary', 'analyze_persons']:
            if field in result:
                value = result[field]
                if isinstance(value, str):
                    result[field] = value.lower() in ('true', '1', 'yes')
        
        return result
    
    def validate_files(self, files):
        """Validar lista de archivos"""
        if not files:
            raise serializers.ValidationError("Debe proporcionar al menos un archivo")
        
        if len(files) > 10:
            raise serializers.ValidationError("No puede subir más de 10 archivos a la vez")
        
        max_size = 50 * 1024 * 1024  # 50MB por archivo
        allowed_extensions = ['.pdf', '.docx', '.doc', '.txt']
        
        for file in files:
            if file.size > max_size:
                raise serializers.ValidationError(
                    f"El archivo '{file.name}' es demasiado grande. Tamaño máximo: 50MB"
                )
            
            file_name = file.name.lower()
            if not any(file_name.endswith(ext) for ext in allowed_extensions):
                raise serializers.ValidationError(
                    f"El archivo '{file.name}' tiene un formato no permitido. "
                    f"Formatos válidos: {', '.join(allowed_extensions)}"
                )
        
        return files


class DocumentAnalysisSerializer(serializers.Serializer):
    """Serializer para solicitar análisis de partes específicas de un documento"""
    parts = serializers.ListField(
        child=serializers.ChoiceField(choices=['metadata', 'title', 'summary', 'persons']),
        help_text="Lista de partes a analizar: 'metadata', 'title', 'summary', 'persons'"
    )
    summarizer_type = serializers.ChoiceField(
        choices=['ollama', 'ollama_hierarchical', 'bart'],
        default='ollama',  # Direct method (6000 chars) - faster
        required=False,
        help_text="Tipo de generador de resumen: 'ollama' (6000 chars, rápido), 'ollama_hierarchical' (documento completo, lento), 'bart' (Hugging Face)"
    )
    
    def validate_parts(self, parts):
        """Validar que haya al menos una parte y no duplicados"""
        if not parts:
            raise serializers.ValidationError("Debe especificar al menos una parte para analizar")
        
        if len(parts) != len(set(parts)):
            raise serializers.ValidationError("No puede haber partes duplicadas")
        
        return parts

class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for document detail (GET /api/documents/{id})"""
    doc_type = DocumentTypeSerializer(read_only=True)
    legal_area = LegalAreaSerializer(read_only=True)
    persons = DocumentPersonSerializer(source='document_persons', many=True, read_only=True)
    file_type = serializers.CharField(source='get_file_type_display', read_only=True)
    file_size_mb = serializers.SerializerMethodField()
    file_path = serializers.SerializerMethodField()
    formatted_summary = serializers.SerializerMethodField()
    
    # Embedding availability flags (don't send full embeddings, just check if they exist)
    has_summary_embedding = serializers.SerializerMethodField()
    has_enhanced_embedding = serializers.SerializerMethodField()
    has_clean_embedding = serializers.SerializerMethodField()
    
    # Estados de análisis modular
    analysis_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'document_id',
            'title',
            'case_number',
            'resolution_number',
            'issue_place',
            'document_date',
            'legal_subject',
            'jurisdictional_body',
            'pages',
            'status',
            'created_at',
            'doc_type',
            'legal_area',
            'file_type',
            'file_size_mb',
            'file_path',
            'persons',
            'summary',
            'formatted_summary',
            'has_summary_embedding',  # Boolean flag to check if embeddings exist
            'has_enhanced_embedding',  # Without sending the full arrays
            'has_clean_embedding',     # Clean embedding for similarity (no Ollama required)
            'analysis_status',  # Estados de cada parte del análisis
        ]
        read_only_fields = [
            'document_id',
            'case_number',
            'resolution_number',
            'issue_place',
            'document_date',
            'legal_subject',
            'jurisdictional_body',
            'pages',
            'status',
            'created_at',
            'doc_type',
            'legal_area',
            'file_type',
            'file_size_mb',
            'persons',
            'summary',
        ]
    
    def get_analysis_status(self, obj):
        """Retorna el estado de análisis de cada parte"""
        return {
            'metadata': obj.metadata_analysis_status,
            'summary': obj.summary_analysis_status,
            'persons': obj.persons_analysis_status,
        }
    
    def get_has_summary_embedding(self, obj):
        """Check if document has summary embedding"""
        return obj.summary_embedding is not None and len(obj.summary_embedding) > 0
    
    def get_has_enhanced_embedding(self, obj):
        """Check if document has enhanced embedding"""
        return obj.enhanced_embedding is not None and len(obj.enhanced_embedding) > 0
    
    def get_has_clean_embedding(self, obj):
        """Check if document has clean embedding (generated without Ollama)"""
        return obj.clean_embedding is not None and len(obj.clean_embedding) > 0
    
    def get_file_size_mb(self, obj):
        """Convert file size to MB"""
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return 0
    
    def get_file_path(self, obj):
        """Return the file URL path"""
        if obj.file_path:
            return obj.file_path.url
        return None
    
    def get_formatted_summary(self, obj):
        """
        Return a comprehensive formatted summary that combines all document information.
        Similar to the old format but now aggregating data from multiple fields.
        """
        # Group persons by role
        persons_by_role = {
            'demandante': [],
            'demandado': [],
            'juez': [],
            'fiscal': [],
            'abogado': [],
            'testigo': [],
            'perito': [],
            'tercero': [],
            'otro': []
        }
        
        for doc_person in obj.document_persons.all():
            role = doc_person.role
            persons_by_role[role].append(doc_person.person.name)
        
        # Format persons section
        persons_section = "PERSONAS INVOLUCRADAS:\n"
        role_labels = {
            'demandante': 'Demandante(s)',
            'demandado': 'Demandado(s)',
            'juez': 'Juez(ces)',
            'fiscal': 'Fiscal(es)',
            'abogado': 'Abogado(s)',
            'testigo': 'Testigo(s)',
            'perito': 'Perito(s)',
            'tercero': 'Tercero(s)',
            'otro': 'Otros'
        }
        
        for role, label in role_labels.items():
            names = persons_by_role.get(role, [])
            if names:
                persons_section += f"{label}: {'; '.join(names)}\n"
            else:
                persons_section += f"{label}: No identificado\n"
        
        # Build complete formatted summary
        formatted = f"""INFORMACIÓN DEL DOCUMENTO

TÍTULO: {obj.title or 'Sin título'}

CLASIFICACIÓN:
Tipo de Documento: {obj.doc_type.name if obj.doc_type else 'No clasificado'}
Área Legal: {obj.legal_area.name if obj.legal_area else 'No clasificada'}
Materia: {obj.legal_subject or 'No especificada'}

DATOS DEL DOCUMENTO:
Número de Resolución: {obj.resolution_number or 'No identificado'}
Lugar de Emisión: {obj.issue_place or 'No identificado'}
Fecha de Emisión: {obj.document_date.strftime('%d/%m/%Y') if obj.document_date else 'No identificada'}

DATOS DEL CASO:
Número de Expediente: {obj.case_number or 'No identificado'}
Órgano Jurisdiccional: {obj.jurisdictional_body or 'No identificado'}

{persons_section}
{'─' * 80}

{obj.summary if obj.summary else 'No se generó resumen para este documento.'}
"""
        
        return formatted

class DocumentListSerializer(serializers.ModelSerializer):
    """
    Optimized serializer for listing documents (GET /api/documents/)
    Incluye solo información esencial + preview del resumen + personas principales
    """
    doc_type = DocumentTypeSerializer(read_only=True)
    legal_area = LegalAreaSerializer(read_only=True)
    file_type = serializers.CharField(source='get_file_type_display', read_only=True)
    file_path = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()
    summary_preview = serializers.SerializerMethodField()
    persons_preview = serializers.SerializerMethodField()
    analysis_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'document_id',
            'title',
            'case_number',
            'resolution_number',
            'issue_place',
            'document_date',
            'legal_subject',
            'jurisdictional_body',
            'pages',
            'status',
            'created_at',
            'doc_type',
            'legal_area',
            'file_type',
            'file_size_mb',
            'file_path',
            'summary_preview',  # Preview de 150 caracteres
            'persons_preview',   # Solo primeras 3 personas
            'analysis_status',  # Estados de cada parte del análisis
        ]
        read_only_fields = fields
    
    def get_analysis_status(self, obj):
        """Retorna el estado de análisis de cada parte"""
        return {
            'metadata': obj.metadata_analysis_status,
            'summary': obj.summary_analysis_status,
            'persons': obj.persons_analysis_status,
        }
    
    def get_file_path(self, obj):
        """Return the file URL path"""
        if obj.file_path:
            return obj.file_path.url
        return None
    
    def get_file_size_mb(self, obj):
        """Convert file size to MB"""
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return 0
    
    def get_summary_preview(self, obj):
        """Return first 150 characters of summary"""
        if obj.summary:
            preview = obj.summary[:150]
            if len(obj.summary) > 150:
                preview += "..."
            return preview
        return None
    
    def get_persons_preview(self, obj):
        """Return first 3 persons with their roles"""
        doc_persons = obj.document_persons.select_related('person').all()[:3]
        return [
            {
                'name': dp.person.name,
                'role': dp.get_role_display() if dp.role else None
            }
            for dp in doc_persons
        ]


# ============================================================================
# SERIALIZERS PARA SISTEMA DE TAREAS
# ============================================================================

class DocumentTaskSerializer(serializers.ModelSerializer):
    """Serializer para tareas de documentos"""
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    duration_seconds = serializers.FloatField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    is_completed = serializers.BooleanField(read_only=True)
    
    # Información básica del documento
    document_title = serializers.CharField(source='document.title', read_only=True)
    document_id = serializers.UUIDField(source='document.document_id', read_only=True)
    
    class Meta:
        model = DocumentTask
        fields = [
            'task_id',
            'document_id',
            'document_title',
            'task_type',
            'task_type_display',
            'status',
            'status_display',
            'priority',
            'progress_percent',
            'progress_message',
            'analysis_parts',
            'result',
            'error_message',
            'created_at',
            'started_at',
            'completed_at',
            'duration_seconds',
            'is_active',
            'is_completed',
            'worker_name',
        ]
        read_only_fields = fields


class DocumentTaskListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listado de tareas"""
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    document_title = serializers.CharField(source='document.title', read_only=True)
    document_id = serializers.UUIDField(source='document.document_id', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = DocumentTask
        fields = [
            'task_id',
            'document_id',
            'document_title',
            'task_type',
            'task_type_display',
            'status',
            'status_display',
            'priority',
            'progress_percent',
            'progress_message',
            'analysis_parts',
            'created_at',
            'started_at',
            'is_active',
        ]
        read_only_fields = fields
