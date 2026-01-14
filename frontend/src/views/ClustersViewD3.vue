<template>
  <v-container
    fluid
    class="clusters-view-d3 pa-6"
    style="max-width: 1800px; margin: 0 auto"
  >
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
              @click="regenerateClusters"
              :loading="regenerating"
              :disabled="regenerating"
            >
              {{ regenerating ? "Regenerando..." : "Recargar" }}
            </v-btn>
          </div>
        </div>
      </v-col>
    </v-row>

    <!-- Regeneration Progress Alert -->
    <v-row v-if="regenerationProgress">
      <v-col cols="12">
        <v-alert
          type="info"
          variant="tonal"
          closable
          @click:close="regenerationProgress = null"
        >
          <div class="d-flex align-center">
            <v-progress-circular
              v-if="!regenerationProgress.completed"
              indeterminate
              size="20"
              width="2"
              class="mr-3"
            ></v-progress-circular>
            <v-icon v-else color="success" class="mr-3"
              >mdi-check-circle</v-icon
            >
            <div>
              <div class="font-weight-bold">
                {{ regenerationProgress.message }}
              </div>
              <div
                v-if="regenerationProgress.details"
                class="text-caption mt-1"
              >
                {{ regenerationProgress.details }}
              </div>
            </div>
          </div>
        </v-alert>
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
                @click:close="clearFilter"
              >
                Cluster {{ selectedCluster }}
              </v-chip>
            </div>
            <div class="d-flex gap-2 align-center">
              <v-switch
                v-model="showEdges"
                density="compact"
                hide-details
                color="primary"
                label="Conexiones"
              ></v-switch>
              <v-switch
                v-model="useForceLayout"
                density="compact"
                hide-details
                color="secondary"
                label="Auto-agrupar"
              ></v-switch>
              <!-- Top-K Edge Control -->
              <div style="min-width: 200px" class="ml-4">
                <div class="text-caption text-grey mb-1">
                  Conexiones por nodo: {{ topK }}
                </div>
                <v-slider
                  v-model="topK"
                  :min="2"
                  :max="15"
                  :step="1"
                  density="compact"
                  hide-details
                  color="primary"
                  @update:modelValue="onTopKChange"
                  thumb-label
                ></v-slider>
              </div>
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
                  • Arrastrar fondo: Pan<br />
                  • Arrastrar nodo: Mover<br />
                  • Click: Ver detalles<br />
                  • Hover: Resaltar conexiones<br />
                  • Auto-agrupar: Agrupación automática<br />
                  <br />
                  <strong>Colores de Conexiones:</strong><br />
                  • <span style="color: #43a047">Verde</span>: Alta similitud
                  (>0.8)<br />
                  • <span style="color: #1e88e5">Azul</span>: Media similitud
                  (>0.6)<br />
                  • <span style="color: #fb8c00">Naranja</span>: Baja-media
                  (>0.4)<br />
                  • <span style="color: #bdbdbd">Gris</span>: Baja similitud
                </div>
              </v-tooltip>
            </div>
          </v-card-title>

          <v-card-text class="pa-0" style="position: relative">
            <!-- Loading State -->
            <div
              v-if="loading"
              class="d-flex align-center justify-center"
              style="height: 600px"
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

            <!-- D3 Graph Container -->
            <div
              v-show="!loading"
              ref="graphContainer"
              class="graph-container"
              style="width: 100%; height: 700px; background: #fafafa"
            ></div>
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
                v-for="stat in clusterStats"
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
                          :color="getClusterColor(stat.cluster_label)"
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
                <strong>Cluster:</strong>
                <v-chip
                  size="small"
                  :color="getClusterColor(selectedDocument.cluster)"
                >
                  {{ selectedDocument.cluster }}
                </v-chip>
              </div>
              <div class="mb-2" v-if="selectedDocument.document_date">
                <strong>Fecha:</strong>
                {{ formatDate(selectedDocument.document_date) }}
              </div>
            </v-col>
          </v-row>

          <!-- Related Documents Section -->
          <v-row v-if="selectedDocumentNeighbors.length > 0" class="mt-4">
            <v-col cols="12">
              <v-divider class="mb-3"></v-divider>
              <h4 class="mb-3">
                📎 Documentos Relacionados ({{
                  selectedDocumentNeighbors.length
                }})
              </h4>
              <v-list density="compact">
                <v-list-item
                  v-for="neighbor in selectedDocumentNeighbors"
                  :key="neighbor.id"
                  class="mb-1"
                >
                  <template v-slot:prepend>
                    <v-chip
                      size="x-small"
                      :color="getClusterColor(neighbor.cluster)"
                      class="mr-2"
                    >
                      {{ neighbor.cluster }}
                    </v-chip>
                  </template>
                  <v-list-item-title>{{ neighbor.title }}</v-list-item-title>
                  <v-list-item-subtitle>
                    Similitud: {{ (neighbor.similarity * 100).toFixed(1) }}% •
                    {{ neighbor.case_number || "Sin expediente" }}
                  </v-list-item-subtitle>
                  <template v-slot:append>
                    <v-progress-linear
                      :model-value="neighbor.similarity * 100"
                      height="4"
                      color="primary"
                      class="ml-2"
                      style="width: 100px"
                    ></v-progress-linear>
                  </template>
                </v-list-item>
              </v-list>
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="showDetails = false">Cerrar</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch } from "vue";
import axios from "axios";
import * as d3 from "d3";

// State
const loading = ref(false);
const regenerating = ref(false); // For cluster regeneration
const regenerationProgress = ref(null); // Progress message for regeneration
const showEdges = ref(true); // Default to showing edges
const useForceLayout = ref(true);
const showDetails = ref(false);
const selectedDocument = ref(null);
const selectedDocumentNeighbors = ref([]); // Related documents for clicked node
const selectedCluster = ref(null);
const hoveredNode = ref(null);
const topK = ref(5); // Number of strongest edges per node to keep

// Data from API
const nodes = ref([]);
const links = ref([]);
const clusterStats = ref([]);
const metadata = ref(null);

// D3 refs
const graphContainer = ref(null);
let svg = null;
let simulation = null;
let g = null; // Main group for zooming
let nodeElements = null;
let linkElements = null;
let zoomBehavior = null; // Zoom behavior
let transform = d3.zoomIdentity;
let containerWidth = 800; // Will be updated in initGraph
let containerHeight = 700; // Will be updated in initGraph
let globalScale = 30; // Calculated based on ALL nodes, preserved across filters
let globalDataCenterX = 0; // Center of ALL data
let globalDataCenterY = 0; // Center of ALL data

// Professional color palette for clusters - Modern, vibrant, and distinguishable
const clusterColors = [
  "#3B82F6", // Bright Blue - Primary
  "#10B981", // Emerald Green - Success
  "#F59E0B", // Amber - Attention
  "#8B5CF6", // Purple - Creative
  "#EC4899", // Pink - Vibrant
  "#06B6D4", // Cyan - Tech
  "#EF4444", // Red - Important
  "#14B8A6", // Teal - Modern
  "#F97316", // Orange - Energy
  "#6366F1", // Indigo - Professional
  "#84CC16", // Lime - Fresh
  "#A855F7", // Fuchsia - Bold
];

// Get cluster color with better contrast
const getClusterColor = (cluster) => {
  if (cluster === -1) return "#94A3B8"; // Slate gray for noise (more professional than plain gray)
  return clusterColors[Math.abs(cluster) % clusterColors.length];
};

// Load clusters from API
const loadClusters = async () => {
  loading.value = true;
  try {
    const response = await axios.get("/api/documents/all_clusters/", {
      params: {
        include_edges: true, // Explicitly request edges
        top_k: topK.value, // Use the slider value for edge pruning
      },
    });

    nodes.value = response.data.nodes || [];
    links.value = response.data.links || [];
    clusterStats.value = response.data.cluster_stats || [];
    metadata.value = response.data.metadata || {};

    console.log("✅ Clusters loaded:", {
      nodes: nodes.value.length,
      links: links.value.length,
      clusters: metadata.value.cluster_count,
      sampleLink: links.value[0],
    });

    // Calculate global scale and center based on ALL nodes
    // This ensures consistent positioning when filtering
    if (nodes.value.length > 0) {
      const allX = nodes.value.map((n) => n.x);
      const allY = nodes.value.map((n) => n.y);
      const minX = Math.min(...allX);
      const maxX = Math.max(...allX);
      const minY = Math.min(...allY);
      const maxY = Math.max(...allY);

      globalDataCenterX = (minX + maxX) / 2;
      globalDataCenterY = (minY + maxY) / 2;

      console.log("📊 Global data bounds:", {
        minX,
        maxX,
        minY,
        maxY,
        centerX: globalDataCenterX,
        centerY: globalDataCenterY,
      });
    }

    // Set loading to false first, then wait for DOM update
    loading.value = false;
    await nextTick();
    await nextTick(); // Extra tick to ensure DOM is ready

    initGraph();
  } catch (error) {
    console.error("❌ Error loading clusters:", error);
    loading.value = false;
  }
};

// Regenerate clusters manually (triggered by Recargar button)
const regenerateClusters = async () => {
  regenerating.value = true;
  regenerationProgress.value = {
    message: "Iniciando regeneración de clusters...",
    details: null,
    completed: false,
  };

  try {
    // Step 1: Trigger cluster regeneration
    console.log("🔄 Triggering cluster regeneration...");
    const response = await axios.post("/api/documents/regenerate_clusters/", {
      max_documents: 1000, // High limit to include all documents
      use_enhanced_embedding: true,
      algorithm: "hdbscan",
    });

    const { task_id, estimated_time_seconds, document_count, message } =
      response.data;

    regenerationProgress.value = {
      message: "Regenerando clusters...",
      details: `Procesando ${document_count} documentos. Tiempo estimado: ${estimated_time_seconds}s`,
      completed: false,
    };

    console.log("✅ Regeneration queued:", {
      task_id,
      estimated_time_seconds,
      document_count,
    });

    // Step 2: Wait for estimated time + 2 seconds buffer
    const waitTime = (estimated_time_seconds + 2) * 1000;
    console.log(`⏳ Waiting ${waitTime}ms for cluster computation...`);
    await new Promise((resolve) => setTimeout(resolve, waitTime));

    // Step 3: Reload cluster data
    regenerationProgress.value = {
      message: "Cargando nuevos clusters...",
      details: null,
      completed: false,
    };

    console.log("📥 Reloading cluster data...");
    await loadClusters();

    // Step 4: Success!
    regenerationProgress.value = {
      message: "✅ Clusters regenerados exitosamente",
      details: `${document_count} documentos procesados`,
      completed: true,
    };

    // Auto-hide success message after 5 seconds
    setTimeout(() => {
      regenerationProgress.value = null;
    }, 5000);

    console.log("✅ Cluster regeneration completed successfully");
  } catch (error) {
    console.error("❌ Error regenerating clusters:", error);

    regenerationProgress.value = {
      message: "❌ Error al regenerar clusters",
      details:
        error.response?.data?.error || error.message || "Error desconocido",
      completed: true,
    };

    // Auto-hide error message after 10 seconds
    setTimeout(() => {
      regenerationProgress.value = null;
    }, 10000);
  } finally {
    regenerating.value = false;
  }
};

// Handle top-k change while preserving cluster filter
const onTopKChange = async () => {
  const currentCluster = selectedCluster.value; // Save current cluster

  try {
    // Reload data without showing loading spinner
    const response = await axios.get("/api/documents/all_clusters/", {
      params: {
        include_edges: true,
        top_k: topK.value,
      },
    });

    nodes.value = response.data.nodes || [];
    links.value = response.data.links || [];
    clusterStats.value = response.data.cluster_stats || [];
    metadata.value = response.data.metadata || {};

    console.log("✅ Top-K updated:", {
      topK: topK.value,
      links: links.value.length,
      preservedCluster: currentCluster,
    });

    // Restore cluster filter
    if (currentCluster !== null) {
      selectedCluster.value = currentCluster;
    }

    // Update graph with new data
    updateGraph();
  } catch (error) {
    console.error("❌ Error updating top-k:", error);
  }
};

// Initialize D3 graph
const initGraph = () => {
  if (!graphContainer.value) {
    console.warn("⚠️ Graph container not ready yet");
    return;
  }

  console.log("🎨 Initializing D3 graph...");

  // Clear previous graph
  d3.select(graphContainer.value).selectAll("*").remove();

  const container = graphContainer.value;
  containerWidth = container.clientWidth || 800;
  containerHeight = container.clientHeight || 700;

  console.log("📏 Container dimensions:", {
    width: containerWidth,
    height: containerHeight,
  });

  // Calculate global scale based on ALL nodes (not filtered)
  if (nodes.value.length > 0) {
    const allX = nodes.value.map((n) => n.x);
    const allY = nodes.value.map((n) => n.y);
    const minX = Math.min(...allX);
    const maxX = Math.max(...allX);
    const minY = Math.min(...allY);
    const maxY = Math.max(...allY);
    const rangeX = maxX - minX || 1;
    const rangeY = maxY - minY || 1;

    // Scale to use ~60% of container, leaving margins
    const scaleX = (containerWidth * 0.6) / rangeX;
    const scaleY = (containerHeight * 0.6) / rangeY;
    globalScale = Math.min(scaleX, scaleY);

    console.log(
      "📐 Global scale calculated:",
      globalScale.toFixed(2),
      "based on range:",
      {
        rangeX: rangeX.toFixed(2),
        rangeY: rangeY.toFixed(2),
      }
    );
  }

  // Create SVG with fixed dimensions (will update on resize)
  svg = d3
    .select(container)
    .append("svg")
    .attr("width", containerWidth)
    .attr("height", containerHeight)
    .style("background", "#fafafa")
    .style("display", "block");

  // Add zoom behavior
  zoomBehavior = d3
    .zoom()
    .scaleExtent([0.1, 10])
    .on("zoom", (event) => {
      transform = event.transform;
      g.attr("transform", transform);
    });

  svg.call(zoomBehavior);

  // Main group for zooming
  g = svg.append("g");

  // Create force simulation with better spacing
  simulation = d3
    .forceSimulation()
    .force("charge", d3.forceManyBody().strength(-100)) // Stronger repulsion
    .force("collision", d3.forceCollide().radius(15)) // More space between nodes
    .force("x", d3.forceX(containerWidth / 2).strength(0.05)) // Gentle pull to center X
    .force("y", d3.forceY(containerHeight / 2).strength(0.05)) // Gentle pull to center Y
    .on("tick", ticked);

  if (useForceLayout.value) {
    simulation.force(
      "link",
      d3
        .forceLink()
        .id((d) => d.id)
        .distance(80)
        .strength(0.5)
    );
  } else {
    // Start in fixed mode - remove forces
    simulation.force("charge", null);
    simulation.force("collision", null);
    simulation.force("x", null);
    simulation.force("y", null);
  }

  console.log(
    "✅ D3 graph initialized in",
    useForceLayout.value ? "FORCE" : "FIXED",
    "mode"
  );
  updateGraph();
};

// Update graph with current data
const updateGraph = () => {
  if (!g || !simulation) {
    console.warn("⚠️ Graph not initialized yet");
    return;
  }

  console.log("🔄 Updating graph...");

  // Filter data
  const filteredNodes =
    selectedCluster.value !== null
      ? nodes.value.filter((n) => n.cluster === selectedCluster.value)
      : nodes.value;

  const filteredNodeIds = new Set(filteredNodes.map((n) => n.id));

  // CRITICAL: Create fresh copies of links to avoid mutation issues
  // D3 force simulation mutates source/target from IDs to objects,
  // so we need fresh copies each time we update the graph
  const filteredLinks = links.value
    .filter((l) => {
      const sourceId = typeof l.source === "object" ? l.source.id : l.source;
      const targetId = typeof l.target === "object" ? l.target.id : l.target;
      return filteredNodeIds.has(sourceId) && filteredNodeIds.has(targetId);
    })
    .map((l) => ({
      ...l,
      source: typeof l.source === "object" ? l.source.id : l.source,
      target: typeof l.target === "object" ? l.target.id : l.target,
    }));

  console.log("📊 Graph data:", {
    nodes: filteredNodes.length,
    links: filteredLinks.length,
    showEdges: showEdges.value,
    useForce: useForceLayout.value,
    totalLinks: links.value.length,
  });

  // Prepare data for D3
  const graphNodes = filteredNodes.map((n) => {
    const node = { ...n };

    // Use consistent global scale for all nodes (not recalculated per filter)
    const centerX = containerWidth / 2;
    const centerY = containerHeight / 2;

    if (useForceLayout.value) {
      // Force layout mode - remove fixed positions
      node.fx = null;
      node.fy = null;
      // Keep existing x/y if they exist (for smooth transition)
      if (node.x === undefined) {
        node.x = (n.x - globalDataCenterX) * globalScale + centerX;
        node.y = (n.y - globalDataCenterY) * globalScale + centerY;
      }
    } else {
      // Fixed layout mode - use UMAP coordinates with global scaling

      // CRITICAL: When filtering a cluster, EXPAND the space between nodes
      // This separates nodes that are too close together in UMAP space
      let expansionFactor = 1.0; // Default: no expansion

      if (selectedCluster.value !== null) {
        // Calculate expansion based on cluster size
        // EXTREME expansion to really separate the nodes
        if (filteredNodes.length <= 10) {
          expansionFactor = 120.0; // Expand 120x for small clusters
        } else if (filteredNodes.length <= 20) {
          expansionFactor = 110.0; // Expand 110x
        } else if (filteredNodes.length <= 35) {
          expansionFactor = 100.0; // Expand 100x for medium clusters
        } else if (filteredNodes.length <= 50) {
          expansionFactor = 90.0; // Expand 90x
        } else {
          expansionFactor = 80.0; // Expand 80x for large clusters
        }

        // Calculate cluster center in UMAP space
        const clusterCenterX =
          filteredNodes.reduce((sum, node) => sum + node.x, 0) /
          filteredNodes.length;
        const clusterCenterY =
          filteredNodes.reduce((sum, node) => sum + node.y, 0) /
          filteredNodes.length;

        // Expand from cluster center
        const expandedX =
          clusterCenterX + (n.x - clusterCenterX) * expansionFactor;
        const expandedY =
          clusterCenterY + (n.y - clusterCenterY) * expansionFactor;

        // Apply global scale to expanded coordinates
        const fixedX = (expandedX - globalDataCenterX) * globalScale + centerX;
        const fixedY = (expandedY - globalDataCenterY) * globalScale + centerY;

        node.x = fixedX;
        node.y = fixedY;
        node.fx = fixedX;
        node.fy = fixedY;
      } else {
        // No filter - use normal positioning
        const fixedX = (n.x - globalDataCenterX) * globalScale + centerX;
        const fixedY = (n.y - globalDataCenterY) * globalScale + centerY;
        node.x = fixedX;
        node.y = fixedY;
        node.fx = fixedX;
        node.fy = fixedY;
      }
    }

    return node;
  });

  console.log("📍 Node positioning:", {
    mode: useForceLayout.value ? "FORCE" : "FIXED",
    globalScale: globalScale.toFixed(2),
    totalNodes: graphNodes.length,
    samplePos: graphNodes[0]
      ? `(${graphNodes[0].x?.toFixed(0)}, ${graphNodes[0].y?.toFixed(0)})`
      : "none",
  });

  // IMPORTANT: Don't clear everything! Use D3 data joins to update
  // Only clear and rebuild if this is the first time OR major structure change
  const needsRebuild = !linkElements || !nodeElements;

  if (needsRebuild) {
    console.log("🔨 Full rebuild needed");
    g.selectAll("*").remove();
  }

  // Draw/Update links using D3 data join
  if (needsRebuild) {
    linkElements = g.append("g").attr("class", "links").selectAll("line");
  }

  // Key function that works with both IDs and objects
  const linkKey = (d) => {
    const sourceId = typeof d.source === "object" ? d.source.id : d.source;
    const targetId = typeof d.target === "object" ? d.target.id : d.target;
    return `${sourceId}-${targetId}`;
  };

  linkElements = linkElements.data(filteredLinks, linkKey);

  // Remove old links
  linkElements.exit().remove();

  // Add new links - SIMPLIFIED: uniform color and thickness by default
  const newLinks = linkElements
    .enter()
    .append("line")
    .attr("stroke", "#000000") // Black for connections
    .style("display", showEdges.value ? null : "none");

  // Merge new and existing
  linkElements = newLinks
    .merge(linkElements)
    .attr("stroke-width", 1.5) // Thicker for better visibility
    .attr("stroke-opacity", 0.8) // More visible - 80% opacity
    .attr("stroke-linecap", "round")
    .style("display", showEdges.value ? null : "none");

  console.log(
    "🔗 Links updated:",
    linkElements.size(),
    "expected:",
    filteredLinks.length,
    "visible:",
    showEdges.value
  );

  // Draw/Update nodes using D3 data join
  if (needsRebuild) {
    nodeElements = g.append("g").attr("class", "nodes").selectAll("circle");
  }

  nodeElements = nodeElements.data(graphNodes, (d) => d.id);

  // Remove old nodes
  nodeElements.exit().remove();

  // Add new nodes
  const newNodes = nodeElements
    .enter()
    .append("circle")
    .attr("fill", (d) => getClusterColor(d.cluster))
    .attr("stroke", "#ffffff")
    .attr("stroke-width", 2)
    .style("filter", "drop-shadow(0px 2px 4px rgba(0,0,0,0.15))") // Subtle shadow for depth
    .style("cursor", "pointer")
    .on("click", (event, d) => handleNodeClick(d))
    .on("mouseenter", (event, d) => handleNodeHover(d, true))
    .on("mouseleave", (event, d) => handleNodeHover(d, false))
    .call(
      d3
        .drag()
        .on("start", dragStarted)
        .on("drag", dragged)
        .on("end", dragEnded)
    );

  // Merge new and existing
  nodeElements = newNodes
    .merge(nodeElements)
    // Dynamic radius: 2x larger when viewing single cluster in fixed mode
    .attr("r", (d) => {
      const baseRadius = d.is_noise ? 5 : 8;
      // If filtering to a single cluster in fixed mode, make nodes 2x larger
      if (selectedCluster.value !== null && !useForceLayout.value) {
        return baseRadius * 2.0; // 2x larger
      }
      return baseRadius;
    })
    // Update opacity
    .attr("opacity", selectedCluster.value !== null ? 1.0 : 0.85);

  console.log(
    "🔵 Nodes updated:",
    nodeElements.size(),
    "expected:",
    graphNodes.length,
    "visible:",
    selectedCluster.value !== null
      ? graphNodes.filter((n) => n.cluster === selectedCluster.value).length
      : graphNodes.length
  );

  // Draw/Update labels using D3 data join
  let labels = g.select(".labels");
  if (needsRebuild || labels.empty()) {
    if (!labels.empty()) labels.remove();
    labels = g.append("g").attr("class", "labels");
  }

  let labelElements = labels.selectAll("text").data(
    graphNodes.filter((d) => !d.is_noise),
    (d) => d.id
  );

  labelElements.exit().remove();

  const newLabels = labelElements
    .enter()
    .append("text")
    .attr("font-size", 10)
    .attr("fill", "#333")
    .attr("text-anchor", "middle")
    .attr("dy", -12)
    .attr("opacity", 0)
    .style("pointer-events", "none") // Don't interfere with clicks
    .style("user-select", "none") // Prevent text selection
    .text((d) => d.case_number || d.title?.substring(0, 15) || "Doc");

  labelElements = newLabels.merge(labelElements);

  // Update simulation
  simulation.nodes(graphNodes);

  // Handle forces based on layout mode
  if (useForceLayout.value) {
    // ===== FORCE LAYOUT MODE =====
    // Re-enable all physics forces if they were removed
    if (!simulation.force("charge")) {
      const centerX = containerWidth / 2;
      const centerY = containerHeight / 2;
      simulation.force("charge", d3.forceManyBody().strength(-100));
      simulation.force("collision", d3.forceCollide().radius(15));
      simulation.force("x", d3.forceX(centerX).strength(0.05));
      simulation.force("y", d3.forceY(centerY).strength(0.05));
      console.log("✅ Re-enabled physics forces (charge, collision, x, y)");
    }

    // Handle link force
    const linkForce = simulation.force("link");
    if (filteredLinks.length > 0) {
      if (!linkForce) {
        // Create link force if it doesn't exist
        simulation.force(
          "link",
          d3
            .forceLink()
            .id((d) => d.id)
            .distance(80)
            .strength(0.5)
            .links(filteredLinks)
        );
        console.log(
          "✅ Created link force with",
          filteredLinks.length,
          "links"
        );
      } else {
        // Update existing link force with new data
        linkForce.links(filteredLinks);
        console.log(
          "✅ Updated link force with",
          filteredLinks.length,
          "links"
        );
      }
    }
  } else {
    // ===== FIXED POSITION MODE =====
    // Remove ALL forces to prevent any movement
    simulation.force("link", null);
    simulation.force("charge", null);
    simulation.force("collision", null);
    simulation.force("x", null);
    simulation.force("y", null);
    console.log("❌ Removed all forces (fixed position mode)");
  }

  // Restart simulation ONLY in force mode
  if (useForceLayout.value) {
    simulation.alpha(1).restart();
    console.log("▶️ Simulation restarted (force mode)");
  } else {
    simulation.stop();

    // In fixed mode, we need to manually resolve link source/target to node objects
    // because the simulation won't do it for us
    const nodeMap = new Map(graphNodes.map((n) => [n.id, n]));

    filteredLinks.forEach((link) => {
      // If source/target are IDs, convert to node references
      if (typeof link.source !== "object") {
        link.source = nodeMap.get(link.source) || {
          x: 0,
          y: 0,
          id: link.source,
        };
      }
      if (typeof link.target !== "object") {
        link.target = nodeMap.get(link.target) || {
          x: 0,
          y: 0,
          id: link.target,
        };
      }
    });

    // Update visual positions immediately
    ticked();

    // If filtering a cluster, center and zoom on it
    if (selectedCluster.value !== null) {
      console.log(
        `🎯 Centering on cluster ${selectedCluster.value} with ${graphNodes.length} nodes (NO collision)`
      );

      // Center immediately without collision
      setTimeout(() => {
        centerOnNodesAfterCollision(graphNodes, selectedCluster.value);
      }, 100);
    }
  }

  console.log("✅ Graph updated:", {
    nodeElements: nodeElements.size(),
    linkElements: linkElements.size(),
    simulationNodes: simulation.nodes().length,
    linksData: filteredLinks.length,
    forces: {
      link: !!simulation.force("link"),
      charge: !!simulation.force("charge"),
      collision: !!simulation.force("collision"),
      x: !!simulation.force("x"),
      y: !!simulation.force("y"),
    },
    mode: useForceLayout.value ? "🔄 FORCE LAYOUT" : "📍 FIXED POSITIONS",
    simulationState: useForceLayout.value ? "RUNNING" : "STOPPED",
    edgesVisible: showEdges.value,
  });
};

// Tick function
const ticked = () => {
  if (!nodeElements) return;

  // Update node positions
  nodeElements.attr("cx", (d) => d.x).attr("cy", (d) => d.y);

  // Update link positions if they exist
  if (linkElements && linkElements.size() > 0) {
    linkElements
      .attr("x1", (d) => {
        // Handle both object references (from force simulation) and plain objects
        const sourceX = typeof d.source === "object" ? d.source.x || 0 : 0;
        return sourceX;
      })
      .attr("y1", (d) => {
        const sourceY = typeof d.source === "object" ? d.source.y || 0 : 0;
        return sourceY;
      })
      .attr("x2", (d) => {
        const targetX = typeof d.target === "object" ? d.target.x || 0 : 0;
        return targetX;
      })
      .attr("y2", (d) => {
        const targetY = typeof d.target === "object" ? d.target.y || 0 : 0;
        return targetY;
      });
  }

  // Update labels
  if (g) {
    g.selectAll(".labels text")
      .attr("x", (d) => d.x)
      .attr("y", (d) => d.y);
  }
};

// Drag functions
const dragStarted = (event, d) => {
  if (!event.active) simulation.alphaTarget(0.3).restart();
  d.fx = d.x;
  d.fy = d.y;
};

const dragged = (event, d) => {
  d.fx = event.x;
  d.fy = event.y;
};

const dragEnded = (event, d) => {
  if (!event.active) simulation.alphaTarget(0);
  if (!useForceLayout.value) {
    d.fx = event.x;
    d.fy = event.y;
  } else {
    d.fx = null;
    d.fy = null;
  }
};

// Node interaction handlers
const handleNodeClick = async (nodeData) => {
  const fullNode = nodes.value.find((n) => n.id === nodeData.id);
  if (fullNode) {
    selectedDocument.value = fullNode;
    showDetails.value = true;

    // Load related documents (neighbors) from the graph
    console.log("📄 Loading neighbors for document:", fullNode.id);
    selectedDocumentNeighbors.value = [];

    try {
      // Find neighbors from the links
      const neighbors = links.value
        .filter(
          (link) => link.source === fullNode.id || link.target === fullNode.id
        )
        .map((link) => {
          const neighborId =
            link.source === fullNode.id ? link.target : link.source;
          const neighbor = nodes.value.find((n) => n.id === neighborId);
          return {
            ...neighbor,
            similarity: link.similarity,
          };
        })
        .filter((n) => n !== undefined)
        .sort((a, b) => b.similarity - a.similarity)
        .slice(0, 10); // Top 10 neighbors

      selectedDocumentNeighbors.value = neighbors;
      console.log(`✅ Found ${neighbors.length} neighbors`);
    } catch (error) {
      console.error("❌ Error loading neighbors:", error);
      selectedDocumentNeighbors.value = [];
    }
  }
};

const handleNodeHover = (nodeData, isHovering) => {
  hoveredNode.value = isHovering ? nodeData.id : null;

  if (!linkElements || !nodeElements) return;

  if (isHovering) {
    // Dim all nodes except hovered and connected
    nodeElements.attr("opacity", (d) => {
      if (d.id === nodeData.id) return 1;
      // Check if this node is connected to hovered node
      const isConnected = links.value.some(
        (link) =>
          (link.source === nodeData.id && link.target === d.id) ||
          (link.target === nodeData.id && link.source === d.id)
      );
      return isConnected ? 1 : 0.2;
    });

    // Highlight connected edges, dim others
    linkElements
      .attr("stroke-opacity", (d) => {
        const isConnected =
          d.source.id === nodeData.id || d.target.id === nodeData.id;
        const similarity = d.similarity || 0.5;

        if (isConnected) {
          return 0.9; // Highlight connected
        } else {
          // Maintain similarity-based opacity for non-connected
          if (selectedCluster.value !== null) {
            if (similarity > 0.8) return 0.15;
            if (similarity > 0.6) return 0.08;
            return 0.03;
          } else {
            if (similarity > 0.8) return 0.12;
            if (similarity > 0.6) return 0.06;
            return 0.02;
          }
        }
      })
      .attr("stroke-width", (d) => {
        const isConnected =
          d.source.id === nodeData.id || d.target.id === nodeData.id;
        const similarity = d.similarity || 0.5;

        if (isConnected) {
          // Reduced thickness - still shows variation but not too thick
          const baseMultiplier =
            selectedCluster.value !== null && !useForceLayout.value ? 6.0 : 5.0;

          // Clear differences based on similarity levels
          if (similarity > 0.8) return baseMultiplier * 2.0; // 12x or 10x - thick for strong
          if (similarity > 0.7) return baseMultiplier * 1.4; // 8.4x or 7x - medium-thick
          if (similarity > 0.6) return baseMultiplier * 1.0; // 6x or 5x - medium
          if (similarity > 0.5) return baseMultiplier * 0.7; // 4.2x or 3.5x - thin
          return baseMultiplier * 0.4; // 2.4x or 2x - very thin for weak
        } else {
          // Dimmed connections - return to default width
          return 1.5;
        }
      })
      .attr("stroke", (d) => {
        const isConnected =
          d.source.id === nodeData.id || d.target.id === nodeData.id;

        if (isConnected) {
          // Show color gradient based on similarity when hovering
          const similarity = d.similarity || 0.5;
          if (similarity > 0.8) return "#37474F"; // Dark blue-grey for very strong connections
          if (similarity > 0.7) return "#546E7A"; // Medium blue-grey
          if (similarity > 0.6) return "#78909C"; // Light blue-grey
          if (similarity > 0.5) return "#90A4AE"; // Very light blue-grey
          return "#B0BEC5"; // Subtle grey for weak connections
        } else {
          // Default black for non-connected
          return "#000000";
        }
      });
  } else {
    // Reset to normal - black with good visibility
    nodeElements.attr("opacity", selectedCluster.value !== null ? 1.0 : 0.85);

    linkElements
      .attr("stroke-opacity", 0.8) // More visible - 80% opacity
      .attr("stroke-width", 1.5) // Uniform width
      .attr("stroke", "#000000"); // Black
  }

  // Show label on hover
  g.selectAll(".labels text").attr("opacity", (d) =>
    d.id === nodeData.id && isHovering ? 1 : 0
  );
};

// Filter by cluster
const filterByCluster = (clusterLabel) => {
  console.log("🔍 Filtering by cluster:", clusterLabel);
  if (selectedCluster.value === clusterLabel) {
    clearFilter();
  } else {
    selectedCluster.value = clusterLabel;
    updateGraph();
    // Center will happen automatically after collision resolution in updateGraph (for fixed mode)
    // For force mode, center after simulation stabilizes
    if (useForceLayout.value) {
      console.log("⏳ Waiting for force simulation to stabilize...");
      setTimeout(() => {
        const simNodes = simulation.nodes();
        const clusterSimNodes = simNodes.filter(
          (n) => n.cluster === clusterLabel
        );
        if (clusterSimNodes.length > 0) {
          centerOnNodes(clusterSimNodes, clusterLabel);
        }
      }, 1500);
    } else {
      console.log("⏳ Centering will happen after collision resolution...");
    }
  }
};

const clearFilter = () => {
  selectedCluster.value = null;
  updateGraph();
  // Reset zoom to show all
  setTimeout(() => fitToView(), 100);
};

// Center view on a specific cluster
const centerOnCluster = (clusterLabel) => {
  if (!svg || !g) return;

  // Different approach based on layout mode
  if (useForceLayout.value && simulation) {
    // Force layout mode - wait for simulation to stabilize
    setTimeout(() => {
      const simNodes = simulation.nodes();
      const clusterSimNodes = simNodes.filter(
        (n) => n.cluster === clusterLabel
      );

      if (clusterSimNodes.length === 0) {
        console.warn("⚠️ No nodes found for cluster", clusterLabel);
        return;
      }

      centerOnNodes(clusterSimNodes, clusterLabel);
    }, 1500); // Wait for simulation
  } else {
    // Fixed position mode - use UMAP coordinates immediately
    const clusterNodes = nodes.value.filter((n) => n.cluster === clusterLabel);

    if (clusterNodes.length === 0) {
      console.warn("⚠️ No nodes found for cluster", clusterLabel);
      return;
    }

    // Use the same global scale and center for consistency
    const centerX = containerWidth / 2;
    const centerY = containerHeight / 2;

    // Convert UMAP coordinates to screen positions using global scaling
    const clusterScreenNodes = clusterNodes.map((n) => ({
      ...n,
      x: (n.x - globalDataCenterX) * globalScale + centerX,
      y: (n.y - globalDataCenterY) * globalScale + centerY,
    }));

    // Wait for collision resolution to finish, then center
    setTimeout(() => centerOnNodes(clusterScreenNodes, clusterLabel), 700);
  }
};

// Helper function to center on a set of nodes
const centerOnNodes = (clusterNodes, clusterLabel) => {
  console.log(
    "🎯 Centering on cluster",
    clusterLabel,
    "with",
    clusterNodes.length,
    "nodes"
  );

  // Calculate bounding box using node positions
  const xs = clusterNodes.map((n) => n.x);
  const ys = clusterNodes.map((n) => n.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;

  const container = graphContainer.value;
  const width = container.clientWidth || 800;
  const height = container.clientHeight || 700;

  // Different zoom strategies based on cluster size
  // For fixed mode: we need to ZOOM OUT to see nodes separated after collision
  let padding, maxZoom;

  if (clusterNodes.length <= 5) {
    // Very small cluster - still need good padding to see separation
    padding = 300;
    maxZoom = 1.5; // Modest zoom, don't go too close
  } else if (clusterNodes.length <= 15) {
    // Small cluster - more padding, zoom out a bit
    padding = 400;
    maxZoom = 1.2;
  } else if (clusterNodes.length <= 30) {
    // Medium cluster - lots of padding to see all nodes clearly
    padding = 500;
    maxZoom = 0.9; // Zoom OUT to see the whole cluster
  } else {
    // Large cluster - maximum padding
    padding = 600;
    maxZoom = 0.7; // Zoom OUT significantly
  }

  const clusterWidth = maxX - minX + padding;
  const clusterHeight = maxY - minY + padding;

  // Calculate scale to fit cluster WITH the extra spacing from collision
  const scale = Math.min(width / clusterWidth, height / clusterHeight, maxZoom);

  // Don't zoom in too much - we want to see the separation
  const finalScale = Math.min(scale, 1.2);

  // Calculate translation to center the cluster
  const translateX = width / 2 - centerX * finalScale;
  const translateY = height / 2 - centerY * finalScale;

  console.log("📐 Transform:", {
    centerX,
    centerY,
    scale: finalScale,
    clusterWidth,
    clusterHeight,
    nodeCount: clusterNodes.length,
  });

  // Apply the zoom transform using the stored zoom behavior
  if (!svg || !zoomBehavior) {
    console.error("❌ Cannot zoom: SVG or zoomBehavior not initialized!");
    return;
  }

  const newTransform = d3.zoomIdentity
    .translate(translateX, translateY)
    .scale(finalScale);

  svg.transition().duration(750).call(zoomBehavior.transform, newTransform);
};

// Helper function to center on nodes after collision (uses actual node positions)
const centerOnNodesAfterCollision = (graphNodes, clusterLabel) => {
  console.log(
    "🎯 Centering on cluster (post-collision)",
    clusterLabel,
    "with",
    graphNodes.length,
    "nodes"
  );

  if (!svg || !g) {
    console.error("❌ Cannot center: SVG or G not initialized!");
    return;
  }

  // Use the ACTUAL positions from the nodes (after collision has moved them)
  const xs = graphNodes.map((n) => n.x);
  const ys = graphNodes.map((n) => n.y);

  console.log("📊 Node positions sample:", {
    firstNode: { x: xs[0], y: ys[0] },
    xRange: [Math.min(...xs), Math.max(...xs)],
    yRange: [Math.min(...ys), Math.max(...ys)],
    spread: {
      width: Math.max(...xs) - Math.min(...xs),
      height: Math.max(...ys) - Math.min(...ys),
    },
  });

  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;

  const container = graphContainer.value;
  const width = container.clientWidth || 800;
  const height = container.clientHeight || 700;

  // Dynamic zoom strategy based on cluster size
  let targetScale;

  if (graphNodes.length <= 5) {
    targetScale = 0.35; // More zoom for tiny clusters
  } else if (graphNodes.length <= 10) {
    targetScale = 0.3;
  } else if (graphNodes.length <= 20) {
    targetScale = 0.25;
  } else if (graphNodes.length <= 35) {
    targetScale = 0.2; // 0.2x zoom for medium clusters
  } else if (graphNodes.length <= 50) {
    targetScale = 0.18;
  } else {
    targetScale = 0.15; // Less zoom for large clusters
  }

  // Use the target scale
  const finalScale = targetScale;

  const translateX = width / 2 - centerX * finalScale;
  const translateY = height / 2 - centerY * finalScale;

  console.log("📐 Transform (post-collision):", {
    boundingBox: { minX, maxX, minY, maxY },
    center: { centerX, centerY },
    containerSize: { width, height },
    targetScale: finalScale.toFixed(2),
    translate: { x: translateX.toFixed(0), y: translateY.toFixed(0) },
    nodeCount: graphNodes.length,
  });

  // Apply the zoom transform using the stored zoom behavior
  console.log("🎬 Starting zoom animation...");

  if (!svg || !zoomBehavior) {
    console.error("❌ Cannot zoom: SVG or zoomBehavior not initialized!");
    return;
  }

  // Create the new transform
  const newTransform = d3.zoomIdentity
    .translate(translateX, translateY)
    .scale(finalScale);

  // Apply it with animation using the EXISTING zoom behavior
  svg
    .transition()
    .duration(750)
    .call(zoomBehavior.transform, newTransform)
    .on("end", () => {
      console.log("✅ Zoom animation complete!");
    });
};

// Fit all nodes to view
const fitToView = () => {
  if (!svg || !nodes.value.length || !zoomBehavior) return;

  const container = graphContainer.value;
  const width = container.clientWidth || 800;
  const height = container.clientHeight || 700;

  // Animate back to initial view using the stored zoom behavior
  svg
    .transition()
    .duration(750)
    .call(zoomBehavior.transform, d3.zoomIdentity.translate(0, 0).scale(1));

  console.log("🔍 Reset to full view");
};

// Toggle force layout
const toggleForceLayout = () => {
  if (!simulation) {
    console.warn("⚠️ Simulation not initialized");
    return;
  }

  console.log(`🔄 Toggling force layout to: ${useForceLayout.value}`);
  console.log("Current state before toggle:", {
    hasLinkForce: !!simulation.force("link"),
    hasCharge: !!simulation.force("charge"),
    alpha: simulation.alpha(),
  });

  if (useForceLayout.value) {
    // Enable force layout with links
    const linkForce = d3
      .forceLink()
      .id((d) => d.id)
      .distance(80)
      .strength(0.5);
    simulation.force("link", linkForce);
    console.log("✅ Force layout enabled");
  } else {
    // Disable force layout - use fixed positions
    simulation.force("link", null);
    console.log("❌ Force layout disabled - using UMAP positions");
  }

  // Reinitialize the graph with new settings
  updateGraph();
};

// Watch for edge toggle - just update visibility, don't rebuild
watch(showEdges, (newValue) => {
  console.log(`🔄 Edges toggled to: ${newValue}`);
  if (linkElements) {
    // Just toggle visibility of existing edges
    linkElements.style("display", newValue ? null : "none");
    console.log(`✅ Edges ${newValue ? "shown" : "hidden"}`);
  }
});

// Watch for force layout toggle - need to rebuild
watch(useForceLayout, (newValue) => {
  console.log(`🔄 Force layout changed to: ${newValue}`);
  toggleForceLayout();
});

// Show neighbors
const showNeighbors = async (documentId) => {
  // Navigate to neighbors view
  console.log("Show neighbors for:", documentId);
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

// Lifecycle - REMOVED duplicate, using the one with ResizeObserver below

onUnmounted(() => {
  if (simulation) simulation.stop();
  if (resizeObserver) {
    resizeObserver.disconnect();
  }
  if (resizeTimeout) {
    clearTimeout(resizeTimeout);
  }
  // No window.resize listener to remove - we only use ResizeObserver
});

// Unified resize handler (handles both window resize and browser zoom)
let resizeObserver = null;
let resizeTimeout = null;
const handleContainerResize = () => {
  // Safety checks: verify all critical elements exist
  if (!graphContainer.value) {
    console.warn("⚠️ Graph container not found");
    return;
  }

  if (!svg) {
    console.warn("⚠️ SVG not initialized yet");
    return;
  }

  if (!g) {
    console.warn("⚠️ SVG group (g) not initialized yet");
    return;
  }

  // Debounce to avoid too many updates
  if (resizeTimeout) {
    clearTimeout(resizeTimeout);
  }

  resizeTimeout = setTimeout(() => {
    const container = graphContainer.value;
    const newWidth = container.clientWidth;
    const newHeight = container.clientHeight;

    // Validate dimensions
    if (!newWidth || !newHeight || newWidth <= 0 || newHeight <= 0) {
      console.warn("⚠️ Invalid container dimensions:", { newWidth, newHeight });
      return;
    }

    // Only update if dimensions actually changed
    const widthChange = Math.abs(newWidth - containerWidth);
    const heightChange = Math.abs(newHeight - containerHeight);

    if (widthChange > 5 || heightChange > 5) {
      console.log("🔄 Container resize detected:", {
        oldWidth: containerWidth,
        oldHeight: containerHeight,
        newWidth: newWidth,
        newHeight: newHeight,
        widthChange,
        heightChange,
      });

      // Update container dimensions
      containerWidth = newWidth;
      containerHeight = newHeight;

      // Update SVG dimensions
      svg.attr("width", newWidth).attr("height", newHeight);

      // Update force simulation center if using force layout
      if (simulation && useForceLayout.value) {
        simulation
          .force("x", d3.forceX(newWidth / 2).strength(0.05))
          .force("y", d3.forceY(newHeight / 2).strength(0.05))
          .alpha(0.3)
          .restart();
      }

      console.log("✅ Container dimensions updated successfully");
    } else {
      console.log("ℹ️ Dimensions change too small, ignoring:", {
        widthChange,
        heightChange,
      });
    }
  }, 150); // 150ms debounce
};

// Setup resize observer on mount
onMounted(async () => {
  await loadClusters();

  // Wait for graph to be fully initialized before attaching ResizeObserver
  await nextTick();
  await nextTick();

  // Setup ResizeObserver to detect ALL container size changes
  // (handles both window resize AND browser zoom)
  setTimeout(() => {
    if (graphContainer.value) {
      resizeObserver = new ResizeObserver((entries) => {
        // Call unified resize handler
        handleContainerResize();
      });
      resizeObserver.observe(graphContainer.value);
      console.log(
        "✅ ResizeObserver attached - handles window resize and browser zoom"
      );
    }
  }, 500); // Wait 500ms to ensure everything is ready

  // NO window.resize listener needed - ResizeObserver handles everything
});
</script>

<style scoped>
.clusters-view-d3 {
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

.graph-container {
  overflow: visible;
  position: relative;
}

.graph-container svg {
  display: block;
}
</style>
