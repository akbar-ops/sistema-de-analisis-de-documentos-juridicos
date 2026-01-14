<template>
  <div class="cluster-view">
    <!-- Controles -->
    <v-card variant="outlined" class="mb-3">
      <v-card-text class="py-2">
        <div class="d-flex flex-column gap-2">
          <!-- Fila 1: Botones y stats -->
          <div class="d-flex align-center gap-3">
            <v-btn
              size="small"
              variant="tonal"
              prepend-icon="mdi-refresh"
              @click="loadCluster"
              :loading="loading"
            >
              Recargar
            </v-btn>

            <v-divider vertical></v-divider>

            <div class="text-caption">
              <strong>Nodos:</strong> {{ graphData.nodes.length }}
            </div>
            <div class="text-caption">
              <strong>Clusters:</strong> {{ statistics.total_clusters || 0 }}
            </div>
            <div class="text-caption">
              <strong>Enlaces:</strong> {{ graphData.links.length }}
            </div>
          </div>

          <!-- Fila 2: Slider de filtro de similitud -->
          <div class="d-flex align-center gap-3">
            <div class="text-caption" style="min-width: 120px">
              <strong>Similitud mínima:</strong>
            </div>
            <v-slider
              v-model="minSimilarityFilter"
              :min="0"
              :max="1"
              :step="0.05"
              thumb-label
              density="compact"
              hide-details
              class="flex-grow-1"
            >
              <template #thumb-label="{ modelValue }">
                {{ (modelValue * 100).toFixed(0) }}%
              </template>
            </v-slider>
            <div class="text-caption" style="min-width: 40px">
              {{ (minSimilarityFilter * 100).toFixed(0) }}%
            </div>
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- Contenedor principal - Layout vertical para drawer lateral -->
    <div class="cluster-container">
      <!-- Grafo de red -->
      <v-card class="graph-card" :loading="loading">
        <v-card-text class="pa-0" style="height: 400px; position: relative">
          <v-network-graph
            v-if="!loading && graphData.nodes.length > 0"
            :nodes="networkNodes"
            :edges="networkEdges"
            :layouts="layouts"
            :configs="configs"
            :event-handlers="eventHandlers"
          >
            >
            <!-- Tooltip personalizado -->
            <template
              #override-node-label="{ nodeId, scale, config, ...slotProps }"
            >
              <text
                v-bind="slotProps"
                :font-size="12 / scale"
                text-anchor="middle"
                dominant-baseline="central"
                fill="#333"
                :y="15 / scale"
              >
                {{ getNodeLabel(nodeId) }}
              </text>
            </template>
          </v-network-graph>

          <div
            v-else-if="loading"
            class="d-flex align-center justify-center"
            style="height: 100%"
          >
            <v-progress-circular
              indeterminate
              color="primary"
            ></v-progress-circular>
          </div>

          <div
            v-else
            class="d-flex align-center justify-center"
            style="height: 100%"
          >
            <v-alert type="info" variant="tonal" class="ma-4">
              No hay documentos similares suficientes para crear un cluster
            </v-alert>
          </div>
        </v-card-text>
      </v-card>
    </div>

    <!-- Leyenda -->
    <v-card variant="outlined" class="mt-3">
      <v-card-text class="py-2">
        <div class="text-caption font-weight-medium mb-2">
          Leyenda de Nodos:
        </div>
        <div class="d-flex flex-wrap gap-3 mb-3">
          <div class="d-flex align-center gap-1">
            <div class="legend-circle" style="background: #1976d2"></div>
            <span class="text-caption">Laboral</span>
          </div>
          <div class="d-flex align-center gap-1">
            <div class="legend-circle" style="background: #388e3c"></div>
            <span class="text-caption">Civil</span>
          </div>
          <div class="d-flex align-center gap-1">
            <div class="legend-circle" style="background: #d32f2f"></div>
            <span class="text-caption">Penal</span>
          </div>
          <div class="d-flex align-center gap-1">
            <div class="legend-circle" style="background: #f57c00"></div>
            <span class="text-caption">Administrativo</span>
          </div>
          <div class="d-flex align-center gap-1">
            <div class="legend-circle" style="background: #757575"></div>
            <span class="text-caption">Sin área</span>
          </div>
          <v-divider vertical></v-divider>
          <div class="d-flex align-center gap-1">
            <div class="legend-shape circle"></div>
            <span class="text-caption">Sentencia</span>
          </div>
          <div class="d-flex align-center gap-1">
            <div class="legend-shape square"></div>
            <span class="text-caption">Resolución</span>
          </div>
          <div class="d-flex align-center gap-1">
            <div class="legend-shape triangle"></div>
            <span class="text-caption">Auto</span>
          </div>
        </div>

        <v-divider class="my-2"></v-divider>

        <div class="text-caption font-weight-medium mb-2">
          Leyenda de Enlaces:
        </div>
        <div class="d-flex flex-wrap gap-3">
          <div class="d-flex align-center gap-1">
            <div
              class="legend-line"
              style="background: #1a1a1a; width: 30px; height: 4px"
            ></div>
            <span class="text-caption">Alta similitud (80-100%)</span>
          </div>
          <div class="d-flex align-center gap-1">
            <div
              class="legend-line"
              style="background: #5a5a5a; width: 30px; height: 2.5px"
            ></div>
            <span class="text-caption">Media-Alta (60-80%)</span>
          </div>
          <div class="d-flex align-center gap-1">
            <div
              class="legend-line"
              style="background: #9a9a9a; width: 30px; height: 1.5px"
            ></div>
            <span class="text-caption">Media (40-60%)</span>
          </div>
          <div class="d-flex align-center gap-1">
            <div
              class="legend-line"
              style="background: #d0d0d0; width: 30px; height: 0.8px"
            ></div>
            <span class="text-caption">Baja (0-40%)</span>
          </div>
          <v-divider vertical></v-divider>
          <div class="text-caption text-grey">
            <v-icon size="small">mdi-information</v-icon>
            Grosor y color = Intensidad de similitud
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- Diálogo de comparación centrado (estilo chat) -->
    <v-dialog
      v-model="showComparison"
      persistent
      scrollable
      scrim="black"
      transition="dialog-bottom-transition"
      content-class="cluster-dialog-overlay"
    >
      <div
        class="cluster-dialog-container"
        :class="{ 'sidebar-open': sidebarOpen }"
        :style="{
          '--drawer-width': sidebarOpen ? drawerWidth + 'px' : '0px',
        }"
      >
        <v-card elevation="24" class="cluster-dialog-card" color="white">
          <v-card-title
            class="d-flex justify-space-between align-center bg-primary"
          >
            <span class="text-h6 text-white">Comparación de Documentos</span>
            <v-btn
              icon="mdi-close"
              variant="text"
              color="white"
              size="small"
              @click="showComparison = false"
            ></v-btn>
          </v-card-title>

          <v-card-text class="pa-0" style="max-height: 70vh; overflow-y: auto">
            <v-row no-gutters style="height: 100%">
              <!-- Documento Central (izquierda) -->
              <v-col cols="6" class="border-e" style="height: 100%">
                <div class="pa-4">
                  <div class="text-h6 mb-3 text-primary">
                    <v-icon color="primary" class="mr-2">mdi-star</v-icon>
                    Documento Principal
                  </div>

                  <div v-if="centralDocument" class="document-details">
                    <div class="detail-item mb-2">
                      <v-icon size="small" class="mr-2">mdi-folder</v-icon>
                      <span class="text-caption">
                        <strong>Expediente:</strong>
                        {{ centralDocument.case_number || "N/A" }}
                      </span>
                    </div>

                    <div class="detail-item mb-2">
                      <v-icon size="small" class="mr-2">mdi-gavel</v-icon>
                      <span class="text-caption">
                        <strong>Área:</strong>
                        {{ centralDocument.legal_area || "N/A" }}
                      </span>
                    </div>

                    <div class="detail-item mb-2">
                      <v-icon size="small" class="mr-2"
                        >mdi-file-document</v-icon
                      >
                      <span class="text-caption">
                        <strong>Tipo:</strong>
                        {{ centralDocument.doc_type || "N/A" }}
                      </span>
                    </div>

                    <div
                      class="detail-item mb-2"
                      v-if="centralDocument.persons"
                    >
                      <v-icon size="small" class="mr-2"
                        >mdi-account-group</v-icon
                      >
                      <span class="text-caption">
                        <strong>Personas:</strong> {{ centralDocument.persons }}
                      </span>
                    </div>

                    <v-divider class="my-3"></v-divider>

                    <div
                      class="text-caption text-grey-darken-1 mb-2 font-weight-bold"
                    >
                      RESUMEN:
                    </div>
                    <div
                      class="text-body-2 summary-text mb-3"
                      style="max-height: 300px; overflow-y: auto"
                    >
                      {{ centralDocument.summary || "Sin resumen disponible" }}
                    </div>

                    <v-btn
                      block
                      color="primary"
                      variant="tonal"
                      prepend-icon="mdi-eye"
                      size="small"
                      @click="viewDocument(centralDocument.id)"
                    >
                      Ver Documento Completo
                    </v-btn>
                  </div>
                </div>
              </v-col>

              <!-- Documento Seleccionado (derecha) -->
              <v-col cols="6" style="height: 100%">
                <div class="pa-4">
                  <div class="text-h6 mb-3 text-secondary">
                    <v-icon color="secondary" class="mr-2"
                      >mdi-file-compare</v-icon
                    >
                    Documento Seleccionado
                  </div>

                  <div v-if="selectedNodeData" class="document-details">
                    <div class="detail-item mb-2">
                      <v-icon size="small" class="mr-2">mdi-folder</v-icon>
                      <span class="text-caption">
                        <strong>Expediente:</strong>
                        {{ selectedNodeData.case_number || "N/A" }}
                      </span>
                    </div>

                    <div class="detail-item mb-2">
                      <v-icon size="small" class="mr-2">mdi-gavel</v-icon>
                      <span class="text-caption">
                        <strong>Área:</strong>
                        {{ selectedNodeData.legal_area || "N/A" }}
                      </span>
                    </div>

                    <div class="detail-item mb-2">
                      <v-icon size="small" class="mr-2"
                        >mdi-file-document</v-icon
                      >
                      <span class="text-caption">
                        <strong>Tipo:</strong>
                        {{ selectedNodeData.doc_type || "N/A" }}
                      </span>
                    </div>

                    <div
                      class="detail-item mb-2"
                      v-if="selectedNodeData.persons"
                    >
                      <v-icon size="small" class="mr-2"
                        >mdi-account-group</v-icon
                      >
                      <span class="text-caption">
                        <strong>Personas:</strong>
                        {{ selectedNodeData.persons }}
                      </span>
                    </div>

                    <v-divider class="my-3"></v-divider>

                    <div
                      class="text-caption text-grey-darken-1 mb-2 font-weight-bold"
                    >
                      RESUMEN:
                    </div>
                    <div
                      class="text-body-2 summary-text mb-3"
                      style="max-height: 300px; overflow-y: auto"
                    >
                      {{ selectedNodeData.summary || "Sin resumen disponible" }}
                    </div>

                    <v-btn
                      block
                      color="secondary"
                      variant="tonal"
                      prepend-icon="mdi-eye"
                      size="small"
                      @click="viewDocument(selectedNodeData.id)"
                    >
                      Ver Documento Completo
                    </v-btn>
                  </div>

                  <div v-else class="text-center text-grey mt-8">
                    <v-icon size="64" color="grey-lighten-2"
                      >mdi-cursor-default-click</v-icon
                    >
                    <div class="text-caption mt-3">
                      Selecciona un nodo del grafo
                    </div>
                  </div>
                </div>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </div>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, toRefs } from "vue";
import axios from "axios";
import { VNetworkGraph } from "v-network-graph";
import "v-network-graph/lib/style.css";
import * as vNG from "v-network-graph";
import { ForceLayout } from "v-network-graph/lib/force-layout";

const props = defineProps({
  documentId: {
    type: String,
    required: true,
  },
  sidebarOpen: {
    type: Boolean,
    default: false,
  },
});

const { sidebarOpen } = toRefs(props);

const emit = defineEmits(["view-document", "comparison-opened"]);

// Estado
const loading = ref(false);
const graphData = ref({ nodes: [], links: [], clusters: {} });
const statistics = ref({});
const selectedNode = ref(null);
const selectedNodeData = ref(null);
const centralDocument = ref(null);
const minSimilarityFilter = ref(0.3); // Filtro de similitud mínima
const showComparison = ref(false);
const drawerWidth = ref(0); // Width del DocDetails drawer

console.log("ClusterView mounted with documentId:", props.documentId);

// Función para obtener color gris según similitud (más oscuro = más similar)
const getEdgeColor = (similarity) => {
  // Escala de grises: gris claro (baja similitud) -> gris oscuro/negro (alta similitud)
  // Para similitudes de 50-100%, creamos una escala más visible

  if (similarity >= 0.8) {
    // 80-100%: Gris muy oscuro a negro
    const intensity = Math.floor(((similarity - 0.8) / 0.2) * 50); // 0-50
    return `rgb(${50 - intensity}, ${50 - intensity}, ${50 - intensity})`; // #323232 a #000000
  } else if (similarity >= 0.6) {
    // 60-80%: Gris oscuro
    const intensity = Math.floor(((similarity - 0.6) / 0.2) * 70); // 0-70
    return `rgb(${120 - intensity}, ${120 - intensity}, ${120 - intensity})`; // #787878 a #323232
  } else if (similarity >= 0.4) {
    // 40-60%: Gris medio
    const intensity = Math.floor(((similarity - 0.4) / 0.2) * 70); // 0-70
    return `rgb(${190 - intensity}, ${190 - intensity}, ${190 - intensity})`; // #BEBEBE a #787878
  } else {
    // 0-40%: Gris claro
    const intensity = Math.floor((similarity / 0.4) * 55); // 0-55
    return `rgb(${245 - intensity}, ${245 - intensity}, ${245 - intensity})`; // #F5F5F5 a #BEBEBE
  }
};

// Event handlers para capturar clicks en nodos
const eventHandlers = {
  "node:click": ({ node }) => {
    console.log("=== NODE CLICK VIA EVENT HANDLER ===");
    console.log("Node ID clicked:", node);
    handleNodeClick({ node });
  },
  "node:pointerover": ({ node }) => {
    console.log("Mouse over node:", node);
  },
};

// Configuración del grafo con estilos mejorados
const configs = vNG.defineConfigs({
  view: {
    layoutHandler: new ForceLayout({
      positionFixedByDrag: false,
      positionFixedByClickWithAltKey: true,
      createSimulation: (d3, nodes, edges) => {
        const forceLink = d3.forceLink(edges).id((d) => d.id);
        return d3
          .forceSimulation(nodes)
          .force("edge", forceLink.distance(100).strength(0.5))
          .force("charge", d3.forceManyBody().strength(-800))
          .force("center", d3.forceCenter().strength(0.05))
          .alphaDecay(0.015);
      },
    }),
  },
  node: {
    selectable: 1, // Habilitar selección de 1 nodo a la vez
    normal: {
      type: (node) => node.shape || "circle",
      radius: (node) => node.val || 8,
      color: (node) => node.color || "#666",
    },
    hover: {
      radius: (node) => (node.val || 8) * 1.2,
      color: (node) => node.color || "#666",
    },
    selected: {
      // Mantener el mismo tamaño y color para evitar desaparición
      radius: (node) => node.val || 8,
      color: (node) => node.color || "#666",
      strokeWidth: 3,
      strokeColor: "#FF9800", // Borde naranja cuando está seleccionado
    },
    label: {
      visible: true,
      fontSize: 10,
      color: "#333",
    },
  },
  edge: {
    normal: {
      // Grosor según similitud - MÁS DELGADO que el original
      width: (edge) => {
        const similarity = edge.value || 0.5;

        // Escala reducida para líneas más delgadas
        if (similarity >= 0.8) {
          // 80-100%: 3-5px (grueso pero no exagerado)
          return 3 + ((similarity - 0.8) / 0.2) * 2;
        } else if (similarity >= 0.6) {
          // 60-80%: 2-3px (medio-grueso)
          return 2 + ((similarity - 0.6) / 0.2) * 1;
        } else if (similarity >= 0.4) {
          // 40-60%: 1.2-2px (medio)
          return 1.2 + ((similarity - 0.4) / 0.2) * 0.8;
        } else {
          // 0-40%: 0.5-1.2px (delgado)
          return 0.5 + (similarity / 0.4) * 0.7;
        }
      },
      // Color usando la función getEdgeColor
      color: (edge) => getEdgeColor(edge.value || 0.5),
      dasharray: "0",
    },
    hover: {
      width: (edge) => {
        const similarity = edge.value || 0.5;
        // +1px en hover para mejor feedback
        if (similarity >= 0.8) return 4 + ((similarity - 0.8) / 0.2) * 2;
        else if (similarity >= 0.6) return 3 + ((similarity - 0.6) / 0.2) * 1;
        else if (similarity >= 0.4)
          return 2.2 + ((similarity - 0.4) / 0.2) * 0.8;
        else return 1.5 + (similarity / 0.4) * 0.7;
      },
      color: (edge) => {
        // En hover, hacemos el gris un poco más oscuro
        const baseColor = getEdgeColor(edge.value || 0.5);
        return baseColor.replace(
          /rgb\((\d+), (\d+), (\d+)\)/,
          (match, r, g, b) => {
            const darker = Math.max(0, parseInt(r) - 30);
            return `rgb(${darker}, ${darker}, ${darker})`;
          }
        );
      },
    },
    selected: {
      width: (edge) => {
        const similarity = edge.value || 0.5;
        // +2px en selección
        if (similarity >= 0.8) return 5 + ((similarity - 0.8) / 0.2) * 2;
        else if (similarity >= 0.6) return 4 + ((similarity - 0.6) / 0.2) * 1;
        else if (similarity >= 0.4)
          return 3.2 + ((similarity - 0.4) / 0.2) * 0.8;
        else return 2.5 + (similarity / 0.4) * 0.7;
      },
      color: "#FF9800", // Naranja cuando está seleccionado
      dasharray: "0",
    },
    gap: 12,
    type: "straight",
    marker: {
      target: {
        type: "none",
      },
    },
  },
});

const layouts = ref({
  nodes: {},
});

// Transformar datos para v-network-graph con filtrado de similitud
const networkNodes = computed(() => {
  const nodes = {};
  graphData.value.nodes.forEach((node) => {
    nodes[node.id] = {
      name: node.label,
      ...node,
    };
  });
  return nodes;
});

const networkEdges = computed(() => {
  const edges = {};
  // Filtrar enlaces por similitud mínima
  const filteredLinks = graphData.value.links.filter(
    (link) => link.value >= minSimilarityFilter.value
  );

  filteredLinks.forEach((link, index) => {
    edges[`edge${index}`] = {
      source: link.source,
      target: link.target,
      value: link.value,
    };
  });
  return edges;
});

// Métodos
const getNodeLabel = (nodeId) => {
  const node = graphData.value.nodes.find((n) => n.id === nodeId);
  return node?.label || "";
};

const handleNodeClick = ({ node }) => {
  console.log("=== NODE CLICK EVENT ===");
  console.log("Node ID clicked:", node);
  console.log("All nodes:", graphData.value.nodes);

  const nodeData = graphData.value.nodes.find((n) => n.id === node);
  console.log("Node data found:", nodeData);

  if (nodeData) {
    selectedNode.value = { ...nodeData };
    selectedNodeData.value = { ...nodeData };
    console.log("Selected node data:", selectedNodeData.value);
    console.log("Opening dialog...");
    showComparison.value = true;
    // Emitir evento para cerrar el chat si está abierto
    emit("comparison-opened");
    console.log("Dialog state:", showComparison.value);
  } else {
    console.error("Node data NOT found for ID:", node);
  }
};

const viewDocument = (documentId) => {
  emit("view-document", documentId);
};

// Función de test para el botón
const testDialog = () => {
  console.log("=== TEST DIALOG ===");
  console.log("Available nodes:", graphData.value.nodes);

  // Seleccionar el primer nodo que NO sea el central
  const firstNode = graphData.value.nodes.find((n) => !n.is_central);

  if (firstNode) {
    console.log("Testing with node:", firstNode);
    selectedNodeData.value = { ...firstNode };
    showComparison.value = true;
  } else {
    console.warn("No nodes available for testing");
    showComparison.value = true; // Abrir de todas formas
  }
};

const loadCluster = async () => {
  loading.value = true;
  console.log("Loading cluster for document:", props.documentId);

  try {
    const response = await axios.get(
      `http://localhost:8000/api/documents/${props.documentId}/cluster/`,
      {
        params: {
          max_neighbors: 20,
          eps: 0.242,
          min_samples: 2,
        },
      }
    );

    console.log("Cluster data received:", response.data);
    graphData.value = response.data;
    statistics.value = response.data.statistics || {};

    // Establecer documento central con más información
    const central = graphData.value.nodes.find((n) => n.is_central);
    console.log("Central document found:", central);

    if (central) {
      centralDocument.value = {
        id: central.id,
        title: central.title,
        case_number: central.case_number,
        legal_area: central.legal_area,
        doc_type: central.doc_type,
        summary: central.summary,
        color: central.color,
        shape: central.shape,
      };
      selectedNode.value = null; // Reset selección
      console.log("Central document set:", centralDocument.value);
    }

    console.log("Nodes:", graphData.value.nodes.length);
    console.log("Links:", graphData.value.links.length);
    console.log(
      "Filtered links (min similarity):",
      networkEdges.value ? Object.keys(networkEdges.value).length : 0
    );
  } catch (error) {
    console.error("Error loading cluster:", error);
    console.error("Error details:", error.response?.data);
  } finally {
    loading.value = false;
  }
};

// Lifecycle
onMounted(() => {
  loadCluster();

  // Detectar ancho del drawer dinámicamente
  const drawer = document.querySelector(".v-navigation-drawer");
  if (drawer) {
    drawerWidth.value = drawer.offsetWidth;

    // Observar cambios de tamaño
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        drawerWidth.value = entry.contentRect.width;
      }
    });
    observer.observe(drawer);
  }
});

watch(
  () => props.documentId,
  () => {
    loadCluster();
  }
);

// Método público para cerrar el diálogo de comparación
const closeComparison = () => {
  showComparison.value = false;
  selectedNodeData.value = null;
  console.log("Comparison dialog closed from parent");
};

// Exponer métodos para el componente padre
defineExpose({
  closeComparison,
});
</script>

<style scoped>
.cluster-view {
  padding: 8px;
}

.cluster-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.graph-card {
  overflow: hidden;
}

.summary-card {
  overflow-y: auto;
  max-height: 400px;
}

.summary-section {
  padding: 12px;
}

.summary-section.border-b {
  border-bottom: 1px solid #e0e0e0;
}

.summary-header {
  margin-bottom: 12px;
}

.summary-content {
  background: #f5f5f5;
  padding: 12px;
  border-radius: 8px;
  max-height: 200px;
  overflow-y: auto;
}

.legend-circle {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1px solid #ccc;
}

.legend-shape {
  width: 12px;
  height: 12px;
  border: 1px solid #666;
  background: #fff;
}

.legend-shape.circle {
  border-radius: 50%;
}

.legend-shape.square {
  border-radius: 2px;
}

.legend-shape.triangle {
  width: 0;
  height: 0;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-bottom: 12px solid #666;
  border: none;
  background: transparent;
}

.gap-3 {
  gap: 12px;
}

/* === Estilos para el diálogo de comparación (similar al chat) === */
.cluster-dialog-overlay {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  padding: 20px !important;
}

.cluster-dialog-container {
  position: relative;
  width: 100%;
  max-width: 1400px; /* Más grande */
  height: 85vh;
  max-height: 900px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.3s ease-in-out;
  padding: 0 20px;
  margin: 0 auto;
}

.cluster-dialog-container.sidebar-open {
  transform: translateX(calc(var(--drawer-width) / -2));
}

.cluster-dialog-card {
  width: 100%;
  height: 100%;
  max-width: 1400px; /* Más grande */
  max-height: 900px;
  display: flex;
  flex-direction: column;
  background-color: #ffffff !important;
  opacity: 1 !important;
  backdrop-filter: none !important;
  border-radius: 12px;
  overflow: hidden;
}

.cluster-dialog-card .v-card-title {
  background-color: rgb(var(--v-theme-primary)) !important;
  color: white !important;
  opacity: 1 !important;
  flex-shrink: 0;
}

.cluster-dialog-card .v-card-text {
  background-color: #ffffff !important;
  opacity: 1 !important;
  flex: 1;
  overflow-y: auto;
}

/* Asegurar que las columnas tengan fondo */
.cluster-dialog-card .v-col {
  background-color: #ffffff !important;
}

.cluster-dialog-card .document-details {
  background-color: #ffffff !important;
}

/* Asegurar que el contenido del resumen tenga fondo */
.cluster-dialog-card .summary-text {
  background-color: #f5f5f5;
  padding: 12px;
  border-radius: 4px;
}

.cluster-dialog-card .detail-item {
  background-color: transparent;
}

/* Responsive */
@media (max-width: 1200px) {
  .cluster-dialog-container {
    max-width: 750px;
  }
  .cluster-dialog-container.sidebar-open {
    transform: translateX(calc(var(--drawer-width) / -3));
  }
}

@media (max-width: 768px) {
  .cluster-dialog-overlay {
    padding: 10px !important;
  }
  .cluster-dialog-container {
    height: 90vh;
    max-height: none;
    padding: 0 10px;
    margin: 0 auto !important;
    transform: none !important;
  }
  .cluster-dialog-container.sidebar-open {
    transform: none !important;
  }
  .cluster-dialog-card {
    width: 100% !important;
    height: 100% !important;
    max-width: none !important;
  }
}

/* Remover estilos antiguos que ya no se usan */
.comparison-dialog {
  z-index: 2400;
}
</style>
