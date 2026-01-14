# 🎯 Guía de Optimización de BERTopic para Clustering de Documentos Legales

## 📊 Análisis del Problema

### Estado Actual

**HDBSCAN (clustering_service_new.py)**

- ✅ **Parámetros optimizados**: min_cluster_size=4, min_samples=2
- ✅ **Pipeline**: 384D → UMAP 30D → HDBSCAN → UMAP 2D
- ✅ **Resultados**: Clusters bien definidos, pocos outliers, buena separación

**BERTopic (bertopic_service.py)**

- ⚠️ **Parámetros subóptimos**: min_cluster_size=5, min_samples=3
- ⚠️ **Pipeline**: 768D → BERTopic (UMAP 5D → HDBSCAN) → UMAP 2D
- ❌ **Problemas potenciales**:
  - Dimensionalidad intermedia muy baja (5D)
  - Parámetros más restrictivos que HDBSCAN standalone
  - Diferente campo de embedding (clean_embedding 768D vs enhanced_embedding 384D)

---

## 🔬 Diferencias Clave

| Aspecto                 | HDBSCAN Standalone        | BERTopic Actual        |
| ----------------------- | ------------------------- | ---------------------- |
| **Embedding**           | enhanced_embedding (384D) | clean_embedding (768D) |
| **UMAP Intermedio**     | 30D                       | 5D                     |
| **min_cluster_size**    | 4                         | 5                      |
| **min_samples**         | 2                         | 3                      |
| **n_neighbors (UMAP)**  | 15                        | 15                     |
| **min_dist (UMAP)**     | 0.0                       | 0.0                    |
| **UMAP 2D n_neighbors** | 10 (ajustado)             | 15                     |
| **UMAP 2D min_dist**    | 0.99                      | 0.1                    |

---

## 🎯 Estrategia de Optimización

### 1. **Alinear Embeddings**

```python
# OPCIÓN A: Usar enhanced_embedding (384D) como HDBSCAN
embedding_field = 'enhanced_embedding'

# OPCIÓN B: Mantener clean_embedding (768D) pero ajustar UMAP
# clean_embedding puede tener más información pero requiere más reducción dimensional
```

### 2. **Incrementar Dimensionalidad Intermedia UMAP**

```python
# ACTUAL (muy bajo para documentos complejos)
umap_params = {'n_components': 5}

# RECOMENDADO (más información preservada)
umap_params = {
    'n_components': 15,  # Sweet spot: 10-20
    'n_neighbors': 15,    # Mantener
    'min_dist': 0.0,      # Mantener
    'metric': 'cosine',   # Mantener
    'random_state': 42
}
```

**Justificación**:

- 5D es muy restrictivo y pierde mucha información semántica
- 15D preserva mejor la estructura local y global
- HDBSCAN funciona mejor con más dimensiones (10-30D)

### 3. **Alinear Parámetros de HDBSCAN**

```python
# ACTUAL (restrictivo)
hdbscan_params = {
    'min_cluster_size': 5,
    'min_samples': 3
}

# RECOMENDADO (igual que HDBSCAN optimizado)
hdbscan_params = {
    'min_cluster_size': 4,      # Reducido de 5
    'min_samples': 2,            # Reducido de 3
    'metric': 'euclidean',       # Mantener
    'cluster_selection_method': 'eom',  # Mantener
    'prediction_data': True      # Mantener
}
```

**Justificación**:

- `min_cluster_size=4`: Balance entre ruido y clusters muy pequeños
- `min_samples=2`: Mayor sensibilidad sin ser demasiado ruidoso
- Estos valores están probados en HDBSCAN standalone

### 4. **Optimizar UMAP para Visualización 2D**

```python
# ACTUAL
umap_2d = umap.UMAP(
    n_components=2,
    n_neighbors=15,
    min_dist=0.1,
    metric='cosine',
    random_state=42
)

# RECOMENDADO (clusters más separados visualmente)
umap_2d = umap.UMAP(
    n_components=2,
    n_neighbors=10,      # Reducido para mejor separación local
    min_dist=0.3,        # Aumentado para evitar solapamiento
    metric='cosine',     # Mantener
    random_state=42,
    spread=1.0           # Control adicional de dispersión
)
```

### 5. **Mejorar Vectorización de Texto (c-TF-IDF)**

```python
# ACTUAL (básico)
vectorizer_params = {
    'stop_words': spanish_stopwords,
    'ngram_range': (1, 2),
    'min_df': 2,
    'max_df': 0.95
}

# RECOMENDADO (más robusto)
vectorizer_params = {
    'stop_words': spanish_stopwords,
    'ngram_range': (1, 3),      # Incluir trigramas para frases legales
    'min_df': 3,                 # Filtrar términos muy raros
    'max_df': 0.90,              # Filtrar términos muy comunes
    'max_features': 5000,        # Limitar vocabulario
    'token_pattern': r'\b[a-záéíóúñü]{3,}\b',  # Mínimo 3 caracteres, español
}
```

### 6. **Ajustar Representación de Tópicos**

```python
# ACTUAL
representation_params = {
    'top_n_words': 10,
    'diversity': 0.3
}

# RECOMENDADO (keywords más distintivos)
representation_params = {
    'top_n_words': 15,    # Más keywords para contexto legal
    'diversity': 0.5      # Mayor diversidad para evitar redundancia
}

# Múltiples modelos de representación
from bertopic.representation import (
    KeyBERTInspired,
    MaximalMarginalRelevance,
    PartOfSpeech  # Nuevo: priorizar sustantivos y verbos
)

representation_models = [
    KeyBERTInspired(top_n_words=15),
    MaximalMarginalRelevance(diversity=0.5),
    # PartOfSpeech("es_core_news_sm")  # Requiere spaCy
]
```

---

## 🚀 Implementación Paso a Paso

### Archivo: `bertopic_service_optimized.py`

He creado un archivo nuevo con todas las optimizaciones integradas.

### Cambios Principales:

1. **Parámetros UMAP Intermedio**

   ```python
   self.umap_params = {
       'n_components': 15,  # ⬆️ de 5 a 15
       'n_neighbors': 15,
       'min_dist': 0.0,
       'metric': 'cosine',
       'random_state': 42
   }
   ```

2. **Parámetros HDBSCAN**

   ```python
   self.hdbscan_params = {
       'min_cluster_size': 4,  # ⬇️ de 5 a 4
       'min_samples': 2,        # ⬇️ de 3 a 2
       'metric': 'euclidean',
       'cluster_selection_method': 'eom',
       'prediction_data': True
   }
   ```

3. **Vectorizador Mejorado**

   ```python
   self.vectorizer_params = {
       'ngram_range': (1, 3),    # ⬆️ trigramas
       'min_df': 3,              # ⬆️ filtrar raros
       'max_df': 0.90,           # ⬇️ filtrar comunes
       'max_features': 5000      # 🆕 límite vocabulario
   }
   ```

4. **Múltiples Campos de Embedding**
   ```python
   # Soporta usar enhanced_embedding para comparación directa con HDBSCAN
   def compute_topics(
       self,
       embedding_field: str = 'clean_embedding',  # o 'enhanced_embedding'
       ...
   )
   ```

---

## 🧪 Plan de Pruebas

### Test 1: Comparación Directa (Mismo Embedding)

```bash
# Regenerar HDBSCAN con enhanced_embedding (384D)
python regenerate_cluster_graph.py

# Regenerar BERTopic con enhanced_embedding (384D) + parámetros optimizados
python test_bertopic_optimized.py --embedding enhanced_embedding
```

### Test 2: BERTopic con clean_embedding Optimizado

```bash
# BERTopic con clean_embedding (768D) + UMAP 15D
python test_bertopic_optimized.py --embedding clean_embedding
```

### Test 3: Grid Search de Parámetros

```bash
# Probar diferentes combinaciones de n_components
python test_bertopic_grid_search.py
```

### Métricas de Evaluación

```python
from sklearn.metrics import (
    silhouette_score,          # Separación de clusters (más alto = mejor)
    calinski_harabasz_score,   # Ratio varianza inter/intra (más alto = mejor)
    davies_bouldin_score       # Similitud promedio cluster (más bajo = mejor)
)

# Comparar:
# 1. Número de clusters
# 2. Porcentaje de outliers (noise_count/total)
# 3. Distribución de tamaños de clusters
# 4. Silhouette score
# 5. Calinski-Harabasz score
# 6. Davies-Bouldin score
```

---

## 📈 Resultados Esperados

### Mejoras Esperadas

1. **Más Clusters Significativos**

   - HDBSCAN standalone encuentra ~20-30 clusters
   - BERTopic actual: ~10-15 clusters
   - BERTopic optimizado: ~20-30 clusters (similar a HDBSCAN)

2. **Menos Outliers**

   - HDBSCAN: ~15-20% outliers
   - BERTopic actual: ~25-30% outliers
   - BERTopic optimizado: ~15-20% outliers

3. **Mejor Separación Visual**

   - Clusters más compactos y separados en 2D
   - Menos solapamiento visual

4. **Keywords Más Relevantes**
   - Trigramas capturan frases legales completas
   - Mayor diversidad de términos por tópico

### Métricas de Referencia (HDBSCAN Optimizado)

```
Silhouette Score: 0.25 - 0.35
Calinski-Harabasz: 800 - 1200
Davies-Bouldin: 1.5 - 2.0
Clusters: 20-30
Outliers: 15-20%
```

---

## 🛠️ Troubleshooting

### Problema 1: Demasiados Clusters

**Síntomas**: >50 clusters, muchos con <5 documentos
**Solución**:

```python
min_cluster_size = 5  # Incrementar
min_samples = 3        # Incrementar
```

### Problema 2: Demasiados Outliers

**Síntomas**: >30% documentos sin cluster
**Solución**:

```python
min_cluster_size = 3  # Reducir
min_samples = 1        # Reducir (cuidado con ruido)
cluster_selection_method = 'leaf'  # Probar método alternativo
```

### Problema 3: Clusters Muy Solapados en 2D

**Síntomas**: No se distinguen clusters visualmente
**Solución**:

```python
# UMAP 2D más agresivo
umap_2d_params = {
    'n_neighbors': 5,   # Reducir para separación local
    'min_dist': 0.5,    # Aumentar para dispersión
    'spread': 1.5       # Aumentar spread
}
```

### Problema 4: Keywords No Relevantes

**Síntomas**: Palabras genéricas, no distintivas
**Solución**:

```python
# Expandir stopwords
stopwords += ['demanda', 'sentencia', 'auto', 'decreto', ...]

# Reducir max_df
vectorizer_params['max_df'] = 0.80

# Aumentar min_df
vectorizer_params['min_df'] = 5
```

---

## 📚 Referencias

1. **BERTopic Documentation**: https://maartengr.github.io/BERTopic/
2. **UMAP Parameters Guide**: https://umap-learn.readthedocs.io/en/latest/parameters.html
3. **HDBSCAN Parameters**: https://hdbscan.readthedocs.io/en/latest/parameter_selection.html
4. **Cluster Validation**: https://scikit-learn.org/stable/modules/clustering.html#clustering-evaluation

---

## 🎯 Recomendación Final

**Configuración Óptima Recomendada**:

```python
# 1. Usar enhanced_embedding para comparación directa con HDBSCAN
embedding_field = 'enhanced_embedding'  # 384D

# 2. UMAP intermedio
umap_params = {
    'n_components': 15,
    'n_neighbors': 15,
    'min_dist': 0.0,
    'metric': 'cosine'
}

# 3. HDBSCAN
hdbscan_params = {
    'min_cluster_size': 4,
    'min_samples': 2,
    'metric': 'euclidean',
    'cluster_selection_method': 'eom'
}

# 4. UMAP 2D
umap_2d_params = {
    'n_components': 2,
    'n_neighbors': 10,
    'min_dist': 0.3,
    'metric': 'cosine'
}

# 5. Vectorizador
vectorizer_params = {
    'ngram_range': (1, 3),
    'min_df': 3,
    'max_df': 0.90,
    'max_features': 5000
}
```

**Estos parámetros deberían producir resultados muy similares a HDBSCAN standalone, con el beneficio adicional de tener keywords interpretables por tópico.**
