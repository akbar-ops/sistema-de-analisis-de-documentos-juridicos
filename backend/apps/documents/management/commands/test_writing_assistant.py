# apps/documents/management/commands/test_writing_assistant.py
"""
Comando para probar el Asistente de Redacción.

Uso:
    python manage.py test_writing_assistant --document-id <uuid>
    python manage.py test_writing_assistant --document-id <uuid> --section considerandos
"""

from django.core.management.base import BaseCommand
from apps.documents.models import Document
from apps.documents.services.writing_assistant import WritingAssistant
from apps.documents.services.section_extractor import SectionExtractor, LegalSection
import json


class Command(BaseCommand):
    help = 'Prueba el Asistente de Redacción'

    def add_arguments(self, parser):
        parser.add_argument(
            '--document-id',
            type=str,
            help='ID del documento a analizar'
        )
        parser.add_argument(
            '--section',
            type=str,
            default='considerandos',
            help='Tipo de sección (considerandos, vistos, etc.)'
        )
        parser.add_argument(
            '--max-suggestions',
            type=int,
            default=5,
            help='Número máximo de sugerencias'
        )
        parser.add_argument(
            '--extract-sections',
            action='store_true',
            help='Solo extraer secciones del documento'
        )

    def handle(self, *args, **options):
        document_id = options.get('document_id')
        
        if not document_id:
            self.stdout.write(self.style.ERROR('Debe especificar --document-id'))
            return

        try:
            document = Document.objects.get(document_id=document_id)
        except Document.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Documento {document_id} no encontrado'))
            return

        self.stdout.write(f"\n{'='*80}")
        self.stdout.write(self.style.SUCCESS(f'📄 Documento: {document.title}'))
        self.stdout.write(f"{'='*80}\n")

        assistant = WritingAssistant()

        # Opción 1: Solo extraer secciones
        if options['extract_sections']:
            self.stdout.write(self.style.WARNING('🔍 Extrayendo secciones del documento...\n'))
            
            sections_dict = assistant.extract_sections_from_document(document)
            
            if not sections_dict:
                self.stdout.write(self.style.ERROR('❌ No se encontraron secciones'))
                return
            
            self.stdout.write(self.style.SUCCESS(f'✅ Encontradas {len(sections_dict)} secciones:\n'))
            
            for section_type, section in sections_dict.items():
                quality = assistant.section_extractor.evaluate_section_quality(section)
                
                self.stdout.write(f"  📌 {section_type.upper()}")
                self.stdout.write(f"     Título: {section.title}")
                self.stdout.write(f"     Longitud: {len(section.content)} caracteres")
                self.stdout.write(f"     Calidad: {quality:.2f} ({self._get_quality_label(quality)})")
                self.stdout.write(f"     Preview: {section.content[:150]}...\n")
            
            return

        # Opción 2: Obtener sugerencias de redacción
        section_type = options['section']
        max_suggestions = options['max_suggestions']

        self.stdout.write(self.style.WARNING(
            f'🔍 Buscando sugerencias para sección: {section_type}\n'
        ))

        result = assistant.get_writing_assistance(
            document=document,
            section_type=section_type,
            max_suggestions=max_suggestions,
            min_quality=0.5,
            min_similarity=0.5
        )

        # Mostrar resultados
        self.stdout.write(self.style.SUCCESS(
            f'✅ Encontradas {result.total_found} sugerencias\n'
        ))

        if result.structure_tips:
            self.stdout.write(self.style.WARNING('📋 TIPS DE ESTRUCTURA:'))
            for i, tip in enumerate(result.structure_tips, 1):
                self.stdout.write(f'   {i}. {tip}')
            self.stdout.write('')

        if result.style_tips:
            self.stdout.write(self.style.WARNING('✨ TIPS DE ESTILO:'))
            for i, tip in enumerate(result.style_tips, 1):
                self.stdout.write(f'   {i}. {tip}')
            self.stdout.write('')

        if result.suggestions:
            self.stdout.write(self.style.SUCCESS('\n📚 SUGERENCIAS:\n'))
            
            for i, suggestion in enumerate(result.suggestions, 1):
                self.stdout.write(f"{'-'*80}")
                self.stdout.write(self.style.SUCCESS(f'\n  SUGERENCIA #{i}'))
                self.stdout.write(f"  Documento: {suggestion.document_title}")
                self.stdout.write(f"  ID: {suggestion.document_id}")
                self.stdout.write(f"  Área: {suggestion.metadata.get('area_legal', 'N/A')}")
                self.stdout.write(f"  Tipo: {suggestion.metadata.get('tipo_documento', 'N/A')}")
                self.stdout.write(f"  Calidad: {suggestion.quality_score:.2%} ({self._get_quality_label(suggestion.quality_score)})")
                self.stdout.write(f"  Similitud: {suggestion.similarity_score:.2%}")
                self.stdout.write(f"  Score combinado: {(suggestion.quality_score * 0.6 + suggestion.similarity_score * 0.4):.2%}")
                
                if suggestion.key_phrases:
                    self.stdout.write(f"\n  🔑 Frases clave:")
                    for phrase in suggestion.key_phrases[:3]:
                        self.stdout.write(f"     • {phrase[:100]}{'...' if len(phrase) > 100 else ''}")
                
                self.stdout.write(f"\n  📝 Contenido (primeros 300 caracteres):")
                preview = suggestion.section_content[:300].replace('\n', '\n     ')
                self.stdout.write(f"     {preview}...")
                self.stdout.write('')
        else:
            self.stdout.write(self.style.WARNING(
                '⚠️  No se encontraron sugerencias. Intenta:\n'
                '   - Reducir filtros de calidad/similitud\n'
                '   - Procesar más documentos similares\n'
                '   - Intentar con otra sección\n'
            ))

        self.stdout.write(f"\n{'='*80}")
        self.stdout.write(self.style.SUCCESS('✨ Prueba completada'))
        self.stdout.write(f"{'='*80}\n")

    def _get_quality_label(self, score):
        """Retorna etiqueta de calidad basada en score"""
        if score >= 0.8:
            return '⭐ Excelente'
        elif score >= 0.6:
            return '✓ Bueno'
        elif score >= 0.4:
            return '~ Regular'
        else:
            return '✗ Mejorable'
