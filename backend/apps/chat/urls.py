from django.urls import path
from .views import DocumentChatView

urlpatterns = [
    path('document/', DocumentChatView.as_view(), name='document-chat'),
]
