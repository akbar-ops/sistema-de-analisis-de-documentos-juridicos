# apps/documents/management/commands/regenerate_chunk_embeddings.py
"""
Comando para regenerar embeddings de chunks con el modelo mejorado.

Este comando:
1. Limpia el contenido de cada chunk (elimina encabezados repetitivos)
2. Genera embeddings de 768 dimensiones (paraphrase-multilingual-mpnet-base-v2)
3. Guarda en el nuevo campo clean_content_embedding

Uso:
    python manage.py regenerate_chunk_embeddings
    python manage.py regenerate_chunk_embeddings --document-id <uuid>
    python manage.py regenerate_chunk_embeddings --batch-size 50
    python manage.py regenerate_chunk_embeddings --dry-run
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.documents.models import Document, DocumentChunk, DocumentStatus
from apps.documents.services.chunk_embedding_service import get_chunk_embedding_service
import logging
import time

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Regenera embeddings de chunks con modelo de 768d y texto limpio para RAG mejorado'

    def add_arguments(self, parser):
        parser.add_argument(
            '--document-id',
            type=str,
            help='Procesa solo los chunks del documento con este ID',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenera embeddings incluso si ya existen',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=32,
            help='Número de chunks a procesar por lote (default: 32)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo muestra estadísticas, sin hacer cambios',
        )
        parser.add_argument(
            '--skip-empty',
            action='store_true',
            default=True,
            help='Omitir chunks que quedan vacíos después de limpiar (default: True)',
        )

    def handle(self, *args, **options):
        document_id = options['document_id']
        force = options['force']
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        skip_empty = options['skip_empty']

        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('REGENERACIÓN DE EMBEDDINGS DE CHUNKS PARA RAG'))
        self.stdout.write(self.style.SUCCESS('='*70))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('*** MODO DRY-RUN: No se harán cambios ***'))
        
        self.stdout.write(f'\nConfiguración:')
        self.stdout.write(f'  • Batch size: {batch_size}')
        self.stdout.write(f'  • Force: {force}')
        self.stdout.write(f'  • Skip empty chunks: {skip_empty}')
        self.stdout.write(f'  • Modelo: paraphrase-multilingual-mpnet-base-v2 (768d)')
        self.stdout.write('')

        # Inicializar servicio
        self.stdout.write('Inicializando servicio de embeddings...')
        embedding_service = get_chunk_embedding_service()

        # Filtrar chunks
        if document_id:
            try:
                document = Document.objects.get(document_id=document_id)
                chunks = DocumentChunk.objects.filter(document_id=document)
                self.stdout.write(f'Procesando chunks del documento: {document.title[:50]}...')
            except Document.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Documento no encontrado: {document_id}'))
                return
        else:
            # Todos los chunks de documentos procesados
            chunks = DocumentChunk.objects.filter(
                document_id__status=DocumentStatus.PROCESSED
            )
            
            if not force:
                # Solo chunks sin clean_content_embedding
                chunks = chunks.filter(clean_content_embedding__isnull=True)

        total = chunks.count()
        
        if total == 0:
            self.stdout.write(self.style.WARNING('\n✓ No hay chunks para procesar'))
            if not force:
                self.stdout.write('  (usa --force para regenerar todos)')
            return

        self.stdout.write(f'\nChunks a procesar: {total}')
        self.stdout.write('-'*70)

        # Estadísticas
        stats = {
            'success': 0,
            'errors': 0,
            'skipped_empty': 0,
            'total_time': 0,
            'documents_processed': set()
        }

        start_time = time.time()
        
        # Procesar en batches
        chunk_ids = list(chunks.values_list('chunk_id', flat=True))
        
        for i in range(0, len(chunk_ids), batch_size):
            batch_ids = chunk_ids[i:i + batch_size]
            batch_chunks = DocumentChunk.objects.filter(chunk_id__in=batch_ids).select_related('document_id')
            
            batch_num = (i // batch_size) + 1
            total_batches = (len(chunk_ids) + batch_size - 1) // batch_size
            
            self.stdout.write(f'\n[Batch {batch_num}/{total_batches}] Procesando {len(batch_chunks)} chunks...')
            
            if dry_run:
                # Solo contar
                for chunk in batch_chunks:
                    cleaned = embedding_service.clean_chunk_content(chunk.content)
                    if cleaned.strip():
                        stats['success'] += 1
                    else:
                        stats['skipped_empty'] += 1
                    stats['documents_processed'].add(str(chunk.document_id.document_id))
                continue
            
            # Preparar contenidos para batch
            contents = [chunk.content for chunk in batch_chunks]
            
            # Generar embeddings en batch
            try:
                embeddings = embedding_service.generate_batch_embeddings(
                    contents,
                    normalize=True,
                    apply_cleaning=True,
                    batch_size=batch_size
                )
                
                # Guardar embeddings
                with transaction.atomic():
                    for chunk, embedding in zip(batch_chunks, embeddings):
                        if embedding is not None:
                            chunk.clean_content_embedding = embedding.tolist()
                            chunk.save(update_fields=['clean_content_embedding'])
                            stats['success'] += 1
                            stats['documents_processed'].add(str(chunk.document_id.document_id))
                        else:
                            if skip_empty:
                                stats['skipped_empty'] += 1
                            else:
                                stats['errors'] += 1
                
                self.stdout.write(self.style.SUCCESS(
                    f'   ✓ Batch completado: {sum(1 for e in embeddings if e is not None)} embeddings generados'
                ))
                
            except Exception as e:
                stats['errors'] += len(batch_chunks)
                self.stdout.write(self.style.ERROR(f'   ✗ Error en batch: {e}'))
                logger.error(f'Error procesando batch: {e}', exc_info=True)

        # Resumen final
        total_time = time.time() - start_time
        stats['total_time'] = total_time

        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('RESUMEN'))
        self.stdout.write('='*70)
        self.stdout.write(f'Chunks procesados exitosamente: {stats["success"]}')
        self.stdout.write(f'Chunks omitidos (vacíos): {stats["skipped_empty"]}')
        self.stdout.write(f'Errores: {stats["errors"]}')
        self.stdout.write(f'Documentos afectados: {len(stats["documents_processed"])}')
        self.stdout.write(f'Tiempo total: {total_time:.2f}s')
        
        if stats['success'] > 0:
            self.stdout.write(f'Tiempo promedio por chunk: {total_time/stats["success"]*1000:.2f}ms')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n*** Esto fue un dry-run. Ejecuta sin --dry-run para aplicar cambios ***'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ RAG ahora usará los nuevos embeddings de 768d'))
            self.stdout.write('  El chat con documentos debería dar mejores resultados.')
