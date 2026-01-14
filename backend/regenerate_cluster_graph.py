#!/usr/bin/env python
"""
Script para regenerar el grafo de clusters con rescalado de distancias.

Este script regenera el grafo de clusters usando el nuevo algoritmo de
rescalado de distancias que normaliza las similitudes antes de construir
el grafo KNN, resultando en un grafo más uniforme.

Uso:
    python regenerate_cluster_graph.py
"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.documents.services.clustering_service_new import ClusteringService
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Regenera el grafo de clusters con rescalado de distancias."""
    logger.info("=" * 80)
    logger.info("🔄 Regenerando grafo de clusters con rescalado de distancias")
    logger.info("=" * 80)
    
    # Crear servicio
    service = ClusteringService()
    
    # Parámetros optimizados - USANDO LOS DEFAULTS CORRECTOS
    logger.info("📋 Parámetros:")
    logger.info("  - UMAP 384D→30D: n_neighbors=15, min_dist=0.0")
    logger.info("  - HDBSCAN: min_cluster_size=4, min_samples=2 (OPTIMIZED)")
    logger.info("  - UMAP 30D→2D: n_neighbors=15, min_dist=0.1")
    logger.info("  - KNN graph: k=20")
    logger.info("")
    
    # Ejecutar clustering
    try:
        result = service.compute_global_clusters(
            # Usar parámetros por defecto del servicio para mantener los mismos clusters
            knn_params={
                'k': 20,  # Más vecinos porque ahora están mejor balanceados con rescaling
                'min_similarity': 0.3
            }
        )
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ Grafo de clusters regenerado exitosamente!")
        logger.info("=" * 80)
        logger.info(f"📊 Resultados:")
        logger.info(f"  - Graph ID: {result.graph_id}")
        logger.info(f"  - Documentos procesados: {result.document_count}")
        logger.info(f"  - Clusters encontrados: {result.cluster_count}")
        logger.info(f"  - Documentos sin cluster: {result.noise_count}")
        logger.info(f"  - Algoritmo: {result.algorithm}")
        logger.info("")
        logger.info("🎯 El rescalado de distancias debería haber creado un grafo más uniforme")
        logger.info("   sin el problema de clusters densos vs dispersos.")
        logger.info("")
        logger.info("💡 Recarga el frontend para ver los cambios!")
        
    except Exception as e:
        logger.error(f"❌ Error regenerando grafo: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
