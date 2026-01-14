# Generated migration for clean_embedding field
# apps/documents/migrations/0015_add_clean_embedding.py

from django.db import migrations
import pgvector.django


class Migration(migrations.Migration):
    """
    Agrega el campo clean_embedding al modelo Document.
    
    Este campo almacena el embedding generado sobre texto LIMPIO (sin stopwords)
    usando el modelo paraphrase-multilingual-mpnet-base-v2 de SentenceTransformers.
    
    Características:
    - 768 dimensiones (vs 384 del enhanced_embedding actual)
    - Generado SIN depender de Ollama
    - Optimizado para similaridad y clustering
    
    El campo es nullable para permitir migración gradual de documentos existentes.
    """

    dependencies = [
        ('documents', '0014_add_clustering_quality_metrics'),
    ]

    operations = [
        # Agregar campo clean_embedding al modelo Document
        migrations.AddField(
            model_name='document',
            name='clean_embedding',
            field=pgvector.django.VectorField(
                dimensions=768,
                blank=True,
                null=True,
                help_text='Embedding sobre texto limpio (sin stopwords) para similaridad y clustering. Generado con SentenceTransformers sin depender de Ollama.'
            ),
        ),
        
        # Agregar índice para búsquedas eficientes con pgvector
        # Nota: pgvector soporta índices IVFFlat y HNSW para búsquedas aproximadas
        # Por ahora dejamos sin índice especializado, se puede agregar después según volumen
    ]
