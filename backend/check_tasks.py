#!/usr/bin/env python
"""Script para verificar tareas en la base de datos"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.documents.models import DocumentTask, Document

print("=" * 60)
print(f"📊 Total de tareas: {DocumentTask.objects.count()}")
print(f"📄 Total de documentos: {Document.objects.count()}")
print("=" * 60)

print("\n🔹 Últimas 10 tareas creadas:")
print("-" * 60)
for task in DocumentTask.objects.all().order_by('-created_at')[:10]:
    print(f"ID: {task.task_id[:12]}... | Tipo: {task.task_type:20} | Estado: {task.status:10} | Doc: {task.document.title[:30]}")

print("\n🔹 Estadísticas por estado:")
print("-" * 60)
from django.db.models import Count
stats = DocumentTask.objects.values('status').annotate(count=Count('id'))
for stat in stats:
    print(f"  {stat['status']:15}: {stat['count']}")

print("\n🔹 Últimos 5 documentos:")
print("-" * 60)
for doc in Document.objects.all().order_by('-created_at')[:5]:
    print(f"ID: {str(doc.document_id)[:12]}... | Estado: {doc.status:15} | Título: {doc.title[:40]}")

print("\n" + "=" * 60)
