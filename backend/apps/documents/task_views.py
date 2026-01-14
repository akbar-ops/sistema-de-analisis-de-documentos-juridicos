# apps/documents/task_views.py
"""
ViewSet para gestión de tareas Celery de documentos.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from celery import current_app
import logging

from .models import DocumentTask, TaskStatus
from .serializers import DocumentTaskSerializer, DocumentTaskListSerializer

logger = logging.getLogger(__name__)


class TaskViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para consultar y gestionar tareas de procesamiento de documentos.
    
    Endpoints:
    - GET /api/tasks/ - Lista todas las tareas
    - GET /api/tasks/{id}/ - Detalle de una tarea (busca por task_id o pk)
    - GET /api/tasks/active/ - Lista tareas activas (pending, started, progress)
    - GET /api/tasks/completed/ - Lista tareas completadas
    - POST /api/tasks/{id}/revoke/ - Cancela una tarea pendiente
    """
    
    queryset = DocumentTask.objects.all().select_related('document').order_by('-created_at')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'retrieve':
            return DocumentTaskSerializer
        return DocumentTaskListSerializer
    
    def retrieve(self, request, pk=None):
        """
        Retrieve a task by pk (integer) or task_id (UUID string from Celery).
        
        This allows looking up tasks by their Celery task_id which is a UUID.
        """
        # Try to find by task_id (Celery UUID) first
        task = DocumentTask.objects.filter(task_id=pk).first()
        
        if not task:
            # Try to find by pk (integer ID)
            try:
                task = DocumentTask.objects.get(pk=int(pk))
            except (ValueError, DocumentTask.DoesNotExist):
                # Return a status response for Celery task polling
                # This happens when the task hasn't been registered in DB yet
                try:
                    from celery.result import AsyncResult
                    result = AsyncResult(pk)
                    return Response({
                        'task_id': pk,
                        'status': result.status,
                        'ready': result.ready(),
                        'successful': result.successful() if result.ready() else None,
                        'result': str(result.result) if result.ready() else None,
                    })
                except Exception:
                    return Response(
                        {'error': f'Task {pk} not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
        
        serializer = self.get_serializer(task)
        return Response(serializer.data)
    
    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = self.queryset
        
        # Filter by status
        task_status = self.request.query_params.get('status', None)
        if task_status:
            queryset = queryset.filter(status=task_status)
        
        # Filter by document
        document_id = self.request.query_params.get('document_id', None)
        if document_id:
            queryset = queryset.filter(document__document_id=document_id)
        
        # Filter by task type
        task_type = self.request.query_params.get('task_type', None)
        if task_type:
            queryset = queryset.filter(task_type=task_type)
        
        # Filter by active status
        is_active = self.request.query_params.get('active', None)
        if is_active == 'true':
            queryset = queryset.filter(status__in=[
                TaskStatus.PENDING,
                TaskStatus.STARTED,
                TaskStatus.PROGRESS
            ])
        elif is_active == 'false':
            queryset = queryset.filter(status__in=[
                TaskStatus.SUCCESS,
                TaskStatus.FAILURE,
                TaskStatus.REVOKED
            ])
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Get all active tasks (pending, started, in progress).
        
        Example: GET /api/tasks/active/
        """
        active_tasks = self.queryset.filter(status__in=[
            TaskStatus.PENDING,
            TaskStatus.STARTED,
            TaskStatus.PROGRESS
        ])
        
        serializer = self.get_serializer(active_tasks, many=True)
        
        return Response({
            'count': active_tasks.count(),
            'tasks': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def completed(self, request):
        """
        Get all completed tasks (success, failure, revoked).
        
        Example: GET /api/tasks/completed/
        Query params:
        - limit: int (default 50) - Max number of results
        """
        limit = int(request.query_params.get('limit', 50))
        
        completed_tasks = self.queryset.filter(status__in=[
            TaskStatus.SUCCESS,
            TaskStatus.FAILURE,
            TaskStatus.REVOKED
        ])[:limit]
        
        serializer = self.get_serializer(completed_tasks, many=True)
        
        return Response({
            'count': completed_tasks.count(),
            'tasks': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get statistics about tasks.
        
        Example: GET /api/tasks/stats/
        """
        from django.db.models import Count, Avg, Sum, Q, F, ExpressionWrapper, DurationField
        from django.db.models.functions import TruncDate, TruncHour
        from datetime import timedelta
        from django.utils import timezone
        
        total = self.queryset.count()
        pending = self.queryset.filter(status=TaskStatus.PENDING).count()
        started = self.queryset.filter(status=TaskStatus.STARTED).count()
        progress = self.queryset.filter(status=TaskStatus.PROGRESS).count()
        success = self.queryset.filter(status=TaskStatus.SUCCESS).count()
        failure = self.queryset.filter(status=TaskStatus.FAILURE).count()
        revoked = self.queryset.filter(status=TaskStatus.REVOKED).count()
        
        # Calculate average duration for completed tasks
        completed_with_duration = self.queryset.filter(
            status=TaskStatus.SUCCESS,
            completed_at__isnull=False,
            started_at__isnull=False
        )
        
        avg_duration = None
        if completed_with_duration.exists():
            durations = [
                (task.completed_at - task.started_at).total_seconds()
                for task in completed_with_duration
                if task.completed_at and task.started_at
            ]
            if durations:
                avg_duration = sum(durations) / len(durations)
        
        # Tasks by type
        by_type = {}
        for task_type_choice in ['upload', 'analysis_metadata', 'analysis_summary', 'analysis_persons', 'analysis_full']:
            by_type[task_type_choice] = self.queryset.filter(task_type=task_type_choice).count()
        
        # Tasks by hour (last 24 hours)
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        tasks_last_24h = self.queryset.filter(created_at__gte=last_24h)
        
        by_hour = list(tasks_last_24h.annotate(
            hour=TruncHour('created_at')
        ).values('hour').annotate(
            count=Count('task_id')
        ).order_by('hour'))
        
        # Tasks by day (last 7 days)
        last_7days = now - timedelta(days=7)
        tasks_last_7days = self.queryset.filter(created_at__gte=last_7days)
        
        by_day = list(tasks_last_7days.annotate(
            day=TruncDate('created_at')
        ).values('day').annotate(
            count=Count('task_id'),
            success_count=Count('task_id', filter=Q(status=TaskStatus.SUCCESS)),
            failure_count=Count('task_id', filter=Q(status=TaskStatus.FAILURE))
        ).order_by('day'))
        
        # Success rate
        total_completed = success + failure
        success_rate = (success / total_completed * 100) if total_completed > 0 else 0
        
        return Response({
            'total': total,
            'active': pending + started + progress,
            'completed': success + failure + revoked,
            'by_status': {
                'pending': pending,
                'started': started,
                'progress': progress,
                'success': success,
                'failure': failure,
                'revoked': revoked
            },
            'by_type': by_type,
            'by_hour': by_hour,
            'by_day': by_day,
            'avg_duration_seconds': avg_duration,
            'success_rate': round(success_rate, 2),
            'failure_rate': round(100 - success_rate, 2) if total_completed > 0 else 0
        })
    
    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """
        Cancel a pending task.
        
        Example: POST /api/tasks/{task_id}/revoke/
        """
        task = self.get_object()
        
        # Only pending or started tasks can be revoked
        if task.status not in [TaskStatus.PENDING, TaskStatus.STARTED]:
            return Response({
                'error': f'No se puede cancelar una tarea en estado: {task.get_status_display()}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Revoke task in Celery
            current_app.control.revoke(task.task_id, terminate=True)
            
            # Update task status
            task.status = TaskStatus.REVOKED
            task.error_message = 'Tarea cancelada por el usuario'
            task.save()
            
            logger.info(f"Task revoked: {task.task_id}")
            
            return Response({
                'message': 'Tarea cancelada exitosamente',
                'task': DocumentTaskSerializer(task).data
            })
            
        except Exception as e:
            logger.error(f"Error revoking task {pk}: {e}", exc_info=True)
            return Response({
                'error': f'Error al cancelar tarea: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def revoke_bulk(self, request):
        """
        Cancel multiple pending tasks.
        
        Body: {"task_ids": ["uuid1", "uuid2", ...]}
        Example: POST /api/tasks/revoke_bulk/
        """
        task_ids = request.data.get('task_ids', [])
        
        if not task_ids:
            return Response({
                'error': 'Se requiere lista de task_ids'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        tasks = self.queryset.filter(
            task_id__in=task_ids,
            status__in=[TaskStatus.PENDING, TaskStatus.STARTED]
        )
        
        revoked_count = 0
        errors = []
        
        for task in tasks:
            try:
                current_app.control.revoke(task.task_id, terminate=True)
                task.status = TaskStatus.REVOKED
                task.error_message = 'Tarea cancelada por el usuario (bulk)'
                task.save()
                revoked_count += 1
            except Exception as e:
                logger.error(f"Error revoking task {task.task_id}: {e}")
                errors.append({
                    'task_id': task.task_id,
                    'error': str(e)
                })
        
        return Response({
            'message': f'{revoked_count} tareas canceladas',
            'revoked_count': revoked_count,
            'errors': errors
        })
