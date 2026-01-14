#!/usr/bin/env python
"""
Test Script para RAG Service v4.0
=================================

Prueba el nuevo servicio RAG con filosofía "menos chunks, más contexto"

Uso:
    python test_rag_v4.py
    python test_rag_v4.py --doc-id 1
    python test_rag_v4.py --prompt "Explica los antecedentes"
"""

import os
import sys
import django
import argparse
import logging

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.documents.models import Document
from apps.documents.services.rag_service_v4 import get_rag_service_v4

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'  # Formato limpio para presentación
)

def print_separator(title: str = "", char: str = "═"):
    """Imprime un separador visual"""
    width = 80
    if title:
        padding = (width - len(title) - 2) // 2
        print(f"\n{char * padding} {title} {char * padding}")
    else:
        print(char * width)


def test_document(doc_id, prompts: list = None):
    """Prueba RAG v4.0 con un documento específico"""
    
    try:
        document = Document.objects.get(pk=doc_id)
    except Document.DoesNotExist:
        print(f"❌ Documento con ID {doc_id} no existe")
        return
    
    print_separator("INFORMACIÓN DEL DOCUMENTO")
    print(f"📄 ID: {document.document_id}")
    print(f"📄 Título: {document.title[:80]}...")
    
    # Verificar chunks
    from apps.documents.models import DocumentChunk
    chunks = DocumentChunk.objects.filter(document_id=document)
    chunks_with_embeddings = chunks.exclude(clean_content_embedding=None)
    
    print(f"📊 Chunks totales: {chunks.count()}")
    print(f"📊 Chunks con embeddings 768d: {chunks_with_embeddings.count()}")
    
    if chunks_with_embeddings.count() == 0:
        print("⚠️  Este documento no tiene embeddings. No se puede probar RAG.")
        return
    
    # Obtener servicio RAG v4.0 (sin pasar documento)
    rag_service = get_rag_service_v4()
    
    if not prompts:
        prompts = [
            "Explica los antecedentes del caso",
            "¿Quiénes son las partes del proceso?",
            "¿Qué se decidió en este caso?",
            "¿Cuáles son los fundamentos de la decisión?",
        ]
    
    for prompt in prompts:
        print_separator(f"PRUEBA: {prompt[:50]}...")
        print(f"\n🔍 Prompt: {prompt}\n")
        
        # Ejecutar búsqueda (v4 necesita document y question)
        result = rag_service.retrieve_with_context(document, prompt)
        
        print(f"\n📋 RESULTADO:")
        print(f"   • Secciones encontradas: {len(result.windows)}")
        print(f"   • Chunks principales: {result.main_chunks_count}")
        print(f"   • Chunks de contexto: {result.context_chunks_count}")
        print(f"   • Total chunks: {result.total_chunks_used}")
        
        print(f"\n📝 CONTEXTO GENERADO:")
        print("-" * 80)
        # Mostrar el contexto formateado para LLM
        context = result.get_context_for_llm(max_chars=3000)
        print(context)
        print("-" * 80)
        
        print_separator()


def list_documents():
    """Lista documentos disponibles para prueba"""
    documents = Document.objects.all()[:10]
    
    print_separator("DOCUMENTOS DISPONIBLES")
    
    from apps.documents.models import DocumentChunk
    
    for doc in documents:
        chunks = DocumentChunk.objects.filter(document_id=doc)
        chunks_768 = chunks.exclude(clean_content_embedding=None).count()
        status = "✅" if chunks_768 > 0 else "⚠️"
        print(f"{status} ID {doc.document_id}: {doc.title[:60]}... ({chunks_768} embeddings)")
    
    print_separator()


def main():
    parser = argparse.ArgumentParser(description='Test RAG Service v4.0')
    parser.add_argument('--doc-id', type=str, help='ID (UUID) del documento a probar')
    parser.add_argument('--prompt', type=str, help='Prompt específico a probar')
    parser.add_argument('--list', action='store_true', help='Listar documentos disponibles')
    
    args = parser.parse_args()
    
    print_separator("RAG SERVICE v4.0 - TEST")
    print("📚 Filosofía: Menos chunks, más contexto")
    print("🎯 Expandir top 3-5 chunks con contexto adyacente")
    print_separator()
    
    if args.list:
        list_documents()
        return
    
    if args.doc_id:
        prompts = [args.prompt] if args.prompt else None
        test_document(args.doc_id, prompts)
    else:
        # Por defecto, probar el primer documento con embeddings
        from apps.documents.models import DocumentChunk
        
        chunk_with_embedding = DocumentChunk.objects.exclude(clean_content_embedding=None).first()
        
        if chunk_with_embedding:
            test_document(chunk_with_embedding.document_id.document_id, prompts=[args.prompt] if args.prompt else None)
        else:
            print("⚠️  No hay documentos con embeddings 768d")
            print("   Ejecuta primero: python manage.py regenerate_all_embeddings")


if __name__ == '__main__':
    main()
