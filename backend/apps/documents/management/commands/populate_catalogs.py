"""
Management command to populate initial catalog data
Usage: python manage.py populate_catalogs
"""
from django.core.management.base import BaseCommand
from apps.documents.models import LegalArea, DocumentType

class Command(BaseCommand):
    help = 'Populate legal areas and document types catalogs'

    def handle(self, *args, **options):
        self.stdout.write('Populating legal areas...')
        self._create_legal_areas()
        
        self.stdout.write('Populating document types...')
        self._create_document_types()
        
        self.stdout.write(self.style.SUCCESS('Successfully populated catalogs!'))

    def _create_legal_areas(self):
        """Create initial legal areas based on Peruvian judicial system specialties"""
        legal_areas = [
            {
                'name': 'Penal',
                'description': 'Derecho penal, delitos, procesos penales, imputados, fiscalía'
            },
            {
                'name': 'Laboral',
                'description': 'Derecho laboral, relaciones de trabajo, despidos, remuneraciones, beneficios sociales'
            },
            {
                'name': 'Familia Civil',
                'description': 'Derecho de familia en materia civil: divorcio, separación de cuerpos, régimen patrimonial'
            },
            {
                'name': 'Civil',
                'description': 'Derecho civil, obligaciones, contratos civiles, responsabilidad civil, propiedad'
            },
            {
                'name': 'Familia Tutelar',
                'description': 'Derecho de familia en materia tutelar: alimentos, tenencia, patria potestad, régimen de visitas'
            },
            {
                'name': 'Comercial',
                'description': 'Derecho comercial y mercantil, empresas, sociedades, contratos mercantiles, títulos valores'
            },
            {
                'name': 'Derecho Constitucional',
                'description': 'Derecho constitucional, amparo, hábeas corpus, hábeas data, derechos fundamentales'
            },
            {
                'name': 'Contencioso Administrativo',
                'description': 'Derecho administrativo, actos administrativos, procedimientos administrativos, entidades públicas'
            },
            {
                'name': 'Familia Penal',
                'description': 'Violencia familiar, violencia contra la mujer, medidas de protección, omisión a la asistencia familiar'
            },
            {
                'name': 'Extension de Dominio',
                'description': 'Extensión de dominio, ampliación de demanda, acumulación de procesos, conexidad'
            },
            {
                'name': 'Otros',
                'description': 'Otras áreas legales no especificadas en las categorías principales'
            }
        ]
        
        for area_data in legal_areas:
            area, created = LegalArea.objects.get_or_create(
                name=area_data['name'],
                defaults={'description': area_data['description']}
            )
            if created:
                self.stdout.write(f'  ✓ Created: {area.name}')
            else:
                self.stdout.write(f'  - Already exists: {area.name}')

    def _create_document_types(self):
        """Create initial document types based on Peruvian judicial documents"""
        document_types = [
            {
                'name': 'Sentencias',
                'description': 'Resoluciones que ponen fin a un proceso al resolver el fondo del asunto litigioso. Deciden sobre el objeto principal del litigio.'
            },
            {
                'name': 'Autos',
                'description': 'Resoluciones con contenido decisorio que se pronuncian sobre puntos dentro del proceso, pero sin resolver el fondo de la controversia.'
            },
            {
                'name': 'Decretos',
                'description': 'Resoluciones de mero trámite, sin contenido decisorio. No resuelven el fondo del asunto, sino que impulsan el procedimiento.'
            },
            {
                'name': 'Otros',
                'description': 'Otros documentos legales que no se clasifican en las categorías principales.'
            }
        ]
        
        for type_data in document_types:
            doc_type, created = DocumentType.objects.get_or_create(
                name=type_data['name'],
                defaults={'description': type_data['description']}
            )
            if created:
                self.stdout.write(f'  ✓ Created: {doc_type.name}')
            else:
                self.stdout.write(f'  - Already exists: {doc_type.name}')
