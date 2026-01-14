<template>
  <v-container class="clusters-view pa-6" style="max-width: 1800px;">
    <!-- Header -->
    <v-row>
      <v-col cols="12">
        <div class="d-flex align-center justify-space-between mb-4">
          <div>
            <h1 class="text-h4 font-weight-bold mb-2">
              <v-icon size="large" class="mr-2">mdi-chart-bubble</v-icon>
              Explorador de Clusters
            </h1>
            <p class="text-subtitle-1 text-grey">
              Visualiza agrupaciones de documentos similares
            </p>
          </div>
          <v-btn
            color="primary"
            prepend-icon="mdi-refresh"
            @click="loadClusters"
            :loading="loading"
          >
            Actualizar
          </v-btn>
        </div>
      </v-col>
    </v-row>

      <!-- Controles -->
      <v-row>
        <v-col cols="12">
          <v-card>
            <v-card-title class="bg-grey-lighten-3">
              <v-icon class="mr-2">mdi-tune</v-icon>
              Configuración del Clustering
            </v-card-title>
            <v-card-text>
              <!-- Selección de Algoritmo -->
              <v-row align="center" class="mb-4">
                <v-col cols="12" md="4">
                  <v-select
                    v-model="params.algorithm"
                    label="Algoritmo de Clustering"
                    :items="algorithmOptions"
                    item-title="label"
                    item-value="value"
                    variant="outlined"
                    density="comfortable"
                    prepend-icon="mdi-brain"
                  >
                    <template #item="{ props, item }">
                      <v-list-item v-bind="props">
                        <template #subtitle>
                          <span class="text-caption">{{ item.raw.description }}</span>
                        </template>
                      </v-list-item>
                    </template>
                  </v-select>
                </v-col>

                <v-col cols="12" md="4">
                  <v-select
                    v-model="params.metric"
                    label="Métrica de Distancia"
                    :items="metricOptions"
                    item-title="label"
                    item-value="value"
                    variant="outlined"
                    density="comfortable"
                    prepend-icon="mdi-ruler"
                  ></v-select>
                </v-col>

                <v-col cols="12" md="4">
                  <v-text-field
                    v-model.number="params.nClusters"
                    label="Número de Clusters (K-Means/Agglomerative)"
                    type="number"
                    :min="2"
                    :max="20"
                    variant="outlined"
                    density="comfortable"
                    prepend-icon="mdi-numeric"
                    :disabled="params.algorithm === 'dbscan'"
                  ></v-text-field>
                </v-col>
              </v-row>

              <v-divider class="my-4"></v-divider>

              <!-- Parámetros específicos -->
              <v-row align="center">
                <!-- Epsilon - rango expandido -->
                <v-col cols="12" md="3">
                  <v-slider
                    v-model="params.eps"
                    label="Epsilon (eps)"
                    :min="0.001"
                    :max="0.5"
                    :step="0.001"
                    thumb-label
                    :disabled="params.algorithm !== 'dbscan'"
                  >
                    <template #append>
                      <v-chip size="small" color="primary">
                        {{ params.eps.toFixed(3) }}
                      </v-chip>
                    </template>
                  </v-slider>
                  <div class="text-caption text-grey mt-n2">
                    Distancia máxima entre puntos (DBSCAN)
                  </div>
                </v-col>

                <v-col cols="12" md="3">
                  <v-slider
                    v-model="params.minSamples"
                    label="Mínimo de muestras"
                    :min="1"
                    :max="20"
                    :step="1"
                    thumb-label
                    :disabled="params.algorithm !== 'dbscan'"
                  >
                    <template #append>
                      <v-chip size="small" color="secondary">
                        {{ params.minSamples }}
                      </v-chip>
                    </template>
                  </v-slider>
                  <div class="text-caption text-grey mt-n2">
                    Puntos mínimos para formar cluster (DBSCAN)
                  </div>
                </v-col>

                <v-col cols="12" md="3">
                  <v-slider
                    v-model="params.minClusterSize"
                    label="Tamaño mínimo de cluster"
                    :min="1"
                    :max="15"
                    :step="1"
                    thumb-label
                  >
                    <template #append>
                      <v-chip size="small" color="success">
                        {{ params.minClusterSize }}
                      </v-chip>
                    </template>
                  </v-slider>
                  <div class="text-caption text-grey mt-n2">
                    Filtrar clusters pequeños
                  </div>
                </v-col>

                <v-col cols="12" md="3">
                  <v-slider
                    v-model="params.maxDocuments"
                    label="Máx. documentos"
                    :min="10"
                    :max="1000"
                    :step="10"
                    thumb-label
                  >
                    <template #append>
                      <v-chip size="small" color="warning">
                        {{ params.maxDocuments }}
                      </v-chip>
                    </template>
                  </v-slider>
                  <div class="text-caption text-grey mt-n2">
                    Limitar para mejor rendimiento
                  </div>
                </v-col>

                <!-- Filtro de similitud -->
                <v-col cols="12" class="mt-2">
                  <v-slider
                    v-model="minSimilarity"
                    label="Similitud mínima de enlaces visibles"
                    :min="0"
                    :max="1"
                    :step="0.01"
                    thumb-label
                    color="info"
                  >
                    <template #thumb-label="{ modelValue }">
                      {{ (modelValue * 100).toFixed(0) }}%
                    </template>
                    <template #append>
                      <v-chip size="small" color="info">
                        {{ (minSimilarity * 100).toFixed(0) }}%
                      </v-chip>
                    </template>
                  </v-slider>
                  <div class="text-caption text-grey mt-n2">
                    Ocultar enlaces débiles en la visualización
                  </div>
                </v-col>
              </v-row>

              <v-row class="mt-2">
                <v-col cols="12">
                  <v-btn
                    color="primary"
                    variant="flat"
                    @click="loadClusters"
                    :loading="loading"
                    block
                  >
                    Aplicar Clustering
                  </v-btn>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Estadísticas -->
      <v-row class="mt-4">
        <v-col cols="12" md="3">
          <v-card color="primary" dark>
            <v-card-text>
              <div class="text-h3 font-weight-bold">
                {{ clusterData.total_documents || 0 }}
              </div>
              <div class="text-caption">Total Documentos</div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" md="3">
          <v-card color="success" dark>
            <v-card-text>
              <div class="text-h3 font-weight-bold">
                {{ clusterData.cluster_count || 0 }}
              </div>
              <div class="text-caption">Clusters Formados</div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" md="3">
          <v-card color="warning" dark>
            <v-card-text>
              <div class="text-h3 font-weight-bold">
                {{ clusterData.noise_count || 0 }}
              </div>
              <div class="text-caption">Documentos sin Cluster</div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" md="3">
          <v-card color="info" dark>
            <v-card-text>
              <div class="text-h3 font-weight-bold">
                {{ filteredLinks.length }}
              </div>
              <div class="text-caption">Enlaces Visibles</div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Contenido principal -->
      <v-row class="mt-4">
        <!-- Lista de Clusters -->
        <v-col cols="12" md="4">
          <v-card>
            <v-card-title class="bg-primary">
              <v-icon class="mr-2">mdi-format-list-bulleted</v-icon>
              Clusters Detectados
            </v-card-title>
            <v-card-text class="pa-0" style="max-height: 600px; overflow-y: auto">
              <v-list v-if="clusterData.cluster_stats && clusterData.cluster_stats.length > 0">
                <v-list-item
                  v-for="cluster in clusterData.cluster_stats"
                  :key="cluster.cluster_id"
                  :class="{ 'bg-blue-lighten-5': selectedCluster === cluster.cluster_id }"
                  @click="selectCluster(cluster.cluster_id)"
                >
                  <template v-slot:prepend>
                    <v-avatar :color="getClusterColor(cluster.cluster_id)" size="40">
                      <span class="text-white font-weight-bold">{{ cluster.cluster_id }}</span>
                    </v-avatar>
                  </template>

                  <v-list-item-title class="font-weight-bold">
                    Cluster {{ cluster.cluster_id }}
                  </v-list-item-title>
                  
                  <v-list-item-subtitle>
                    <div>{{ cluster.size }} documentos</div>
                    <div class="text-caption">
                      <v-icon size="x-small">mdi-gavel</v-icon>
                      {{ cluster.dominant_area }}
                    </div>
                  </v-list-item-subtitle>

                  <template v-slot:append>
                    <v-btn
                      icon="mdi-eye"
                      size="small"
                      variant="text"
                      @click.stop="focusCluster(cluster.cluster_id)"
                    ></v-btn>
                  </template>
                </v-list-item>
              </v-list>

              <v-alert v-else type="info" variant="tonal" class="ma-4">
                No se encontraron clusters. Ajusta los parámetros.
              </v-alert>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Visualización del Grafo -->
        <v-col cols="12" md="8">
          <v-card>
            <v-card-title class="bg-primary">
              <v-icon class="mr-2">mdi-graph</v-icon>
              Visualización de Red
              <v-spacer></v-spacer>
              <v-chip size="small" variant="outlined" color="white">
                {{ filteredNodes.length }} nodos
              </v-chip>
            </v-card-title>
            <v-card-text class="pa-0" style="height: 600px; overflow: hidden;">
              <v-network-graph
                v-if="filteredNodes.length > 0"
                :nodes="nodesData"
                :edges="edgesData"
                :layouts="layouts"
                :configs="configs"
                :event-handlers="eventHandlers"
                style="height: 100%;"
              />
              <v-alert v-else type="info" variant="tonal" class="ma-4">
                No hay datos para visualizar. Ajusta los parámetros y aplica el clustering.
              </v-alert>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
              Visualización de Red
              <v-spacer></v-spacer>
              <v-chip size="small" color="white">
                {{ filteredNodes.length }} nodos
              </v-chip>
            </v-card-title>
            <v-card-text class="pa-0" style="height: calc(100% - 64px); position: relative">
              <v-network-graph
                v-if="!loading && filteredNodes.length > 0"
                :nodes="networkNodes"
                :edges="networkEdges"
                :layouts="layouts"
                :configs="configs"
                :event-handlers="eventHandlers"
              />

              <div
                v-else-if="loading"
                class="d-flex align-center justify-center"
                style="height: 100%"
              >
                <div class="text-center">
                  <v-progress-circular
                    indeterminate
                    color="primary"
                    size="64"
                  ></v-progress-circular>
                  <div class="text-h6 mt-4">Procesando clusters...</div>
                </div>
              </div>

              <div
                v-else
                class="d-flex align-center justify-center"
                style="height: 100%"
              >
                <v-alert type="info" variant="tonal">
                  Configura los parámetros y haz clic en "Aplicar Clustering"
                </v-alert>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Leyenda -->
      <v-row class="mt-4">
        <v-col cols="12">
          <v-card>
            <v-card-title>
              <v-icon class="mr-2">mdi-information</v-icon>
              Leyenda
            </v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="12" md="6">
                  <div class="text-subtitle-2 mb-2">Colores por Área Legal:</div>
                  <div class="d-flex flex-wrap gap-2">
                    <v-chip size="small" color="#1976D2">Laboral</v-chip>
                    <v-chip size="small" color="#388E3C">Civil</v-chip>
                    <v-chip size="small" color="#D32F2F">Penal</v-chip>
                    <v-chip size="small" color="#7B1FA2">Constitucional</v-chip>
                    <v-chip size="small" color="#F57C00">Administrativo</v-chip>
                    <v-chip size="small" color="#757575">Sin área</v-chip>
                  </div>
                </v-col>
                <v-col cols="12" md="6">
                  <div class="text-subtitle-2 mb-2">Enlaces (Similitud):</div>
                  <div class="text-caption">
                    • Grosor = Mayor similitud<br>
                    • Color oscuro = Alta similitud (>80%)<br>
                    • Color claro = Baja similitud (<40%)
                  </div>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-container>

    <!-- Diálogo de documento -->
    <v-dialog v-model="showDocDialog" max-width="800">
      <v-card v-if="selectedDocument">
        <v-card-title class="bg-primary">
          <v-icon class="mr-2">mdi-file-document</v-icon>
          Detalles del Documento
          <v-spacer></v-spacer>
          <v-btn icon="mdi-close" variant="text" @click="showDocDialog = false"></v-btn>
        </v-card-title>
        <v-card-text class="pa-4">
          <div class="mb-3">
            <v-chip :color="getClusterColor(selectedDocument.cluster)" class="mb-2">
              Cluster {{ selectedDocument.cluster }}
            </v-chip>
            <v-chip v-if="selectedDocument.is_noise" color="warning" class="mb-2 ml-2">
              Ruido
            </v-chip>
          </div>

          <div class="mb-3">
            <strong>Título:</strong>
            <div>{{ selectedDocument.title }}</div>
          </div>

          <v-row>
            <v-col cols="6">
              <strong>Expediente:</strong>
              <div>{{ selectedDocument.case_number || 'N/A' }}</div>
            </v-col>
            <v-col cols="6">
              <strong>Área Legal:</strong>
              <div>{{ selectedDocument.legal_area || 'N/A' }}</div>
            </v-col>
            <v-col cols="6">
              <strong>Tipo:</strong>
              <div>{{ selectedDocument.doc_type || 'N/A' }}</div>
            </v-col>
            <v-col cols="6">
              <strong>Fecha:</strong>
              <div>{{ selectedDocument.document_date || 'N/A' }}</div>
            </v-col>
          </v-row>

          <div class="mt-3">
            <strong>Resumen:</strong>
            <div class="mt-2 text-body-2" style="max-height: 200px; overflow-y: auto">
              {{ selectedDocument.summary || 'Sin resumen disponible' }}
            </div>
          </div>

          <div class="mt-3" v-if="selectedDocument.persons">
            <strong>Personas:</strong>
            <div class="text-body-2">{{ selectedDocument.persons }}</div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="viewFullDocument(selectedDocument.id)">
            Ver Documento Completo
          </v-btn>
          <v-btn variant="text" @click="showDocDialog = false">
            Cerrar
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import axios from 'axios';
import { VNetworkGraph } from 'v-network-graph';
import 'v-network-graph/lib/style.css';
import * as vNG from 'v-network-graph';
import { ForceLayout } from 'v-network-graph/lib/force-layout';
import { useRouter } from 'vue-router';

const router = useRouter();

// Estado
const loading = ref(false);
const clusterData = ref({
  nodes: [],
  links: [],
  clusters: {},
  cluster_stats: [],
  total_documents: 0,
  cluster_count: 0,
  noise_count: 0
});

const params = ref({
  eps: 0.01,
  minSamples: 2,
  minClusterSize: 2,
  maxDocuments: 200
});

const minSimilarity = ref(0.3);
const selectedCluster = ref(null);
const selectedDocument = ref(null);
const showDocDialog = ref(false);

// Nodos y enlaces filtrados
const filteredNodes = computed(() => {
  if (selectedCluster.value === null) {
    return clusterData.value.nodes || [];
  }
  return (clusterData.value.nodes || []).filter(
    node => node.cluster === selectedCluster.value
  );
});

const filteredLinks = computed(() => {
  const links = clusterData.value.links || [];
  return links.filter(link => {
    // Filtrar por similitud
    if (link.value < minSimilarity.value) return false;
    
    // Si hay cluster seleccionado, solo mostrar enlaces de ese cluster
    if (selectedCluster.value !== null) {
      return link.cluster === selectedCluster.value;
    }
    
    return true;
  });
});

// Transformar para v-network-graph
const networkNodes = computed(() => {
  const nodes = {};
  filteredNodes.value.forEach(node => {
    nodes[node.id] = {
      name: node.label,
      ...node
    };
  });
  return nodes;
});

const networkEdges = computed(() => {
  const edges = {};
  filteredLinks.value.forEach((link, index) => {
    edges[`edge${index}`] = {
      source: link.source,
      target: link.target,
      value: link.value,
      cluster: link.cluster
    };
  });
  return edges;
});

// Configuración del grafo
const layouts = ref({ nodes: {} });

const getEdgeColor = (similarity) => {
  if (similarity >= 0.8) {
    const intensity = Math.floor(((similarity - 0.8) / 0.2) * 50);
    return `rgb(${50 - intensity}, ${50 - intensity}, ${50 - intensity})`;
  } else if (similarity >= 0.6) {
    const intensity = Math.floor(((similarity - 0.6) / 0.2) * 70);
    return `rgb(${120 - intensity}, ${120 - intensity}, ${120 - intensity})`;
  } else if (similarity >= 0.4) {
    const intensity = Math.floor(((similarity - 0.4) / 0.2) * 70);
    return `rgb(${190 - intensity}, ${190 - intensity}, ${190 - intensity})`;
  } else {
    const intensity = Math.floor((similarity / 0.4) * 55);
    return `rgb(${245 - intensity}, ${245 - intensity}, ${245 - intensity})`;
  }
};

const configs = vNG.defineConfigs({
  view: {
    layoutHandler: new ForceLayout({
      positionFixedByDrag: false,
      positionFixedByClickWithAltKey: true,
      createSimulation: (d3, nodes, edges) => {
        const forceLink = d3.forceLink(edges).id((d) => d.id);
        return d3
          .forceSimulation(nodes)
          .force('edge', forceLink.distance(80).strength(0.5))
          .force('charge', d3.forceManyBody().strength(-600))
          .force('center', d3.forceCenter().strength(0.05))
          .alphaDecay(0.015);
      }
    })
  },
  node: {
    selectable: true,
    normal: {
      type: (node) => node.shape || 'circle',
      radius: (node) => node.val || 6,
      color: (node) => node.color || '#666'
    },
    hover: {
      radius: (node) => (node.val || 6) * 1.3,
      color: (node) => node.color || '#666'
    },
    selected: {
      radius: (node) => (node.val || 6) * 1.2,
      color: (node) => node.color || '#666',
      strokeWidth: 3,
      strokeColor: '#FF9800'
    },
    label: {
      visible: true,
      fontSize: 10,
      color: '#333'
    }
  },
  edge: {
    normal: {
      width: (edge) => {
        const similarity = edge.value || 0.5;
        if (similarity >= 0.8) return 3 + ((similarity - 0.8) / 0.2) * 2;
        else if (similarity >= 0.6) return 2 + ((similarity - 0.6) / 0.2) * 1;
        else if (similarity >= 0.4) return 1.2 + ((similarity - 0.4) / 0.2) * 0.8;
        else return 0.5 + (similarity / 0.4) * 0.7;
      },
      color: (edge) => getEdgeColor(edge.value || 0.5)
    },
    hover: {
      width: (edge) => {
        const similarity = edge.value || 0.5;
        if (similarity >= 0.8) return 4 + ((similarity - 0.8) / 0.2) * 2;
        else if (similarity >= 0.6) return 3 + ((similarity - 0.6) / 0.2) * 1;
        else if (similarity >= 0.4) return 2.2 + ((similarity - 0.4) / 0.2) * 0.8;
        else return 1.5 + (similarity / 0.4) * 0.7;
      },
      color: (edge) => '#FF9800'
    },
    gap: 8,
    type: 'straight',
    marker: {
      target: {
        type: 'none'
      }
    }
  }
});

const eventHandlers = {
  'node:click': ({ node }) => {
    const nodeData = clusterData.value.nodes.find(n => n.id === node);
    if (nodeData) {
      selectedDocument.value = nodeData;
      showDocDialog.value = true;
    }
  }
};

// Métodos
const getClusterColor = (clusterId) => {
  const colors = [
    'primary', 'secondary', 'success', 'warning', 'error',
    'info', 'purple', 'pink', 'indigo', 'teal'
  ];
  return colors[Math.abs(clusterId) % colors.length];
};

const loadClusters = async () => {
  loading.value = true;
  
  try {
    const response = await axios.get('http://localhost:8000/api/documents/all_clusters/', {
      params: {
        eps: params.value.eps,
        min_samples: params.value.minSamples,
        min_cluster_size: params.value.minClusterSize,
        max_documents: params.value.maxDocuments
      }
    });
    
    clusterData.value = response.data;
    selectedCluster.value = null;
  } catch (error) {
    console.error('Error loading clusters:', error);
  } finally {
    loading.value = false;
  }
};

const selectCluster = (clusterId) => {
  selectedCluster.value = selectedCluster.value === clusterId ? null : clusterId;
};

const focusCluster = (clusterId) => {
  selectedCluster.value = clusterId;
};

const viewFullDocument = (docId) => {
  showDocDialog.value = false;
  router.push({ name: 'Home', query: { doc: docId } });
};

// Lifecycle
onMounted(() => {
  loadClusters();
});
</script>

<style scoped>
.clusters-view {
  min-height: 100vh;
  background: #f5f5f5;
}

.gap-2 {
  gap: 8px;
}
</style>
