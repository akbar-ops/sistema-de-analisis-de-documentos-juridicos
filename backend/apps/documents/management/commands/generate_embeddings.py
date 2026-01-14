from django.core.management.base import BaseCommand
from apps.documents.models import Document, DocumentChunk
from apps.documents.services.embedding_service import get_embedding_service
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Genera embeddings para documentos y chunks existentes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--documents',
            action='store_true',
            help='Genera embeddings solo para resúmenes de documentos',
        )
        parser.add_argument(
            '--chunks',
            action='store_true',
            help='Genera embeddings solo para chunks',
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
            help='Tamaño de lote para procesamiento de chunks',
        )

    def handle(self, *args, **options):
        process_documents = options['documents']
        process_chunks = options['chunks']
        force = options['force']
        batch_size = options['batch_size']

        # Si no se especifica nada, procesar ambos
        if not process_documents and not process_chunks:
            process_documents = True
            process_chunks = True

        # Obtener servicio de embeddings
        self.stdout.write(self.style.SUCCESS('Inicializando servicio de embeddings...'))
        embedding_service = get_embedding_service()
        
        # Procesar documentos
        if process_documents:
            self._generate_document_embeddings(embedding_service, force)
        
        # Procesar chunks
        if process_chunks:
            self._generate_chunk_embeddings(embedding_service, force, batch_size)
        
        self.stdout.write(self.style.SUCCESS('✓ Proceso completado'))

    def _generate_document_embeddings(self, embedding_service, force):
        """Genera embeddings para resúmenes de documentos."""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.WARNING('GENERANDO EMBEDDINGS PARA DOCUMENTOS'))
        self.stdout.write('='*60)
        
        # Filtrar documentos
        if force:
            documents = Document.objects.exclude(summary__isnull=True).exclude(summary='')
        else:
            documents = Document.objects.filter(
                summary_embedding__isnull=True
            ).exclude(summary__isnull=True).exclude(summary='')
        
        total = documents.count()
        
        if total == 0:
            self.stdout.write(self.style.WARNING('No hay documentos para procesar'))
            return
        
        self.stdout.write(f'Documentos a procesar: {total}')
        
        success_count = 0
        error_count = 0
        
        for i, doc in enumerate(documents, 1):
            try:
                # Generar embedding
                embedding = embedding_service.encode_document_summary(doc.summary)
                
                if embedding is not None:
                    doc.summary_embedding = embedding.tolist()
                    doc.save(update_fields=['summary_embedding'])
                    success_count += 1
                    
                    self.stdout.write(
                        f'  [{i}/{total}] ✓ Documento {doc.id}: {doc.title[:50]}...'
                    )
                else:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'  [{i}/{total}] ✗ Documento {doc.id}: Resumen vacío')
                    )
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  [{i}/{total}] ✗ Documento {doc.id}: Error - {str(e)}')
                )
                logger.error(f'Error generando embedding para documento {doc.id}: {e}')
        
        self.stdout.write('\n' + '-'*60)
        self.stdout.write(self.style.SUCCESS(f'Documentos procesados exitosamente: {success_count}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'Documentos con errores: {error_count}'))

    def _generate_chunk_embeddings(self, embedding_service, force, batch_size):
        """Genera embeddings para chunks de documentos."""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.WARNING('GENERANDO EMBEDDINGS PARA CHUNKS'))
        self.stdout.write('='*60)
        
        # Filtrar chunks
        if force:
            chunks = DocumentChunk.objects.exclude(content__isnull=True).exclude(content='')
        else:
            chunks = DocumentChunk.objects.filter(
                content_embedding__isnull=True
            ).exclude(content__isnull=True).exclude(content='')
        
        total = chunks.count()
        
        if total == 0:
            self.stdout.write(self.style.WARNING('No hay chunks para procesar'))
            return
        
        self.stdout.write(f'Chunks a procesar: {total}')
        self.stdout.write(f'Tamaño de lote: {batch_size}')
        
        success_count = 0
        error_count = 0
        
        # Procesar en batches
        chunk_list = list(chunks)
        
        for i in range(0, len(chunk_list), batch_size):
            batch = chunk_list[i:i + batch_size]
            batch_contents = [chunk.content for chunk in batch]
            
            try:
                # Generar embeddings en batch
                embeddings = embedding_service.encode_chunks_batch(batch_contents, batch_size)
                
                # Guardar embeddings
                for chunk, embedding in zip(batch, embeddings):
                    try:
                        chunk.content_embedding = embedding.tolist()
                        chunk.save(update_fields=['content_embedding'])
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        logger.error(f'Error guardando embedding para chunk {chunk.id}: {e}')
                
                # Mostrar progreso cada batch
                progress = min(i + batch_size, total)
                self.stdout.write(
                    f'  Progreso: {progress}/{total} chunks procesados '
                    f'({int(progress/total*100)}%)'
                )
                
            except Exception as e:
                error_count += len(batch)
                self.stdout.write(
                    self.style.ERROR(f'  Error procesando batch {i//batch_size + 1}: {str(e)}')
                )
                logger.error(f'Error generando embeddings en batch: {e}')
        
        self.stdout.write('\n' + '-'*60)
        self.stdout.write(self.style.SUCCESS(f'Chunks procesados exitosamente: {success_count}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'Chunks con errores: {error_count}'))
