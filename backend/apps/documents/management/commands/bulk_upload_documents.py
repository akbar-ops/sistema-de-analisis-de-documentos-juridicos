"""
Management command para carga masiva de documentos.
Permite subir ~1000 documentos de forma eficiente con procesamiento en batch.

Uso:
    python manage.py bulk_upload_documents /ruta/a/carpeta [opciones]

Opciones:
    --batch-size: Número de documentos a procesar por batch (default: 10)
    --processing-mode: 'chat_only' o 'full' (default: 'chat_only')
    --pattern: Patrón glob para filtrar archivos (default: '*.pdf')
    --dry-run: Solo mostrar qué archivos se procesarían
    --skip-existing: Saltar documentos que ya existen (por nombre)
    --workers: Número de workers paralelos (default: 2)
"""

import os
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile
from django.db import transaction, connection
from apps.documents.models import Document, DocumentTask, TaskStatus, TaskType
from apps.documents.services.document_processing import DocumentProcessingService
from apps.documents.tasks import process_document_upload


class Command(BaseCommand):
    help = 'Carga masiva de documentos desde una carpeta'

    def add_arguments(self, parser):
        parser.add_argument(
            'folder_path',
            type=str,
            help='Ruta a la carpeta con los documentos PDF'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Número de documentos a procesar por batch (default: 10)'
        )
        parser.add_argument(
            '--processing-mode',
            type=str,
            default='chat_only',
            choices=['chat_only', 'full'],
            help='Modo: chat_only (regex+embedding, SIN Ollama) o full (CON Ollama para summary/persons)'
        )
        parser.add_argument(
            '--pattern',
            type=str,
            default='*.pdf',
            help='Patrón glob para filtrar archivos (default: *.pdf)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar qué archivos se procesarían'
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Saltar documentos que ya existen (por nombre de archivo)'
        )
        parser.add_argument(
            '--workers',
            type=int,
            default=2,
            help='Número de workers paralelos (default: 2, recomendado para embeddings)'
        )
        parser.add_argument(
            '--use-celery',
            action='store_true',
            help='Usar Celery para procesamiento asíncrono (recomendado para >100 docs)'
        )

    def handle(self, *args, **options):
        folder_path = Path(options['folder_path'])
        batch_size = options['batch_size']
        processing_mode = options['processing_mode']
        pattern = options['pattern']
        dry_run = options['dry_run']
        skip_existing = options['skip_existing']
        workers = options['workers']
        use_celery = options['use_celery']

        # Validar carpeta
        if not folder_path.exists():
            raise CommandError(f'La carpeta no existe: {folder_path}')
        
        if not folder_path.is_dir():
            raise CommandError(f'La ruta no es una carpeta: {folder_path}')

        # Buscar archivos
        files = list(folder_path.glob(pattern))
        
        # También buscar recursivamente
        files.extend(folder_path.glob(f'**/{pattern}'))
        
        # Eliminar duplicados
        files = list(set(files))
        files.sort()

        if not files:
            self.stdout.write(
                self.style.WARNING(f'No se encontraron archivos con el patrón "{pattern}" en {folder_path}')
            )
            return

        self.stdout.write(f'\n📁 Encontrados {len(files)} archivos\n')

        # Filtrar existentes si se solicita
        if skip_existing:
            existing_titles = set(
                Document.objects.values_list('title', flat=True)
            )
            original_count = len(files)
            files = [f for f in files if f.stem not in existing_titles and f.name not in existing_titles]
            skipped = original_count - len(files)
            if skipped > 0:
                self.stdout.write(
                    self.style.WARNING(f'⏭️  Saltando {skipped} documentos existentes')
                )

        if not files:
            self.stdout.write(
                self.style.SUCCESS('✅ Todos los documentos ya están cargados')
            )
            return

        # Dry run
        if dry_run:
            self.stdout.write('\n🔍 DRY RUN - Archivos que se procesarían:\n')
            for i, f in enumerate(files[:50], 1):
                self.stdout.write(f'  {i}. {f.name}')
            if len(files) > 50:
                self.stdout.write(f'  ... y {len(files) - 50} más')
            self.stdout.write(f'\n📊 Total: {len(files)} archivos')
            return

        # Información de configuración
        self.stdout.write(f'\n⚙️  Configuración:')
        self.stdout.write(f'   - Modo de procesamiento: {processing_mode}')
        self.stdout.write(f'   - Tamaño de batch: {batch_size}')
        self.stdout.write(f'   - Workers paralelos: {workers}')
        self.stdout.write(f'   - Usar Celery: {use_celery}')
        self.stdout.write('')

        # Procesar
        total_files = len(files)
        processed = 0
        errors = []
        start_time = time.time()

        if use_celery:
            # Modo Celery: crear documentos y enviar a cola
            self.stdout.write(self.style.NOTICE('\n🚀 Modo Celery: Creando documentos y enviando a cola...\n'))
            
            for batch_num, batch_start in enumerate(range(0, total_files, batch_size)):
                batch_files = files[batch_start:batch_start + batch_size]
                batch_num_display = batch_num + 1
                total_batches = (total_files + batch_size - 1) // batch_size

                self.stdout.write(f'📦 Batch {batch_num_display}/{total_batches}...')
                
                for file_path in batch_files:
                    result = self._create_document_for_celery(file_path)
                    if result['success']:
                        processed += 1
                    else:
                        errors.append(result)
                
                self.stdout.write(f'   ✅ {processed} enviados a cola | ❌ {len(errors)} errores')
            
            self.stdout.write(self.style.SUCCESS(
                f'\n📤 {processed} documentos enviados a Celery para procesamiento'
            ))
            self.stdout.write('   Revisa la cola de tareas para ver el progreso.')
        
        else:
            # Modo síncrono: procesar directamente
            self.stdout.write(self.style.NOTICE('\n🔄 Modo síncrono: Procesando documentos...\n'))
            
            # Cargar modelo de embeddings una vez
            self.stdout.write('   Cargando modelo de embeddings...')
            processor = DocumentProcessingService()
            self.stdout.write('   ✅ Modelo cargado\n')
            
            for batch_num, batch_start in enumerate(range(0, total_files, batch_size)):
                batch_files = files[batch_start:batch_start + batch_size]
                batch_num_display = batch_num + 1
                total_batches = (total_files + batch_size - 1) // batch_size

                self.stdout.write(f'📦 Procesando batch {batch_num_display}/{total_batches} ({len(batch_files)} archivos)...')
                
                # Procesar secuencialmente para evitar problemas de memoria con embeddings
                for file_path in batch_files:
                    result = self._process_single_file(file_path, processing_mode, processor)
                    if result['success']:
                        processed += 1
                        if 'message' not in result:  # Solo si realmente se procesó
                            self.stdout.write(f'   ✅ {file_path.name}')
                    else:
                        errors.append(result)
                        self.stdout.write(self.style.ERROR(f'   ❌ {file_path.name}: {result["error"][:50]}...'))
                
                # Mostrar progreso del batch
                elapsed = time.time() - start_time
                rate = processed / elapsed if elapsed > 0 else 0
                remaining = (total_files - processed - len(errors)) / rate if rate > 0 else 0
                
                self.stdout.write(
                    f'   📊 {processed}/{total_files} procesados | '
                    f'❌ {len(errors)} errores | '
                    f'⏱️ {elapsed:.0f}s | '
                    f'ETA: {remaining:.0f}s'
                )
                
                # Cerrar conexiones para liberar recursos
                connection.close()

        # Resumen final
        total_time = time.time() - start_time
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS(f'\n🎉 Carga masiva completada!'))
        self.stdout.write(f'\n📊 Resumen:')
        self.stdout.write(f'   - Total archivos: {total_files}')
        self.stdout.write(f'   - Procesados correctamente: {processed}')
        self.stdout.write(f'   - Errores: {len(errors)}')
        self.stdout.write(f'   - Tiempo total: {total_time:.1f} segundos')
        if processed > 0:
            self.stdout.write(f'   - Velocidad: {processed / total_time:.2f} documentos/segundo')

        # Mostrar errores si hay
        if errors:
            self.stdout.write(self.style.ERROR(f'\n❌ Errores encontrados:'))
            for err in errors[:10]:
                self.stdout.write(f'   - {err["file"]}: {err["error"][:80]}')
            if len(errors) > 10:
                self.stdout.write(f'   ... y {len(errors) - 10} errores más')
        
        # Diagnóstico de embeddings
        self.stdout.write(f'\n🔍 Diagnóstico de embeddings:')
        # No usar exclude(clean_embedding=[]) porque pgvector no soporta comparación con lista vacía
        docs_with_embedding = Document.objects.exclude(clean_embedding__isnull=True).count()
        docs_total = Document.objects.count()
        docs_processed = Document.objects.filter(status='processed').count()
        self.stdout.write(f'   - Total documentos en BD: {docs_total}')
        self.stdout.write(f'   - Documentos procesados: {docs_processed}')
        self.stdout.write(f'   - Documentos con clean_embedding: {docs_with_embedding}')
        
        if docs_with_embedding < docs_processed:
            self.stdout.write(self.style.WARNING(
                f'\n⚠️  ADVERTENCIA: {docs_processed - docs_with_embedding} documentos procesados NO tienen embedding!'
            ))

    def _create_document_for_celery(self, file_path):
        """Crear documento y enviarlo a Celery para procesamiento."""
        try:
            # Verificar duplicados por título
            if Document.objects.filter(title=file_path.stem).exists():
                return {
                    'success': True,
                    'file': file_path.name,
                    'message': 'Ya existe (título duplicado)'
                }
            
            # Leer contenido
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Crear documento
            with transaction.atomic():
                document = Document.objects.create(
                    title=file_path.stem,
                    status='pending'
                )
                
                # Guardar archivo usando FileField correctamente
                document.file_path.save(
                    file_path.name,
                    ContentFile(content),
                    save=True
                )
                
                # Actualizar metadatos
                document.file_size = len(content)
                document.file_type = 'pdf'
                document.save(update_fields=['file_size', 'file_type'])
                
                # Crear tarea de procesamiento
                task = DocumentTask.objects.create(
                    document=document,
                    task_type=TaskType.UPLOAD,
                    status=TaskStatus.PENDING
                )
                
                # Enviar a Celery
                process_document_upload.delay(
                    str(document.document_id),
                    str(task.task_id)
                )
            
            return {
                'success': True,
                'file': file_path.name,
                'document_id': str(document.document_id),
                'task_id': str(task.task_id)
            }
            
        except Exception as e:
            return {
                'success': False,
                'file': str(file_path.name),
                'error': str(e)
            }

    def _process_single_file(self, file_path, processing_mode, processor):
        """Procesar un solo archivo de forma síncrona."""
        try:
            # Verificar duplicados por título
            if Document.objects.filter(title=file_path.stem).exists():
                return {
                    'success': True,
                    'file': file_path.name,
                    'message': 'Ya existe (título duplicado)'
                }
            
            # Leer contenido
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Crear documento (sin tarea, modo síncrono no necesita tracking)
            with transaction.atomic():
                document = Document.objects.create(
                    title=file_path.stem,
                    status='pending'
                )
                
                # Guardar archivo usando FileField correctamente
                document.file_path.save(
                    file_path.name,
                    ContentFile(content),
                    save=False  # No guardamos aún, lo haremos al final
                )
                
                # Actualizar metadatos básicos
                document.file_size = len(content)
                document.file_type = 'pdf'
                document.save()
            
            # Procesar documento según modo
            # - chat_only: usa process_document_light (NO Ollama)
            # - full: usa process_document completo (CON Ollama)
            if processing_mode == 'chat_only':
                # LIGHT MODE: Solo texto, regex metadata, clean_embedding, chunks
                # NO usa Ollama en absoluto
                success = processor.process_document_light(document)
            else:
                # FULL MODE: Incluye Ollama para summary y person extraction
                success = processor.process_document(
                    document,
                    generate_summary=True
                )
            
            # Refrescar documento para obtener valores actualizados
            document.refresh_from_db()
            
            if success:
                has_embedding = document.clean_embedding is not None and len(document.clean_embedding) > 0
                return {
                    'success': True,
                    'file': file_path.name,
                    'document_id': str(document.document_id),
                    'has_embedding': has_embedding,
                    'embedding_length': len(document.clean_embedding) if has_embedding else 0
                }
            else:
                return {
                    'success': False,
                    'file': file_path.name,
                    'error': document.error_message or 'Error desconocido en procesamiento'
                }
            
        except Exception as e:
            return {
                'success': False,
                'file': str(file_path.name),
                'error': str(e)
            }
