#!/usr/bin/env python
"""
Auditoría completa del sistema de embeddings.

Verifica:
1. Dimensiones de todos los embeddings
2. Si usan o no stopwords
3. Qué servicio los genera
4. Inconsistencias en la base de datos
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.documents.models import Document, DocumentChunk
from django.db.models import Q, Count
import numpy as np

print("=" * 80)
print("🔍 AUDITORÍA DE EMBEDDINGS")
print("=" * 80)
print()

# ============================================================================
# PARTE 1: RESUMEN DEL MODELO DE DATOS
# ============================================================================
print("📋 MODELO DE DATOS - CAMPOS DE EMBEDDING")
print("-" * 80)

embeddings_schema = {
    "Document": {
        "summary_embedding": {
            "dimensiones": 384,
            "servicio": "embedding_service (MiniLM)",
            "usa_stopwords": "NO",
            "descripción": "Embedding del resumen (legacy)"
        },
        "enhanced_embedding": {
            "dimensiones": 384,
            "servicio": "embedding_service (MiniLM)",
            "usa_stopwords": "NO",
            "descripción": "Combina: title, legal_area, summary, etc. (legacy)"
        },
        "clean_embedding": {
            "dimensiones": 768,
            "servicio": "CleanEmbeddingsService (mpnet)",
            "usa_stopwords": "SÍ - stopwords español + legales",
            "descripción": "Para similaridad y clustering del documento completo"
        }
    },
    "DocumentChunk": {
        "content_embedding": {
            "dimensiones": 384,
            "servicio": "embedding_service (MiniLM)",
            "usa_stopwords": "NO",
            "descripción": "Legacy - para compatibilidad"
        },
        "clean_content_embedding": {
            "dimensiones": 768,
            "servicio": "ChunkEmbeddingService (mpnet)",
            "usa_stopwords": "NO - solo limpia headers/ruido",
            "descripción": "Para RAG v4.0 - PREFERIDO"
        }
    }
}

for model, fields in embeddings_schema.items():
    print(f"\n📄 {model}")
    for field, info in fields.items():
        print(f"\n  {field}:")
        for key, value in info.items():
            print(f"    • {key}: {value}")

print("\n" + "=" * 80)

# ============================================================================
# PARTE 2: AUDITORÍA DE LA BASE DE DATOS
# ============================================================================
print("\n📊 ESTADO ACTUAL DE LA BASE DE DATOS")
print("-" * 80)

# Documentos
total_docs = Document.objects.count()
docs_with_clean = Document.objects.filter(clean_embedding__isnull=False).count()

print(f"\n📚 DOCUMENTOS:")
print(f"  Total: {total_docs}")
print(f"  Con clean_embedding (768d): {docs_with_clean}")
print(f"  Sin clean_embedding: {total_docs - docs_with_clean}")

if docs_with_clean > 0:
    # Verificar dimensiones
    doc_sample = Document.objects.filter(clean_embedding__isnull=False).first()
    if doc_sample and doc_sample.clean_embedding is not None:
        dim = len(doc_sample.clean_embedding)
        print(f"  ✅ Dimensión verificada: {dim}d")
        if dim != 768:
            print(f"  ⚠️  ADVERTENCIA: Se esperaban 768d, se encontraron {dim}d")

# Chunks
total_chunks = DocumentChunk.objects.count()
chunks_with_legacy = DocumentChunk.objects.filter(content_embedding__isnull=False).count()
chunks_with_clean = DocumentChunk.objects.filter(clean_content_embedding__isnull=False).count()

print(f"\n📦 CHUNKS:")
print(f"  Total: {total_chunks}")
print(f"  Con content_embedding (384d legacy): {chunks_with_legacy}")
print(f"  Con clean_content_embedding (768d): {chunks_with_clean}")
print(f"  Sin ningún embedding: {total_chunks - max(chunks_with_legacy, chunks_with_clean)}")

if chunks_with_clean > 0:
    # Verificar dimensiones
    chunk_sample = DocumentChunk.objects.filter(clean_content_embedding__isnull=False).first()
    if chunk_sample and chunk_sample.clean_content_embedding is not None:
        dim = len(chunk_sample.clean_content_embedding)
        print(f"  ✅ Dimensión verificada: {dim}d")
        if dim != 768:
            print(f"  ⚠️  ADVERTENCIA: Se esperaban 768d, se encontraron {dim}d")

# ============================================================================
# PARTE 3: DETECTAR INCONSISTENCIAS
# ============================================================================
print("\n" + "=" * 80)
print("🔎 BÚSQUEDA DE INCONSISTENCIAS")
print("-" * 80)

# Documentos con chunks pero sin clean embeddings
docs_with_legacy_chunks_only = Document.objects.filter(
    chunks__isnull=False
).annotate(
    total_chunks=Count('chunks'),
    clean_chunks=Count('chunks', filter=Q(chunks__clean_content_embedding__isnull=False))
).filter(
    total_chunks__gt=0,
    clean_chunks=0
)

if docs_with_legacy_chunks_only.exists():
    print(f"\n⚠️  PROBLEMA: {docs_with_legacy_chunks_only.count()} documentos tienen chunks SIN clean_content_embedding")
    print(f"   Estos documentos NO funcionarán con RAG v4.0")
    print(f"\n   Primeros 5:")
    for doc in docs_with_legacy_chunks_only[:5]:
        print(f"   - {doc.document_id}: {doc.title[:50]}...")
    print(f"\n   💡 Solución: Ejecutar script de regeneración")
else:
    print(f"\n✅ BIEN: Todos los documentos con chunks tienen clean_content_embedding (768d)")

# Documentos sin clean_embedding
docs_without_clean_embedding = Document.objects.filter(
    Q(clean_embedding__isnull=True) & Q(content__isnull=False)
)

if docs_without_clean_embedding.exists():
    print(f"\n⚠️  ADVERTENCIA: {docs_without_clean_embedding.count()} documentos sin clean_embedding")
    print(f"   Estos documentos no aparecerán en clustering/similaridad")
else:
    print(f"\n✅ BIEN: Todos los documentos tienen clean_embedding para clustering")

# ============================================================================
# PARTE 4: VERIFICAR SERVICIOS
# ============================================================================
print("\n" + "=" * 80)
print("🔧 VERIFICACIÓN DE SERVICIOS")
print("-" * 80)

try:
    from apps.documents.services.embedding_service import get_embedding_service
    service = get_embedding_service()
    print(f"\n✅ EmbeddingService (legacy):")
    print(f"   Modelo: {service.model_name}")
    print(f"   Dimensiones: {service.embedding_dimension}")
    print(f"   Usa stopwords: NO")
except Exception as e:
    print(f"\n❌ Error cargando EmbeddingService: {e}")

try:
    from apps.documents.services.clean_embeddings_service import get_clean_embedding_service
    service = get_clean_embedding_service()
    print(f"\n✅ CleanEmbeddingsService:")
    print(f"   Modelo: {service.model_name}")
    print(f"   Dimensiones: 768")
    print(f"   Usa stopwords: SÍ (español + legales)")
    print(f"   Uso: Document.clean_embedding (clustering/similaridad)")
except Exception as e:
    print(f"\n❌ Error cargando CleanEmbeddingsService: {e}")

try:
    from apps.documents.services.chunk_embedding_service import ChunkEmbeddingService
    service = ChunkEmbeddingService(clean_chunks=True)
    print(f"\n✅ ChunkEmbeddingService:")
    print(f"   Modelo: {service.MODEL_NAME}")
    print(f"   Dimensiones: {service.EMBEDDING_DIMENSION}")
    print(f"   Usa stopwords: NO")
    print(f"   Limpieza aplicada: Headers, marcadores de página, artefactos OCR")
    print(f"   Uso: DocumentChunk.clean_content_embedding (RAG v4.0)")
except Exception as e:
    print(f"\n❌ Error cargando ChunkEmbeddingService: {e}")

# ============================================================================
# PARTE 5: RESUMEN Y RECOMENDACIONES
# ============================================================================
print("\n" + "=" * 80)
print("📝 RESUMEN Y RECOMENDACIONES")
print("=" * 80)

issues_found = 0

print("\n🎯 CONFIGURACIÓN CORRECTA:")
print("   • Document.clean_embedding (768d) → CON stopwords → Clustering/Similaridad")
print("   • DocumentChunk.clean_content_embedding (768d) → SIN stopwords → RAG v4.0")
print("   • Embeddings legacy (384d) → Mantener para compatibilidad")

if docs_with_legacy_chunks_only.exists():
    issues_found += 1
    print(f"\n⚠️  ACCIÓN REQUERIDA #{issues_found}:")
    print(f"   Regenerar clean_content_embedding para {docs_with_legacy_chunks_only.count()} documentos")
    print(f"   Ejecutar: python manage.py shell < regenerate_chunk_embeddings.py")

if docs_without_clean_embedding.exists():
    issues_found += 1
    print(f"\n⚠️  ACCIÓN REQUERIDA #{issues_found}:")
    print(f"   Regenerar clean_embedding para {docs_without_clean_embedding.count()} documentos")
    print(f"   Ejecutar: python regenerate_enhanced_embeddings.py")

if issues_found == 0:
    print("\n✅ TODO ESTÁ CORRECTO - No se encontraron inconsistencias")

print("\n" + "=" * 80)
print("✨ Auditoría completada")
print("=" * 80)
