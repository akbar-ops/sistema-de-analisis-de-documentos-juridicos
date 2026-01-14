# apps/documents/management/commands/regenerate_chunks_clean.py
"""
Comando para regenerar chunks de documentos con limpieza de encabezados.

Este comando:
1. Limpia encabezados/pies de página repetitivos de cada documento
2. Regenera los chunks con texto limpio
3. Regenera embeddings de los chunks
4. Opcionalmente regenera embeddings del documento

Uso:
    python manage.py regenerate_chunks_clean
    python manage.py regenerate_chunks_clean --document-id <uuid>
    python manage.py regenerate_chunks_clean --force --regenerate-embeddings
    python manage.py regenerate_chunks_clean --dry-run  # Ver qué se eliminaría
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.documents.models import Document, DocumentChunk, DocumentStatus
from apps.documents.services.chunking_service import ChunkingService
from apps.documents.services.embedding_service import get_embedding_service
from apps.documents.services.header_cleaner_service import get_header_cleaner_service
from apps.documents.services.clean_embeddings_service import get_clean_embedding_service
import logging
import time

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Regenera chunks de documentos con limpieza de encabezados judiciales'

    def add_arguments(self, parser):
        parser.add_argument(
            '--document-id',
            type=str,
            help='Procesa solo el documento con este ID',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Procesa todos los documentos, incluso los que ya tienen chunks',
        )
        parser.add_argument(
            '--chunk-size',
            type=int,
            default=1000,
            help='Tamaño de cada chunk en caracteres (default: 1000)',
        )
        parser.add_argument(
            '--chunk-overlap',
            type=int,
            default=200,
            help='Solapamiento entre chunks en caracteres (default: 200)',
        )
        parser.add_argument(
            '--regenerate-embeddings',
            action='store_true',
            help='También regenera el embedding limpio del documento',
        )
        parser.add_argument(
            '--regenerate-content',
            action='store_true',
            help='Re-extrae el texto del PDF y lo limpia (más lento)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo muestra qué se limpiaría, sin hacer cambios',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Número de documentos a procesar por lote (default: 10)',
        )
        parser.add_argument(
            '--skip-chunk-embeddings',
            action='store_true',
            help='No generar embeddings para los chunks (más rápido)',
        )

    def handle(self, *args, **options):
        document_id = options['document_id']
        force = options['force']
        chunk_size = options['chunk_size']
        chunk_overlap = options['chunk_overlap']
        regenerate_embeddings = options['regenerate_embeddings']
        regenerate_content = options['regenerate_content']
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        skip_chunk_embeddings = options['skip_chunk_embeddings']

        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('REGENERACIÓN DE CHUNKS CON LIMPIEZA DE ENCABEZADOS'))
        self.stdout.write(self.style.SUCCESS('='*70))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('*** MODO DRY-RUN: No se harán cambios ***'))
        
        self.stdout.write(f'\nConfiguración:')
        self.stdout.write(f'  • Chunk size: {chunk_size} caracteres')
        self.stdout.write(f'  • Chunk overlap: {chunk_overlap} caracteres')
        self.stdout.write(f'  • Force: {force}')
        self.stdout.write(f'  • Regenerar embeddings documento: {regenerate_embeddings}')
        self.stdout.write(f'  • Re-extraer contenido: {regenerate_content}')
        self.stdout.write(f'  • Skip chunk embeddings: {skip_chunk_embeddings}')
        self.stdout.write('')

        # Inicializar servicios
        header_cleaner = get_header_cleaner_service()
        chunking_service = ChunkingService(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            clean_headers=True  # Forzar limpieza
        )
        
        embedding_service = None
        clean_embedding_service = None
        
        if not skip_chunk_embeddings:
            self.stdout.write('Inicializando servicio de embeddings para chunks...')
            embedding_service = get_embedding_service()
        
        if regenerate_embeddings:
            self.stdout.write('Inicializando servicio de embeddings limpios...')
            clean_embedding_service = get_clean_embedding_service()

        # Filtrar documentos
        if document_id:
            try:
                documents = Document.objects.filter(document_id=document_id)
                if not documents.exists():
                    self.stdout.write(self.style.ERROR(f'Documento no encontrado: {document_id}'))
                    return
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error buscando documento: {e}'))
                return
        else:
            # Obtener documentos procesados con contenido
            documents = Document.objects.filter(
                status=DocumentStatus.PROCESSED
            ).exclude(content__isnull=True).exclude(content='')
            
            if not force:
                # Solo documentos sin chunks o con chunks antiguos
                self.stdout.write(self.style.WARNING(
                    'Tip: Usa --force para procesar todos los documentos'
                ))

        total = documents.count()
        
        if total == 0:
            self.stdout.write(self.style.WARNING('\n✓ No hay documentos para procesar'))
            return

        self.stdout.write(f'\nDocumentos a procesar: {total}')
        self.stdout.write('-'*70)

        # Estadísticas
        stats = {
            'success': 0,
            'errors': 0,
            'total_chunks_before': 0,
            'total_chunks_after': 0,
            'total_chars_cleaned': 0,
            'total_time': 0
        }

        start_time = time.time()

        for i, document in enumerate(documents.iterator(), 1):
            doc_start = time.time()
            
            self.stdout.write(f'\n[{i}/{total}] Procesando: {document.title[:50]}...')
            self.stdout.write(f'    ID: {document.document_id}')
            
            try:
                # Contar chunks actuales
                current_chunks = DocumentChunk.objects.filter(document_id=document).count()
                stats['total_chunks_before'] += current_chunks
                
                if dry_run:
                    # Solo mostrar estadísticas de limpieza
                    if document.content:
                        cleaned = header_cleaner.clean_document_text(document.content)
                        cleaning_stats = header_cleaner.get_cleaning_stats(document.content, cleaned)
                        
                        self.stdout.write(f'    Estadísticas de limpieza:')
                        self.stdout.write(f'      - Caracteres originales: {cleaning_stats["original_chars"]:,}')
                        self.stdout.write(f'      - Caracteres después: {cleaning_stats["cleaned_chars"]:,}')
                        self.stdout.write(f'      - Removidos: {cleaning_stats["chars_removed"]:,} ({cleaning_stats["chars_removed_percent"]}%)')
                        self.stdout.write(f'      - Líneas removidas: {cleaning_stats["lines_removed"]}')
                        
                        stats['total_chars_cleaned'] += cleaning_stats['chars_removed']
                    
                    stats['success'] += 1
                    continue
                
                with transaction.atomic():
                    # Paso 1: Limpiar contenido del documento
                    if document.content:
                        original_content = document.content
                        cleaned_content = header_cleaner.clean_document_text(original_content)
                        cleaning_stats = header_cleaner.get_cleaning_stats(original_content, cleaned_content)
                        
                        # Actualizar contenido del documento
                        document.content = cleaned_content
                        document.save(update_fields=['content'])
                        
                        stats['total_chars_cleaned'] += cleaning_stats['chars_removed']
                        
                        self.stdout.write(self.style.SUCCESS(
                            f'    ✓ Limpieza: {cleaning_stats["chars_removed"]:,} chars removidos '
                            f'({cleaning_stats["chars_removed_percent"]}%)'
                        ))
                    
                    # Paso 2: Eliminar chunks antiguos
                    if current_chunks > 0:
                        DocumentChunk.objects.filter(document_id=document).delete()
                        self.stdout.write(f'    ✓ Eliminados {current_chunks} chunks antiguos')
                    
                    # Paso 3: Crear nuevos chunks
                    if document.file_path:
                        num_chunks = chunking_service.create_chunks_for_document(
                            document,
                            method='contextual'
                        )
                        stats['total_chunks_after'] += num_chunks
                        self.stdout.write(self.style.SUCCESS(f'    ✓ Creados {num_chunks} chunks nuevos'))
                    
                    # Paso 4: Generar embeddings para chunks (si no skip)
                    if not skip_chunk_embeddings and embedding_service:
                        chunks = DocumentChunk.objects.filter(document_id=document)
                        chunks_with_embeddings = 0
                        
                        for chunk in chunks:
                            try:
                                embedding = embedding_service.generate_embedding(chunk.content)
                                if embedding is not None:
                                    chunk.content_embedding = embedding.tolist()
                                    chunk.save(update_fields=['content_embedding'])
                                    chunks_with_embeddings += 1
                            except Exception as e:
                                logger.warning(f'Error generando embedding para chunk: {e}')
                        
                        if chunks_with_embeddings > 0:
                            self.stdout.write(self.style.SUCCESS(
                                f'    ✓ Embeddings generados para {chunks_with_embeddings} chunks'
                            ))
                    
                    # Paso 5: Regenerar embedding del documento (si solicitado)
                    if regenerate_embeddings and clean_embedding_service:
                        try:
                            embedding = clean_embedding_service.generate_document_embedding(
                                document.content
                            )
                            if embedding is not None:
                                document.clean_embedding = embedding.tolist()
                                document.save(update_fields=['clean_embedding'])
                                self.stdout.write(self.style.SUCCESS(
                                    f'    ✓ Embedding de documento regenerado'
                                ))
                        except Exception as e:
                            logger.warning(f'Error regenerando embedding de documento: {e}')
                
                stats['success'] += 1
                
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f'    ✗ Error: {e}'))
                logger.error(f'Error procesando documento {document.document_id}: {e}', exc_info=True)
            
            doc_time = time.time() - doc_start
            self.stdout.write(f'    Tiempo: {doc_time:.2f}s')

        # Resumen final
        total_time = time.time() - start_time
        stats['total_time'] = total_time

        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('RESUMEN'))
        self.stdout.write('='*70)
        self.stdout.write(f'Documentos procesados: {stats["success"]}/{total}')
        self.stdout.write(f'Errores: {stats["errors"]}')
        self.stdout.write(f'Caracteres limpiados (total): {stats["total_chars_cleaned"]:,}')
        
        if not dry_run:
            self.stdout.write(f'Chunks antes: {stats["total_chunks_before"]}')
            self.stdout.write(f'Chunks después: {stats["total_chunks_after"]}')
        
        self.stdout.write(f'Tiempo total: {total_time:.2f}s')
        self.stdout.write(f'Tiempo promedio por documento: {total_time/max(stats["success"], 1):.2f}s')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n*** Esto fue un dry-run. Ejecuta sin --dry-run para aplicar cambios ***'))
