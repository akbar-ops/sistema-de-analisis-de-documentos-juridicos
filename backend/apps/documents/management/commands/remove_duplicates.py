"""
Comando para encontrar y eliminar documentos duplicados
Criterios: mismo número de expediente, resolución o fecha
"""
from django.core.management.base import BaseCommand
from django.db.models import Q, Count
from apps.documents.models import Document, DocumentPerson, DocumentTask, DocumentChunk
from collections import defaultdict
import os


class Command(BaseCommand):
    help = 'Encuentra y elimina documentos duplicados'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar duplicados sin eliminarlos',
        )
        parser.add_argument(
            '--auto',
            action='store_true',
            help='Eliminar automáticamente sin confirmación',
        )
        parser.add_argument(
            '--criteria',
            type=str,
            default='all',
            choices=['case_number', 'resolution', 'date', 'all'],
            help='Criterio de duplicación (default: all)',
        )

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*80)
        self.stdout.write("🔍 BÚSQUEDA DE DOCUMENTOS DUPLICADOS")
        self.stdout.write("="*80 + "\n")

        dry_run = options['dry_run']
        auto_delete = options['auto']
        criteria = options['criteria']

        if dry_run:
            self.stdout.write(self.style.WARNING("Modo DRY-RUN: No se eliminarán documentos\n"))

        # Buscar duplicados
        duplicates_groups = self.find_duplicates(criteria)

        if not duplicates_groups:
            self.stdout.write(self.style.SUCCESS("\n✅ No se encontraron documentos duplicados\n"))
            return

        # Mostrar resumen
        total_docs = sum(len(group) for group in duplicates_groups.values())
        total_groups = len(duplicates_groups)
        docs_to_delete = total_docs - total_groups  # Mantener 1 por grupo

        self.stdout.write(f"\n📊 RESUMEN:")
        self.stdout.write(f"  • Grupos de duplicados: {total_groups}")
        self.stdout.write(f"  • Documentos duplicados: {total_docs}")
        self.stdout.write(f"  • Documentos a eliminar: {docs_to_delete}")
        self.stdout.write(f"  • Documentos a mantener: {total_groups}\n")

        # Mostrar detalles de duplicados
        self.show_duplicates(duplicates_groups)

        if dry_run:
            self.stdout.write("\n" + "="*80)
            self.stdout.write("Ejecuta sin --dry-run para eliminar duplicados")
            self.stdout.write("="*80 + "\n")
            return

        # Confirmación
        if not auto_delete:
            self.stdout.write("\n" + self.style.WARNING("⚠️  ADVERTENCIA:"))
            self.stdout.write("Esta operación eliminará documentos, relaciones y archivos físicos.")
            self.stdout.write("No se puede deshacer.\n")
            
            confirm = input("¿Deseas continuar? (escribe 'SI' para confirmar): ")
            if confirm != 'SI':
                self.stdout.write(self.style.ERROR("\n❌ Operación cancelada\n"))
                return

        # Eliminar duplicados
        self.delete_duplicates(duplicates_groups)

    def find_duplicates(self, criteria):
        """Encuentra documentos duplicados según criterio"""
        self.stdout.write("🔎 Buscando duplicados...\n")
        
        duplicates = defaultdict(list)
        
        # Obtener todos los documentos
        all_docs = Document.objects.select_related(
            'doc_type', 'legal_area'
        ).prefetch_related('document_persons')

        if criteria in ['case_number', 'all']:
            self.stdout.write("  → Por número de expediente...")
            case_duplicates = (
                all_docs
                .exclude(case_number__isnull=True)
                .exclude(case_number='')
                .values('case_number')
                .annotate(count=Count('document_id'))
                .filter(count__gt=1)
            )
            
            for item in case_duplicates:
                case_num = item['case_number']
                docs = list(all_docs.filter(case_number=case_num))
                if len(docs) > 1:
                    key = f"case_{case_num}"
                    duplicates[key] = docs

        if criteria in ['resolution', 'all']:
            self.stdout.write("  → Por número de resolución...")
            resolution_duplicates = (
                all_docs
                .exclude(resolution_number__isnull=True)
                .exclude(resolution_number='')
                .values('resolution_number')
                .annotate(count=Count('document_id'))
                .filter(count__gt=1)
            )
            
            for item in resolution_duplicates:
                res_num = item['resolution_number']
                docs = list(all_docs.filter(resolution_number=res_num))
                if len(docs) > 1:
                    key = f"resolution_{res_num}"
                    # Solo agregar si no está ya por caso
                    doc_ids = [d.document_id for d in docs]
                    already_found = False
                    for existing_docs in duplicates.values():
                        existing_ids = [d.document_id for d in existing_docs]
                        if set(doc_ids) == set(existing_ids):
                            already_found = True
                            break
                    if not already_found:
                        duplicates[key] = docs

        if criteria in ['date', 'all']:
            self.stdout.write("  → Por fecha de documento...")
            date_duplicates = (
                all_docs
                .exclude(document_date__isnull=True)
                .values('document_date', 'legal_area')
                .annotate(count=Count('document_id'))
                .filter(count__gt=1)
            )
            
            for item in date_duplicates:
                date = item['document_date']
                area = item['legal_area']
                docs = list(all_docs.filter(
                    document_date=date,
                    legal_area=area
                ))
                if len(docs) > 1:
                    key = f"date_{date}_{area}"
                    # Solo agregar si no está ya
                    doc_ids = [d.document_id for d in docs]
                    already_found = False
                    for existing_docs in duplicates.values():
                        existing_ids = [d.document_id for d in existing_docs]
                        if set(doc_ids) == set(existing_ids):
                            already_found = True
                            break
                    if not already_found:
                        duplicates[key] = docs

        return duplicates

    def show_duplicates(self, duplicates_groups):
        """Muestra detalles de documentos duplicados"""
        self.stdout.write("\n📋 DETALLES DE DUPLICADOS:")
        self.stdout.write("-"*80 + "\n")

        for i, (key, docs) in enumerate(duplicates_groups.items(), 1):
            # Determinar criterio
            if key.startswith('case_'):
                criterion = f"Expediente: {key[5:]}"
            elif key.startswith('resolution_'):
                criterion = f"Resolución: {key[11:]}"
            else:
                criterion = f"Fecha y Área: {key[5:]}"

            self.stdout.write(f"\n{i}. {criterion}")
            self.stdout.write(f"   {len(docs)} documentos duplicados:\n")

            # Ordenar: el más completo primero (más relaciones)
            docs_sorted = sorted(
                docs,
                key=lambda d: (
                    d.document_persons.count(),
                    1 if d.status == 'processed' else 0,
                    d.created_at
                ),
                reverse=True
            )

            for j, doc in enumerate(docs_sorted, 1):
                marker = "✅ MANTENER" if j == 1 else "❌ ELIMINAR"
                persons_count = doc.document_persons.count()
                
                self.stdout.write(f"\n   {marker}")
                self.stdout.write(f"   ID: {doc.document_id}")
                self.stdout.write(f"   Título: {doc.title[:70]}")
                self.stdout.write(f"   Estado: {doc.status}")
                self.stdout.write(f"   Creado: {doc.created_at.strftime('%Y-%m-%d %H:%M')}")
                self.stdout.write(f"   Personas relacionadas: {persons_count}")
                self.stdout.write(f"   Expediente: {doc.case_number or 'N/A'}")
                self.stdout.write(f"   Resolución: {doc.resolution_number or 'N/A'}")
                self.stdout.write(f"   Fecha: {doc.document_date or 'N/A'}")

            self.stdout.write("")

    def delete_duplicates(self, duplicates_groups):
        """Elimina documentos duplicados manteniendo el mejor de cada grupo"""
        self.stdout.write("\n🗑️  ELIMINANDO DUPLICADOS...")
        self.stdout.write("-"*80 + "\n")

        total_deleted = 0
        total_persons_deleted = 0
        total_tasks_deleted = 0
        total_chunks_deleted = 0
        total_files_deleted = 0

        for key, docs in duplicates_groups.items():
            # Ordenar: el más completo primero
            docs_sorted = sorted(
                docs,
                key=lambda d: (
                    d.document_persons.count(),
                    1 if d.status == 'processed' else 0,
                    d.created_at
                ),
                reverse=True
            )

            # Mantener el primero, eliminar el resto
            to_keep = docs_sorted[0]
            to_delete = docs_sorted[1:]

            self.stdout.write(f"\nGrupo: {key}")
            self.stdout.write(f"  ✅ Manteniendo: {to_keep.title[:60]}")

            for doc in to_delete:
                self.stdout.write(f"  ❌ Eliminando: {doc.title[:60]}")
                
                # Contar relaciones antes de eliminar
                persons = doc.document_persons.count()
                tasks = DocumentTask.objects.filter(document=doc).count()
                chunks = doc.chunks.count()

                # Eliminar relaciones (cascade automático, pero contamos)
                total_persons_deleted += persons
                total_tasks_deleted += tasks
                total_chunks_deleted += chunks

                # Eliminar archivo físico
                if doc.file_path:
                    try:
                        file_path = doc.file_path.path
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            total_files_deleted += 1
                            self.stdout.write(f"     → Archivo eliminado: {os.path.basename(file_path)}")
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f"     → Error eliminando archivo: {e}")
                        )

                # Eliminar documento (cascade eliminará relaciones)
                doc.delete()
                total_deleted += 1

        # Resumen final
        self.stdout.write("\n" + "="*80)
        self.stdout.write("✅ ELIMINACIÓN COMPLETADA")
        self.stdout.write("="*80)
        self.stdout.write(f"\nDocumentos eliminados: {total_deleted}")
        self.stdout.write(f"Relaciones documento-persona eliminadas: {total_persons_deleted}")
        self.stdout.write(f"Tareas eliminadas: {total_tasks_deleted}")
        self.stdout.write(f"Chunks eliminados: {total_chunks_deleted}")
        self.stdout.write(f"Archivos físicos eliminados: {total_files_deleted}")
        self.stdout.write("")
