# apps/documents/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentViewSet
from .task_views import TaskViewSet
from .writing_views import WritingAssistantViewSet

router = DefaultRouter()
router.register(r'documents', DocumentViewSet)
router.register(r'tasks', TaskViewSet)
router.register(r'writing-assistant', WritingAssistantViewSet, basename='writing-assistant')

urlpatterns = [
    path('', include(router.urls)),
]
