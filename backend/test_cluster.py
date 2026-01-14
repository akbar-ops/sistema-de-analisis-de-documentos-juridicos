#!/usr/bin/env python
"""
Script de prueba para verificar el endpoint de clustering
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.documents.models import Document
from apps.documents.services.clustering_service import ClusteringService

def test_clustering():
    """Prueba el servicio de clustering"""
    
    # Buscar documentos procesados
    processed_docs = Document.objects.filter(status='processed')
    
    print(f"\n{'='*60}")
    print("PRUEBA DE CLUSTERING")
    print(f"{'='*60}\n")
    
    print(f"📊 Documentos procesados encontrados: {processed_docs.count()}")
    
    if processed_docs.count() == 0:
        print("❌ No hay documentos procesados para hacer clustering")
        return
    
    # Seleccionar el primer documento procesado
    doc = processed_docs.first()
    print(f"\n📄 Documento seleccionado:")
    print(f"   ID: {doc.pk}")
    print(f"   Título: {doc.title}")
    print(f"   Expediente: {doc.case_number}")
    print(f"   Área: {doc.legal_area}")
    print(f"   Tipo: {doc.doc_type}")
    
    # Verificar que tenga embedding
    if doc.enhanced_embedding is None or len(doc.enhanced_embedding) == 0:
        print("❌ El documento no tiene enhanced_embedding")
        return
    
    print(f"   Embedding: ✓ (dimensiones: {len(doc.enhanced_embedding)})")
    
    # Ejecutar clustering
    print(f"\n🔄 Ejecutando clustering...")
    print(f"   Parámetros: max_neighbors=20, eps=0.3, min_samples=2")
    
    try:
        service = ClusteringService()
        result = service.get_document_cluster(
            document_id=str(doc.pk),
            max_neighbors=20,
            eps=0.3,
            min_samples=2
        )
        
        print(f"\n✅ Clustering exitoso!")
        print(f"\n📈 Resultados:")
        print(f"   Nodos totales: {len(result['nodes'])}")
        print(f"   Enlaces: {len(result['links'])}")
        print(f"   Clusters encontrados: {result.get('cluster_count', 0)}")
        print(f"   Nodos de ruido: {result.get('noise_count', 0)}")
        
        # Mostrar estadísticas
        if 'statistics' in result:
            stats = result['statistics']
            print(f"\n📊 Estadísticas:")
            print(f"   Total clusters: {stats.get('total_clusters', 0)}")
            print(f"   Nodos en ruido: {stats.get('noise_nodes', 0)}")
            
            if 'area_distribution' in stats:
                print(f"\n   Distribución por área:")
                for area, count in stats['area_distribution'].items():
                    print(f"      - {area}: {count}")
            
            if 'type_distribution' in stats:
                print(f"\n   Distribución por tipo:")
                for doc_type, count in stats['type_distribution'].items():
                    print(f"      - {doc_type}: {count}")
        
        # Mostrar algunos nodos
        print(f"\n📍 Primeros 5 nodos:")
        for i, node in enumerate(result['nodes'][:5], 1):
            cluster_label = "Ruido" if node.get('is_noise') else f"Cluster {node.get('cluster')}"
            print(f"   {i}. {node['label']}")
            print(f"      - Área: {node.get('legal_area', 'N/A')}")
            print(f"      - Tipo: {node.get('doc_type', 'N/A')}")
            print(f"      - {cluster_label}")
            print(f"      - Color: {node.get('color', 'N/A')}")
            print(f"      - Forma: {node.get('shape', 'N/A')}")
        
        # Mostrar algunos enlaces
        if result['links']:
            print(f"\n🔗 Primeros 3 enlaces:")
            for i, link in enumerate(result['links'][:3], 1):
                source_node = next((n for n in result['nodes'] if n['id'] == link['source']), None)
                target_node = next((n for n in result['nodes'] if n['id'] == link['target']), None)
                print(f"   {i}. {source_node.get('label', 'N/A')} → {target_node.get('label', 'N/A')}")
                print(f"      Similitud: {link.get('value', 0):.3f}")
        
        print(f"\n{'='*60}")
        print("✅ Prueba completada exitosamente")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\n❌ Error durante el clustering:")
        print(f"   {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_clustering()
