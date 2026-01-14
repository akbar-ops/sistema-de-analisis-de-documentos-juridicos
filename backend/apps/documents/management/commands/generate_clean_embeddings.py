# apps/documents/management/commands/generate_clean_embeddings.py
import logging
import time
from django.core.management.base import BaseCommand
from apps.documents.models import Document
from apps.documents.services.clean_embeddings_service import get_clean_embedding_service

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate clean_embeddings for documents that do not have one'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Number of documents to process in chunks (default: 50)'
        )
        parser.add_argument(
            '--document-id',
            type=str,
            help='Process a specific document by UUID'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regeneration of all embeddings, even if they exist'
        )
        parser.add_argument(
            '--status',
            type=str,
            default='processed',
            help='Only process documents with this status (default: processed)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        document_id = options.get('document_id')
        force = options['force']
        doc_status = options.get('status')
        dry_run = options['dry_run']

        self.stdout.write(self.style.NOTICE('=' * 60))
        self.stdout.write(self.style.NOTICE('Generate Clean Embeddings Command'))
        self.stdout.write(self.style.NOTICE('=' * 60))

        # 1. Inicializar Servicio
        try:
            embedding_service = get_clean_embedding_service()
            self.stdout.write(self.style.SUCCESS(
                f'✅ Embedding service initialized (model: {embedding_service.model_name})'
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error initializing embedding service: {e}'))
            return

        # 2. Construir Queryset
        if document_id:
            queryset = Document.objects.filter(document_id=document_id)
            if not queryset.exists():
                self.stdout.write(self.style.ERROR(f'❌ Document {document_id} not found'))
                return
        else:
            queryset = Document.objects.all()
            
            if doc_status:
                queryset = queryset.filter(status=doc_status)
            
            if not force:
                queryset = queryset.filter(clean_embedding__isnull=True)
            
            # CORRECCIÓN 1: Usar 'content' en lugar de 'extracted_text'
            queryset = queryset.exclude(content__isnull=True)
            queryset = queryset.exclude(content='')

        total_docs = queryset.count()
        
        if total_docs == 0:
            self.stdout.write(self.style.SUCCESS(
                '✅ No documents to process. All documents already have clean_embedding.'
            ))
            return

        self.stdout.write(self.style.NOTICE(f'📊 Found {total_docs} documents to process'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN - No changes will be made'))
            for doc in queryset[:5]:
                # CORRECCIÓN 1: Usar 'content'
                text_preview = (doc.content or '')[:100]
                self.stdout.write(f'  - {doc.document_id}: {doc.title[:50]}...')
                self.stdout.write(f'    Text preview: {text_preview}...')
            return

        # 3. Procesar Documentos
        processed = 0
        errors = 0
        start_time = time.time()

        # CORRECCIÓN 3: Usar iterator() para evitar problemas de memoria y paginación
        # Esto es más seguro que el bucle "range" cuando el queryset cambia dinámicamente
        self.stdout.write(f"Starting processing with batch size {batch_size}...")
        
        for doc in queryset.iterator(chunk_size=batch_size):
            try:
                # CORRECCIÓN 1: Usar 'content'
                text = doc.content
                if not text or len(text.strip()) < 50:
                    self.stdout.write(self.style.WARNING(
                        f'⚠️ Skipping {doc.document_id}: Text too short ({len(text or "")} chars)'
                    ))
                    continue
                
                # CORRECCIÓN 2: Llamar al método correcto 'generate_document_embedding'
                embedding = embedding_service.generate_document_embedding(text)
                
                if embedding is not None:
                    # Guardar embedding (convertir numpy array a list para JSON/PGVector)
                    doc.clean_embedding = list(embedding)
                    doc.save(update_fields=['clean_embedding'])
                    processed += 1
                    
                    # Log cada 10 docs para no saturar la terminal
                    if processed % 10 == 0:
                        self.stdout.write(self.style.SUCCESS(
                            f'✅ [{processed}/{total_docs}] {doc.document_id} processed'
                        ))
                else:
                    self.stdout.write(self.style.WARNING(
                        f'⚠️ {doc.document_id}: Failed to generate embedding (None returned)'
                    ))
                    errors += 1
                    
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(
                    f'❌ Error processing {doc.document_id}: {e}'
                ))

        # Resumen Final
        elapsed = time.time() - start_time
        rate = processed / elapsed if elapsed > 0 else 0
        
        self.stdout.write(self.style.NOTICE('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'✅ Processing complete!'))
        self.stdout.write(f'   Total processed: {processed}')
        self.stdout.write(f'   Errors: {errors}')
        self.stdout.write(f'   Time elapsed: {elapsed:.1f} seconds')
        self.stdout.write(f'   Average rate: {rate:.2f} docs/sec')