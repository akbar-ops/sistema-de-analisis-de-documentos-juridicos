#!/usr/bin/env python
"""
Test BERTopic Optimizado vs Original

Compara los resultados de BERTopic optimizado con la versión original
y con HDBSCAN standalone.

Uso:
    python test_bertopic_comparison.py --embedding enhanced_embedding
    python test_bertopic_comparison.py --embedding clean_embedding
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
from apps.documents.services.bertopic_service import BERTopicService
from apps.documents.models import BERTopicModel, ClusterGraph
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_optimized(embedding_field='enhanced_embedding', max_docs=1000):
    """Prueba el servicio optimizado de BERTopic."""
    logger.info("=" * 80)
    logger.info("🧪 TESTING OPTIMIZED BERTOPIC")
    logger.info("=" * 80)
    logger.info(f"Embedding: {embedding_field}")
    logger.info(f"Max docs: {max_docs}")
    logger.info("")
    
    service = BERTopicServiceOptimized(require_bertopic=True)
    
    result = service.compute_topics(
        max_documents=max_docs,
        embedding_field=embedding_field,
        min_topic_size=4,  # Optimizado
        compute_metrics=True
    )
    
    return result


def test_original(embedding_field='clean_embedding', max_docs=1000):
    """Prueba el servicio original de BERTopic."""
    logger.info("=" * 80)
    logger.info("🧪 TESTING ORIGINAL BERTOPIC")
    logger.info("=" * 80)
    logger.info(f"Embedding: {embedding_field}")
    logger.info(f"Max docs: {max_docs}")
    logger.info("")
    
    service = BERTopicService(require_bertopic=True)
    
    result = service.compute_topics(
        max_documents=max_docs,
        embedding_field=embedding_field,
        min_topic_size=5  # Original
    )
    
    return result


def compare_results():
    """Compara todos los modelos disponibles."""
    logger.info("=" * 80)
    logger.info("📊 COMPARING ALL MODELS")
    logger.info("=" * 80)
    logger.info("")
    
    # Obtener modelos BERTopic
    bertopic_models = BERTopicModel.objects.all().order_by('-created_at')
    
    # Obtener grafos HDBSCAN
    hdbscan_graphs = ClusterGraph.objects.filter(algorithm='hdbscan').order_by('-created_at')
    
    logger.info(f"Found {bertopic_models.count()} BERTopic models")
    logger.info(f"Found {hdbscan_graphs.count()} HDBSCAN graphs")
    logger.info("")
    
    # Tabla comparativa
    print("\n" + "=" * 120)
    print(f"{'Model':<30} {'Docs':<8} {'Clusters':<10} {'Outliers':<10} {'Outlier %':<12} {'Time (s)':<10} {'Silhouette':<12}")
    print("=" * 120)
    
    # HDBSCAN
    for graph in hdbscan_graphs[:3]:
        params = graph.parameters
        quality = params.get('quality_metrics', {})
        silhouette = quality.get('silhouette_score', 'N/A')
        if isinstance(silhouette, float):
            silhouette = f"{silhouette:.3f}"
        
        print(f"{'HDBSCAN #' + str(graph.graph_id):<30} "
              f"{graph.document_count:<8} "
              f"{graph.cluster_count:<10} "
              f"{graph.noise_count:<10} "
              f"{graph.noise_count/graph.document_count*100:>6.1f}%      "
              f"{graph.computation_time:<10.1f} "
              f"{silhouette:<12}")
    
    # BERTopic
    for model in bertopic_models[:5]:
        params = model.parameters
        quality = params.get('quality_metrics', {})
        silhouette = quality.get('silhouette_score', 'N/A')
        if isinstance(silhouette, float):
            silhouette = f"{silhouette:.3f}"
        
        optimized = params.get('optimized', False)
        embedding = params.get('embedding_field', 'unknown')
        umap_comp = params.get('umap_params', {}).get('n_components', '?')
        
        name = f"BERTopic #{model.model_id}"
        if optimized:
            name += " ✨"
        name += f" ({embedding[:3]}{umap_comp}D)"
        
        print(f"{name:<30} "
              f"{model.document_count:<8} "
              f"{model.topic_count:<10} "
              f"{model.outlier_count:<10} "
              f"{model.outlier_count/model.document_count*100:>6.1f}%      "
              f"{model.computation_time:<10.1f} "
              f"{silhouette:<12}")
    
    print("=" * 120)
    print("\n✨ = Optimized version")
    print("enh = enhanced_embedding (384D), cle = clean_embedding (768D)")
    print("Number after embedding = UMAP intermediate dimensions\n")


def main():
    parser = argparse.ArgumentParser(description='Test BERTopic optimized vs original')
    parser.add_argument('--mode', choices=['optimized', 'original', 'both', 'compare'],
                       default='compare',
                       help='Test mode (default: compare)')
    parser.add_argument('--embedding', choices=['enhanced_embedding', 'clean_embedding'],
                       default='enhanced_embedding',
                       help='Embedding field to use (default: enhanced_embedding)')
    parser.add_argument('--max-docs', type=int, default=1000,
                       help='Maximum documents to process (default: 1000)')
    
    args = parser.parse_args()
    
    try:
        if args.mode == 'optimized':
            test_optimized(args.embedding, args.max_docs)
        elif args.mode == 'original':
            test_original(args.embedding, args.max_docs)
        elif args.mode == 'both':
            test_optimized(args.embedding, args.max_docs)
            logger.info("\n" + "="*80 + "\n")
            test_original('clean_embedding', args.max_docs)  # Original usa clean_embedding
        elif args.mode == 'compare':
            compare_results()
        
        logger.info("")
        logger.info("✅ Test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
