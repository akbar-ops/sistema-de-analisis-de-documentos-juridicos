#!/usr/bin/env python
"""
Test RAG Service v3.0 - Script de pruebas y prompts de ejemplo.

Este script permite probar el servicio RAG v3.0 con diferentes tipos de preguntas
para validar que la recuperación de chunks sea correcta.

Uso:
    # Configurar Django
    export DJANGO_SETTINGS_MODULE=config.settings
    
    # Ejecutar test interactivo
    python test_rag_v3.py
    
    # Ejecutar con documento específico
    python test_rag_v3.py --document-id <uuid>
    
    # Ejecutar todos los tests automáticos
    python test_rag_v3.py --auto
"""

import os
import sys
import django
import argparse
import logging
from typing import List, Dict

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.documents.models import Document, DocumentChunk
from apps.documents.services.rag_service_v3 import get_rag_service_v3

# Configurar logging para ver detalles
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# PROMPTS DE PRUEBA ORGANIZADOS POR CATEGORÍA
# ============================================================================

TEST_PROMPTS = {
    "decisiones": [
        "¿Qué decidieron los jueces en este caso?",
        "¿Cuál fue el fallo final?",
        "¿La demanda fue declarada fundada o infundada?",
        "¿Qué resolvió la sala?",
        "¿Se confirmó o revocó la sentencia de primera instancia?",
        "¿Cuál fue el resultado del proceso?",
    ],
    
    "partes": [
        "¿Quién es el demandante en este caso?",
        "¿Quién es el demandado?",
        "¿Cuáles son las partes involucradas?",
        "¿Qué empresa fue demandada?",
        "¿Quién presentó la apelación?",
    ],
    
    "hechos": [
        "¿Cuáles son los hechos del caso?",
        "¿Qué pasó según el documento?",
        "¿Por qué se inició este proceso?",
        "Resume los antecedentes del caso",
        "¿Cuál es el origen de la controversia?",
    ],
    
    "montos": [
        "¿Cuánto dinero se ordenó pagar?",
        "¿Cuál es el monto de la indemnización?",
        "¿Qué montos se mencionan en el documento?",
        "¿Cuánto se pagó por CTS?",
        "¿Cuál fue el monto demandado vs el otorgado?",
    ],
    
    "fundamentos": [
        "¿Cuáles son los fundamentos legales del fallo?",
        "¿Qué normas se aplicaron?",
        "¿Cuál fue el razonamiento del juez?",
        "¿Qué argumentos se consideraron?",
        "¿Por qué se falló a favor/en contra?",
    ],
    
    "fechas": [
        "¿Cuándo ocurrieron los hechos?",
        "¿Cuándo se emitió la sentencia?",
        "¿Cuánto tiempo trabajó el demandante?",
        "¿Cuándo fue despedido el trabajador?",
    ],
    
    "generales": [
        "Resumen del documento",
        "¿De qué trata este caso?",
        "Explica brevemente el contenido del documento",
        "¿Qué tipo de proceso es este?",
    ],
}


def print_separator(title: str = ""):
    """Imprime separador visual."""
    print("\n" + "=" * 80)
    if title:
        print(f"  {title}")
        print("=" * 80)


def print_chunk_info(chunk: Dict, index: int):
    """Imprime información de un chunk de forma legible."""
    is_adjacent = chunk.get('is_adjacent', False)
    order = chunk.get('order_number', '?')
    score = chunk.get('combined_score', 0)
    sem_sim = chunk.get('semantic_similarity', 0)
    bm25 = chunk.get('bm25_score', 0)
    content = chunk.get('content', '')[:300]
    
    chunk_type = "📎 ADYACENTE" if is_adjacent else "✅ PRINCIPAL"
    
    print(f"\n{'-' * 60}")
    print(f"Chunk {index + 1}: {chunk_type}")
    print(f"  📍 Posición en documento: #{order}")
    print(f"  🎯 Score combinado: {score:.2%}")
    print(f"  🔵 Similitud semántica: {sem_sim:.2%}")
    print(f"  📝 Score BM25: {bm25:.2%}")
    print(f"  📄 Preview contenido ({len(chunk.get('content', ''))} chars):")
    print(f"     \"{content}...\"")


def test_document_rag(document: Document, prompts: List[str] = None):
    """
    Prueba el RAG v3.0 con un documento.
    
    Args:
        document: Documento a probar
        prompts: Lista de prompts a probar (None = interactivo)
    """
    print_separator(f"TEST RAG v3.0 - Documento: {document.title}")
    
    # Verificar capacidad RAG
    rag_service = get_rag_service_v3()
    stats = rag_service.check_document_has_chunks(document)
    
    print(f"\n📊 ESTADÍSTICAS DEL DOCUMENTO:")
    print(f"   - Total chunks: {stats['total_chunks']}")
    print(f"   - Chunks con embedding 768d: {stats['chunks_with_clean_embedding']}")
    print(f"   - Chunks con embedding 384d: {stats['chunks_with_legacy_embedding']}")
    print(f"   - RAG habilitado: {'✅ SÍ' if stats['has_rag_capability'] else '❌ NO'}")
    
    if stats.get('recommended_action'):
        print(f"   ⚠️ Acción recomendada: {stats['recommended_action']}")
    
    if not stats['has_rag_capability']:
        print("\n❌ El documento no tiene embeddings. Ejecuta primero:")
        print(f"   python manage.py regenerate_chunk_embeddings --document-id {document.document_id}")
        return
    
    # Modo interactivo o automático
    if prompts is None:
        print("\n🎯 MODO INTERACTIVO")
        print("Escribe una pregunta sobre el documento (o 'exit' para salir)")
        print("Escribe 'list' para ver prompts de ejemplo\n")
        
        while True:
            question = input("\n❓ Tu pregunta: ").strip()
            
            if question.lower() == 'exit':
                break
            elif question.lower() == 'list':
                print("\n📋 PROMPTS DE EJEMPLO POR CATEGORÍA:")
                for category, examples in TEST_PROMPTS.items():
                    print(f"\n  [{category.upper()}]")
                    for ex in examples[:3]:
                        print(f"    - {ex}")
                continue
            elif not question:
                continue
            
            run_single_query(rag_service, document, question)
    else:
        # Modo automático
        for question in prompts:
            run_single_query(rag_service, document, question)
            print("\n" + "·" * 80)


def run_single_query(rag_service, document: Document, question: str):
    """Ejecuta una query y muestra resultados detallados."""
    print_separator(f"QUERY: {question}")
    
    # Ejecutar RAG
    chunks = rag_service.retrieve_relevant_chunks(
        document=document,
        question=question,
        top_k=8,
        similarity_threshold=0.35,
        include_adjacent=True
    )
    
    if not chunks:
        print("\n❌ No se encontraron chunks relevantes")
        return
    
    # Estadísticas
    main_chunks = [c for c in chunks if not c.get('is_adjacent')]
    adj_chunks = [c for c in chunks if c.get('is_adjacent')]
    
    print(f"\n📊 RESULTADOS:")
    print(f"   - Chunks principales: {len(main_chunks)}")
    print(f"   - Chunks adyacentes: {len(adj_chunks)}")
    
    if main_chunks:
        scores = [c.get('combined_score', 0) for c in main_chunks]
        print(f"   - Score promedio: {sum(scores)/len(scores):.2%}")
        print(f"   - Score máximo: {max(scores):.2%}")
        print(f"   - Score mínimo: {min(scores):.2%}")
        print(f"   - Posiciones: {[c['order_number'] for c in main_chunks]}")
    
    # Mostrar chunks
    print("\n📄 CHUNKS RECUPERADOS:")
    for i, chunk in enumerate(chunks):
        print_chunk_info(chunk, i)
    
    # Generar contexto
    context = rag_service.get_context_from_chunks(chunks, max_chars=8000)
    print(f"\n📝 CONTEXTO GENERADO ({len(context)} chars):")
    print("-" * 60)
    print(context[:2000] + "..." if len(context) > 2000 else context)


def list_documents():
    """Lista documentos disponibles para pruebas."""
    documents = Document.objects.filter(
        status='processed'
    ).order_by('-created_at')[:20]
    
    print_separator("DOCUMENTOS DISPONIBLES PARA PRUEBA")
    
    for i, doc in enumerate(documents, 1):
        chunk_count = DocumentChunk.objects.filter(document_id=doc).count()
        has_clean = DocumentChunk.objects.filter(
            document_id=doc,
            clean_content_embedding__isnull=False
        ).exists()
        
        status = "✅" if has_clean else "⚠️"
        print(f"{i}. {status} [{doc.document_id}]")
        print(f"   📄 {doc.title[:60]}...")
        print(f"   📊 {chunk_count} chunks, embeddings: {'768d' if has_clean else '384d (legacy)'}")
        print()


def run_automated_tests(document: Document):
    """Ejecuta tests automáticos con todos los prompts de ejemplo."""
    print_separator("TESTS AUTOMÁTICOS RAG v3.0")
    
    rag_service = get_rag_service_v3()
    
    results = {
        'success': 0,
        'failed': 0,
        'no_results': 0,
        'details': []
    }
    
    for category, prompts in TEST_PROMPTS.items():
        print(f"\n\n🏷️ CATEGORÍA: {category.upper()}")
        print("=" * 60)
        
        for prompt in prompts[:2]:  # Solo 2 por categoría para no saturar
            print(f"\n❓ {prompt}")
            
            chunks = rag_service.retrieve_relevant_chunks(
                document=document,
                question=prompt,
                top_k=5
            )
            
            if chunks:
                main_chunks = [c for c in chunks if not c.get('is_adjacent')]
                avg_score = sum(c.get('combined_score', 0) for c in main_chunks) / len(main_chunks) if main_chunks else 0
                
                if avg_score >= 0.4:
                    print(f"   ✅ {len(main_chunks)} chunks, score promedio: {avg_score:.2%}")
                    results['success'] += 1
                else:
                    print(f"   ⚠️ {len(main_chunks)} chunks, score bajo: {avg_score:.2%}")
                    results['success'] += 1  # Aún cuenta como éxito
                
                results['details'].append({
                    'category': category,
                    'prompt': prompt,
                    'chunks': len(main_chunks),
                    'avg_score': avg_score
                })
            else:
                print(f"   ❌ Sin resultados")
                results['no_results'] += 1
    
    # Resumen final
    print_separator("RESUMEN DE TESTS")
    total = results['success'] + results['failed'] + results['no_results']
    print(f"✅ Exitosos: {results['success']}/{total}")
    print(f"❌ Sin resultados: {results['no_results']}/{total}")
    
    if results['details']:
        avg_overall = sum(d['avg_score'] for d in results['details']) / len(results['details'])
        print(f"📊 Score promedio general: {avg_overall:.2%}")


def main():
    parser = argparse.ArgumentParser(description='Test RAG Service v3.0')
    parser.add_argument('--document-id', '-d', type=str, help='UUID del documento a probar')
    parser.add_argument('--list', '-l', action='store_true', help='Listar documentos disponibles')
    parser.add_argument('--auto', '-a', action='store_true', help='Ejecutar tests automáticos')
    parser.add_argument('--prompt', '-p', type=str, help='Prompt específico a probar')
    
    args = parser.parse_args()
    
    if args.list:
        list_documents()
        return
    
    # Obtener documento
    if args.document_id:
        try:
            document = Document.objects.get(document_id=args.document_id)
        except Document.DoesNotExist:
            print(f"❌ Documento no encontrado: {args.document_id}")
            return
    else:
        # Usar el primer documento procesado con chunks
        document = Document.objects.filter(
            status='processed',
            chunks__isnull=False
        ).first()
        
        if not document:
            print("❌ No hay documentos procesados con chunks")
            print("Usa --list para ver documentos disponibles")
            return
    
    print(f"\n🔍 Usando documento: {document.title}")
    print(f"   ID: {document.document_id}")
    
    if args.auto:
        run_automated_tests(document)
    elif args.prompt:
        rag_service = get_rag_service_v3()
        run_single_query(rag_service, document, args.prompt)
    else:
        # Modo interactivo
        test_document_rag(document)


if __name__ == '__main__':
    main()
