# config/celery.py
"""
Configuración de Celery para procesamiento asíncrono de documentos.
"""
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('poder_judicial')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Configure task priorities
app.conf.task_routes = {
    'apps.documents.tasks.process_document_upload': {'queue': 'high_priority'},
    'apps.documents.tasks.process_document_analysis': {'queue': 'default'},
    'apps.documents.tasks.compute_cluster_graph': {'queue': 'default'},
}

# Configure periodic tasks (Celery Beat)
# For local development, we rebuild on document upload instead of nightly
# Uncomment below for production nightly rebuilds:
# app.conf.beat_schedule = {
#     'rebuild-cluster-graph-nightly': {
#         'task': 'apps.documents.tasks.compute_cluster_graph',
#         'schedule': crontab(hour=2, minute=0),  # 2:00 AM daily
#         'args': (1000, True, 'hdbscan'),
#         'options': {
#             'expires': 3600.0,
#         }
#     },
# }
app.conf.beat_schedule = {}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
