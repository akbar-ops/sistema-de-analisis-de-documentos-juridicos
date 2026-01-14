#!/usr/bin/env python
"""
Test script for the regenerate_clusters endpoint.
"""
import django
import os
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from rest_framework.test import APIRequestFactory
from apps.documents.views import DocumentViewSet

def test_regenerate_endpoint():
    """Test that the regenerate_clusters endpoint is accessible."""
    factory = APIRequestFactory()
    
    # Create POST request
    request = factory.post(
        '/api/documents/regenerate_clusters/',
        {
            'max_documents': 100,
            'use_enhanced_embedding': True,
            'algorithm': 'hdbscan'
        },
        format='json'
    )
    
    # Get the view
    view = DocumentViewSet.as_view({'post': 'regenerate_clusters'})
    
    # Call the view
    response = view(request)
    
    print("=" * 60)
    print("🧪 Testing regenerate_clusters endpoint")
    print("=" * 60)
    print(f"Status Code: {response.status_code}")
    print(f"Response Data: {response.data}")
    print("=" * 60)
    
    if response.status_code == 200:
        print("✅ Endpoint is working correctly!")
        print(f"Task ID: {response.data.get('task_id')}")
        print(f"Estimated Time: {response.data.get('estimated_time_seconds')}s")
        print(f"Document Count: {response.data.get('document_count')}")
    else:
        print("❌ Endpoint returned an error")
    
    return response

if __name__ == '__main__':
    test_regenerate_endpoint()
