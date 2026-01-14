<template>
  <v-container fluid class="clusters-view-new pa-6">
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
              Mapa visual de documentos legales agrupados por similitud
              semántica
            </p>
          </div>
          <div class="d-flex gap-2">
            <v-chip
              v-if="metadata"
              color="success"
              variant="outlined"
              prepend-icon="mdi-clock-outline"
            >
              Actualizado: {{ formatDate(metadata.created_at) }}
            </v-chip>
            <v-btn
              color="primary"
              prepend-icon="mdi-refresh"
              @click="loadClusters"
              :loading="loading"
            >
              Recargar
            </v-btn>
          </div>
        </div>
      </v-col>
    </v-row>

    <!-- Stats Cards -->
    <v-row v-if="metadata">
      <v-col cols="12" md="3">
        <v-card>
          <v-card-text>
            <div class="text-caption text-grey mb-1">Total Documentos</div>
            <div class="text-h4">{{ metadata.document_count }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card>
          <v-card-text>
            <div class="text-caption text-grey mb-1">Clusters Encontrados</div>
            <div class="text-h4 text-primary">{{ metadata.cluster_count }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card>
          <v-card-text>
            <div class="text-caption text-grey mb-1">
              Documentos Sin Cluster
            </div>
            <div class="text-h4 text-warning">{{ metadata.noise_count }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card>
          <v-card-text>
            <div class="text-caption text-grey mb-1">Algoritmo</div>
            <div class="text-h6">{{ metadata.algorithm?.toUpperCase() }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Main Graph View -->
    <v-row>
      <v-col cols="12">
        <v-card elevation="2">
          <v-card-title
            class="bg-grey-lighten-3 d-flex justify-space-between align-center"
          >
            <div>
              <v-icon class="mr-2">mdi-graph</v-icon>
              Vista de Clusters
              <v-chip
                v-if="selectedCluster !== null"
                size="small"
                color="primary"
                class="ml-2"
                closable
                @click:close="selectedCluster = null"
              >
                Cluster {{ selectedCluster }}
              </v-chip>
            </div>
            <div class="d-flex gap-2">
              <v-btn
                size="small"
                :color="showAllEdges ? 'primary' : 'default'"
                @click="toggleAllEdges"
                prepend-icon="mdi-connection"
              >
                {{ showAllEdges ? "Ocultar" : "Mostrar" }} Conexiones
              </v-btn>
              <v-tooltip bottom>
                <template v-slot:activator="{ props }">
                  <v-btn
                    v-bind="props"
                    size="small"
                    icon="mdi-help-circle-outline"
                    variant="text"
                  ></v-btn>
                </template>
                <div style="max-width: 300px">
                  <strong>Controles:</strong><br />
                  • Rueda del ratón: Zoom<br />
                  • Arrastrar: Pan<br />
                  • Click: Ver detalles<br />
                  • Doble click: Ver vecinos<br />
                  • Click en cluster: Filtrar
                </div>
              </v-tooltip>
            </div>
          </v-card-title>

          <v-card-text class="pa-4" style="height: 600px; position: relative">
            <!-- Loading State -->
            <div
              v-if="loading"
              class="d-flex align-center justify-center"
              style="height: 100%"
            >
              <div class="text-center">
                <v-progress-circular
                  indeterminate
                  color="primary"
                  size="64"
                ></v-progress-circular>
                <div class="mt-4 text-h6">Cargando clusters...</div>
              </div>
            </div>

            <!-- Empty State -->
            <div
              v-else-if="!nodes || nodes.length === 0"
              class="d-flex align-center justify-center"
              style="height: 100%"
            >
              <div class="text-center">
                <v-icon size="80" color="grey">mdi-chart-bubble</v-icon>
                <div class="text-h6 mt-4">No hay clusters disponibles</div>
                <div class="text-caption text-grey mt-2">
                  Los clusters se generan automáticamente al procesar documentos
                </div>
              </div>
            </div>

            <!-- Network Graph -->
            <v-network-graph
              v-else
              :nodes="networkNodes"
              :edges="networkEdges"
              :layouts="layouts"
              :configs="configs"
              :event-handlers="eventHandlers"
            >
              <template #override-node-label="{ nodeId, scale, ...slotProps }">
                <text
                  v-bind="slotProps"
                  :font-size="10 / scale"
                  text-anchor="middle"
                  dominant-baseline="central"
                  :fill="getNodeTextColor(nodeId)"
                  :y="15 / scale"
                >
                  {{ getNodeLabel(nodeId) }}
                </text>
              </template>
            </v-network-graph>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Cluster Statistics -->
    <v-row v-if="clusterStats && clusterStats.length > 0">
      <v-col cols="12">
        <v-card elevation="2">
          <v-card-title class="bg-grey-lighten-3">
            <v-icon class="mr-2">mdi-chart-bar</v-icon>
            Estadísticas por Cluster
          </v-card-title>
          <v-card-text>
            <v-row>
              <v-col
                v-for="stat in clusterStats.slice(0, 6)"
                :key="stat.cluster_label"
                cols="12"
                md="6"
                lg="4"
              >
                <v-card
                  variant="outlined"
                  @click="filterByCluster(stat.cluster_label)"
                  :color="
                    selectedCluster === stat.cluster_label ? 'primary' : ''
                  "
                  :class="{
                    'selected-cluster': selectedCluster === stat.cluster_label,
                  }"
                  style="cursor: pointer; transition: all 0.3s"
                >
                  <v-card-text>
                    <div class="d-flex justify-space-between align-center mb-2">
                      <div class="text-h6">
                        <v-icon
                          :color="
                            clusterColors[
                              stat.cluster_label % clusterColors.length
                            ]
                          "
                          size="small"
                          class="mr-1"
                        >
                          mdi-circle
                        </v-icon>
                        Cluster {{ stat.cluster_label }}
                      </div>
                      <v-chip size="small" color="primary">
                        {{ stat.size }} docs
                      </v-chip>
                    </div>
                    <div class="text-caption text-grey mb-2">
                      Área principal: <strong>{{ stat.main_area }}</strong>
                    </div>
                    <div class="d-flex gap-1 flex-wrap">
                      <v-chip
                        v-for="(count, area) in stat.area_distribution"
                        :key="area"
                        size="x-small"
                        variant="outlined"
                      >
                        {{ area }}: {{ count }}
                      </v-chip>
                    </div>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Document Details Dialog -->
    <v-dialog v-model="showDetails" max-width="800">
      <v-card v-if="selectedDocument">
        <v-card-title class="bg-primary text-white">
          <div class="d-flex justify-space-between align-center">
            <span>{{ selectedDocument.title }}</span>
            <v-btn
              icon="mdi-close"
              variant="text"
              color="white"
              size="small"
              @click="showDetails = false"
            ></v-btn>
          </div>
        </v-card-title>
        <v-card-text class="pa-4">
          <v-row>
            <v-col cols="12">
              <div class="mb-2">
                <strong>Expediente:</strong>
                {{ selectedDocument.case_number || "N/A" }}
              </div>
              <div class="mb-2">
                <strong>Área Legal:</strong>
                {{ selectedDocument.legal_area || "N/A" }}
              </div>
              <div class="mb-2">
                <strong>Tipo:</strong> {{ selectedDocument.doc_type || "N/A" }}
              </div>
              <div class="mb-2">
                <strong>Cluster:</strong> {{ selectedDocument.cluster }}
              </div>
              <div class="mb-2" v-if="selectedDocument.document_date">
                <strong>Fecha:</strong>
                {{ formatDate(selectedDocument.document_date) }}
              </div>
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-btn color="primary" @click="showNeighbors(selectedDocument.id)">
            Ver Documentos Relacionados
          </v-btn>
          <v-spacer></v-spacer>
          <v-btn @click="showDetails = false">Cerrar</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import axios from "axios";
import { VNetworkGraph } from "v-network-graph";
import * as vNG from "v-network-graph";
import "v-network-graph/lib/style.css";

// State
const loading = ref(false);
const showAllEdges = ref(false);
const showDetails = ref(false);
const selectedDocument = ref(null);
const selectedNode = ref(null);
const selectedCluster = ref(null); // For cluster filtering

// Data from API
const nodes = ref([]);
const links = ref([]);
const clusters = ref({});
const clusterStats = ref([]);
const metadata = ref(null);

// Neighbors data (for connected mode)
const neighborsData = ref(null);

// Color palette for clusters
const clusterColors = [
  "#D32F2F", // Red
  "#1976D2", // Blue
  "#388E3C", // Green
  "#F57C00", // Orange
  "#7B1FA2", // Purple
  "#0097A7", // Cyan
  "#E91E63", // Pink
  "#5D4037", // Brown
  "#455A64", // Blue Grey
  "#FBC02D", // Yellow
];

// Area colors (from your original implementation)
const areaColors = {
  Penal: "#D32F2F",
  Laboral: "#1976D2",
  "Familia Civil": "#E91E63",
  Civil: "#388E3C",
  "Familia Tutelar": "#F06292",
  Comercial: "#0097A7",
  "Derecho Constitucional": "#7B1FA2",
  "Contencioso Administrativo": "#F57C00",
  "Familia Penal": "#AD1457",
  "Extension de Dominio": "#5E35B1",
  Otros: "#757575",
};

// Load clusters from new API
const loadClusters = async () => {
  loading.value = true;
  try {
    const response = await axios.get("/api/documents/all_clusters/", {
      params: {
        include_edges: showAllEdges.value,
      },
    });

    nodes.value = response.data.nodes || [];
    links.value = response.data.links || [];
    clusters.value = response.data.clusters || {};
    clusterStats.value = response.data.cluster_stats || [];
    metadata.value = response.data.metadata || null;

    console.log("✅ Clusters loaded:", {
      nodes: nodes.value.length,
      links: links.value.length,
      clusters: Object.keys(clusters.value).length,
    });

    // Debug: Check if we have data
    console.log("📊 First 3 nodes:", nodes.value.slice(0, 3));
  } catch (error) {
    console.error("❌ Error loading clusters:", error);
    console.error("Error details:", error.response?.data || error.message);
  } finally {
    loading.value = false;
  }
};

// Show neighbors for a specific document
const showNeighbors = async (documentId) => {
  try {
    const response = await axios.get(
      `/api/documents/${documentId}/neighbors/`,
      {
        params: {
          max_neighbors: 10,
        },
      }
    );

    neighborsData.value = response.data;
    selectedNode.value = documentId;

    console.log("✅ Neighbors loaded:", response.data);
  } catch (error) {
    console.error("❌ Error loading neighbors:", error);
  }
};

// Toggle showing all edges
const toggleAllEdges = async () => {
  showAllEdges.value = !showAllEdges.value;
  await loadClusters();
};

// Filter by cluster
const filterByCluster = (clusterLabel) => {
  if (selectedCluster.value === clusterLabel) {
    // Unfilter - show all
    selectedCluster.value = null;
    console.log("✅ Showing all clusters");
  } else {
    // Filter to specific cluster
    selectedCluster.value = clusterLabel;
    console.log("✅ Filtering to cluster:", clusterLabel);
  }
};

// Format date
const formatDate = (dateString) => {
  if (!dateString) return "N/A";
  const date = new Date(dateString);
  return date.toLocaleDateString("es-ES", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
};

// Network graph configuration
const networkNodes = computed(() => {
  const result = {};

  // Filter nodes by selected cluster if any
  const filteredNodes =
    selectedCluster.value !== null
      ? nodes.value.filter((node) => node.cluster === selectedCluster.value)
      : nodes.value;

  filteredNodes.forEach((node) => {
    result[node.id] = {
      name: getNodeLabel(node.id),
      color: getNodeColor(node),
      size: node.is_noise ? 3 : 6, // Slightly bigger for visibility: 3 for noise, 6 for clustered
    };
  });

  console.log("🔵 networkNodes computed:", Object.keys(result).length, "nodes");

  return result;
});

const networkEdges = computed(() => {
  const result = {};

  if (showAllEdges.value) {
    // Get node IDs that are currently visible
    const visibleNodeIds = new Set(
      Object.keys(networkNodes.value).map((id) => parseInt(id))
    );

    // Show only edges between visible nodes
    links.value.forEach((link, idx) => {
      if (visibleNodeIds.has(link.source) && visibleNodeIds.has(link.target)) {
        result[`edge-${idx}`] = {
          source: link.source,
          target: link.target,
          width: (link.similarity || 0.5) * 1.5, // Slightly thicker for visibility
          color: getEdgeColor(link.similarity || 0.5),
        };
      }
    });
  }

  return result;
});

// Get node color based on cluster (ALWAYS use cluster colors for consistency)
const getNodeColor = (node) => {
  if (node.is_noise) {
    return "#BDBDBD"; // Gray for noise points
  }

  // Use cluster color consistently
  const clusterIdx = Math.abs(node.cluster) % clusterColors.length;
  return clusterColors[clusterIdx];
};

// Get edge color based on similarity
const getEdgeColor = (similarity) => {
  if (similarity > 0.8) return "#2E7D32"; // Dark green
  if (similarity > 0.6) return "#5a5a5a"; // Dark gray
  if (similarity > 0.4) return "#9a9a9a"; // Medium gray
  return "#d0d0d0"; // Light gray
};

// Get node label
const getNodeLabel = (nodeId) => {
  const node = nodes.value.find((n) => n.id === nodeId);
  if (!node) return "";
  return node.case_number || node.title?.substring(0, 15) + "..." || "Doc";
};

// Get node text color
const getNodeTextColor = (nodeId) => {
  const node = nodes.value.find((n) => n.id === nodeId);
  return node?.is_noise ? "#757575" : "#333333";
};

// Network graph layouts
const layouts = ref({
  nodes: {}, // Will be populated with x, y from API
});

// Update layouts when nodes change
watch(
  nodes,
  (newNodes) => {
    const nodeLayouts = {};
    newNodes.forEach((node) => {
      nodeLayouts[node.id] = {
        x: node.x * 15, // Reduced scale for much tighter clustering: 30 -> 15
        y: node.y * 15,
      };
    });
    layouts.value = { nodes: nodeLayouts };

    console.log(
      "📐 Layouts updated:",
      Object.keys(nodeLayouts).length,
      "positions"
    );
    console.log("📍 First layout:", Object.values(nodeLayouts)[0]);
  },
  { immediate: true }
);

// Network graph configs
const configs = ref(
  vNG.defineConfigs({
    view: {
      scalingObjects: true,
      minZoomLevel: 0.05, // Allow zooming out to see all clusters
      maxZoomLevel: 20, // Allow zooming in close
      autoPanAndZoomOnLoad: "fit-content", // Auto-fit the graph on load
      autoPanOnResize: true,
      fit: {
        padding: { top: 40, bottom: 40, left: 40, right: 40 }, // Balanced padding
      },
      layoutHandler: new vNG.SimpleLayout(),
      mouseWheelZoomEnabled: true, // Enable mouse wheel zoom
      doubleClickZoomEnabled: true, // Enable double-click zoom
      panEnabled: true, // Enable panning
    },
    node: {
      selectable: true,
      normal: {
        radius: (node) => node.size || 6, // Bigger nodes for visibility
        strokeWidth: 1.5, // Visible stroke
        strokeColor: "#ffffff",
        strokeDasharray: 0,
      },
      hover: {
        radius: (node) => (node.size || 6) * 1.8, // Bigger hover effect
        strokeWidth: 3,
        strokeColor: "#FFC107",
        color: (node) => node.color, // Keep same color on hover
      },
      selected: {
        radius: (node) => (node.size || 6) * 2, // Bigger selected effect
        strokeWidth: 4,
        strokeColor: "#FF5722",
        color: (node) => node.color, // Keep same color when selected
      },
      label: {
        visible: false, // Hide labels by default for cleaner view
        fontSize: 10,
        fontFamily: "Roboto, sans-serif",
        color: "#333333",
      },
    },
    edge: {
      normal: {
        width: (edge) => edge.width || 1.5,
        color: (edge) => edge.color || "#dddddd",
        dasharray: 0,
      },
      hover: {
        width: (edge) => (edge.width || 1.5) * 2,
        color: "#FFC107",
      },
      selected: {
        width: (edge) => (edge.width || 1.5) * 2,
        color: "#FF5722",
      },
      margin: 3, // Space between edge and node
      marker: {
        target: {
          type: "none", // No arrowheads
        },
      },
    },
  })
);

// Event handlers
const eventHandlers = ref({
  "node:click": ({ node }) => {
    const nodeData = nodes.value.find((n) => n.id === node);
    if (nodeData) {
      selectedDocument.value = nodeData;
      showDetails.value = true;
    }
  },
  "node:dblclick": ({ node }) => {
    showNeighbors(node);
  },
});

// Lifecycle
onMounted(() => {
  loadClusters();
});
</script>

<style scoped>
.clusters-view-new {
  max-height: calc(100vh - 64px);
  overflow-y: auto;
}

.gap-2 {
  gap: 8px;
}

.selected-cluster {
  border: 2px solid #1976d2 !important;
  box-shadow: 0 4px 8px rgba(25, 118, 210, 0.3) !important;
  transform: scale(1.02);
}
</style>
