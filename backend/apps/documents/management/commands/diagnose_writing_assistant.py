"""
Comando para diagnosticar problemas del Asistente de Redacción
"""
from django.core.management.base import BaseCommand
from apps.documents.models import Document
from apps.documents.services.section_extractor import SectionExtractor, LegalSection
from apps.documents.services.writing_assistant import extract_text_from_file
from collections import Counter
import time


class Command(BaseCommand):
    help = 'Diagnóstico del Asistente de Redacción'

    def add_arguments(self, parser):
        parser.add_argument(
            '--full',
            action='store_true',
            help='Análisis completo de todos los documentos (lento)',
        )

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*80)
        self.stdout.write("🔍 DIAGNÓSTICO DEL ASISTENTE DE REDACCIÓN")
        self.stdout.write("="*80 + "\n")

        # 1. Estado de la base de datos
        self.stdout.write("📊 ESTADO DE LA BASE DE DATOS")
        self.stdout.write("-" * 80)
        
        total_docs = Document.objects.count()
        processed_docs = Document.objects.filter(status='processed')
        processed_count = processed_docs.count()
        
        self.stdout.write(f"Total documentos: {total_docs}")
        self.stdout.write(f"Documentos procesados: {processed_count}")
        
        if processed_count == 0:
            self.stdout.write(self.style.ERROR("\n❌ No hay documentos procesados!"))
            self.stdout.write("Primero procesa algunos documentos antes de usar el asistente.\n")
            return
        
        # 2. Embeddings disponibles
        with_embeddings = processed_docs.exclude(enhanced_embedding__isnull=True).count()
        self.stdout.write(f"Con enhanced_embedding: {with_embeddings}")
        
        if with_embeddings < processed_count:
            self.stdout.write(self.style.WARNING(
                f"\n⚠️  {processed_count - with_embeddings} documentos sin embeddings"
            ))
            self.stdout.write("Ejecuta: python manage.py regenerate_embeddings\n")
        
        # 3. Verificar PyMuPDF
        self.stdout.write("\n📦 DEPENDENCIAS")
        self.stdout.write("-" * 80)
        try:
            import fitz
            self.stdout.write(self.style.SUCCESS("✅ PyMuPDF instalado (extracción rápida)"))
        except ImportError:
            self.stdout.write(self.style.WARNING("⚠️  PyMuPDF no instalado (extracción lenta)"))
            self.stdout.write("   Instalar: pip install pymupdf\n")
        
        # 4. Análisis de secciones (solo si --full)
        if options['full']:
            self.stdout.write("\n📝 ANÁLISIS DE SECCIONES (puede tardar...)")
            self.stdout.write("-" * 80)
            
            extractor = SectionExtractor()
            section_counter = Counter()
            quality_scores = []
            extraction_times = []
            
            sample_size = min(10, processed_count)
            self.stdout.write(f"Analizando {sample_size} documentos...\n")
            
            for i, doc in enumerate(processed_docs[:sample_size], 1):
                self.stdout.write(f"  {i}/{sample_size}: {doc.title[:50]}...")
                
                try:
                    start = time.time()
                    text = extract_text_from_file(doc.file_path)
                    extraction_time = time.time() - start
                    extraction_times.append(extraction_time)
                    
                    if text:
                        sections = extractor.extract_sections(text)
                        for section in sections:
                            section_counter[section.section_type.value] += 1
                            quality = extractor.evaluate_section_quality(section)
                            quality_scores.append(quality)
                        
                        self.stdout.write(
                            f"    ✅ {len(sections)} secciones en {extraction_time:.2f}s"
                        )
                    else:
                        self.stdout.write(self.style.WARNING("    ⚠️  Sin texto extraído"))
                
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"    ❌ Error: {e}"))
            
            # Resultados
            self.stdout.write("\n📈 RESULTADOS:")
            self.stdout.write("-" * 80)
            
            if section_counter:
                self.stdout.write("\nSecciones encontradas:")
                for section_type, count in section_counter.most_common():
                    self.stdout.write(f"  • {section_type}: {count} veces")
            
            if quality_scores:
                avg_quality = sum(quality_scores) / len(quality_scores)
                self.stdout.write(f"\nCalidad promedio: {avg_quality:.1%}")
                self.stdout.write(f"Secciones con calidad >= 60%: {sum(1 for q in quality_scores if q >= 0.6)}/{len(quality_scores)}")
            
            if extraction_times:
                avg_time = sum(extraction_times) / len(extraction_times)
                self.stdout.write(f"\nTiempo promedio extracción: {avg_time:.2f}s")
                if avg_time > 3:
                    self.stdout.write(self.style.WARNING(
                        "  ⚠️  Extracción lenta. Instala PyMuPDF para mejorar velocidad."
                    ))
        
        # 5. Recomendaciones
        self.stdout.write("\n💡 RECOMENDACIONES")
        self.stdout.write("-" * 80)
        
        if processed_count < 10:
            self.stdout.write("📌 Procesa más documentos (ideal: 20+) para mejores resultados")
        
        if with_embeddings < processed_count:
            self.stdout.write("📌 Regenera embeddings para todos los documentos")
        
        try:
            import fitz
        except ImportError:
            self.stdout.write("📌 Instala PyMuPDF: pip install pymupdf")
        
        if not options['full']:
            self.stdout.write("📌 Ejecuta con --full para análisis completo de secciones")
        
        # 6. Comandos útiles
        self.stdout.write("\n🔧 COMANDOS ÚTILES")
        self.stdout.write("-" * 80)
        
        if processed_count > 0:
            first_doc = processed_docs.first()
            self.stdout.write("\n# Probar extracción de secciones:")
            self.stdout.write(f"python manage.py test_writing_assistant --document-id {first_doc.document_id} --extract-sections")
            
            self.stdout.write("\n# Probar búsqueda de sugerencias:")
            self.stdout.write(f"python manage.py test_writing_assistant --document-id {first_doc.document_id} --section considerandos")
        
        self.stdout.write("\n# Ver este diagnóstico completo:")
        self.stdout.write("python manage.py diagnose_writing_assistant --full")
        
        self.stdout.write("\n" + "="*80 + "\n")
