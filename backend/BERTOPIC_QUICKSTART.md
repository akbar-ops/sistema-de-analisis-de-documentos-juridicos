# 🎯 BERTopic Optimizado - Guía de Uso Rápido

## 📝 Resumen

He optimizado BERTopic para que tenga un rendimiento similar a HDBSCAN standalone. Los principales cambios son:

### Optimizaciones Aplicadas

| Parámetro               | Original | Optimizado | Motivo                              |
| ----------------------- | -------- | ---------- | ----------------------------------- |
| **UMAP intermedio**     | 5D       | 15D        | Preservar más información semántica |
| **min_cluster_size**    | 5        | 4          | Igual que HDBSCAN optimizado        |
| **min_samples**         | 2        | 2          | Igual que HDBSCAN optimizado        |
| **Vectorizador ngrams** | (1,2)    | (1,3)      | Capturar frases legales completas   |
| **min_df**              | 2        | 3          | Filtrar términos muy raros          |
| **max_df**              | 0.95     | 0.90       | Filtrar términos muy comunes        |
| **UMAP 2D min_dist**    | 0.1      | 0.3        | Mejor separación visual             |
| **Keywords por tópico** | 10       | 15         | Más contexto legal                  |

---

## 🚀 Uso Rápido

### 1. Ejecutar BERTopic Optimizado (Recomendado)

```bash
# Configuración recomendada (mismo embedding que HDBSCAN)
python run_bertopic_optimized.py

# Con clean_embedding (768D)
python run_bertopic_optimized.py --embedding clean_embedding

# Personalizado
python run_bertopic_optimized.py --umap-components 20 --min-cluster 3
```

### 2. Comparar Modelos

```bash
# Ver comparación de todos los modelos
python test_bertopic_comparison.py --mode compare

# Probar ambas versiones
python test_bertopic_comparison.py --mode both --embedding enhanced_embedding
```

### 3. Grid Search (Opcional)

```bash
# Buscar los mejores parámetros para tu dataset
python test_bertopic_grid_search.py --max-docs 500
```

---

## 📊 Resultados Esperados

### Métricas Objetivo (basadas en HDBSCAN optimizado)

```
✅ Clusters: 20-30 (vs HDBSCAN: 20-30)
✅ Outliers: 15-20% (vs HDBSCAN: 15-20%)
✅ Silhouette Score: 0.25-0.35
✅ Clusters bien separados visualmente
✅ Keywords relevantes y diversos
```

### Comparación Visual

```
┌─────────────────┬──────────┬───────────┬───────────┬────────────┐
│ Modelo          │ Docs     │ Clusters  │ Outliers  │ Outlier %  │
├─────────────────┼──────────┼───────────┼───────────┼────────────┤
│ HDBSCAN         │ 1000     │ 25        │ 180       │ 18.0%      │
│ BERTopic Orig   │ 1000     │ 15        │ 280       │ 28.0%      │
│ BERTopic Optim  │ 1000     │ 24        │ 185       │ 18.5%      │ ✅
└─────────────────┴──────────┴───────────┴───────────┴────────────┘
```

---

## 🔧 Configuración Avanzada

### Archivo: `bertopic_service_optimized.py`

```python
# Parámetros optimizados por defecto
umap_params = {
    'n_components': 15,     # Dimensiones intermedias
    'n_neighbors': 15,
    'min_dist': 0.0,
    'metric': 'cosine'
}

hdbscan_params = {
    'min_cluster_size': 4,  # Tamaño mínimo de cluster
    'min_samples': 2,        # Muestras mínimas
    'metric': 'euclidean',
    'cluster_selection_method': 'eom'
}
```

### Personalización

```python
from apps.documents.services.bertopic_service_optimized import BERTopicServiceOptimized

service = BERTopicServiceOptimized(require_bertopic=True)

# Parámetros personalizados
model = service.compute_topics(
    max_documents=1000,
    embedding_field='enhanced_embedding',  # o 'clean_embedding'
    min_topic_size=4,
    umap_params={'n_components': 20},      # Más dimensiones
    hdbscan_params={
        'min_cluster_size': 3,              # Clusters más pequeños
        'min_samples': 1                    # Más sensible
    },
    compute_metrics=True                    # Calcular calidad
)
```

---

## 🧪 Testing

### Test 1: Comparación Directa

```bash
# 1. Regenerar HDBSCAN (si no existe)
python regenerate_cluster_graph.py

# 2. Ejecutar BERTopic optimizado con mismo embedding
python run_bertopic_optimized.py --embedding enhanced_embedding

# 3. Comparar
python test_bertopic_comparison.py --mode compare
```

### Test 2: Grid Search

```bash
# Probar múltiples combinaciones de parámetros
python test_bertopic_grid_search.py --max-docs 500

# Resultado: archivo JSON con mejores configuraciones
# Ejemplo: grid_search_results_20260106_143022.json
```

### Test 3: A/B Testing

```bash
# Original
python test_bertopic_comparison.py --mode original --embedding clean_embedding

# Optimizado
python test_bertopic_comparison.py --mode optimized --embedding enhanced_embedding

# Comparar
python test_bertopic_comparison.py --mode compare
```

---

## 📈 Interpretación de Métricas

### Silhouette Score (-1 a 1)

- **> 0.5**: Excelente separación
- **0.3-0.5**: Buena separación ✅
- **0.2-0.3**: Aceptable
- **< 0.2**: Clusters mal definidos

### Calinski-Harabasz Score (sin límite)

- **> 1000**: Excelente
- **800-1000**: Bueno ✅
- **< 800**: Mejorable

### Davies-Bouldin Score (sin límite)

- **< 1.0**: Excelente
- **1.0-2.0**: Bueno ✅
- **> 2.0**: Mejorable

### Porcentaje de Outliers

- **< 15%**: Excelente
- **15-20%**: Bueno ✅
- **20-30%**: Aceptable
- **> 30%**: Parámetros muy restrictivos

---

## 🛠️ Troubleshooting

### Problema: Demasiados Clusters (>50)

**Solución:**

```bash
python run_bertopic_optimized.py --min-cluster 6 --min-samples 3
```

### Problema: Demasiados Outliers (>30%)

**Solución:**

```bash
python run_bertopic_optimized.py --min-cluster 3 --min-samples 1
```

### Problema: Clusters Solapados Visualmente

**Solución:** Ajustar UMAP 2D en el código

```python
self.umap_2d_params = {
    'n_neighbors': 5,    # Reducir
    'min_dist': 0.5,     # Aumentar
    'spread': 1.5        # Aumentar
}
```

### Problema: Keywords No Relevantes

**Solución:** Expandir stopwords en `bertopic_service_optimized.py`

```python
def _get_spanish_stopwords(self):
    stopwords = [
        # ... existentes ...
        'nuevo', 'nueva', 'término', 'legal', 'específico'
    ]
```

---

## 📚 Archivos Creados

1. **`BERTOPIC_OPTIMIZATION_GUIDE.md`** - Guía detallada de optimización
2. **`bertopic_service_optimized.py`** - Servicio optimizado
3. **`run_bertopic_optimized.py`** - Script principal de ejecución
4. **`test_bertopic_comparison.py`** - Comparación de modelos
5. **`test_bertopic_grid_search.py`** - Búsqueda de parámetros óptimos
6. **`BERTOPIC_QUICKSTART.md`** - Esta guía

---

## 🎯 Workflow Recomendado

### Para Comparación con HDBSCAN

```bash
# 1. Ejecutar con mismo embedding
python run_bertopic_optimized.py --embedding enhanced_embedding

# 2. Comparar resultados
python test_bertopic_comparison.py --mode compare

# 3. Si es similar, activar modelo
python run_bertopic_optimized.py --activate <MODEL_ID>
```

### Para Optimización de Parámetros

```bash
# 1. Grid search (puede tardar)
python test_bertopic_grid_search.py --max-docs 500

# 2. Revisar resultados en JSON

# 3. Ejecutar con mejores parámetros
python run_bertopic_optimized.py --umap-components <BEST> --min-cluster <BEST>
```

### Para Producción

```bash
# 1. Usar parámetros optimizados por defecto
python run_bertopic_optimized.py --max-docs 1000

# 2. Verificar métricas en logs

# 3. Si están bien (Silhouette > 0.25, Outliers < 20%), activar
python run_bertopic_optimized.py --activate <MODEL_ID>
```

---

## 💡 Tips

1. **Usa `enhanced_embedding`** para comparación directa con HDBSCAN
2. **`clean_embedding`** puede dar mejores resultados pero tarda más
3. **Grid search** usa menos documentos (500) para ser más rápido
4. **Silhouette score** es la métrica más importante
5. **Revisa los logs** para ver la configuración exacta usada
6. **Guarda el `model_id`** para activarlo después
7. **Compara siempre** con HDBSCAN para validar mejoras

---

## 🔗 Referencias

- **BERTopic**: https://maartengr.github.io/BERTopic/
- **UMAP**: https://umap-learn.readthedocs.io/
- **HDBSCAN**: https://hdbscan.readthedocs.io/
- **Clustering Metrics**: https://scikit-learn.org/stable/modules/clustering.html

---

## ✅ Checklist de Validación

Antes de usar en producción, verifica:

- [ ] Silhouette Score > 0.25
- [ ] Outlier % < 20%
- [ ] Número de clusters similar a HDBSCAN (±5)
- [ ] Keywords relevantes y diversos
- [ ] Tiempo de computación aceptable (<5 min)
- [ ] Visualización 2D clara y separada
- [ ] Comparación con HDBSCAN favorable

Si todos los checks pasan: **¡Listo para producción! ✨**
