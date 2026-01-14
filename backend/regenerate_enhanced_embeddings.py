#!/usr/bin/env python
"""
Script para regenerar embeddings con la nueva configuración optimizada.

Este script actualiza todos los enhanced_embeddings de los documentos
usando el método mejorado de encode_enhanced_document que incluye:
- Repetición de campos importantes
- Contexto adicional
- Mejor balance de pesos

Uso:
    python regenerate_enhanced_embeddings.py [--limit N] [--dry-run]

Opciones:
    --limit N      Procesar solo N documentos (para pruebas)
    --dry-run      Mostrar qué se haría sin hacer cambios
    --batch-size N Tamaño de lote para procesamiento (default: 10)
"""

import os
import sys
import django
import argparse
from datetime import datetime

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import transaction
from apps.documents.models import Document
from apps.documents.services.embedding_service import get_embedding_service
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def prepare_document_data(document: Document) -> dict:
    """
    Prepara los datos del documento para generar el embedding.
    
    Args:
        document: Instancia del documento
    
    Returns:
        Diccionario con los datos necesarios para el embedding
    """
    # Obtener personas relacionadas
    persons = []
    for dp in document.document_persons.select_related('person').all():
        persons.append({
            'name': dp.person.name,
            'role': dp.role
        })
    
    return {
        'title': document.title,
        'legal_area': document.legal_area.name if document.legal_area else None,
        'legal_subject': document.legal_subject,
        'summary': document.summary,
        'issue_place': document.issue_place,
        'case_number': document.case_number,
        'resolution_number': document.resolution_number,
        'jurisdictional_body': document.jurisdictional_body,
        'persons': persons
    }


def regenerate_embeddings(limit: int = None, dry_run: bool = False, batch_size: int = 10):
    """
    Regenera los enhanced_embeddings de los documentos.
    
    Args:
        limit: Número máximo de documentos a procesar
        dry_run: Si True, solo muestra qué se haría
        batch_size: Tamaño de lote para commits
    """
    logger.info("=" * 80)
    logger.info("REGENERACIÓN DE EMBEDDINGS MEJORADOS")
    logger.info("=" * 80)
    
    if dry_run:
        logger.warning("MODO DRY-RUN: No se harán cambios en la base de datos")
    
    # Obtener servicio de embeddings
    embedding_service = get_embedding_service()
    logger.info(f"Servicio de embeddings cargado: {embedding_service.MODEL_NAME}")
    
    # Obtener documentos a procesar
    queryset = Document.objects.prefetch_related(
        'document_persons__person',
        'legal_area',
        'doc_type'
    ).filter(
        status__in=['processed', 'partial']
    ).exclude(
        title__isnull=True
    ).exclude(
        title=''
    ).order_by('-created_at')
    
    if limit:
        queryset = queryset[:limit]
    
    total_docs = queryset.count()
    logger.info(f"Documentos a procesar: {total_docs}")
    
    if total_docs == 0:
        logger.warning("No hay documentos para procesar")
        return
    
    # Procesar documentos
    processed = 0
    errors = 0
    updated = 0
    skipped = 0
    
    start_time = datetime.now()
    
    for i, document in enumerate(queryset, 1):
        try:
            logger.info(f"\n[{i}/{total_docs}] Procesando: {document.title[:50]}...")
            logger.info(f"  ID: {document.document_id}")
            
            # Preparar datos
            doc_data = prepare_document_data(document)
            
            # Mostrar información del documento
            logger.info(f"  Área legal: {doc_data.get('legal_area', 'N/A')}")
            logger.info(f"  Materia: {doc_data.get('legal_subject', 'N/A')}")
            logger.info(f"  Expediente: {doc_data.get('case_number', 'N/A')}")
            logger.info(f"  Personas: {len(doc_data.get('persons', []))}")
            
            # Generar nuevo embedding
            if not dry_run:
                new_embedding = embedding_service.encode_enhanced_document(doc_data)
                
                if new_embedding is not None:
                    # Guardar en base de datos
                    with transaction.atomic():
                        document.enhanced_embedding = new_embedding.tolist()
                        document.save(update_fields=['enhanced_embedding'])
                    
                    logger.info(f"  ✓ Embedding actualizado ({len(new_embedding)} dimensiones)")
                    updated += 1
                else:
                    logger.warning(f"  ⚠ No se pudo generar embedding (datos insuficientes)")
                    skipped += 1
            else:
                logger.info(f"  [DRY-RUN] Se generaría nuevo embedding")
                updated += 1
            
            processed += 1
            
            # Commit cada batch_size documentos
            if processed % batch_size == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = processed / elapsed if elapsed > 0 else 0
                remaining = total_docs - processed
                eta_seconds = remaining / rate if rate > 0 else 0
                
                logger.info(f"\n{'='*80}")
                logger.info(f"PROGRESO: {processed}/{total_docs} documentos")
                logger.info(f"  Actualizados: {updated}")
                logger.info(f"  Omitidos: {skipped}")
                logger.info(f"  Errores: {errors}")
                logger.info(f"  Velocidad: {rate:.2f} docs/seg")
                logger.info(f"  ETA: {eta_seconds/60:.1f} minutos")
                logger.info(f"{'='*80}\n")
        
        except Exception as e:
            logger.error(f"  ✗ Error procesando documento {document.document_id}: {e}")
            errors += 1
    
    # Resumen final
    elapsed = (datetime.now() - start_time).total_seconds()
    
    logger.info("\n" + "=" * 80)
    logger.info("RESUMEN FINAL")
    logger.info("=" * 80)
    logger.info(f"Total procesados: {processed}/{total_docs}")
    logger.info(f"  ✓ Actualizados: {updated}")
    logger.info(f"  ⚠ Omitidos: {skipped}")
    logger.info(f"  ✗ Errores: {errors}")
    logger.info(f"Tiempo total: {elapsed/60:.2f} minutos")
    logger.info(f"Velocidad promedio: {processed/elapsed:.2f} docs/seg")
    
    if dry_run:
        logger.warning("\nMODO DRY-RUN: No se realizaron cambios")
    else:
        logger.info("\n✅ Regeneración completada exitosamente")
    
    logger.info("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description='Regenera embeddings mejorados para documentos'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Número máximo de documentos a procesar'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Mostrar qué se haría sin hacer cambios'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Tamaño de lote para mostrar progreso (default: 10)'
    )
    
    args = parser.parse_args()
    
    # Confirmación si no es dry-run
    if not args.dry_run:
        print("\n" + "⚠" * 40)
        print("ADVERTENCIA: Este script modificará la base de datos")
        print("⚠" * 40)
        
        if args.limit:
            print(f"\nSe procesarán hasta {args.limit} documentos")
        else:
            print("\nSe procesarán TODOS los documentos")
        
        response = input("\n¿Desea continuar? (escriba 'SI' para confirmar): ")
        if response != 'SI':
            print("Operación cancelada")
            return
    
    # Ejecutar regeneración
    regenerate_embeddings(
        limit=args.limit,
        dry_run=args.dry_run,
        batch_size=args.batch_size
    )


if __name__ == '__main__':
    main()
