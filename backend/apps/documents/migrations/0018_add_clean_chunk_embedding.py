# apps/documents/migrations/0018_add_clean_chunk_embedding.py
"""
Migración para agregar campo clean_content_embedding a DocumentChunk.

Este campo almacena embeddings de 768 dimensiones (vs 384 del antiguo).
Usa el mismo modelo que Document.clean_embedding para consistencia.

Beneficios:
- Mejor calidad de embeddings para RAG
- Consistencia con búsqueda de documentos similares
- Texto limpio sin encabezados repetitivos
"""

from django.db import migrations
from pgvector.django import VectorField


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0017_add_bertopic_models'),
    ]

    operations = [
        # Agregar nuevo campo de embedding de 768 dimensiones
        migrations.AddField(
            model_name='documentchunk',
            name='clean_content_embedding',
            field=VectorField(
                dimensions=768,
                blank=True,
                null=True,
                help_text='Embedding de 768d del contenido limpio (sin encabezados)'
            ),
        ),
        
        # Agregar índice para búsqueda eficiente por vector
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS documents_documentchunk_clean_embedding_idx 
                ON documents_documentchunk 
                USING ivfflat (clean_content_embedding vector_cosine_ops)
                WITH (lists = 100);
            """,
            reverse_sql="DROP INDEX IF EXISTS documents_documentchunk_clean_embedding_idx;",
        ),
    ]
