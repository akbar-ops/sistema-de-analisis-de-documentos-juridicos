"""
Quick verification script to check if all categories are properly configured
Usage: python manage.py verify_categories
"""
from django.core.management.base import BaseCommand
from apps.documents.models import LegalArea, DocumentType
from apps.documents.services.constants import LEGAL_AREAS, DOCUMENT_TYPES


class Command(BaseCommand):
    help = 'Verify that all categories are properly configured'

    def handle(self, *args, **options):
        self.stdout.write('=' * 60)
        self.stdout.write('VERIFICACIÓN DE CATEGORÍAS LEGALES')
        self.stdout.write('=' * 60)
        
        all_ok = True
        
        # Check Legal Areas
        self.stdout.write('\n📋 Verificando Áreas Legales...\n')
        all_ok = self._verify_areas() and all_ok
        
        # Check Document Types
        self.stdout.write('\n📋 Verificando Tipos de Documentos...\n')
        all_ok = self._verify_types() and all_ok
        
        # Summary
        self.stdout.write('\n' + '=' * 60)
        if all_ok:
            self.stdout.write(self.style.SUCCESS('✅ TODAS LAS VERIFICACIONES PASARON'))
            self.stdout.write(self.style.SUCCESS('El sistema está listo para usar las nuevas categorías'))
        else:
            self.stdout.write(self.style.ERROR('❌ HAY PROBLEMAS QUE CORREGIR'))
            self.stdout.write('Ejecuta: python manage.py populate_catalogs')
        self.stdout.write('=' * 60 + '\n')
        
        return 0 if all_ok else 1

    def _verify_areas(self):
        """Verify legal areas"""
        all_ok = True
        
        # Expected areas from constants
        expected = set(LEGAL_AREAS)
        
        # Get actual areas from database
        actual = set(LegalArea.objects.filter(is_active=True).values_list('name', flat=True))
        
        # Check if all expected areas exist
        missing = expected - actual
        if missing:
            self.stdout.write(self.style.ERROR(f'  ❌ Áreas faltantes en DB: {", ".join(missing)}'))
            all_ok = False
        else:
            self.stdout.write(self.style.SUCCESS(f'  ✅ Todas las {len(expected)} áreas legales están en la DB'))
        
        # Check for extra areas
        extra = actual - expected
        if extra:
            self.stdout.write(self.style.WARNING(f'  ⚠️  Áreas extras en DB (podrían ser antiguas): {", ".join(extra)}'))
        
        # List all active areas
        self.stdout.write('\n  Áreas activas en la base de datos:')
        for i, area in enumerate(LegalArea.objects.filter(is_active=True).order_by('name'), 1):
            icon = '✓' if area.name in expected else '⚠'
            self.stdout.write(f'    {i:2d}. [{icon}] {area.name}')
        
        return all_ok

    def _verify_types(self):
        """Verify document types"""
        all_ok = True
        
        # Expected types from constants
        expected = set(DOCUMENT_TYPES)
        
        # Get actual types from database
        actual = set(DocumentType.objects.filter(is_active=True).values_list('name', flat=True))
        
        # Check if all expected types exist
        missing = expected - actual
        if missing:
            self.stdout.write(self.style.ERROR(f'  ❌ Tipos faltantes en DB: {", ".join(missing)}'))
            all_ok = False
        else:
            self.stdout.write(self.style.SUCCESS(f'  ✅ Todos los {len(expected)} tipos de documentos están en la DB'))
        
        # Check for extra types
        extra = actual - expected
        if extra:
            self.stdout.write(self.style.WARNING(f'  ⚠️  Tipos extras en DB (podrían ser antiguos): {", ".join(extra)}'))
        
        # List all active types
        self.stdout.write('\n  Tipos activos en la base de datos:')
        for i, doc_type in enumerate(DocumentType.objects.filter(is_active=True).order_by('name'), 1):
            icon = '✓' if doc_type.name in expected else '⚠'
            self.stdout.write(f'    {i:2d}. [{icon}] {doc_type.name}')
        
        return all_ok
