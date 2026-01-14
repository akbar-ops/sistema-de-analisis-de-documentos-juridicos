<template>
  <v-container
    fluid
    class="clusters-view-echarts pa-4"
    style="max-width: 1920px; margin: 0 auto"
  >
    <!-- Header Row -->
    <v-row class="mb-3">
      <v-col cols="12">
        <div class="d-flex align-center justify-space-between">
          <div class="d-flex align-center">
            <v-icon size="large" class="mr-2" color="primary"
              >mdi-chart-bubble</v-icon
            >
            <div>
              <h1 class="text-h5 font-weight-bold mb-0">
                Explorador de Tópicos
              </h1>
              <p class="text-caption text-grey mb-0">
                Mapa visual de documentos agrupados por temas (BERTopic)
              </p>
            </div>
          </div>
          <div class="d-flex gap-2 align-center">
            <!-- Compact Stats -->
            <v-chip
              v-if="metadata"
              size="small"
              color="primary"
              variant="tonal"
            >
              <v-icon start size="small">mdi-file-document-multiple</v-icon>
              {{ metadata.document_count }} docs
            </v-chip>
            <v-chip
              v-if="metadata"
              size="small"
              color="success"
              variant="tonal"
            >
              <v-icon start size="small">mdi-chart-bubble</v-icon>
              {{ metadata.cluster_count }} clusters
            </v-chip>
            <v-chip
              v-if="metadata && metadata.noise_count > 0"
              size="small"
              color="warning"
              variant="tonal"
            >
              <v-icon start size="small">mdi-help-circle</v-icon>
              {{ metadata.noise_count }} sin grupo
            </v-chip>
            <v-divider vertical class="mx-2"></v-divider>
            <v-chip
              v-if="metadata"
              size="small"
              variant="outlined"
              prepend-icon="mdi-clock-outline"
            >
              {{ formatDate(metadata.created_at) }}
            </v-chip>
            <v-btn
              color="primary"
              size="small"
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
    <v-row v-if="regenerationProgress" class="mb-2">
      <v-col cols="12">
        <v-alert
          type="info"
          variant="tonal"
          density="compact"
          closable
          @click:close="regenerationProgress = null"
        >
          <div class="d-flex align-center">
            <v-progress-circular
              v-if="!regenerationProgress.completed"
              indeterminate
              size="16"
              width="2"
              class="mr-2"
            ></v-progress-circular>
            <v-icon v-else color="success" size="small" class="mr-2"
              >mdi-check-circle</v-icon
            >
            <span class="font-weight-medium">{{
              regenerationProgress.message
            }}</span>
            <span v-if="regenerationProgress.details" class="text-caption ml-2">
              {{ regenerationProgress.details }}
            </span>
          </div>
        </v-alert>
      </v-col>
    </v-row>

    <!-- Main Content: Graph (Left) + Sidebar (Right) -->
    <v-row>
      <!-- Graph Panel - Takes ~70% -->
      <v-col cols="12" lg="8" xl="9">
        <v-card elevation="2" class="graph-card">
          <v-card-title
            class="bg-grey-lighten-4 py-2 d-flex justify-space-between align-center"
          >
            <div class="d-flex align-center">
              <v-icon class="mr-2" size="small">mdi-graph</v-icon>
              <span class="text-subtitle-1 font-weight-medium"
                >Vista de Clusters</span
              >
              <v-chip
                v-if="selectedCluster !== null"
                size="x-small"
                color="primary"
                class="ml-2"
                closable
                @click:close="clearFilter"
              >
                Cluster {{ selectedCluster }}
              </v-chip>
            </div>
            <div class="d-flex gap-1 align-center">
              <v-switch
                v-model="showEdges"
                density="compact"
                hide-details
                color="primary"
                class="compact-switch"
              >
                <template v-slot:label>
                  <span class="text-caption">Conexiones</span>
                </template>
              </v-switch>
              <v-switch
                v-model="useForceLayout"
                density="compact"
                hide-details
                color="secondary"
                class="compact-switch"
              >
                <template v-slot:label>
                  <span class="text-caption">Auto-agrupar</span>
                </template>
              </v-switch>
              <v-divider vertical class="mx-1"></v-divider>
              <div style="width: 120px">
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
                >
                  <template v-slot:prepend>
                    <span class="text-caption text-grey">K:{{ topK }}</span>
                  </template>
                </v-slider>
              </div>
              <v-btn-group density="compact" variant="outlined" class="ml-1">
                <v-btn
                  size="x-small"
                  icon="mdi-magnify-plus"
                  @click="zoomIn"
                ></v-btn>
                <v-btn
                  size="x-small"
                  icon="mdi-magnify-minus"
                  @click="zoomOut"
                ></v-btn>
                <v-btn
                  size="x-small"
                  icon="mdi-fit-to-screen"
                  @click="fitToView"
                ></v-btn>
              </v-btn-group>
            </div>
          </v-card-title>

          <v-card-text class="pa-0" style="position: relative">
            <div
              v-if="loading"
              class="d-flex align-center justify-center"
              style="height: 550px"
            >
              <div class="text-center">
                <v-progress-circular
                  indeterminate
                  color="primary"
                  size="48"
                ></v-progress-circular>
                <div class="mt-3 text-subtitle-2">Cargando clusters...</div>
              </div>
            </div>
            <div
              v-show="!loading"
              ref="chartContainer"
              class="chart-container"
              style="width: 100%; height: 550px"
            ></div>
          </v-card-text>
        </v-card>

        <!-- Keywords Barchart - Shows when a topic is selected -->
        <v-card
          v-if="selectedCluster !== null && selectedClusterKeywords.length > 0"
          elevation="1"
          class="mt-3"
        >
          <v-card-text class="pa-3">
            <div class="d-flex align-center justify-space-between mb-2">
              <div class="d-flex align-center">
                <v-avatar
                  :color="getClusterColor(selectedCluster)"
                  size="24"
                  class="mr-2"
                >
                  <span class="text-white text-caption font-weight-bold">{{
                    selectedCluster
                  }}</span>
                </v-avatar>
                <span class="text-subtitle-2 font-weight-medium">
                  Keywords del Tópico
                </span>
              </div>
              <v-chip size="x-small" variant="outlined" color="grey">
                {{ selectedClusterKeywords.length }} términos
              </v-chip>
            </div>
            <div
              ref="keywordsChartContainer"
              class="keywords-chart-container"
              style="width: 100%; height: 220px"
            ></div>
          </v-card-text>
        </v-card>

        <!-- Quality Metrics - Compact horizontal row below graph (for legacy HDBSCAN) -->
        <v-card
          v-if="qualityMetrics && !qualityMetrics.error"
          elevation="1"
          class="mt-3"
        >
          <v-card-text class="py-2">
            <div
              class="d-flex align-center justify-space-between flex-wrap gap-3"
            >
              <div class="d-flex align-center">
                <v-icon size="small" class="mr-2" color="grey"
                  >mdi-chart-areaspline</v-icon
                >
                <span class="text-caption font-weight-medium text-grey-darken-1"
                  >Métricas de Calidad:</span
                >
              </div>

              <!-- Silhouette -->
              <div class="d-flex align-center metric-item">
                <v-avatar
                  size="24"
                  :color="getSilhouetteColor(qualityMetrics.silhouette_score)"
                  class="mr-1"
                >
                  <v-icon size="x-small" color="white"
                    >mdi-circle-slice-8</v-icon
                  >
                </v-avatar>
                <div>
                  <span class="text-caption text-grey">Silhouette</span>
                  <div class="text-subtitle-2 font-weight-bold">
                    {{ qualityMetrics.silhouette_score?.toFixed(3) ?? "N/A" }}
                  </div>
                </div>
                <v-tooltip activator="parent" location="bottom">
                  <div style="max-width: 200px">
                    {{ qualityMetrics.interpretation?.silhouette?.message
                    }}<br />
                    <small>Rango: -1 a 1 (mayor es mejor)</small>
                  </div>
                </v-tooltip>
              </div>

              <!-- Calinski-Harabasz -->
              <div class="d-flex align-center metric-item">
                <v-avatar size="24" color="primary" class="mr-1">
                  <v-icon size="x-small" color="white"
                    >mdi-chart-scatter-plot</v-icon
                  >
                </v-avatar>
                <div>
                  <span class="text-caption text-grey">Calinski-Harabasz</span>
                  <div class="text-subtitle-2 font-weight-bold">
                    {{
                      qualityMetrics.calinski_harabasz_score?.toFixed(1) ??
                      "N/A"
                    }}
                  </div>
                </div>
                <v-tooltip activator="parent" location="bottom">
                  <div style="max-width: 200px">
                    {{
                      qualityMetrics.interpretation?.calinski_harabasz?.message
                    }}<br />
                    <small>Sin límite superior (mayor es mejor)</small>
                  </div>
                </v-tooltip>
              </div>

              <!-- Davies-Bouldin -->
              <div class="d-flex align-center metric-item">
                <v-avatar
                  size="24"
                  :color="
                    getDaviesBouldinColor(qualityMetrics.davies_bouldin_score)
                  "
                  class="mr-1"
                >
                  <v-icon size="x-small" color="white">mdi-target</v-icon>
                </v-avatar>
                <div>
                  <span class="text-caption text-grey">Davies-Bouldin</span>
                  <div class="text-subtitle-2 font-weight-bold">
                    {{
                      qualityMetrics.davies_bouldin_score?.toFixed(3) ?? "N/A"
                    }}
                  </div>
                </div>
                <v-tooltip activator="parent" location="bottom">
                  <div style="max-width: 200px">
                    {{ qualityMetrics.interpretation?.davies_bouldin?.message
                    }}<br />
                    <small>Rango: 0+ (menor es mejor)</small>
                  </div>
                </v-tooltip>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Sidebar - Takes ~30% -->
      <v-col cols="12" lg="4" xl="3">
        <v-card
          elevation="2"
          class="sidebar-card"
          style="height: 620px; display: flex; flex-direction: column"
        >
          <!-- CLUSTERS VIEW (when no cluster selected) -->
          <template v-if="selectedCluster === null">
            <v-card-title class="bg-grey-lighten-4 py-2 flex-shrink-0">
              <v-icon class="mr-2" size="small">mdi-tag-multiple</v-icon>
              <span class="text-subtitle-1 font-weight-medium">Tópicos</span>
              <v-spacer></v-spacer>
              <v-chip size="x-small" color="primary" variant="tonal">
                {{ clusterStats?.length || 0 }} temas
              </v-chip>
            </v-card-title>

            <div class="cluster-list-section flex-grow-1">
              <v-list density="compact" class="pa-0">
                <v-list-item
                  v-for="stat in clusterStats"
                  :key="stat.cluster_label || stat.topic_id"
                  @click="filterByCluster(stat.cluster_label || stat.topic_id)"
                  class="cluster-list-item"
                  lines="three"
                >
                  <template v-slot:prepend>
                    <v-avatar
                      :color="getClusterColor(stat.cluster_label || stat.topic_id)"
                      size="28"
                    >
                      <span class="text-white text-caption font-weight-bold">{{
                        stat.cluster_label || stat.topic_id
                      }}</span>
                    </v-avatar>
                  </template>

                  <v-list-item-title class="text-body-2 font-weight-medium">
                    {{ stat.topic_label || stat.label || stat.main_area || `Tópico ${stat.topic_id}` }}
                  </v-list-item-title>
                  <v-list-item-subtitle class="text-caption mb-1">
                    {{ stat.size || stat.document_count }} documentos
                  </v-list-item-subtitle>
                  <!-- Keywords preview -->
                  <div v-if="stat.keywords?.length" class="d-flex flex-wrap gap-1 mt-1">
                    <v-chip
                      v-for="keyword in stat.keywords.slice(0, 3)"
                      :key="keyword"
                      size="x-small"
                      variant="outlined"
                      :color="getClusterColor(stat.cluster_label || stat.topic_id)"
                      class="px-1"
                    >
                      {{ keyword }}
                    </v-chip>
                    <span v-if="stat.keywords.length > 3" class="text-caption text-grey">
                      +{{ stat.keywords.length - 3 }}
                    </span>
                  </div>

                  <template v-slot:append>
                    <v-chip size="x-small" color="grey" variant="tonal">
                      {{ stat.size || stat.document_count }}
                    </v-chip>
                  </template>
                </v-list-item>
              </v-list>
            </div>
          </template>

          <!-- DOCUMENTS VIEW (when cluster is selected) -->
          <template v-else>
            <!-- Header with back button -->
            <div class="bg-primary pa-2 d-flex align-center flex-shrink-0">
              <v-btn
                icon="mdi-arrow-left"
                variant="text"
                color="white"
                size="small"
                @click="clearFilter"
                class="mr-2"
              ></v-btn>
              <v-avatar
                :color="getClusterColor(selectedCluster)"
                size="28"
                class="mr-2"
              >
                <span class="text-white text-caption font-weight-bold">{{
                  selectedCluster
                }}</span>
              </v-avatar>
              <div class="text-white flex-grow-1">
                <div class="text-subtitle-2 font-weight-medium">
                  {{
                    selectedClusterStats?.topic_label ||
                    selectedClusterStats?.label ||
                    selectedClusterStats?.main_area ||
                    "Tópico " + selectedCluster
                  }}
                </div>
                <div class="text-caption" style="opacity: 0.8">
                  {{ selectedClusterDocuments.length }} documentos
                </div>
              </div>
              <v-btn
                icon="mdi-close"
                variant="text"
                color="white"
                size="x-small"
                @click="clearFilter"
              ></v-btn>
            </div>

            <!-- Area Distribution Tags -->
            <div
              class="pa-2 bg-grey-lighten-4 flex-shrink-0"
              v-if="selectedClusterStats?.area_distribution"
            >
              <div class="d-flex gap-1 flex-wrap">
                <v-chip
                  v-for="(
                    count, area
                  ) in selectedClusterStats.area_distribution"
                  :key="area"
                  size="x-small"
                  variant="flat"
                  :color="
                    area === selectedClusterStats.main_area
                      ? 'primary'
                      : 'grey-lighten-1'
                  "
                >
                  {{ area }}: {{ count }}
                </v-chip>
              </div>
            </div>

            <!-- Keywords Section for BERTopic -->
            <div 
              class="pa-2 bg-grey-lighten-5 flex-shrink-0 keywords-section"
              v-if="selectedClusterKeywords.length > 0"
            >
              <div class="text-caption text-grey-darken-1 mb-1 d-flex align-center">
                <v-icon size="x-small" class="mr-1">mdi-key-variant</v-icon>
                Keywords del Tópico
              </div>
              <div class="d-flex gap-1 flex-wrap">
                <v-chip
                  v-for="(keyword, idx) in selectedClusterKeywords"
                  :key="keyword"
                  size="small"
                  variant="elevated"
                  :color="getClusterColor(selectedCluster)"
                  :style="{
                    opacity: Math.max(0.5, 1 - (idx * 0.05))
                  }"
                  class="px-2 font-weight-medium"
                >
                  {{ keyword }}
                </v-chip>
              </div>
            </div>

            <!-- Documents List -->
            <div
              class="documents-list-section flex-grow-1"
              style="min-height: 0"
            >
              <v-virtual-scroll
                :items="selectedClusterDocuments"
                :item-height="56"
                class="fill-height"
              >
                <template v-slot:default="{ item, index }">
                  <v-list-item
                    :key="item.id"
                    @click="openDocumentDetails(item)"
                    @mouseenter="highlightNodeInGraph(item.id)"
                    @mouseleave="unhighlightNodeInGraph()"
                    class="cluster-doc-item px-2"
                    :class="{ 'bg-grey-lighten-5': index % 2 === 0 }"
                    density="compact"
                  >
                    <v-list-item-title
                      class="text-body-2 font-weight-medium text-truncate"
                    >
                      {{ item.title || "Documento sin título" }}
                    </v-list-item-title>
                    <v-list-item-subtitle class="text-caption">
                      <span v-if="item.case_number"
                        >📁 {{ item.case_number }}</span
                      >
                      <span v-if="item.legal_area" class="ml-2"
                        >⚖️ {{ item.legal_area }}</span
                      >
                    </v-list-item-subtitle>

                    <template v-slot:append>
                      <v-btn
                        icon="mdi-eye-outline"
                        variant="text"
                        color="primary"
                        size="x-small"
                        @click.stop="openDocumentDetails(item)"
                      ></v-btn>
                    </template>
                  </v-list-item>
                </template>
              </v-virtual-scroll>
            </div>
          </template>
        </v-card>
      </v-col>
    </v-row>

    <!-- Document Details Dialog -->
    <v-dialog v-model="showDetails" max-width="700">
      <v-card v-if="selectedDocument">
        <v-card-title class="bg-primary text-white py-3">
          <div
            class="d-flex justify-space-between align-center"
            style="width: 100%"
          >
            <span
              class="text-subtitle-1 text-truncate"
              style="max-width: 500px"
            >
              {{ selectedDocument.title }}
            </span>
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
          <v-row dense>
            <v-col cols="6">
              <div class="text-caption text-grey">Expediente</div>
              <div class="text-body-2 font-weight-medium">
                {{ selectedDocument.case_number || "N/A" }}
              </div>
            </v-col>
            <v-col cols="6">
              <div class="text-caption text-grey">Área Legal</div>
              <div class="text-body-2 font-weight-medium">
                {{ selectedDocument.legal_area || "N/A" }}
              </div>
            </v-col>
            <v-col cols="6">
              <div class="text-caption text-grey">Tipo</div>
              <div class="text-body-2 font-weight-medium">
                {{ selectedDocument.doc_type || "N/A" }}
              </div>
            </v-col>
            <v-col cols="6">
              <div class="text-caption text-grey">Tópico</div>
              <v-chip
                size="small"
                :color="getClusterColor(selectedDocument.cluster)"
              >
                {{ selectedDocument.topic_label || `Tópico ${selectedDocument.cluster}` }}
              </v-chip>
            </v-col>
            <v-col v-if="selectedDocument.probability" cols="6">
              <div class="text-caption text-grey">Confianza</div>
              <div class="text-body-2 font-weight-medium">
                {{ (selectedDocument.probability * 100).toFixed(1) }}%
              </div>
            </v-col>
            <v-col v-if="selectedDocument.document_date" cols="6">
              <div class="text-caption text-grey">Fecha</div>
              <div class="text-body-2 font-weight-medium">
                {{ formatDate(selectedDocument.document_date) }}
              </div>
            </v-col>
          </v-row>

          <!-- Action Button: Chat with Document -->
          <v-tooltip
            location="bottom"
            text="Abrir en nueva pestaña para analizar con IA"
          >
            <template v-slot:activator="{ props }">
              <v-btn
                v-bind="props"
                color="primary"
                size="large"
                block
                class="mt-4"
                prepend-icon="mdi-chat-processing"
                @click="openDocumentChat(selectedDocument)"
              >
                Chat con Documento
                <v-icon end size="small">mdi-open-in-new</v-icon>
              </v-btn>
            </template>
          </v-tooltip>

          <!-- Related Documents -->
          <template v-if="selectedDocumentNeighbors.length > 0">
            <v-divider class="my-4"></v-divider>
            <div class="text-subtitle-2 mb-2">
              📎 Documentos Relacionados ({{
                selectedDocumentNeighbors.length
              }})
            </div>
            <v-list
              density="compact"
              class="pa-0"
              style="max-height: 200px; overflow-y: auto"
            >
              <v-list-item
                v-for="neighbor in selectedDocumentNeighbors"
                :key="neighbor.id"
                class="px-0"
                @click="openDocumentChat(neighbor)"
                style="cursor: pointer"
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
                <v-list-item-title class="text-body-2">{{
                  neighbor.title
                }}</v-list-item-title>
                <v-list-item-subtitle class="text-caption">
                  {{ (neighbor.similarity * 100).toFixed(1) }}% similar •
                  {{ neighbor.case_number || "Sin expediente" }}
                </v-list-item-subtitle>
                <template v-slot:append>
                  <v-progress-linear
                    :model-value="neighbor.similarity * 100"
                    height="4"
                    color="primary"
                    style="width: 60px"
                  ></v-progress-linear>
                </template>
              </v-list-item>
            </v-list>
          </template>
        </v-card-text>
        <v-card-actions class="px-4 pb-4">
          <v-btn
            variant="outlined"
            color="primary"
            prepend-icon="mdi-open-in-new"
            @click="openDocumentChat(selectedDocument)"
          >
            Ver Análisis Completo
          </v-btn>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="showDetails = false">Cerrar</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from "vue";
import { useRouter } from "vue-router";
import axios from "axios";
import * as echarts from "echarts";

const router = useRouter();

// State
const loading = ref(false);
const regenerating = ref(false);
const regenerationProgress = ref(null);
const showEdges = ref(true);
const useForceLayout = ref(true);
const showDetails = ref(false);
const selectedDocument = ref(null);
const selectedDocumentNeighbors = ref([]);
const selectedCluster = ref(null);
const topK = ref(5);

// Data from API (BERTopic)
const nodes = ref([]);
const links = ref([]);
const clusterStats = ref([]);  // Now contains topic_stats from BERTopic
const topics = ref([]);  // Raw topics data with keywords
const metadata = ref(null);
const qualityMetrics = ref(null);

// ECharts refs
const chartContainer = ref(null);
const keywordsChartContainer = ref(null);
let chartInstance = null;
let keywordsChartInstance = null;
let resizeObserver = null;

// Professional color palette for clusters - Vibrant, high contrast, colorblind-friendly
const clusterColors = [
  "#2563EB", // Royal Blue
  "#DC2626", // Crimson Red
  "#059669", // Emerald
  "#7C3AED", // Vivid Purple
  "#EA580C", // Burnt Orange
  "#0891B2", // Teal Cyan
  "#C026D3", // Fuchsia
  "#CA8A04", // Gold
  "#4F46E5", // Indigo
  "#16A34A", // Kelly Green
  "#E11D48", // Rose
  "#0D9488", // Dark Teal
  "#9333EA", // Violet
  "#F97316", // Bright Orange
  "#0284C7", // Sky Blue
  "#65A30D", // Lime Green
  "#DB2777", // Hot Pink
  "#1D4ED8", // Deep Blue
  "#B91C1C", // Dark Red
  "#047857", // Forest Green
];

// Get cluster color with improved contrast
const getClusterColor = (cluster) => {
  if (cluster === -1) return "#6B7280"; // Neutral gray for noise
  return clusterColors[Math.abs(cluster) % clusterColors.length];
};

// Helper functions for quality metrics visualization
const getSilhouetteColor = (score) => {
  if (score === null || score === undefined) return "grey";
  if (score >= 0.7) return "success";
  if (score >= 0.5) return "light-green";
  if (score >= 0.25) return "warning";
  return "error";
};

const getDaviesBouldinColor = (score) => {
  if (score === null || score === undefined) return "grey";
  if (score < 0.5) return "success";
  if (score < 1.0) return "light-green";
  if (score < 2.0) return "warning";
  return "error";
};

const getMetricTextColor = (level) => {
  const colors = {
    excellent: "text-success",
    good: "text-light-green",
    fair: "text-warning",
    poor: "text-error",
    info: "text-info",
  };
  return colors[level] || "text-grey";
};

const getMetricIcon = (level) => {
  const icons = {
    excellent: "mdi-check-circle",
    good: "mdi-check-circle-outline",
    fair: "mdi-alert-circle-outline",
    poor: "mdi-close-circle",
    info: "mdi-information",
  };
  return icons[level] || "mdi-information";
};

// Open document details from cluster list
const openDocumentDetails = (doc) => {
  selectedDocument.value = doc;
  showDetails.value = true;

  // Find neighbors from links
  const neighbors = links.value
    .filter((link) => link.source === doc.id || link.target === doc.id)
    .map((link) => {
      const neighborId = link.source === doc.id ? link.target : link.source;
      const neighbor = nodes.value.find((n) => n.id === neighborId);
      return neighbor ? { ...neighbor, similarity: link.similarity } : null;
    })
    .filter((n) => n !== null)
    .sort((a, b) => b.similarity - a.similarity)
    .slice(0, 10);

  selectedDocumentNeighbors.value = neighbors;
};

// Get edge color based on similarity - Elegant red gradient palette
const getEdgeColor = (similarity) => {
  if (similarity > 0.85) return "#7F1D1D"; // Deep Maroon - Very High
  if (similarity > 0.7) return "#991B1B"; // Dark Burgundy - High
  if (similarity > 0.55) return "#DC2626"; // Crimson Red - Medium-High
  if (similarity > 0.4) return "#EF4444"; // Bright Red - Medium
  if (similarity > 0.25) return "#F87171"; // Coral Red - Low-Medium
  return "#D6D3D1"; // Warm Gray - Low (stone-300)
};

// Get edge width based on similarity - more visible differences
const getEdgeWidth = (similarity) => {
  if (similarity > 0.85) return 4;
  if (similarity > 0.7) return 3;
  if (similarity > 0.55) return 2.5;
  if (similarity > 0.4) return 2;
  if (similarity > 0.25) return 1.5;
  return 1;
};

// Get edge opacity based on similarity - uniform when not hovered
const getEdgeOpacity = (similarity) => {
  return 0.25; // Uniform low opacity for all edges by default
};

// Get edge opacity when hovered/emphasized - show similarity differences
const getEdgeOpacityEmphasis = (similarity) => {
  if (similarity > 0.85) return 1.0;
  if (similarity > 0.7) return 0.9;
  if (similarity > 0.55) return 0.8;
  if (similarity > 0.4) return 0.7;
  if (similarity > 0.25) return 0.6;
  return 0.5;
};

// Get edge width when hovered - more visible differences
const getEdgeWidthEmphasis = (similarity) => {
  if (similarity > 0.85) return 8;
  if (similarity > 0.7) return 6;
  if (similarity > 0.55) return 5;
  if (similarity > 0.4) return 4;
  if (similarity > 0.25) return 3;
  return 2;
};

// Load clusters from BERTopic API
const loadClusters = async () => {
  loading.value = true;
  try {
    // Use BERTopic endpoint instead of HDBSCAN clustering
    const response = await axios.get("/api/documents/bertopic_topics/", {
      params: {
        include_edges: true,
        include_outliers: true,
        top_k: topK.value,
      },
    });

    nodes.value = response.data.nodes || [];
    links.value = response.data.links || [];
    topics.value = response.data.topics || [];  // Raw topics with keywords
    clusterStats.value = response.data.topic_stats || response.data.cluster_stats || [];
    metadata.value = response.data.metadata || {};
    // BERTopic doesn't compute traditional quality metrics
    qualityMetrics.value = null;

    console.log("✅ BERTopic topics loaded:", {
      nodes: nodes.value.length,
      links: links.value.length,
      topics: topics.value.length,
      clusters: metadata.value.topic_count || metadata.value.cluster_count,
    });

    loading.value = false;
    await nextTick();

    initChart();
  } catch (error) {
    console.error("❌ Error loading BERTopic topics:", error);
    loading.value = false;
  }
};

// Regenerate BERTopic model
const regenerateClusters = async () => {
  regenerating.value = true;
  regenerationProgress.value = {
    message: "Iniciando regeneración de tópicos BERTopic...",
    details: null,
    completed: false,
  };

  try {
    console.log("🔄 Triggering BERTopic regeneration...");
    const response = await axios.post("/api/documents/regenerate_bertopic/", {
      max_documents: 1000,
      min_topic_size: 5,
    });

    const { task_id, estimated_time_seconds, document_count, message } =
      response.data;

    regenerationProgress.value = {
      message: "Generando modelo BERTopic...",
      details: `Procesando ${document_count} documentos. Tiempo estimado: ${estimated_time_seconds}s`,
      completed: false,
    };

    const waitTime = (estimated_time_seconds + 2) * 1000;
    await new Promise((resolve) => setTimeout(resolve, waitTime));

    regenerationProgress.value = {
      message: "Cargando nuevos tópicos...",
      details: null,
      completed: false,
    };

    await loadClusters();

    regenerationProgress.value = {
      message: "✅ Modelo BERTopic regenerado exitosamente",
      details: `${document_count} documentos procesados`,
      completed: true,
    };

    setTimeout(() => {
      regenerationProgress.value = null;
    }, 5000);
  } catch (error) {
    console.error("❌ Error regenerating BERTopic:", error);
    regenerationProgress.value = {
      message: "❌ Error al regenerar tópicos",
      details:
        error.response?.data?.error || error.message || "Error desconocido",
      completed: true,
    };
    setTimeout(() => {
      regenerationProgress.value = null;
    }, 10000);
  } finally {
    regenerating.value = false;
  }
};

// Handle top-k change
const onTopKChange = async () => {
  const currentCluster = selectedCluster.value;

  try {
    const response = await axios.get("/api/documents/bertopic_topics/", {
      params: {
        include_edges: true,
        include_outliers: true,
        top_k: topK.value,
      },
    });

    nodes.value = response.data.nodes || [];
    links.value = response.data.links || [];
    topics.value = response.data.topics || [];
    clusterStats.value = response.data.topic_stats || response.data.cluster_stats || [];
    metadata.value = response.data.metadata || {};

    if (currentCluster !== null) {
      selectedCluster.value = currentCluster;
    }

    updateChart();
  } catch (error) {
    console.error("❌ Error updating top-k:", error);
  }
};

// Compute filtered data
const filteredNodes = computed(() => {
  if (selectedCluster.value === null) {
    return nodes.value;
  }
  return nodes.value.filter((n) => n.cluster === selectedCluster.value);
});

const filteredLinks = computed(() => {
  const nodeIds = new Set(filteredNodes.value.map((n) => n.id));
  return links.value.filter((l) => {
    const sourceId = typeof l.source === "object" ? l.source.id : l.source;
    const targetId = typeof l.target === "object" ? l.target.id : l.target;
    return nodeIds.has(sourceId) && nodeIds.has(targetId);
  });
});

// Get documents belonging to selected cluster (sorted by title)
const selectedClusterDocuments = computed(() => {
  if (selectedCluster.value === null) return [];
  return nodes.value
    .filter((n) => n.cluster === selectedCluster.value)
    .sort((a, b) => (a.title || "").localeCompare(b.title || ""));
});

// Get stats for selected cluster
const selectedClusterStats = computed(() => {
  if (selectedCluster.value === null) return null;
  return clusterStats.value.find(
    (s) => s.cluster_label === selectedCluster.value || s.topic_id === selectedCluster.value
  );
});

// Get keywords for selected cluster/topic
const selectedClusterKeywords = computed(() => {
  if (selectedCluster.value === null) return [];
  
  // First try to get from clusterStats (topic_stats)
  const topicStat = clusterStats.value.find(
    (s) => s.cluster_label === selectedCluster.value || s.topic_id === selectedCluster.value
  );
  if (topicStat?.keywords) {
    return topicStat.keywords.slice(0, 10);
  }
  
  // Fallback to topics array
  const topic = topics.value.find((t) => t.topic_id === selectedCluster.value);
  if (topic?.keywords) {
    return topic.keywords.slice(0, 10);
  }
  
  return [];
});

// Get keyword weights for selected cluster/topic
const selectedClusterKeywordWeights = computed(() => {
  if (selectedCluster.value === null) return {};
  
  const topicStat = clusterStats.value.find(
    (s) => s.cluster_label === selectedCluster.value || s.topic_id === selectedCluster.value
  );
  if (topicStat?.keyword_weights) {
    return topicStat.keyword_weights;
  }
  
  const topic = topics.value.find((t) => t.topic_id === selectedCluster.value);
  return topic?.keyword_weights || {};
});

// Keywords Barchart Methods
const initKeywordsChart = () => {
  if (!keywordsChartContainer.value) return;
  
  // Dispose existing instance
  if (keywordsChartInstance) {
    keywordsChartInstance.dispose();
  }
  
  keywordsChartInstance = echarts.init(keywordsChartContainer.value, null, {
    renderer: "canvas",
  });
  
  updateKeywordsChart();
};

const updateKeywordsChart = () => {
  if (!keywordsChartInstance || selectedClusterKeywords.value.length === 0) return;
  
  const keywords = selectedClusterKeywords.value;
  const weights = selectedClusterKeywordWeights.value;
  
  // Prepare data - reverse for horizontal bar display
  const data = keywords.map((kw) => ({
    name: kw,
    value: weights[kw] || 0.5,
  })).reverse();
  
  const topicColor = getClusterColor(selectedCluster.value);
  
  const option = {
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter: (params) => {
        const data = params[0];
        return `<strong>${data.name}</strong><br/>Relevancia: ${(data.value * 100).toFixed(1)}%`;
      },
    },
    grid: {
      left: 100,
      right: 20,
      top: 10,
      bottom: 20,
    },
    xAxis: {
      type: "value",
      axisLabel: { show: false },
      splitLine: { show: false },
      max: (value) => value.max * 1.1,
    },
    yAxis: {
      type: "category",
      data: data.map((d) => d.name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        fontSize: 11,
        color: "#374151",
        fontWeight: "500",
      },
    },
    series: [
      {
        type: "bar",
        data: data.map((d) => ({
          value: d.value,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: topicColor },
              { offset: 1, color: adjustColorBrightness(topicColor, 30) },
            ]),
          },
        })),
        itemStyle: {
          borderRadius: [0, 4, 4, 0],
        },
        barWidth: "60%",
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: "rgba(0,0,0,0.2)",
          },
        },
      },
    ],
    animation: true,
    animationDuration: 500,
  };
  
  keywordsChartInstance.setOption(option);
};

// Helper to adjust color brightness
const adjustColorBrightness = (hex, percent) => {
  const num = parseInt(hex.replace("#", ""), 16);
  const amt = Math.round(2.55 * percent);
  const R = Math.min(255, (num >> 16) + amt);
  const G = Math.min(255, ((num >> 8) & 0x00ff) + amt);
  const B = Math.min(255, (num & 0x0000ff) + amt);
  return `#${(0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1)}`;
};

// Initialize ECharts
const initChart = () => {
  if (!chartContainer.value) {
    console.warn("⚠️ Chart container not ready");
    return;
  }

  // Dispose existing instance
  if (chartInstance) {
    chartInstance.dispose();
  }

  chartInstance = echarts.init(chartContainer.value, null, {
    renderer: "canvas",
  });

  // Set up event handlers
  chartInstance.on("click", "series.graph", handleNodeClick);
  chartInstance.on("mouseover", "series.graph", handleNodeHover);
  chartInstance.on("mouseout", "series.graph", handleNodeMouseOut);

  updateChart();
  console.log("✅ ECharts initialized");
};

// Build chart option
const buildChartOption = () => {
  // Safety check for empty data
  if (filteredNodes.value.length === 0) {
    return {
      series: [],
    };
  }

  // Calculate bounds for centering
  const xValues = filteredNodes.value.map((n) => n.x);
  const yValues = filteredNodes.value.map((n) => n.y);
  const minX = Math.min(...xValues);
  const maxX = Math.max(...xValues);
  const minY = Math.min(...yValues);
  const maxY = Math.max(...yValues);
  const rangeX = maxX - minX || 1;
  const rangeY = maxY - minY || 1;

  // Normalize positions to fit in chart area
  const padding = 80;
  const chartWidth = chartContainer.value?.clientWidth || 800;
  const chartHeight = chartContainer.value?.clientHeight || 700;
  const scaleX = (chartWidth - padding * 2) / rangeX;
  const scaleY = (chartHeight - padding * 2) / rangeY;
  const scale = Math.min(scaleX, scaleY);

  // When viewing single cluster, expand nodes more aggressively
  let expansionFactor = 1.0;
  if (selectedCluster.value !== null) {
    const nodeCount = filteredNodes.value.length;
    if (nodeCount <= 5) expansionFactor = 4.0;
    else if (nodeCount <= 10) expansionFactor = 3.0;
    else if (nodeCount <= 20) expansionFactor = 2.5;
    else if (nodeCount <= 35) expansionFactor = 2.0;
    else expansionFactor = 1.5;
  }

  // Center of filtered data
  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;

  // Build categories first - map cluster values to indices
  const uniqueClusters = [
    ...new Set(filteredNodes.value.map((n) => n.cluster)),
  ].sort((a, b) => a - b);
  const clusterToIndex = new Map();
  const categories = uniqueClusters.map((cluster, index) => {
    clusterToIndex.set(cluster, index);
    // Try to get topic label from clusterStats/topics
    const topicStat = clusterStats.value.find(s => (s.cluster_label === cluster || s.topic_id === cluster));
    const topicLabel = topicStat?.topic_label || topicStat?.label || null;
    
    return {
      name: cluster === -1 ? "Sin tópico" : (topicLabel || `Tópico ${cluster}`),
      itemStyle: {
        color: getClusterColor(cluster),
      },
    };
  });

  // Transform nodes for ECharts
  const graphNodes = filteredNodes.value.map((node) => {
    // Expand from center
    const expandedX = centerX + (node.x - centerX) * expansionFactor;
    const expandedY = centerY + (node.y - centerY) * expansionFactor;

    // Normalize to chart coordinates
    const normalizedX =
      ((expandedX - minX) / rangeX) * (chartWidth - padding * 2) + padding;
    const normalizedY =
      ((expandedY - minY) / rangeY) * (chartHeight - padding * 2) + padding;

    // Get the category index for this cluster
    const categoryIndex = clusterToIndex.get(node.cluster) ?? 0;

    return {
      id: String(node.id),
      name: node.title || `Doc ${node.id}`,
      x: useForceLayout.value ? undefined : normalizedX,
      y: useForceLayout.value ? undefined : normalizedY,
      value: [normalizedX, normalizedY],
      symbolSize: node.is_noise ? 12 : 18,
      category: categoryIndex, // Use index, not raw cluster value
      itemStyle: {
        color: getClusterColor(node.cluster),
        borderColor: "#ffffff",
        borderWidth: 2,
        shadowBlur: 8,
        shadowColor: "rgba(0, 0, 0, 0.25)",
      },
      label: {
        show: false,
      },
      emphasis: {
        scale: 1.5,
        focus: "adjacency",
        label: {
          show: true,
          formatter: (params) => {
            const title = params.data.name || "";
            return title.length > 25 ? title.substring(0, 25) + "..." : title;
          },
          position: "top",
          fontSize: 11,
          fontWeight: "bold",
          color: "#1F2937",
          backgroundColor: "rgba(255, 255, 255, 0.95)",
          padding: [6, 10],
          borderRadius: 6,
          borderColor: "#E5E7EB",
          borderWidth: 1,
        },
      },
      // Store original data for click handler
      originalData: node,
    };
  });

  // Create a set of valid node IDs for link validation
  const validNodeIds = new Set(graphNodes.map((n) => n.id));

  // Transform links for ECharts with better styling
  const graphLinks = showEdges.value
    ? filteredLinks.value
        .map((link) => {
          const sourceId = String(
            typeof link.source === "object" ? link.source.id : link.source
          );
          const targetId = String(
            typeof link.target === "object" ? link.target.id : link.target
          );
          const similarity = link.similarity || 0.5;

          // Only include links where both nodes exist
          if (!validNodeIds.has(sourceId) || !validNodeIds.has(targetId)) {
            return null;
          }

          return {
            source: sourceId,
            target: targetId,
            value: similarity,
            lineStyle: {
              color: getEdgeColor(similarity),
              width: 1.5, // Uniform width when not hovered
              opacity: 0.15, // Uniform low opacity when not hovered
              curveness: 0.15, // Slight curve to avoid overlap
              cap: "round",
              join: "round",
            },
            emphasis: {
              lineStyle: {
                color: getEdgeColor(similarity),
                width: getEdgeWidthEmphasis(similarity), // Show width differences on hover
                opacity: getEdgeOpacityEmphasis(similarity), // Show opacity differences on hover
                shadowBlur: 10,
                shadowColor: getEdgeColor(similarity),
              },
            },
          };
        })
        .filter((link) => link !== null)
    : [];

  console.log("📊 Building chart:", {
    nodes: graphNodes.length,
    links: graphLinks.length,
    categories: categories.length,
    selectedCluster: selectedCluster.value,
    clusterMapping: Object.fromEntries(clusterToIndex),
  });

  return {
    tooltip: {
      trigger: "item",
      enterable: true,
      confine: true,
      formatter: (params) => {
        if (params.dataType === "node") {
          const data = params.data.originalData || {};
          const clusterColor = getClusterColor(data.cluster);
          const topicLabel = data.topic_label || `Tópico ${data.cluster}`;
          const probability = data.probability ? `${(data.probability * 100).toFixed(1)}%` : null;
          
          return `
            <div style="padding: 10px; min-width: 220px;">
              <div style="font-weight: bold; font-size: 14px; margin-bottom: 8px; color: #1F2937;">
                ${data.title || "Documento"}
              </div>
              <div style="display: flex; align-items: center; margin-bottom: 6px;">
                <span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background: ${clusterColor}; margin-right: 8px;"></span>
                <span>${data.cluster === -1 ? "Sin tópico (outlier)" : topicLabel}</span>
              </div>
              ${probability ? `<div style="color: #6B7280; margin-bottom: 4px;">📊 Confianza: ${probability}</div>` : ""}
              ${
                data.case_number
                  ? `<div style="color: #6B7280; margin-bottom: 4px;">📁 ${data.case_number}</div>`
                  : ""
              }
              ${
                data.legal_area
                  ? `<div style="color: #6B7280;">⚖️ ${data.legal_area}</div>`
                  : ""
              }
            </div>
          `;
        } else if (params.dataType === "edge") {
          const similarity = params.data.value || 0;
          const percent = (similarity * 100).toFixed(1);
          const color = getEdgeColor(similarity);
          return `
            <div style="padding: 8px;">
              <div style="font-weight: bold; margin-bottom: 4px;">Conexión</div>
              <div style="display: flex; align-items: center;">
                <span style="display: inline-block; width: 30px; height: 4px; background: ${color}; border-radius: 2px; margin-right: 8px;"></span>
                <span>Similitud: ${percent}%</span>
              </div>
            </div>
          `;
        }
        return "";
      },
      backgroundColor: "rgba(255, 255, 255, 0.98)",
      borderColor: "#E5E7EB",
      borderWidth: 1,
      borderRadius: 8,
      textStyle: {
        color: "#374151",
        fontSize: 13,
      },
      extraCssText: "box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);",
    },
    legend: {
      show: false,
    },
    animationDuration: 600,
    animationEasingUpdate: "cubicInOut",
    series: [
      {
        type: "graph",
        layout: useForceLayout.value ? "force" : "none",
        data: graphNodes,
        links: graphLinks,
        categories: categories,
        roam: true,
        draggable: true,
        edgeSymbol: ["none", "none"],
        cursor: "pointer",
        force: useForceLayout.value
          ? {
              repulsion: 250,
              gravity: 0.08,
              edgeLength: [100, 250],
              friction: 0.5,
              layoutAnimation: true,
            }
          : undefined,
        scaleLimit: {
          min: 0.1,
          max: 10,
        },
        lineStyle: {
          curveness: 0.15,
          cap: "round",
        },
        emphasis: {
          focus: "adjacency",
          lineStyle: {
            width: 5,
          },
          itemStyle: {
            borderWidth: 3,
            borderColor: "#1F2937",
          },
        },
        blur: {
          itemStyle: {
            opacity: 0.15,
          },
          lineStyle: {
            opacity: 0.05,
          },
        },
      },
    ],
  };
};

// Update chart with current data
const updateChart = () => {
  if (!chartInstance) {
    console.warn("⚠️ Chart instance not ready");
    return;
  }

  const option = buildChartOption();
  chartInstance.setOption(option, {
    notMerge: true,
    lazyUpdate: true,
  });

  console.log("✅ Chart updated:", {
    nodes: filteredNodes.value.length,
    links: showEdges.value ? filteredLinks.value.length : 0,
    mode: useForceLayout.value ? "FORCE" : "FIXED",
  });
};

// Event handlers
const handleNodeClick = (params) => {
  if (params.dataType === "node" && params.data.originalData) {
    const nodeData = params.data.originalData;
    const fullNode = nodes.value.find((n) => n.id === nodeData.id);

    if (fullNode) {
      selectedDocument.value = fullNode;
      showDetails.value = true;

      // Find neighbors from links
      const neighbors = links.value
        .filter(
          (link) => link.source === fullNode.id || link.target === fullNode.id
        )
        .map((link) => {
          const neighborId =
            link.source === fullNode.id ? link.target : link.source;
          const neighbor = nodes.value.find((n) => n.id === neighborId);
          return neighbor ? { ...neighbor, similarity: link.similarity } : null;
        })
        .filter((n) => n !== null)
        .sort((a, b) => b.similarity - a.similarity)
        .slice(0, 10);

      selectedDocumentNeighbors.value = neighbors;
      console.log(
        `✅ Found ${neighbors.length} neighbors for document ${fullNode.id}`
      );
    }
  }
};

const handleNodeHover = (params) => {
  if (params.dataType !== "node" || !chartInstance) return;

  const nodeId = params.data.id;

  // Find all links connected to this node and update their styles
  const option = chartInstance.getOption();
  if (!option.series || !option.series[0] || !option.series[0].links) return;

  const updatedLinks = option.series[0].links.map((link) => {
    const isConnected = link.source === nodeId || link.target === nodeId;
    const similarity = link.value || 0.5;

    if (isConnected) {
      // Highlight connected edges with similarity-based styling
      return {
        ...link,
        lineStyle: {
          ...link.lineStyle,
          color: getEdgeColor(similarity),
          width: getEdgeWidthEmphasis(similarity),
          opacity: getEdgeOpacityEmphasis(similarity),
          shadowBlur: 12,
          shadowColor: getEdgeColor(similarity),
        },
      };
    } else {
      // Dim non-connected edges
      return {
        ...link,
        lineStyle: {
          ...link.lineStyle,
          color: getEdgeColor(similarity),
          width: 1,
          opacity: 0.15,
          shadowBlur: 0,
          shadowColor: "transparent",
        },
      };
    }
  });

  chartInstance.setOption({
    series: [
      {
        links: updatedLinks,
      },
    ],
  });
};

const handleNodeMouseOut = (params) => {
  if (!chartInstance) return;

  // Reset all edges to default uniform style
  const option = chartInstance.getOption();
  if (!option.series || !option.series[0] || !option.series[0].links) return;

  const resetLinks = option.series[0].links.map((link) => {
    const similarity = link.value || 0.5;
    return {
      ...link,
      lineStyle: {
        color: getEdgeColor(similarity),
        width: 1.5,
        opacity: 0.15,
        curveness: 0.15,
        cap: "round",
        join: "round",
        shadowBlur: 0,
        shadowColor: "transparent",
      },
    };
  });

  chartInstance.setOption({
    series: [
      {
        links: resetLinks,
      },
    ],
  });
};

// Filter by cluster
const filterByCluster = (clusterLabel) => {
  if (selectedCluster.value === clusterLabel) {
    clearFilter();
  } else {
    selectedCluster.value = clusterLabel;
    updateChart();

    // Center on cluster after a short delay
    setTimeout(() => {
      if (chartInstance) {
        chartInstance.dispatchAction({
          type: "restore",
        });
      }
    }, 300);
  }
};

const clearFilter = () => {
  selectedCluster.value = null;
  updateChart();
};

// Highlight node in graph when hovering document in list
// Replicates the same behavior as handleNodeHover for consistency
const highlightNodeInGraph = (nodeId) => {
  if (!chartInstance) return;

  const nodeIdStr = String(nodeId);

  // Dispatch highlight action to ECharts for node emphasis
  const nodeIndex = filteredNodes.value.findIndex((n) => n.id === nodeId);
  if (nodeIndex !== -1) {
    chartInstance.dispatchAction({
      type: "highlight",
      seriesIndex: 0,
      dataIndex: nodeIndex,
    });

    // Show tooltip
    chartInstance.dispatchAction({
      type: "showTip",
      seriesIndex: 0,
      dataIndex: nodeIndex,
    });
  }

  // Update edges with same logic as handleNodeHover
  const option = chartInstance.getOption();
  if (!option.series || !option.series[0] || !option.series[0].links) return;

  const updatedLinks = option.series[0].links.map((link) => {
    const isConnected = link.source === nodeIdStr || link.target === nodeIdStr;
    const similarity = link.value || 0.5;

    if (isConnected) {
      // Highlight connected edges with similarity-based styling
      return {
        ...link,
        lineStyle: {
          ...link.lineStyle,
          color: getEdgeColor(similarity),
          width: getEdgeWidthEmphasis(similarity),
          opacity: getEdgeOpacityEmphasis(similarity),
          shadowBlur: 12,
          shadowColor: getEdgeColor(similarity),
        },
      };
    } else {
      // Dim non-connected edges
      return {
        ...link,
        lineStyle: {
          ...link.lineStyle,
          color: getEdgeColor(similarity),
          width: 1,
          opacity: 0.05,
          shadowBlur: 0,
          shadowColor: "transparent",
        },
      };
    }
  });

  chartInstance.setOption({
    series: [
      {
        links: updatedLinks,
      },
    ],
  });
};

const unhighlightNodeInGraph = () => {
  if (!chartInstance) return;

  // Remove highlight
  chartInstance.dispatchAction({
    type: "downplay",
    seriesIndex: 0,
  });

  // Hide tooltip
  chartInstance.dispatchAction({
    type: "hideTip",
  });

  // Reset all edges to default uniform style (same as handleNodeMouseOut)
  const option = chartInstance.getOption();
  if (!option.series || !option.series[0] || !option.series[0].links) return;

  const resetLinks = option.series[0].links.map((link) => {
    const similarity = link.value || 0.5;
    return {
      ...link,
      lineStyle: {
        color: getEdgeColor(similarity),
        width: 1.5,
        opacity: 0.15,
        curveness: 0.15,
        cap: "round",
        join: "round",
        shadowBlur: 0,
        shadowColor: "transparent",
      },
    };
  });

  chartInstance.setOption({
    series: [
      {
        links: resetLinks,
      },
    ],
  });
};

// Zoom controls
const zoomIn = () => {
  if (!chartInstance) return;
  const option = chartInstance.getOption();
  if (option.series && option.series[0]) {
    const currentZoom = option.series[0].zoom || 1;
    chartInstance.setOption({
      series: [
        {
          zoom: currentZoom * 1.3,
        },
      ],
    });
  }
};

const zoomOut = () => {
  if (!chartInstance) return;
  const option = chartInstance.getOption();
  if (option.series && option.series[0]) {
    const currentZoom = option.series[0].zoom || 1;
    chartInstance.setOption({
      series: [
        {
          zoom: currentZoom / 1.3,
        },
      ],
    });
  }
};

const fitToView = () => {
  if (!chartInstance) return;
  chartInstance.dispatchAction({
    type: "restore",
  });
};

// Watch for changes
watch(showEdges, () => {
  updateChart();
});

watch(useForceLayout, () => {
  updateChart();
});

// Watch for selected cluster changes to update keywords chart
watch(selectedCluster, async (newVal) => {
  if (newVal !== null && selectedClusterKeywords.value.length > 0) {
    await nextTick();
    initKeywordsChart();
  } else if (keywordsChartInstance) {
    keywordsChartInstance.dispose();
    keywordsChartInstance = null;
  }
});

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

// Navigate to document chat/analysis view (opens in new tab to preserve state)
const openDocumentChat = (doc) => {
  if (!doc || !doc.id) {
    console.warn("No document ID available");
    return;
  }

  // Open in new tab to preserve current view state
  const url = `/document/${doc.id}`;
  window.open(url, "_blank");
};

// Lifecycle
onMounted(async () => {
  await loadClusters();

  // Setup resize observer
  await nextTick();
  if (chartContainer.value) {
    resizeObserver = new ResizeObserver(() => {
      if (chartInstance) {
        chartInstance.resize();
      }
    });
    resizeObserver.observe(chartContainer.value);
    console.log("✅ ResizeObserver attached");
  }
});

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose();
    chartInstance = null;
  }
  if (keywordsChartInstance) {
    keywordsChartInstance.dispose();
    keywordsChartInstance = null;
  }
  if (resizeObserver) {
    resizeObserver.disconnect();
  }
});
</script>

<style scoped>
.clusters-view-echarts {
  min-height: calc(100vh - 64px);
}

.gap-2 {
  gap: 8px;
}

.gap-3 {
  gap: 12px;
}

.chart-container {
  overflow: hidden;
  position: relative;
  background: linear-gradient(135deg, #fafafa 0%, #f5f5f5 100%);
}

.graph-card {
  height: 100%;
}

.sidebar-card {
  overflow: hidden;
}

/* Cluster list section with scroll */
.cluster-list-section {
  overflow-y: auto;
  transition: max-height 0.3s ease;
}

/* Documents list section */
.documents-list-section {
  overflow: hidden;
}

.cluster-list-item {
  cursor: pointer;
  transition: all 0.2s ease;
  border-left: 3px solid transparent;
}

.cluster-list-item:hover {
  background-color: rgba(25, 118, 210, 0.08);
}

.selected-cluster-item {
  background-color: rgba(25, 118, 210, 0.12) !important;
  border-left: 3px solid #1976d2 !important;
}

.cluster-doc-item {
  cursor: pointer;
  transition: background-color 0.2s;
}

.cluster-doc-item:hover {
  background-color: rgba(25, 118, 210, 0.08) !important;
}

.metric-item {
  padding: 4px 12px;
  border-radius: 8px;
  transition: background-color 0.2s;
}

.metric-item:hover {
  background-color: rgba(0, 0, 0, 0.04);
}

.gap-1 {
  gap: 4px;
}

/* Compact switch styling */
.compact-switch {
  transform: scale(0.9);
}

/* Fill height utility */
.fill-height {
  height: 100%;
}

/* Custom scrollbar for sidebar */
.cluster-list-section::-webkit-scrollbar,
.documents-list-section::-webkit-scrollbar {
  width: 6px;
}

.cluster-list-section::-webkit-scrollbar-track,
.documents-list-section::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.cluster-list-section::-webkit-scrollbar-thumb,
.documents-list-section::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.cluster-list-section::-webkit-scrollbar-thumb:hover,
.documents-list-section::-webkit-scrollbar-thumb:hover {
  background: #a1a1a1;
}
</style>
