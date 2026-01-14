<template>
  <v-card elevation="2">
    <v-card-title
      class="bg-primary text-white d-flex justify-space-between align-center"
    >
      <div>
        <v-icon class="mr-2">mdi-graph-outline</v-icon>
        Documentos Relacionados
      </div>
      <v-btn
        icon="mdi-close"
        variant="text"
        color="white"
        size="small"
        @click="$emit('close')"
      ></v-btn>
    </v-card-title>

    <v-card-text class="pa-0">
      <!-- Loading State -->
      <div v-if="loading" class="d-flex align-center justify-center pa-12">
        <div class="text-center">
          <v-progress-circular
            indeterminate
            color="primary"
            size="64"
          ></v-progress-circular>
          <div class="mt-4 text-h6">Cargando vecinos...</div>
        </div>
      </div>

      <!-- Network Graph -->
      <div v-else style="height: 500px; position: relative">
        <v-network-graph
          :nodes="networkNodes"
          :edges="networkEdges"
          :layouts="layouts"
          :configs="configs"
          :event-handlers="eventHandlers"
        >
          <template #override-node-label="{ nodeId, scale, ...slotProps }">
            <text
              v-bind="slotProps"
              :font-size="12 / scale"
              text-anchor="middle"
              dominant-baseline="central"
              :fill="nodeId === documentId ? '#fff' : '#333'"
              :y="20 / scale"
            >
              {{ getNodeLabel(nodeId) }}
            </text>
          </template>
        </v-network-graph>
      </div>

      <!-- Neighbor List -->
      <v-divider></v-divider>
      <div class="pa-4">
        <div class="text-subtitle-1 font-weight-bold mb-3">
          Documentos más similares ({{ neighbors.length }})
        </div>
        <v-list density="compact">
          <v-list-item
            v-for="neighbor in neighbors"
            :key="neighbor.id"
            @click="$emit('select-document', neighbor.id)"
            :prepend-icon="getSimilarityIcon(neighbor.similarity)"
            :class="{ 'bg-grey-lighten-4': neighbor.id === selectedDocId }"
          >
            <v-list-item-title>{{ neighbor.title }}</v-list-item-title>
            <v-list-item-subtitle>
              {{ neighbor.case_number }} • {{ neighbor.legal_area }}
            </v-list-item-subtitle>
            <template #append>
              <v-chip
                size="small"
                :color="getSimilarityColor(neighbor.similarity)"
              >
                {{ (neighbor.similarity * 100).toFixed(1) }}%
              </v-chip>
            </template>
          </v-list-item>
        </v-list>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import axios from "axios";
import { VNetworkGraph } from "v-network-graph";
import * as vNG from "v-network-graph";
import "v-network-graph/lib/style.css";

const props = defineProps({
  documentId: {
    type: Number,
    required: true,
  },
  maxNeighbors: {
    type: Number,
    default: 10,
  },
});

const emit = defineEmits(["close", "select-document"]);

// State
const loading = ref(false);
const centralNode = ref(null);
const neighbors = ref([]);
const edges = ref([]);
const selectedDocId = ref(null);

// Load neighbors
const loadNeighbors = async () => {
  loading.value = true;
  try {
    const response = await axios.get(
      `/api/documents/${props.documentId}/neighbors/`,
      {
        params: {
          max_neighbors: props.maxNeighbors,
        },
      }
    );

    centralNode.value = response.data.central_node;
    neighbors.value = response.data.neighbors || [];
    edges.value = response.data.edges || [];

    console.log("✅ Neighbors loaded:", {
      central: centralNode.value?.id,
      neighbors: neighbors.value.length,
      edges: edges.value.length,
    });
  } catch (error) {
    console.error("❌ Error loading neighbors:", error);
  } finally {
    loading.value = false;
  }
};

// Network graph nodes
const networkNodes = computed(() => {
  const result = {};

  if (centralNode.value) {
    result[centralNode.value.id] = {
      name: centralNode.value.case_number || "Central",
      color: "#1976D2", // Blue for central node
      size: 20,
    };
  }

  neighbors.value.forEach((neighbor) => {
    result[neighbor.id] = {
      name: neighbor.case_number || "Doc",
      color: getNeighborColor(neighbor.similarity),
      size: 15,
    };
  });

  return result;
});

// Network graph edges
const networkEdges = computed(() => {
  const result = {};

  edges.value.forEach((edge, idx) => {
    result[`edge-${idx}`] = {
      source: edge.source,
      target: edge.target,
      width: edge.similarity * 4,
      color: getEdgeColor(edge.similarity),
    };
  });

  return result;
});

// Get neighbor color based on similarity
const getNeighborColor = (similarity) => {
  if (similarity > 0.8) return "#2E7D32"; // Dark green
  if (similarity > 0.6) return "#43A047"; // Green
  if (similarity > 0.4) return "#FFA726"; // Orange
  return "#EF5350"; // Red
};

// Get edge color
const getEdgeColor = (similarity) => {
  if (similarity > 0.8) return "#2E7D32";
  if (similarity > 0.6) return "#5a5a5a";
  return "#9a9a9a";
};

// Get node label
const getNodeLabel = (nodeId) => {
  if (centralNode.value?.id === nodeId) {
    return centralNode.value.case_number || "Central";
  }
  const neighbor = neighbors.value.find((n) => n.id === nodeId);
  return neighbor?.case_number || "Doc";
};

// Get similarity icon
const getSimilarityIcon = (similarity) => {
  if (similarity > 0.8) return "mdi-star";
  if (similarity > 0.6) return "mdi-star-half-full";
  return "mdi-star-outline";
};

// Get similarity color
const getSimilarityColor = (similarity) => {
  if (similarity > 0.8) return "success";
  if (similarity > 0.6) return "primary";
  if (similarity > 0.4) return "warning";
  return "error";
};

// Network graph layouts - radial around central node
const layouts = computed(() => {
  const nodeLayouts = {};

  if (centralNode.value) {
    // Central node at center
    nodeLayouts[centralNode.value.id] = { x: 0, y: 0 };

    // Neighbors in a circle
    const angleStep = (2 * Math.PI) / neighbors.value.length;
    neighbors.value.forEach((neighbor, idx) => {
      const angle = idx * angleStep;
      const radius = 150;
      nodeLayouts[neighbor.id] = {
        x: Math.cos(angle) * radius,
        y: Math.sin(angle) * radius,
      };
    });
  }

  return { nodes: nodeLayouts };
});

// Network graph configs
const configs = ref(
  vNG.defineConfigs({
    view: {
      scalingObjects: true,
      minZoomLevel: 0.5,
      maxZoomLevel: 4,
    },
    node: {
      selectable: true,
      normal: {
        radius: (node) => node.size || 15,
        strokeWidth: 2,
        strokeColor: "#ffffff",
      },
      hover: {
        radius: (node) => (node.size || 15) * 1.2,
        strokeWidth: 3,
      },
      selected: {
        radius: (node) => (node.size || 15) * 1.3,
        strokeWidth: 4,
        strokeColor: "#FFC107",
      },
      label: {
        visible: true,
        fontSize: 11,
      },
    },
    edge: {
      normal: {
        width: (edge) => edge.width || 2,
        color: (edge) => edge.color || "#999999",
      },
      hover: {
        width: (edge) => (edge.width || 2) * 1.5,
      },
    },
  })
);

// Event handlers
const eventHandlers = ref({
  "node:click": ({ node }) => {
    selectedDocId.value = node;
    emit("select-document", node);
  },
});

// Watch for document ID changes
watch(
  () => props.documentId,
  () => {
    if (props.documentId) {
      loadNeighbors();
    }
  },
  { immediate: true }
);

// Lifecycle
onMounted(() => {
  loadNeighbors();
});
</script>

<style scoped>
/* Add any specific styles here */
</style>
