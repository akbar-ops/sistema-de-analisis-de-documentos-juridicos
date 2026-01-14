#!/usr/bin/env python
"""
Ejecutar BERTopic Optimizado

Script simple para ejecutar BERTopic con los parámetros optimizados.

Uso:
    # Con enhanced_embedding (384D) - igual que HDBSCAN
    python run_bertopic_optimized.py
    
    # Con clean_embedding (768D)
    python run_bertopic_optimized.py --embedding clean_embedding
    
    # Con parámetros personalizados
    python run_bertopic_optimized.py --umap-components 20 --min-cluster 3
"""

import os
import sys
import django
import argparse

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.documents.services.bertopic_service_optimized import BERTopicServiceOptimized
from apps.documents.models import BERTopicModel, ClusterGraph
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_optimized_bertopic(
    embedding_field='clean_embedding',  # 🔥 Usar clean_embedding (768D) por defecto
    max_docs=1000,
    umap_components=15,
    min_cluster_size=4,
    min_samples=2,
    compare_with_hdbscan=True
):
    """
    Ejecuta BERTopic optimizado y opcionalmente compara con HDBSCAN.
    """
    
    logger.info("=" * 80)
    logger.info("🚀 RUNNING OPTIMIZED BERTOPIC")
    logger.info("=" * 80)
    logger.info("")
    logger.info("📋 Configuration:")
    logger.info(f"   Embedding: {embedding_field}")
    logger.info(f"   Max documents: {max_docs}")
    logger.info(f"   UMAP components: {umap_components}D")
    logger.info(f"   Min cluster size: {min_cluster_size}")
    logger.info(f"   Min samples: {min_samples}")
    logger.info("")
    
    # Crear servicio
    service = BERTopicServiceOptimized(require_bertopic=True)
    
    # Configurar parámetros
    umap_params = {'n_components': umap_components}
    hdbscan_params = {
        'min_cluster_size': min_cluster_size,
        'min_samples': min_samples
    }
    
    # Ejecutar BERTopic
    bertopic_model = service.compute_topics(
        max_documents=max_docs,
        embedding_field=embedding_field,
        min_topic_size=min_cluster_size,
        umap_params=umap_params,
        hdbscan_params=hdbscan_params,
        compute_metrics=True
    )
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("✅ BERTopic computation completed!")
    logger.info("=" * 80)
    logger.info("")
    
    # Comparar con HDBSCAN si está disponible
    if compare_with_hdbscan:
        logger.info("🔍 Looking for HDBSCAN graph to compare...")
        hdbscan_graph = ClusterGraph.objects.filter(
            algorithm='hdbscan',
            is_active=True
        ).first()
        
        if hdbscan_graph:
            logger.info(f"   Found active HDBSCAN graph #{hdbscan_graph.graph_id}")
            logger.info("")
            
            comparison = service.compare_with_hdbscan(
                bertopic_model_id=bertopic_model.model_id,
                hdbscan_graph_id=hdbscan_graph.graph_id
            )
            
            # Mostrar resumen de comparación
            logger.info("")
            logger.info("📊 Quick Comparison:")
            logger.info(f"   Cluster difference: {comparison['differences']['cluster_count_diff']:+d}")
            logger.info(f"   Outlier % difference: {comparison['differences']['outlier_percentage_diff']:+.1f}%")
            
            if abs(comparison['differences']['cluster_count_diff']) <= 5:
                logger.info("   ✅ Similar number of clusters!")
            
            if abs(comparison['differences']['outlier_percentage_diff']) <= 5:
                logger.info("   ✅ Similar outlier percentage!")
            
        else:
            logger.info("   No active HDBSCAN graph found for comparison")
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("🎯 NEXT STEPS:")
    logger.info("=" * 80)
    logger.info("")
    logger.info("1. Activate this model:")
    logger.info(f"   Model ID: {bertopic_model.model_id}")
    logger.info("")
    logger.info("2. View in frontend:")
    logger.info("   Navigate to BERTopic view in the application")
    logger.info("")
    logger.info("3. Compare models:")
    logger.info("   python test_bertopic_comparison.py --mode compare")
    logger.info("")
    
    return bertopic_model


def activate_model(model_id):
    """Activa un modelo BERTopic específico."""
    try:
        model = BERTopicModel.objects.get(model_id=model_id)
        model.activate()
        logger.info(f"✅ Activated BERTopic model #{model_id}")
    except BERTopicModel.DoesNotExist:
        logger.error(f"❌ Model #{model_id} not found")


def main():
    parser = argparse.ArgumentParser(
        description='Run optimized BERTopic clustering',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with enhanced_embedding (recommended for comparison with HDBSCAN)
  python run_bertopic_optimized.py
  
  # Use clean_embedding (768D)
  python run_bertopic_optimized.py --embedding clean_embedding
  
  # Custom parameters
  python run_bertopic_optimized.py --umap-components 20 --min-cluster 3 --min-samples 1
  
  # Activate a specific model
  python run_bertopic_optimized.py --activate 5
        """
    )
    
    parser.add_argument('--embedding', 
                       choices=['enhanced_embedding', 'clean_embedding'],
                       default='clean_embedding',  # 🔥 Usar clean_embedding (768D) por defecto
                       help='Embedding field to use (default: clean_embedding for consistency)')
    
    parser.add_argument('--max-docs', type=int, default=1000,
                       help='Maximum documents to process (default: 1000)')
    
    parser.add_argument('--umap-components', type=int, default=15,
                       help='UMAP intermediate dimensions (default: 15)')
    
    parser.add_argument('--min-cluster', type=int, default=4,
                       help='Minimum cluster size (default: 4)')
    
    parser.add_argument('--min-samples', type=int, default=2,
                       help='Minimum samples for HDBSCAN (default: 2)')
    
    parser.add_argument('--no-compare', action='store_true',
                       help='Skip comparison with HDBSCAN')
    
    parser.add_argument('--activate', type=int, metavar='MODEL_ID',
                       help='Activate a specific model by ID and exit')
    
    args = parser.parse_args()
    
    try:
        # Modo activación
        if args.activate:
            activate_model(args.activate)
            return
        
        # Ejecutar BERTopic optimizado
        run_optimized_bertopic(
            embedding_field=args.embedding,
            max_docs=args.max_docs,
            umap_components=args.umap_components,
            min_cluster_size=args.min_cluster,
            min_samples=args.min_samples,
            compare_with_hdbscan=not args.no_compare
        )
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
