# apps/documents/management/commands/regenerate_embeddings.py
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.documents.models import Document
from apps.documents.services.embedding_service import get_embedding_service
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Regenera los enhanced embeddings para documentos existentes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--document-id',
            type=str,
            help='Regenerar embedding solo para un documento específico (UUID)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Número de documentos a procesar por batch (default: 10)',
        )
        parser.add_argument(
            '--only-missing',
            action='store_true',
            help='Solo regenerar embeddings para documentos que no tienen enhanced_embedding',
        )

    def handle(self, *args, **options):
        document_id = options.get('document_id')
        batch_size = options.get('batch_size')
        only_missing = options.get('only_missing')
        
        embedding_service = get_embedding_service()
        
        # Filtrar documentos a procesar
        if document_id:
            # Procesar un solo documento
            try:
                documents = [Document.objects.get(document_id=document_id)]
                self.stdout.write(f"Procesando documento {document_id}...")
            except Document.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Documento {document_id} no encontrado")
                )
                return
        else:
            # Procesar todos los documentos procesados
            queryset = Document.objects.filter(status='processed')
            
            if only_missing:
                queryset = queryset.filter(enhanced_embedding__isnull=True)
            
            documents = list(queryset.select_related('doc_type', 'legal_area'))
            
            self.stdout.write(
                f"Encontrados {len(documents)} documentos para procesar"
            )
        
        if not documents:
            self.stdout.write(self.style.WARNING("No hay documentos para procesar"))
            return
        
        # Procesar documentos
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        for i, document in enumerate(documents, 1):
            try:
                self.stdout.write(
                    f"[{i}/{len(documents)}] Procesando: {document.title[:50]}..."
                )
                
                # Verificar que tenga la información necesaria
                if not document.summary and not document.title:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Documento {document.document_id} no tiene información suficiente. Omitiendo."
                        )
                    )
                    skipped_count += 1
                    continue
                
                # Preparar datos para enhanced embedding
                document_persons = document.document_persons.select_related('person').all()
                persons_data = [
                    {
                        'name': dp.person.name,
                        'role': dp.role
                    }
                    for dp in document_persons
                ]
                
                enhanced_data = {
                    'title': document.title,
                    'legal_area': document.legal_area.name if document.legal_area else None,
                    'legal_subject': document.legal_subject,
                    'summary': document.summary,
                    'issue_place': document.issue_place,
                    'case_number': document.case_number,
                    'resolution_number': document.resolution_number,
                    'persons': persons_data
                }
                
                # Generar enhanced embedding
                enhanced_embedding = embedding_service.encode_enhanced_document(enhanced_data)
                
                if enhanced_embedding is not None:
                    # Guardar en la base de datos
                    with transaction.atomic():
                        document.enhanced_embedding = enhanced_embedding.tolist()
                        document.save(update_fields=['enhanced_embedding'])
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ Enhanced embedding generado exitosamente"
                        )
                    )
                    success_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  No se pudo generar embedding (datos insuficientes)"
                        )
                    )
                    skipped_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"  ✗ Error procesando documento {document.document_id}: {e}"
                    )
                )
                error_count += 1
                logger.error(f"Error regenerating embedding for {document.document_id}: {e}")
        
        # Resumen final
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS(f"Procesamiento completado:"))
        self.stdout.write(f"  Exitosos: {success_count}")
        self.stdout.write(f"  Omitidos: {skipped_count}")
        self.stdout.write(f"  Errores: {error_count}")
        self.stdout.write("="*60)
