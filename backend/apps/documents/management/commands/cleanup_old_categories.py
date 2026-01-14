"""
Management command to cleanup old legal categories after migration
Usage: python manage.py cleanup_old_categories [--dry-run] [--delete]
"""
from django.core.management.base import BaseCommand
from apps.documents.models import LegalArea, DocumentType, Document


class Command(BaseCommand):
    help = 'Cleanup old legal area and document type categories that are no longer in use'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned up without making changes',
        )
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Delete old categories (default is to just deactivate)',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        delete_mode = options.get('delete', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved\n'))
        
        # Categories that should be kept (current system)
        valid_areas = [
            'Penal', 'Laboral', 'Familia Civil', 'Civil', 'Familia Tutelar',
            'Comercial', 'Derecho Constitucional', 'Contencioso Administrativo',
            'Familia Penal', 'Extension de Dominio', 'Otros'
        ]
        
        valid_types = ['Sentencias', 'Autos', 'Decretos', 'Otros']
        
        self.stdout.write('=== CHECKING LEGAL AREAS ===\n')
        self._cleanup_areas(valid_areas, dry_run, delete_mode)
        
        self.stdout.write('\n=== CHECKING DOCUMENT TYPES ===\n')
        self._cleanup_types(valid_types, dry_run, delete_mode)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN completed - No changes were saved'))
        else:
            self.stdout.write(self.style.SUCCESS('\nCleanup completed successfully!'))

    def _cleanup_areas(self, valid_areas, dry_run, delete_mode):
        """Cleanup old legal areas"""
        old_areas = LegalArea.objects.exclude(name__in=valid_areas)
        
        if not old_areas.exists():
            self.stdout.write(self.style.SUCCESS('  ✓ No old legal areas found'))
            return
        
        for area in old_areas:
            doc_count = Document.objects.filter(legal_area=area).count()
            
            if doc_count > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⚠ Cannot cleanup "{area.name}" - still has {doc_count} documents'
                    )
                )
                self.stdout.write(
                    f'     Run migrate_legal_categories first to move these documents'
                )
            else:
                action = 'DELETE' if delete_mode else 'DEACTIVATE'
                self.stdout.write(f'  {action}: "{area.name}" (0 documents)')
                
                if not dry_run:
                    if delete_mode:
                        area.delete()
                        self.stdout.write(self.style.SUCCESS(f'    ✓ Deleted "{area.name}"'))
                    else:
                        area.is_active = False
                        area.save()
                        self.stdout.write(self.style.SUCCESS(f'    ✓ Deactivated "{area.name}"'))

    def _cleanup_types(self, valid_types, dry_run, delete_mode):
        """Cleanup old document types"""
        old_types = DocumentType.objects.exclude(name__in=valid_types)
        
        if not old_types.exists():
            self.stdout.write(self.style.SUCCESS('  ✓ No old document types found'))
            return
        
        for doc_type in old_types:
            doc_count = Document.objects.filter(doc_type=doc_type).count()
            
            if doc_count > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⚠ Cannot cleanup "{doc_type.name}" - still has {doc_count} documents'
                    )
                )
                self.stdout.write(
                    f'     Run migrate_legal_categories first to move these documents'
                )
            else:
                action = 'DELETE' if delete_mode else 'DEACTIVATE'
                self.stdout.write(f'  {action}: "{doc_type.name}" (0 documents)')
                
                if not dry_run:
                    if delete_mode:
                        doc_type.delete()
                        self.stdout.write(self.style.SUCCESS(f'    ✓ Deleted "{doc_type.name}"'))
                    else:
                        doc_type.is_active = False
                        doc_type.save()
                        self.stdout.write(self.style.SUCCESS(f'    ✓ Deactivated "{doc_type.name}"'))
