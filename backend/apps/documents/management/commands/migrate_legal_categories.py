"""
Management command to migrate existing documents to new legal categories
Usage: python manage.py migrate_legal_categories [--dry-run]
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from apps.documents.models import LegalArea, DocumentType, Document


class Command(BaseCommand):
    help = 'Migrate existing documents to new legal area and document type categories'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show changes without applying them',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))
        
        # Mapping tables for migration
        area_mapping = {
            'Familia': ['Familia Civil', 'Familia Tutelar'],  # Needs manual review
            'Constitucional': 'Derecho Constitucional',
            'Administrativo': 'Contencioso Administrativo',
            'Tributario': 'Otros',  # No existe en nuevo sistema
        }
        
        type_mapping = {
            'Sentencia': 'Sentencias',
            'Auto': 'Autos',
            'Decreto': 'Decretos',
            'Demanda': 'Otros',
            'Resolución': 'Autos',  # Generalmente son autos
            'Dictamen': 'Otros',
            'Informe': 'Otros',
            'Oficio': 'Otros',
            'Acta': 'Otros',
            'Cédula': 'Otros',
            'Notificación': 'Decretos',  # Generalmente son decretos
            'Escrito': 'Otros',
            'Recurso': 'Otros',
            'Contrato': 'Otros',
            'Acuerdo': 'Otros',
            'Medida Cautelar': 'Autos',
            'Amparo': 'Sentencias',  # Generalmente sentencias
            'Providencia': 'Decretos',
        }
        
        self.stdout.write('\n=== MIGRATING LEGAL AREAS ===\n')
        self._migrate_areas(area_mapping, dry_run)
        
        self.stdout.write('\n=== MIGRATING DOCUMENT TYPES ===\n')
        self._migrate_types(type_mapping, dry_run)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN completed - No changes were saved'))
        else:
            self.stdout.write(self.style.SUCCESS('\nMigration completed successfully!'))

    def _migrate_areas(self, mapping, dry_run):
        """Migrate legal areas"""
        for old_name, new_name in mapping.items():
            try:
                old_area = LegalArea.objects.get(name=old_name)
                
                if isinstance(new_name, list):
                    # Special case: Familia needs manual review
                    count = Document.objects.filter(legal_area=old_area).count()
                    self.stdout.write(
                        self.style.WARNING(
                            f'  ⚠ "{old_name}" ({count} docs) needs manual review:'
                        )
                    )
                    for option in new_name:
                        self.stdout.write(f'     - Option: {option}')
                    self.stdout.write(
                        f'     Run: Document.objects.filter(legal_area__name="{old_name}").update(...)'
                    )
                else:
                    new_area = LegalArea.objects.get(name=new_name)
                    count = Document.objects.filter(legal_area=old_area).count()
                    
                    if count > 0:
                        self.stdout.write(f'  Migrating "{old_name}" → "{new_name}" ({count} documents)')
                        
                        if not dry_run:
                            Document.objects.filter(legal_area=old_area).update(legal_area=new_area)
                            # Optionally deactivate old area
                            # old_area.is_active = False
                            # old_area.save()
                        
                        self.stdout.write(self.style.SUCCESS(f'    ✓ Migrated {count} documents'))
                    else:
                        self.stdout.write(f'  No documents found for "{old_name}"')
                        
            except LegalArea.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'  ⚠ Area "{old_name}" not found, skipping'))

    def _migrate_types(self, mapping, dry_run):
        """Migrate document types"""
        for old_name, new_name in mapping.items():
            try:
                old_type = DocumentType.objects.get(name=old_name)
                new_type = DocumentType.objects.get(name=new_name)
                
                count = Document.objects.filter(doc_type=old_type).count()
                
                if count > 0:
                    self.stdout.write(f'  Migrating "{old_name}" → "{new_name}" ({count} documents)')
                    
                    if not dry_run:
                        Document.objects.filter(doc_type=old_type).update(doc_type=new_type)
                        # Optionally deactivate old type
                        # old_type.is_active = False
                        # old_type.save()
                    
                    self.stdout.write(self.style.SUCCESS(f'    ✓ Migrated {count} documents'))
                else:
                    self.stdout.write(f'  No documents found for "{old_name}"')
                    
            except DocumentType.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'  ⚠ Type "{old_name}" not found, skipping'))
