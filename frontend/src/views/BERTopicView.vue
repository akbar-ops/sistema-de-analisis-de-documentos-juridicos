<template>
  <v-container
    fluid
    class="bertopic-view pa-4"
    style="max-width: 1920px; margin: 0 auto"
  >
    <!-- Header Row -->
    <v-row class="mb-3">
      <v-col cols="12">
        <div class="d-flex align-center justify-space-between">
          <div class="d-flex align-center">
            <v-icon size="large" class="mr-2" color="deep-purple"
              >mdi-tag-multiple</v-icon
            >
            <div>
              <h1 class="text-h5 font-weight-bold mb-0">
                Topic Modeling (BERTopic)
              </h1>
              <p class="text-caption text-grey mb-0">
                Descubrimiento automático de temas con keywords representativos
              </p>
            </div>
          </div>
          <div class="d-flex gap-2 align-center">
            <!-- Compact Stats -->
            <v-chip
              v-if="metadata"
              size="small"
              color="deep-purple"
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
              <v-icon start size="small">mdi-tag-multiple</v-icon>
              {{ metadata.topic_count }} tópicos
            </v-chip>
            <v-chip
              v-if="metadata && metadata.outlier_count > 0"
              size="small"
              color="warning"
              variant="tonal"
            >
              <v-icon start size="small">mdi-help-circle</v-icon>
              {{ metadata.outlier_count }} sin tópico
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
              color="deep-purple"
              size="small"
              prepend-icon="mdi-refresh"
              @click="regenerateTopics"
              :loading="regenerating"
              :disabled="regenerating"
            >
              {{ regenerating ? "Regenerando..." : "Regenerar" }}
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
          </div>
        </v-alert>
      </v-col>
    </v-row>

    <!-- Main Content -->
    <v-row>
      <!-- Scatter Plot Panel -->
      <v-col cols="12" lg="8" xl="9">
        <v-card elevation="2" class="graph-card">
          <v-card-title
            class="bg-grey-lighten-4 py-2 d-flex justify-space-between align-center"
          >
            <div class="d-flex align-center">
              <v-icon class="mr-2" size="small">mdi-chart-scatter-plot</v-icon>
              <span class="text-subtitle-1 font-weight-medium"
                >Mapa de Documentos por Tópico</span
              >
              <v-chip
                v-if="selectedTopic !== null"
                size="x-small"
                color="deep-purple"
                class="ml-2"
                closable
                @click:close="clearFilter"
              >
                Tópico {{ selectedTopic }}
              </v-chip>
            </div>
            <div class="d-flex gap-1 align-center">
              <v-switch
                v-model="showOutliers"
                density="compact"
                hide-details
                color="warning"
                class="compact-switch"
              >
                <template v-slot:label>
                  <span class="text-caption">Mostrar Outliers</span>
                </template>
              </v-switch>
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
                  color="deep-purple"
                  size="48"
                ></v-progress-circular>
                <div class="mt-3 text-subtitle-2">Cargando tópicos...</div>
              </div>
            </div>
            <div
              v-else-if="!metadata"
              class="d-flex align-center justify-center"
              style="height: 550px"
            >
              <div class="text-center">
                <v-icon size="64" color="grey-lighten-1">mdi-tag-off</v-icon>
                <div class="mt-3 text-subtitle-1 text-grey">
                  No hay modelo BERTopic disponible
                </div>
                <v-btn
                  color="deep-purple"
                  class="mt-4"
                  @click="regenerateTopics"
                  :loading="regenerating"
                >
                  Generar Modelo
                </v-btn>
              </div>
            </div>
            <div
              v-show="!loading && metadata"
              ref="chartContainer"
              class="chart-container"
              style="width: 100%; height: 550px"
            ></div>
          </v-card-text>
        </v-card>

        <!-- Keywords Barchart for selected topic -->
        <v-card v-if="selectedTopicData" elevation="1" class="mt-3">
          <v-card-title class="py-2 bg-deep-purple-lighten-5">
            <v-icon class="mr-2" size="small" color="deep-purple"
              >mdi-chart-bar</v-icon
            >
            <span class="text-subtitle-1">
              Keywords: {{ selectedTopicData.label }}
            </span>
            <v-spacer></v-spacer>
            <v-chip size="small" color="deep-purple" variant="tonal">
              {{ selectedTopicData.document_count }} docs
            </v-chip>
          </v-card-title>
          <v-card-text class="pa-3">
            <div
              ref="keywordsChartContainer"
              style="width: 100%; height: 200px"
            ></div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Topics Sidebar -->
      <v-col cols="12" lg="4" xl="3">
        <v-card
          elevation="2"
          class="sidebar-card"
          style="height: 620px; display: flex; flex-direction: column"
        >
          <!-- Topics List Header -->
          <v-card-title class="bg-grey-lighten-4 py-2 flex-shrink-0">
            <v-icon class="mr-2" size="small">mdi-tag-multiple</v-icon>
            <span class="text-subtitle-1 font-weight-medium">Tópicos</span>
            <v-spacer></v-spacer>
            <v-chip size="x-small" color="deep-purple" variant="tonal">
              {{ topics.length }} temas
            </v-chip>
          </v-card-title>

          <!-- Topics List -->
          <div class="topics-list-section flex-grow-1" style="overflow-y: auto">
            <v-list density="compact" class="pa-0">
              <v-list-item
                v-for="topic in sortedTopics"
                :key="topic.topic_id"
                @click="selectTopic(topic.topic_id)"
                class="topic-list-item"
                :class="{
                  'bg-deep-purple-lighten-5': selectedTopic === topic.topic_id,
                }"
              >
                <template v-slot:prepend>
                  <v-avatar
                    :color="
                      topic.is_outlier ? 'grey' : getTopicColor(topic.topic_id)
                    "
                    size="32"
                  >
                    <span class="text-white text-caption font-weight-bold">
                      {{ topic.is_outlier ? "?" : topic.topic_id }}
                    </span>
                  </v-avatar>
                </template>

                <v-list-item-title class="text-body-2 font-weight-medium">
                  {{
                    topic.is_outlier ? "Sin Tópico" : truncateLabel(topic.label)
                  }}
                </v-list-item-title>
                <v-list-item-subtitle class="text-caption">
                  <div class="d-flex flex-wrap gap-1 mt-1">
                    <v-chip
                      v-for="keyword in topic.keywords.slice(0, 3)"
                      :key="keyword"
                      size="x-small"
                      variant="outlined"
                      :color="
                        topic.is_outlier
                          ? 'grey'
                          : getTopicColor(topic.topic_id)
                      "
                    >
                      {{ keyword }}
                    </v-chip>
                  </div>
                </v-list-item-subtitle>

                <template v-slot:append>
                  <v-chip
                    size="x-small"
                    :color="topic.is_outlier ? 'grey' : 'deep-purple'"
                    variant="tonal"
                  >
                    {{ topic.document_count }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
          </div>

          <!-- Selected Topic Documents -->
          <template
            v-if="selectedTopic !== null && selectedTopicDocuments.length > 0"
          >
            <v-divider></v-divider>
            <div class="bg-grey-lighten-4 pa-2 flex-shrink-0">
              <div class="text-caption font-weight-medium">
                Documentos en Tópico {{ selectedTopic }} ({{
                  selectedTopicDocuments.length
                }})
              </div>
            </div>
            <div
              class="documents-list-section"
              style="max-height: 200px; overflow-y: auto"
            >
              <v-list density="compact" class="pa-0">
                <v-list-item
                  v-for="doc in selectedTopicDocuments.slice(0, 20)"
                  :key="doc.id"
                  @click="openDocumentDetails(doc)"
                  class="px-2"
                  density="compact"
                >
                  <v-list-item-title class="text-body-2 text-truncate">
                    {{ doc.title || "Documento sin título" }}
                  </v-list-item-title>
                  <v-list-item-subtitle class="text-caption">
                    <span v-if="doc.legal_area">⚖️ {{ doc.legal_area }}</span>
                    <span v-if="doc.probability" class="ml-2">
                      📊 {{ (doc.probability * 100).toFixed(0) }}%
                    </span>
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </div>
          </template>
        </v-card>
      </v-col>
    </v-row>

    <!-- Document Details Dialog -->
    <v-dialog v-model="showDetails" max-width="700">
      <v-card v-if="selectedDocument">
        <v-card-title class="bg-deep-purple text-white py-3">
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
                :color="getTopicColor(selectedDocument.topic_id)"
              >
                {{
                  selectedDocument.topic_label ||
                  `Tópico ${selectedDocument.topic_id}`
                }}
              </v-chip>
            </v-col>
            <v-col v-if="selectedDocument.probability" cols="6">
              <div class="text-caption text-grey">Probabilidad</div>
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

          <v-btn
            color="deep-purple"
            size="large"
            block
            class="mt-4"
            prepend-icon="mdi-chat-processing"
            @click="openDocumentChat(selectedDocument)"
          >
            Chat con Documento
            <v-icon end size="small">mdi-open-in-new</v-icon>
          </v-btn>
        </v-card-text>
        <v-card-actions class="px-4 pb-4">
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="showDetails = false">Cerrar</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from "vue";
import axios from "axios";
import * as echarts from "echarts";

// State
const loading = ref(false);
const regenerating = ref(false);
const regenerationProgress = ref(null);
const showOutliers = ref(true);
const showDetails = ref(false);
const selectedDocument = ref(null);
const selectedTopic = ref(null);

// Data from API
const nodes = ref([]);
const topics = ref([]);
const metadata = ref(null);

// ECharts refs
const chartContainer = ref(null);
const keywordsChartContainer = ref(null);
let chartInstance = null;
let keywordsChartInstance = null;
let resizeObserver = null;

// Vibrant color palette for topics
const topicColors = [
  "#7C3AED", // Vivid Purple
  "#2563EB", // Royal Blue
  "#DC2626", // Crimson Red
  "#059669", // Emerald
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

// Computed
const sortedTopics = computed(() => {
  return [...topics.value].sort((a, b) => {
    // Outliers last
    if (a.is_outlier && !b.is_outlier) return 1;
    if (!a.is_outlier && b.is_outlier) return -1;
    // Then by document count
    return b.document_count - a.document_count;
  });
});

const selectedTopicData = computed(() => {
  if (selectedTopic.value === null) return null;
  return topics.value.find((t) => t.topic_id === selectedTopic.value);
});

const selectedTopicDocuments = computed(() => {
  if (selectedTopic.value === null) return [];
  return nodes.value.filter((n) => n.topic_id === selectedTopic.value);
});

const filteredNodes = computed(() => {
  if (showOutliers.value) return nodes.value;
  return nodes.value.filter((n) => !n.is_outlier);
});

// Methods
const getTopicColor = (topicId) => {
  if (topicId === -1) return "#6B7280"; // Gray for outliers
  return topicColors[Math.abs(topicId) % topicColors.length];
};

const truncateLabel = (label, maxLength = 40) => {
  if (!label || label.length <= maxLength) return label;
  return label.substring(0, maxLength) + "...";
};

const formatDate = (dateStr) => {
  if (!dateStr) return "N/A";
  const date = new Date(dateStr);
  return date.toLocaleDateString("es-PE", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
};

// API Methods
const loadTopics = async () => {
  loading.value = true;
  try {
    const params = {
      include_outliers: showOutliers.value,
    };

    const response = await axios.get("/api/documents/bertopic_topics/", {
      params,
    });

    nodes.value = response.data.nodes || [];
    topics.value = response.data.topics || [];
    metadata.value = response.data.metadata;

    if (metadata.value) {
      await nextTick();
      initChart();
    }
  } catch (error) {
    console.error("Error loading BERTopic data:", error);
    nodes.value = [];
    topics.value = [];
    metadata.value = null;
  } finally {
    loading.value = false;
  }
};

const regenerateTopics = async () => {
  regenerating.value = true;
  regenerationProgress.value = {
    message: "Iniciando generación de modelo BERTopic OPTIMIZADO...",
    completed: false,
  };

  try {
    const response = await axios.post("/api/documents/regenerate_bertopic/", {
      max_documents: 1000,
      min_topic_size: 4, // 🔥 Optimizado: 4 en lugar de 5
    });

    regenerationProgress.value = {
      message: `Modelo en cola. Tiempo estimado: ${response.data.estimated_time_seconds}s`,
      completed: false,
    };

    // Poll for completion
    const taskId = response.data.task_id;
    if (taskId) {
      pollTaskStatus(taskId);
    } else {
      // No task ID, just reload after delay
      setTimeout(async () => {
        await loadTopics();
        regenerating.value = false;
        regenerationProgress.value = {
          message: "Modelo BERTopic generado correctamente",
          completed: true,
        };
      }, 5000);
    }
  } catch (error) {
    console.error("Error regenerating BERTopic:", error);
    regenerating.value = false;
    regenerationProgress.value = {
      message:
        "Error al generar modelo: " +
        (error.response?.data?.error || error.message),
      completed: true,
    };
  }
};

const pollTaskStatus = async (taskId) => {
  const maxAttempts = 60;
  let attempts = 0;

  const poll = async () => {
    attempts++;
    try {
      const response = await axios.get(`/api/tasks/${taskId}/`);
      const task = response.data;

      if (task.status === "SUCCESS" || task.status === "success") {
        regenerating.value = false;
        regenerationProgress.value = {
          message: "Modelo BERTopic generado correctamente",
          completed: true,
        };
        await loadTopics();
      } else if (task.status === "FAILURE" || task.status === "failure") {
        regenerating.value = false;
        regenerationProgress.value = {
          message:
            "Error al generar modelo: " + (task.error || "Unknown error"),
          completed: true,
        };
      } else if (attempts < maxAttempts) {
        setTimeout(poll, 2000);
      } else {
        regenerating.value = false;
        regenerationProgress.value = {
          message: "Tiempo de espera agotado. Recarga la página.",
          completed: true,
        };
      }
    } catch (error) {
      if (attempts < maxAttempts) {
        setTimeout(poll, 2000);
      }
    }
  };

  poll();
};

// Chart Methods
const initChart = () => {
  if (!chartContainer.value) return;

  if (chartInstance) {
    chartInstance.dispose();
  }

  chartInstance = echarts.init(chartContainer.value);
  updateChart();

  // Handle resize
  resizeObserver = new ResizeObserver(() => {
    chartInstance?.resize();
  });
  resizeObserver.observe(chartContainer.value);
};

const updateChart = () => {
  if (!chartInstance || !filteredNodes.value.length) return;

  // Group nodes by topic
  const seriesData = {};
  filteredNodes.value.forEach((node) => {
    const topicId = node.topic_id;
    if (!seriesData[topicId]) {
      seriesData[topicId] = [];
    }
    seriesData[topicId].push({
      value: [node.x, node.y],
      name: node.title,
      itemData: node,
    });
  });

  // Create series for each topic
  const series = Object.keys(seriesData).map((topicId) => {
    const tid = parseInt(topicId);
    const topicInfo = topics.value.find((t) => t.topic_id === tid);
    return {
      name: topicInfo ? topicInfo.label : `Tópico ${tid}`,
      type: "scatter",
      data: seriesData[topicId],
      symbolSize: tid === -1 ? 6 : 10,
      itemStyle: {
        color: getTopicColor(tid),
        opacity: tid === -1 ? 0.4 : 0.8,
      },
      emphasis: {
        scale: 1.5,
        itemStyle: {
          shadowBlur: 10,
          shadowColor: "rgba(0,0,0,0.3)",
        },
      },
    };
  });

  const option = {
    tooltip: {
      trigger: "item",
      formatter: (params) => {
        const data = params.data.itemData;
        return `
          <div style="max-width: 300px;">
            <strong>${data.title || "Sin título"}</strong><br/>
            <span style="color: ${getTopicColor(data.topic_id)}">●</span> 
            ${data.topic_label || `Tópico ${data.topic_id}`}<br/>
            ${data.legal_area ? `⚖️ ${data.legal_area}<br/>` : ""}
            ${
              data.probability
                ? `📊 Probabilidad: ${(data.probability * 100).toFixed(1)}%`
                : ""
            }
          </div>
        `;
      },
    },
    legend: {
      type: "scroll",
      orient: "horizontal",
      bottom: 0,
      data: series.map((s) => s.name),
      textStyle: { fontSize: 10 },
      pageIconSize: 12,
    },
    grid: {
      left: 40,
      right: 40,
      top: 20,
      bottom: 60,
    },
    xAxis: {
      type: "value",
      scale: true,
      axisLabel: { show: false },
      splitLine: { show: false },
    },
    yAxis: {
      type: "value",
      scale: true,
      axisLabel: { show: false },
      splitLine: { show: false },
    },
    series: series,
    dataZoom: [{ type: "inside", xAxisIndex: 0, yAxisIndex: 0 }],
  };

  chartInstance.setOption(option);

  // Handle click
  chartInstance.off("click");
  chartInstance.on("click", (params) => {
    if (params.data?.itemData) {
      openDocumentDetails(params.data.itemData);
    }
  });
};

const updateKeywordsChart = () => {
  if (!keywordsChartContainer.value || !selectedTopicData.value) return;

  if (keywordsChartInstance) {
    keywordsChartInstance.dispose();
  }

  keywordsChartInstance = echarts.init(keywordsChartContainer.value);

  const keywords = selectedTopicData.value.keywords.slice(0, 10);
  const weights = selectedTopicData.value.keyword_weights || {};

  const data = keywords
    .map((kw) => ({
      name: kw,
      value: weights[kw] || 0.5,
    }))
    .reverse(); // Reverse for horizontal bar

  const option = {
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
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
    },
    yAxis: {
      type: "category",
      data: data.map((d) => d.name),
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        type: "bar",
        data: data.map((d) => d.value),
        itemStyle: {
          color: getTopicColor(selectedTopicData.value.topic_id),
          borderRadius: [0, 4, 4, 0],
        },
        barWidth: "60%",
      },
    ],
  };

  keywordsChartInstance.setOption(option);
};

// Topic Selection - with chart centering like in clusters view
const selectTopic = (topicId) => {
  if (selectedTopic.value === topicId) {
    // Deselect - show all
    selectedTopic.value = null;
    updateChart();
    // Reset zoom
    setTimeout(() => {
      if (chartInstance) {
        chartInstance.dispatchAction({
          type: "restore",
        });
      }
    }, 100);
  } else {
    // Select topic
    selectedTopic.value = topicId;
    updateChartWithFocus(topicId);
  }
};

// Update chart with focus on specific topic
const updateChartWithFocus = (focusTopicId) => {
  if (!chartInstance || !nodes.value.length) return;

  // Get nodes for the focused topic
  const topicNodes = nodes.value.filter((n) => n.topic_id === focusTopicId);

  if (topicNodes.length === 0) {
    updateChart();
    return;
  }

  // Calculate bounds of the focused topic
  const xValues = topicNodes.map((n) => n.x);
  const yValues = topicNodes.map((n) => n.y);
  const minX = Math.min(...xValues);
  const maxX = Math.max(...xValues);
  const minY = Math.min(...yValues);
  const maxY = Math.max(...yValues);

  // Add padding
  const padX = (maxX - minX) * 0.2 || 1;
  const padY = (maxY - minY) * 0.2 || 1;

  // Build chart with all data but highlight the focused topic
  const seriesData = {};
  const displayNodes = showOutliers.value
    ? nodes.value
    : nodes.value.filter((n) => !n.is_outlier);

  displayNodes.forEach((node) => {
    const topicId = node.topic_id;
    if (!seriesData[topicId]) {
      seriesData[topicId] = [];
    }
    seriesData[topicId].push({
      value: [node.x, node.y],
      name: node.title,
      itemData: node,
    });
  });

  // Create series - dim non-focused topics
  const series = Object.keys(seriesData).map((topicId) => {
    const tid = parseInt(topicId);
    const topicInfo = topics.value.find((t) => t.topic_id === tid);
    const isFocused = tid === focusTopicId;

    return {
      name: topicInfo ? topicInfo.label : `Tópico ${tid}`,
      type: "scatter",
      data: seriesData[topicId],
      symbolSize: isFocused ? 14 : tid === -1 ? 4 : 6,
      itemStyle: {
        color: getTopicColor(tid),
        opacity: isFocused ? 1.0 : 0.15,
      },
      emphasis: {
        scale: 1.5,
        itemStyle: {
          shadowBlur: 10,
          shadowColor: "rgba(0,0,0,0.3)",
          opacity: 1.0,
        },
      },
      z: isFocused ? 10 : 1,
    };
  });

  const option = {
    tooltip: {
      trigger: "item",
      formatter: (params) => {
        const data = params.data.itemData;
        return `
          <div style="max-width: 300px;">
            <strong>${data.title || "Sin título"}</strong><br/>
            <span style="color: ${getTopicColor(data.topic_id)}">●</span> 
            ${data.topic_label || `Tópico ${data.topic_id}`}<br/>
            ${data.legal_area ? `⚖️ ${data.legal_area}<br/>` : ""}
            ${
              data.probability
                ? `📊 Probabilidad: ${(data.probability * 100).toFixed(1)}%`
                : ""
            }
          </div>
        `;
      },
    },
    legend: {
      type: "scroll",
      orient: "horizontal",
      bottom: 0,
      data: series.map((s) => s.name),
      textStyle: { fontSize: 10 },
      pageIconSize: 12,
    },
    grid: {
      left: 40,
      right: 40,
      top: 20,
      bottom: 60,
    },
    xAxis: {
      type: "value",
      scale: true,
      min: minX - padX,
      max: maxX + padX,
      axisLabel: { show: false },
      splitLine: { show: false },
    },
    yAxis: {
      type: "value",
      scale: true,
      min: minY - padY,
      max: maxY + padY,
      axisLabel: { show: false },
      splitLine: { show: false },
    },
    series: series,
    dataZoom: [{ type: "inside", xAxisIndex: 0, yAxisIndex: 0 }],
    animation: true,
    animationDuration: 500,
  };

  chartInstance.setOption(option, { notMerge: true });

  // Handle click
  chartInstance.off("click");
  chartInstance.on("click", (params) => {
    if (params.data?.itemData) {
      openDocumentDetails(params.data.itemData);
    }
  });
};

const clearFilter = () => {
  selectedTopic.value = null;
  updateChart();
  // Reset zoom
  setTimeout(() => {
    if (chartInstance) {
      chartInstance.dispatchAction({
        type: "restore",
      });
    }
  }, 100);
};

// Document Details
const openDocumentDetails = (doc) => {
  selectedDocument.value = doc;
  showDetails.value = true;
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
  showDetails.value = false;
};

// Zoom Controls
const zoomIn = () => {
  if (chartInstance) {
    chartInstance.dispatchAction({
      type: "dataZoom",
      start: 25,
      end: 75,
    });
  }
};

const zoomOut = () => {
  if (chartInstance) {
    chartInstance.dispatchAction({
      type: "dataZoom",
      start: 0,
      end: 100,
    });
  }
};

const fitToView = () => {
  if (chartInstance) {
    chartInstance.dispatchAction({
      type: "dataZoom",
      start: 0,
      end: 100,
    });
  }
};

// Watchers
watch(showOutliers, () => {
  loadTopics();
});

watch(selectedTopic, async () => {
  await nextTick();
  if (selectedTopicData.value) {
    updateKeywordsChart();
  }
});

// Lifecycle
onMounted(() => {
  loadTopics();
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
.bertopic-view {
  background-color: #f5f5f5;
  min-height: 100vh;
}

.graph-card,
.sidebar-card {
  border-radius: 12px !important;
}

.topic-list-item {
  cursor: pointer;
  transition: background-color 0.2s;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.topic-list-item:hover {
  background-color: rgba(124, 58, 237, 0.05);
}

.topics-list-section {
  overflow-y: auto;
  scrollbar-width: thin;
}

.topics-list-section::-webkit-scrollbar {
  width: 6px;
}

.topics-list-section::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.topics-list-section::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.compact-switch {
  transform: scale(0.85);
  margin-left: -8px;
}

.compact-switch :deep(.v-label) {
  font-size: 12px !important;
}
</style>
