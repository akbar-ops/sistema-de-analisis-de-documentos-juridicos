"""
Management command para reconstruir el grafo de clusters.

Uso:
    python manage.py rebuild_clusters
    python manage.py rebuild_clusters --max-docs 500
    python manage.py rebuild_clusters --algorithm dbscan
    python manage.py rebuild_clusters --use-summary-embedding
"""

from django.core.management.base import BaseCommand, CommandError
from apps.documents.tasks import compute_cluster_graph


class Command(BaseCommand):
    help = 'Recompute the global cluster graph for all documents'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-docs',
            type=int,
            default=1000,
            help='Maximum number of documents to include (default: 1000)'
        )
        
        parser.add_argument(
            '--algorithm',
            type=str,
            default='hdbscan',
            choices=['hdbscan', 'dbscan'],
            help='Clustering algorithm to use (default: hdbscan)'
        )
        
        parser.add_argument(
            '--use-summary-embedding',
            action='store_true',
            help='Use summary_embedding instead of enhanced_embedding'
        )
        
        parser.add_argument(
            '--async',
            action='store_true',
            dest='run_async',
            help='Run as Celery task (async) instead of synchronously'
        )

    def handle(self, *args, **options):
        max_docs = options['max_docs']
        algorithm = options['algorithm']
        use_enhanced = not options['use_summary_embedding']
        run_async = options['run_async']
        
        embedding_type = 'enhanced_embedding' if use_enhanced else 'summary_embedding'
        
        self.stdout.write(self.style.WARNING('=' * 80))
        self.stdout.write(self.style.WARNING('CLUSTER GRAPH REBUILD'))
        self.stdout.write(self.style.WARNING('=' * 80))
        self.stdout.write(f'Algorithm: {algorithm}')
        self.stdout.write(f'Max documents: {max_docs}')
        self.stdout.write(f'Embedding type: {embedding_type}')
        self.stdout.write(f'Mode: {"Async (Celery)" if run_async else "Synchronous"}')
        self.stdout.write('')
        
        if run_async:
            # Ejecutar como tarea Celery
            self.stdout.write(self.style.WARNING('Queuing task to Celery...'))
            
            task = compute_cluster_graph.delay(
                max_documents=max_docs,
                use_enhanced_embedding=use_enhanced,
                algorithm=algorithm
            )
            
            self.stdout.write(self.style.SUCCESS(f'✅ Task queued: {task.id}'))
            self.stdout.write(f'Monitor progress with: celery -A config inspect active')
            
        else:
            # Ejecutar sincrónicamente
            self.stdout.write(self.style.WARNING('Starting cluster computation...'))
            self.stdout.write(self.style.WARNING('This may take several minutes.'))
            self.stdout.write('')
            
            try:
                result = compute_cluster_graph(
                    max_documents=max_docs,
                    use_enhanced_embedding=use_enhanced,
                    algorithm=algorithm
                )
                
                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS('=' * 80))
                self.stdout.write(self.style.SUCCESS('✅ CLUSTER GRAPH REBUILT SUCCESSFULLY'))
                self.stdout.write(self.style.SUCCESS('=' * 80))
                self.stdout.write(f'Graph ID: {result["graph_id"]}')
                self.stdout.write(f'Documents: {result["document_count"]}')
                self.stdout.write(f'Clusters: {result["cluster_count"]}')
                self.stdout.write(f'Noise: {result["noise_count"]}')
                self.stdout.write(f'Computation time: {result["computation_time"]:.2f} seconds')
                
            except Exception as e:
                self.stdout.write('')
                self.stdout.write(self.style.ERROR('=' * 80))
                self.stdout.write(self.style.ERROR('❌ CLUSTER GRAPH REBUILD FAILED'))
                self.stdout.write(self.style.ERROR('=' * 80))
                raise CommandError(f'Error: {e}')
