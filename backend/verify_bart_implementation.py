#!/usr/bin/env python
"""
Script para verificar que la implementación de BART esté correcta.
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.documents.models import Document, DocumentTask, SummarizerType

print("=" * 60)
print("VERIFICACIÓN DE IMPLEMENTACIÓN DE BART")
print("=" * 60)

# 1. Verificar que el modelo tiene el campo
print("\n1. Verificando campos en modelo Document...")
try:
    from apps.documents.models import Document
    doc = Document()
    assert hasattr(doc, 'summarizer_type'), "❌ Campo 'summarizer_type' no existe en Document"
    print("✅ Campo 'summarizer_type' existe en Document")
except Exception as e:
    print(f"❌ Error: {e}")

# 2. Verificar que DocumentTask tiene el campo
print("\n2. Verificando campos en modelo DocumentTask...")
try:
    from apps.documents.models import DocumentTask
    task = DocumentTask()
    assert hasattr(task, 'summarizer_type'), "❌ Campo 'summarizer_type' no existe en DocumentTask"
    print("✅ Campo 'summarizer_type' existe en DocumentTask")
except Exception as e:
    print(f"❌ Error: {e}")

# 3. Verificar enum SummarizerType
print("\n3. Verificando enum SummarizerType...")
try:
    from apps.documents.models import SummarizerType
    assert hasattr(SummarizerType, 'OLLAMA'), "❌ OLLAMA no existe en SummarizerType"
    assert hasattr(SummarizerType, 'BART'), "❌ BART no existe en SummarizerType"
    print(f"✅ SummarizerType.OLLAMA = '{SummarizerType.OLLAMA}'")
    print(f"✅ SummarizerType.BART = '{SummarizerType.BART}'")
except Exception as e:
    print(f"❌ Error: {e}")

# 4. Verificar que DocumentSummarizer acepta el parámetro
print("\n4. Verificando DocumentSummarizer...")
try:
    from apps.documents.services.document_summarizer import DocumentSummarizer
    import inspect
    
    sig = inspect.signature(DocumentSummarizer.generate_summary)
    params = list(sig.parameters.keys())
    
    assert 'summarizer_type' in params, "❌ Parámetro 'summarizer_type' no existe en generate_summary"
    print("✅ DocumentSummarizer.generate_summary() acepta 'summarizer_type'")
    
    # Verificar default
    default = sig.parameters['summarizer_type'].default
    print(f"   Default: {default}")
except Exception as e:
    print(f"❌ Error: {e}")

# 5. Verificar ModularDocumentProcessor
print("\n5. Verificando ModularDocumentProcessor...")
try:
    from apps.documents.services.modular_processing import ModularDocumentProcessor
    import inspect
    
    sig = inspect.signature(ModularDocumentProcessor.process_summary)
    params = list(sig.parameters.keys())
    
    assert 'summarizer_type' in params, "❌ Parámetro 'summarizer_type' no existe en process_summary"
    print("✅ ModularDocumentProcessor.process_summary() acepta 'summarizer_type'")
    
    # Verificar default
    default = sig.parameters['summarizer_type'].default
    print(f"   Default: {default}")
except Exception as e:
    print(f"❌ Error: {e}")

# 6. Verificar tarea Celery
print("\n6. Verificando tarea process_document_analysis...")
try:
    from apps.documents.tasks import process_document_analysis
    import inspect
    
    # Para tasks con bind=True, el primer parámetro es 'self'
    sig = inspect.signature(process_document_analysis)
    params = list(sig.parameters.keys())
    
    assert 'summarizer_type' in params, "❌ Parámetro 'summarizer_type' no existe en process_document_analysis"
    print("✅ process_document_analysis() acepta 'summarizer_type'")
    print(f"   Parámetros: {params}")
    
    # Verificar default
    default = sig.parameters['summarizer_type'].default
    print(f"   Default: {default}")
except Exception as e:
    print(f"❌ Error: {e}")

# 7. Verificar migración aplicada
print("\n7. Verificando migración en base de datos...")
try:
    from django.db import connection
    with connection.cursor() as cursor:
        # Verificar que la columna existe en la tabla documents_document
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'documents_document' 
            AND column_name = 'summarizer_type'
        """)
        result = cursor.fetchone()
        
        if result:
            print(f"✅ Columna 'summarizer_type' existe en documents_document")
            print(f"   Tipo: {result[1]}")
        else:
            print("❌ Columna 'summarizer_type' NO existe en documents_document")
        
        # Verificar en documents_task
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'documents_task' 
            AND column_name = 'summarizer_type'
        """)
        result = cursor.fetchone()
        
        if result:
            print(f"✅ Columna 'summarizer_type' existe en documents_task")
            print(f"   Tipo: {result[1]}")
        else:
            print("❌ Columna 'summarizer_type' NO existe en documents_task")
except Exception as e:
    print(f"❌ Error verificando migración: {e}")

print("\n" + "=" * 60)
print("VERIFICACIÓN COMPLETADA")
print("=" * 60)

# Contar documentos por tipo de summarizer
print("\n8. Estadísticas de uso...")
try:
    from django.db.models import Count
    
    stats = Document.objects.values('summarizer_type').annotate(count=Count('document_id'))
    
    if stats:
        print("Documentos por tipo de summarizer:")
        for stat in stats:
            tipo = stat['summarizer_type'] or 'NULL'
            count = stat['count']
            print(f"  - {tipo}: {count} documentos")
    else:
        print("  No hay documentos en la base de datos")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n✅ Implementación lista para uso!")
