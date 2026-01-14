#!/usr/bin/env python
"""
Grid Search para Optimizar Parámetros de BERTopic

Prueba diferentes combinaciones de parámetros para encontrar
la mejor configuración para documentos legales.

Uso:
    python test_bertopic_grid_search.py
"""

import os
import sys
import django
import itertools
import json
from datetime import datetime

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.documents.services.bertopic_service_optimized import BERTopicServiceOptimized
from apps.documents.models import BERTopicModel
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Parámetros a probar
PARAM_GRID = {
    'umap_n_components': [10, 15, 20],  # Dimensiones intermedias
    'min_cluster_size': [3, 4, 5],       # Tamaño mínimo de cluster
    'min_samples': [1, 2, 3],            # Muestras mínimas
    'embedding_field': ['enhanced_embedding'],  # Usar solo uno para comparación justa
}


def run_grid_search(max_docs=500):  # Reducido para grid search
    """Ejecuta grid search sobre los parámetros."""
    
    logger.info("=" * 80)
    logger.info("🔬 BERTOPIC GRID SEARCH")
    logger.info("=" * 80)
    logger.info(f"Max documents: {max_docs}")
    logger.info(f"Parameter grid:")
    for key, values in PARAM_GRID.items():
        logger.info(f"  {key}: {values}")
    logger.info("")
    
    # Generar todas las combinaciones
    keys = list(PARAM_GRID.keys())
    values = list(PARAM_GRID.values())
    combinations = list(itertools.product(*values))
    
    logger.info(f"Total combinations to test: {len(combinations)}")
    logger.info("")
    
    results = []
    
    for i, combo in enumerate(combinations, 1):
        params = dict(zip(keys, combo))
        
        logger.info("=" * 80)
        logger.info(f"🧪 Test {i}/{len(combinations)}")
        logger.info("=" * 80)
        logger.info(f"Parameters: {params}")
        logger.info("")
        
        try:
            service = BERTopicServiceOptimized(require_bertopic=True)
            
            # Configurar parámetros
            umap_params = {'n_components': params['umap_n_components']}
            hdbscan_params = {
                'min_cluster_size': params['min_cluster_size'],
                'min_samples': params['min_samples']
            }
            
            # Ejecutar clustering
            start_time = datetime.now()
            model = service.compute_topics(
                max_documents=max_docs,
                embedding_field=params['embedding_field'],
                min_topic_size=params['min_cluster_size'],
                umap_params=umap_params,
                hdbscan_params=hdbscan_params,
                compute_metrics=True
            )
            end_time = datetime.now()
            
            # Extraer métricas
            model_params = model.parameters
            quality = model_params.get('quality_metrics', {})
            
            result = {
                'test_id': i,
                'model_id': model.model_id,
                'parameters': params,
                'results': {
                    'document_count': model.document_count,
                    'topic_count': model.topic_count,
                    'outlier_count': model.outlier_count,
                    'outlier_percentage': model.outlier_count / model.document_count * 100,
                    'computation_time': model.computation_time,
                    'silhouette_score': quality.get('silhouette_score'),
                    'calinski_harabasz_score': quality.get('calinski_harabasz_score'),
                    'davies_bouldin_score': quality.get('davies_bouldin_score'),
                },
                'timestamp': end_time.isoformat()
            }
            
            results.append(result)
            
            logger.info("")
            logger.info("📊 Results:")
            logger.info(f"   Topics: {model.topic_count}")
            logger.info(f"   Outliers: {model.outlier_count} ({result['results']['outlier_percentage']:.1f}%)")
            logger.info(f"   Silhouette: {quality.get('silhouette_score', 'N/A')}")
            logger.info(f"   Time: {model.computation_time:.1f}s")
            logger.info("")
            
        except Exception as e:
            logger.error(f"❌ Test {i} failed: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'test_id': i,
                'parameters': params,
                'error': str(e)
            })
    
    return results


def analyze_results(results):
    """Analiza y muestra los mejores resultados."""
    
    logger.info("=" * 80)
    logger.info("📊 GRID SEARCH RESULTS ANALYSIS")
    logger.info("=" * 80)
    logger.info("")
    
    # Filtrar errores
    valid_results = [r for r in results if 'error' not in r]
    
    if not valid_results:
        logger.error("No valid results to analyze!")
        return
    
    logger.info(f"Valid tests: {len(valid_results)}/{len(results)}")
    logger.info("")
    
    # Ordenar por diferentes métricas
    
    # 1. Mejor Silhouette Score
    by_silhouette = sorted(
        [r for r in valid_results if r['results'].get('silhouette_score') is not None],
        key=lambda x: x['results']['silhouette_score'],
        reverse=True
    )
    
    if by_silhouette:
        logger.info("🏆 TOP 3 BY SILHOUETTE SCORE (higher is better)")
        logger.info("-" * 80)
        for i, result in enumerate(by_silhouette[:3], 1):
            p = result['parameters']
            r = result['results']
            logger.info(f"{i}. Model #{result['model_id']}")
            logger.info(f"   Parameters: UMAP={p['umap_n_components']}D, "
                       f"min_cluster={p['min_cluster_size']}, "
                       f"min_samples={p['min_samples']}")
            logger.info(f"   Silhouette: {r['silhouette_score']:.3f}")
            logger.info(f"   Topics: {r['topic_count']}, Outliers: {r['outlier_percentage']:.1f}%")
            logger.info("")
    
    # 2. Menor porcentaje de outliers
    by_outliers = sorted(
        valid_results,
        key=lambda x: x['results']['outlier_percentage']
    )
    
    logger.info("🏆 TOP 3 BY LOWEST OUTLIER PERCENTAGE")
    logger.info("-" * 80)
    for i, result in enumerate(by_outliers[:3], 1):
        p = result['parameters']
        r = result['results']
        logger.info(f"{i}. Model #{result['model_id']}")
        logger.info(f"   Parameters: UMAP={p['umap_n_components']}D, "
                   f"min_cluster={p['min_cluster_size']}, "
                   f"min_samples={p['min_samples']}")
        logger.info(f"   Outliers: {r['outlier_percentage']:.1f}%")
        logger.info(f"   Topics: {r['topic_count']}, Silhouette: {r.get('silhouette_score', 'N/A')}")
        logger.info("")
    
    # 3. Balance: Silhouette alto + pocos outliers
    by_balance = sorted(
        [r for r in valid_results if r['results'].get('silhouette_score') is not None],
        key=lambda x: (
            x['results']['silhouette_score'] - 
            x['results']['outlier_percentage'] / 100
        ),
        reverse=True
    )
    
    logger.info("🏆 TOP 3 BY BALANCE (Silhouette - Outlier%/100)")
    logger.info("-" * 80)
    for i, result in enumerate(by_balance[:3], 1):
        p = result['parameters']
        r = result['results']
        balance_score = r['silhouette_score'] - r['outlier_percentage'] / 100
        logger.info(f"{i}. Model #{result['model_id']}")
        logger.info(f"   Parameters: UMAP={p['umap_n_components']}D, "
                   f"min_cluster={p['min_cluster_size']}, "
                   f"min_samples={p['min_samples']}")
        logger.info(f"   Balance Score: {balance_score:.3f}")
        logger.info(f"   Silhouette: {r['silhouette_score']:.3f}, "
                   f"Outliers: {r['outlier_percentage']:.1f}%, "
                   f"Topics: {r['topic_count']}")
        logger.info("")
    
    # Guardar resultados completos
    output_file = f"grid_search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info("=" * 80)
    logger.info(f"📄 Full results saved to: {output_file}")
    logger.info("=" * 80)
    logger.info("")
    
    # Recomendación final
    if by_balance:
        best = by_balance[0]
        logger.info("💡 RECOMMENDED CONFIGURATION:")
        logger.info("-" * 80)
        p = best['parameters']
        logger.info(f"umap_params = {{'n_components': {p['umap_n_components']}}}")
        logger.info(f"hdbscan_params = {{")
        logger.info(f"    'min_cluster_size': {p['min_cluster_size']},")
        logger.info(f"    'min_samples': {p['min_samples']}")
        logger.info(f"}}")
        logger.info(f"embedding_field = '{p['embedding_field']}'")
        logger.info("")


def main():
    """Función principal."""
    
    import argparse
    parser = argparse.ArgumentParser(description='BERTopic Grid Search')
    parser.add_argument('--max-docs', type=int, default=500,
                       help='Maximum documents to process (default: 500 for faster grid search)')
    
    args = parser.parse_args()
    
    try:
        # Ejecutar grid search
        results = run_grid_search(max_docs=args.max_docs)
        
        # Analizar resultados
        analyze_results(results)
        
        logger.info("✅ Grid search completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error during grid search: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
