from django.core.management.base import BaseCommand
from apps.documents.models import Document, DocumentChunk
from apps.documents.services.chunking_service import ChunkingService
from apps.documents.services.embedding_service import get_embedding_service
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Genera chunks y embeddings para documentos existentes que no los tienen (habilita RAG)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenera chunks incluso si el documento ya tiene chunks',
        )
        parser.add_argument(
            '--document-id',
            type=str,
            help='Procesa solo el documento con este ID',
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
            '--skip-embeddings',
            action='store_true',
            help='Solo crear chunks, no generar embeddings',
        )

    def handle(self, *args, **options):
        force = options['force']
        document_id = options['document_id']
        chunk_size = options['chunk_size']
        chunk_overlap = options['chunk_overlap']
        skip_embeddings = options['skip_embeddings']

        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('GENERADOR DE CHUNKS PARA RAG'))
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(f'Chunk size: {chunk_size} caracteres')
        self.stdout.write(f'Chunk overlap: {chunk_overlap} caracteres')
        self.stdout.write(f'Force: {force}')
        self.stdout.write(f'Skip embeddings: {skip_embeddings}')
        self.stdout.write('')

        # Inicializar servicios
        chunking_service = ChunkingService(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        embedding_service = None
        if not skip_embeddings:
            self.stdout.write('Inicializando servicio de embeddings...')
            embedding_service = get_embedding_service()

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
            # Obtener documentos con contenido y file_path
            documents = Document.objects.exclude(content__isnull=True).exclude(content='')
            
            if not force:
                # Excluir documentos que ya tienen chunks con embeddings
                docs_with_chunks = DocumentChunk.objects.filter(
                    content_embedding__isnull=False
                ).values_list('document_id', flat=True).distinct()
                
                documents = documents.exclude(document_id__in=docs_with_chunks)

        total = documents.count()
        
        if total == 0:
            self.stdout.write(self.style.WARNING('\n✓ No hay documentos para procesar'))
            self.stdout.write('  (todos los documentos ya tienen chunks con embeddings)')
            return

        self.stdout.write(f'\nDocumentos a procesar: {total}')
        self.stdout.write('-'*70)

        success_count = 0
        error_count = 0
        total_chunks = 0

        for i, doc in enumerate(documents, 1):
            try:
                self.stdout.write(f'\n[{i}/{total}] Procesando: {doc.title[:60]}...')
                
                # Verificar si tiene file_path (necesario para extraer PDF por páginas)
                if not doc.file_path:
                    self.stdout.write(self.style.WARNING(f'  ⚠ Sin archivo PDF, usando método de texto'))
                
                # Crear chunks
                num_chunks = chunking_service.create_chunks_for_document(
                    doc,
                    method='contextual' if doc.file_path else 'simple'
                )
                
                if num_chunks == 0:
                    self.stdout.write(self.style.WARNING(f'  ⚠ No se crearon chunks'))
                    continue
                
                self.stdout.write(self.style.SUCCESS(f'  ✓ Creados {num_chunks} chunks'))
                total_chunks += num_chunks
                
                # Generar embeddings para los chunks
                if not skip_embeddings and embedding_service:
                    chunks = DocumentChunk.objects.filter(
                        document_id=doc
                    ).order_by('order_number')
                    
                    if chunks.exists():
                        chunk_contents = [chunk.content for chunk in chunks]
                        chunk_embeddings = embedding_service.encode_chunks_batch(
                            chunk_contents,
                            batch_size=32
                        )
                        
                        # Guardar embeddings
                        for chunk, embedding in zip(chunks, chunk_embeddings):
                            chunk.content_embedding = embedding.tolist()
                            chunk.save(update_fields=['content_embedding'])
                        
                        self.stdout.write(self.style.SUCCESS(f'  ✓ Generados {len(chunk_embeddings)} embeddings'))
                
                success_count += 1
                
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
                logger.error(f'Error procesando documento {doc.document_id}: {e}', exc_info=True)

        # Resumen final
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('RESUMEN'))
        self.stdout.write('='*70)
        self.stdout.write(f'Documentos procesados exitosamente: {success_count}')
        self.stdout.write(f'Documentos con errores: {error_count}')
        self.stdout.write(f'Total de chunks creados: {total_chunks}')
        
        if success_count > 0:
            self.stdout.write(self.style.SUCCESS('\n✓ RAG habilitado para los documentos procesados'))
            self.stdout.write('  Los usuarios ahora pueden hacer preguntas específicas')
            self.stdout.write('  y el sistema buscará las partes más relevantes del documento.')
