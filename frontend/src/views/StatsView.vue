<template>
  <v-container
    fluid
    class="stats-view pa-6"
    style="height: calc(100vh - 64px); overflow-y: auto"
  >
    <!-- Header -->
    <v-row class="mb-4">
      <v-col cols="12">
        <div class="d-flex align-center justify-space-between">
          <div>
            <h1 class="text-h4 font-weight-bold mb-2">
              📊 Panel de Estadísticas
            </h1>
            <p class="text-subtitle-1 text-medium-emphasis">
              Análisis completo del sistema de documentos y tareas
            </p>
          </div>
          <v-btn
            icon="mdi-refresh"
            variant="tonal"
            color="primary"
            @click="refreshAll"
            :loading="loading"
          />
        </div>
      </v-col>
    </v-row>

    <!-- Loading State -->
    <v-row v-if="loading && !docStats">
      <v-col cols="12" class="text-center py-12">
        <v-progress-circular indeterminate size="64" color="primary" />
        <p class="mt-4 text-medium-emphasis">Cargando estadísticas...</p>
      </v-col>
    </v-row>

    <!-- Stats Content -->
    <div v-else>
      <!-- Summary Cards -->
      <v-row>
        <v-col cols="12" sm="6" md="3">
          <v-card variant="tonal" color="primary">
            <v-card-text>
              <div class="d-flex align-center">
                <v-icon size="48" class="me-3"
                  >mdi-file-document-multiple</v-icon
                >
                <div>
                  <div class="text-caption">Total Documentos</div>
                  <div class="text-h4 font-weight-bold">
                    {{ docStats?.total_documents || 0 }}
                  </div>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" sm="6" md="3">
          <v-card variant="tonal" color="success">
            <v-card-text>
              <div class="d-flex align-center">
                <v-icon size="48" class="me-3">mdi-check-circle</v-icon>
                <div>
                  <div class="text-caption">Tareas Exitosas</div>
                  <div class="text-h4 font-weight-bold">
                    {{ taskStats?.by_status?.success || 0 }}
                  </div>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" sm="6" md="3">
          <v-card variant="tonal" color="warning">
            <v-card-text>
              <div class="d-flex align-center">
                <v-icon size="48" class="me-3">mdi-clock-outline</v-icon>
                <div>
                  <div class="text-caption">Tareas Activas</div>
                  <div class="text-h4 font-weight-bold">
                    {{ taskStats?.active || 0 }}
                  </div>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" sm="6" md="3">
          <v-card variant="tonal" color="info">
            <v-card-text>
              <div class="d-flex align-center">
                <v-icon size="48" class="me-3">mdi-file-chart</v-icon>
                <div>
                  <div class="text-caption">Total Páginas</div>
                  <div class="text-h4 font-weight-bold">
                    {{ formatNumber(docStats?.total_pages || 0) }}
                  </div>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Charts Row 1 -->
      <v-row>
        <!-- Task Status Distribution -->
        <v-col cols="12" md="6">
          <v-card>
            <v-card-title>Estado de Tareas</v-card-title>
            <v-card-text>
              <canvas ref="taskStatusChart"></canvas>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Task Types Distribution -->
        <v-col cols="12" md="6">
          <v-card>
            <v-card-title>Tipos de Tareas</v-card-title>
            <v-card-text>
              <canvas ref="taskTypeChart"></canvas>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Charts Row 2 -->
      <v-row>
        <!-- Documents by Day -->
        <v-col cols="12">
          <v-card>
            <v-card-title>Documentos Subidos (Últimos 7 días)</v-card-title>
            <v-card-text>
              <canvas ref="docsByDayChart"></canvas>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Charts Row 3 -->
      <v-row>
        <!-- Tasks by Hour -->
        <v-col cols="12" md="6">
          <v-card>
            <v-card-title>Tareas por Hora (Últimas 24h)</v-card-title>
            <v-card-text>
              <canvas ref="tasksByHourChart"></canvas>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Success Rate -->
        <v-col cols="12" md="6">
          <v-card>
            <v-card-title>Tasa de Éxito</v-card-title>
            <v-card-text>
              <canvas ref="successRateChart"></canvas>
              <div class="text-center mt-4">
                <div
                  class="text-h3 font-weight-bold"
                  :style="{ color: getSuccessRateColor() }"
                >
                  {{ taskStats?.success_rate || 0 }}%
                </div>
                <div class="text-caption text-medium-emphasis">
                  Tareas completadas exitosamente
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Charts Row 4 -->
      <v-row>
        <!-- Documents by Legal Area -->
        <v-col cols="12" md="6">
          <v-card>
            <v-card-title>Top 10 Áreas Legales</v-card-title>
            <v-card-text>
              <canvas ref="legalAreaChart"></canvas>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Documents by Type -->
        <v-col cols="12" md="6">
          <v-card>
            <v-card-title>Top 10 Tipos de Documento</v-card-title>
            <v-card-text>
              <canvas ref="docTypeChart"></canvas>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Additional Stats -->
      <v-row>
        <v-col cols="12" md="4">
          <v-card>
            <v-card-title>Estadísticas de Archivos</v-card-title>
            <v-card-text>
              <v-list density="compact">
                <v-list-item>
                  <template #prepend>
                    <v-icon>mdi-file-outline</v-icon>
                  </template>
                  <v-list-item-title>Promedio de Páginas</v-list-item-title>
                  <v-list-item-subtitle>
                    {{ docStats?.avg_pages || 0 }} páginas
                  </v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <template #prepend>
                    <v-icon>mdi-harddisk</v-icon>
                  </template>
                  <v-list-item-title>Tamaño Promedio</v-list-item-title>
                  <v-list-item-subtitle>
                    {{ docStats?.avg_size_mb || 0 }} MB
                  </v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <template #prepend>
                    <v-icon>mdi-database</v-icon>
                  </template>
                  <v-list-item-title>Almacenamiento Total</v-list-item-title>
                  <v-list-item-subtitle>
                    {{ formatSize(docStats?.total_size_mb || 0) }}
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" md="4">
          <v-card>
            <v-card-title>Análisis de Documentos</v-card-title>
            <v-card-text>
              <v-list density="compact">
                <v-list-item>
                  <template #prepend>
                    <v-icon color="success">mdi-check</v-icon>
                  </template>
                  <v-list-item-title>Metadatos Extraídos</v-list-item-title>
                  <v-list-item-subtitle>
                    {{ docStats?.by_analysis?.metadata_completed || 0 }}
                    documentos
                  </v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <template #prepend>
                    <v-icon color="success">mdi-check</v-icon>
                  </template>
                  <v-list-item-title>Resúmenes Generados</v-list-item-title>
                  <v-list-item-subtitle>
                    {{ docStats?.by_analysis?.summary_completed || 0 }}
                    documentos
                  </v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <template #prepend>
                    <v-icon color="success">mdi-check</v-icon>
                  </template>
                  <v-list-item-title>Personas Extraídas</v-list-item-title>
                  <v-list-item-subtitle>
                    {{ docStats?.docs_with_persons || 0 }} documentos
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" md="4">
          <v-card>
            <v-card-title>Rendimiento de Tareas</v-card-title>
            <v-card-text>
              <v-list density="compact">
                <v-list-item>
                  <template #prepend>
                    <v-icon>mdi-timer-outline</v-icon>
                  </template>
                  <v-list-item-title>Duración Promedio</v-list-item-title>
                  <v-list-item-subtitle>
                    {{ formatDuration(taskStats?.avg_duration_seconds) }}
                  </v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <template #prepend>
                    <v-icon>mdi-upload</v-icon>
                  </template>
                  <v-list-item-title>Subidas Recientes (24h)</v-list-item-title>
                  <v-list-item-subtitle>
                    {{ docStats?.recent_uploads_24h || 0 }} documentos
                  </v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <template #prepend>
                    <v-icon>mdi-chart-line</v-icon>
                  </template>
                  <v-list-item-title>Total Tareas</v-list-item-title>
                  <v-list-item-subtitle>
                    {{ taskStats?.total || 0 }} tareas
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </div>
  </v-container>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from "vue";
import axios from "axios";
import { Chart, registerables } from "chart.js";

// Register Chart.js components
Chart.register(...registerables);

// State
const loading = ref(false);
const docStats = ref(null);
const taskStats = ref(null);
const pollingInterval = ref(null);

// Chart refs
const taskStatusChart = ref(null);
const taskTypeChart = ref(null);
const docsByDayChart = ref(null);
const tasksByHourChart = ref(null);
const successRateChart = ref(null);
const legalAreaChart = ref(null);
const docTypeChart = ref(null);

// Chart instances
let chartInstances = {};

// Fetch data
async function fetchDocStats() {
  try {
    const response = await axios.get(
      "http://localhost:8000/api/documents/statistics/"
    );
    docStats.value = response.data;
  } catch (error) {
    console.error("Error fetching document stats:", error);
  }
}

async function fetchTaskStats() {
  try {
    const response = await axios.get("http://localhost:8000/api/tasks/stats/");
    taskStats.value = response.data;
  } catch (error) {
    console.error("Error fetching task stats:", error);
  }
}

async function refreshAll() {
  loading.value = true;
  await Promise.all([fetchDocStats(), fetchTaskStats()]);
  await nextTick();
  createCharts();
  loading.value = false;
}

// Create charts
function createCharts() {
  // Destroy existing charts
  Object.values(chartInstances).forEach((chart) => chart?.destroy());
  chartInstances = {};

  // Task Status Chart (Doughnut)
  if (taskStatusChart.value && taskStats.value) {
    const ctx = taskStatusChart.value.getContext("2d");
    chartInstances.taskStatus = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: [
          "Pendiente",
          "Iniciado",
          "En Progreso",
          "Exitoso",
          "Fallido",
          "Revocado",
        ],
        datasets: [
          {
            data: [
              taskStats.value.by_status.pending,
              taskStats.value.by_status.started,
              taskStats.value.by_status.progress,
              taskStats.value.by_status.success,
              taskStats.value.by_status.failure,
              taskStats.value.by_status.revoked,
            ],
            backgroundColor: [
              "#FFA726", // orange - pending
              "#42A5F5", // blue - started
              "#66BB6A", // green - progress
              "#26A69A", // teal - success
              "#EF5350", // red - failure
              "#78909C", // gray - revoked
            ],
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            position: "bottom",
          },
        },
      },
    });
  }

  // Task Type Chart (Pie)
  if (taskTypeChart.value && taskStats.value) {
    const ctx = taskTypeChart.value.getContext("2d");
    const typeLabels = {
      upload: "Carga",
      analysis_metadata: "Análisis Metadatos",
      analysis_summary: "Análisis Resumen",
      analysis_persons: "Análisis Personas",
      analysis_full: "Análisis Completo",
    };

    chartInstances.taskType = new Chart(ctx, {
      type: "pie",
      data: {
        labels: Object.keys(taskStats.value.by_type).map(
          (k) => typeLabels[k] || k
        ),
        datasets: [
          {
            data: Object.values(taskStats.value.by_type),
            backgroundColor: [
              "#7D1619", // primary
              "#981A1E", // carmine
              "#3B3A3B", // jet
              "#C74444", // accent
              "#999999", // gray
            ],
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            position: "bottom",
          },
        },
      },
    });
  }

  // Documents by Day Chart (Line)
  if (docsByDayChart.value && docStats.value?.by_day) {
    const ctx = docsByDayChart.value.getContext("2d");
    chartInstances.docsByDay = new Chart(ctx, {
      type: "line",
      data: {
        labels: docStats.value.by_day.map((d) => formatDate(d.day)),
        datasets: [
          {
            label: "Documentos",
            data: docStats.value.by_day.map((d) => d.count),
            borderColor: "#7D1619",
            backgroundColor: "rgba(125, 22, 25, 0.1)",
            fill: true,
            tension: 0.4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              stepSize: 1,
            },
          },
        },
      },
    });
  }

  // Tasks by Hour Chart (Bar)
  if (tasksByHourChart.value && taskStats.value?.by_hour) {
    const ctx = tasksByHourChart.value.getContext("2d");
    chartInstances.tasksByHour = new Chart(ctx, {
      type: "bar",
      data: {
        labels: taskStats.value.by_hour.map((h) => formatHour(h.hour)),
        datasets: [
          {
            label: "Tareas",
            data: taskStats.value.by_hour.map((h) => h.count),
            backgroundColor: "#981A1E",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              stepSize: 1,
            },
          },
        },
      },
    });
  }

  // Success Rate Chart (Doughnut)
  if (successRateChart.value && taskStats.value) {
    const ctx = successRateChart.value.getContext("2d");
    chartInstances.successRate = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: ["Exitoso", "Fallido"],
        datasets: [
          {
            data: [taskStats.value.success_rate, taskStats.value.failure_rate],
            backgroundColor: [
              "#26A69A", // success
              "#EF5350", // failure
            ],
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        cutout: "70%",
        plugins: {
          legend: {
            position: "bottom",
          },
        },
      },
    });
  }

  // Legal Area Chart (Horizontal Bar)
  if (legalAreaChart.value && docStats.value?.by_legal_area) {
    const ctx = legalAreaChart.value.getContext("2d");
    chartInstances.legalArea = new Chart(ctx, {
      type: "bar",
      data: {
        labels: docStats.value.by_legal_area.map(
          (a) => a.legal_area__name || "Sin área"
        ),
        datasets: [
          {
            label: "Documentos",
            data: docStats.value.by_legal_area.map((a) => a.count),
            backgroundColor: "#7D1619",
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: true,
        scales: {
          x: {
            beginAtZero: true,
            ticks: {
              stepSize: 1,
            },
          },
        },
      },
    });
  }

  // Doc Type Chart (Horizontal Bar)
  if (docTypeChart.value && docStats.value?.by_doc_type) {
    const ctx = docTypeChart.value.getContext("2d");
    chartInstances.docType = new Chart(ctx, {
      type: "bar",
      data: {
        labels: docStats.value.by_doc_type.map(
          (t) => t.doc_type__name || "Sin tipo"
        ),
        datasets: [
          {
            label: "Documentos",
            data: docStats.value.by_doc_type.map((t) => t.count),
            backgroundColor: "#981A1E",
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: true,
        scales: {
          x: {
            beginAtZero: true,
            ticks: {
              stepSize: 1,
            },
          },
        },
      },
    });
  }
}

// Utility functions
function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleDateString("es-PE", { day: "2-digit", month: "2-digit" });
}

function formatHour(dateString) {
  const date = new Date(dateString);
  return date.toLocaleTimeString("es-PE", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatNumber(num) {
  return new Intl.NumberFormat("es-PE").format(num);
}

function formatSize(mb) {
  if (mb >= 1024) {
    return (mb / 1024).toFixed(2) + " GB";
  }
  return mb.toFixed(2) + " MB";
}

function formatDuration(seconds) {
  if (!seconds) return "—";

  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);

  return `${minutes}m ${remainingSeconds}s`;
}

function getSuccessRateColor() {
  const rate = taskStats.value?.success_rate || 0;
  if (rate >= 90) return "#26A69A"; // green
  if (rate >= 70) return "#FFA726"; // orange
  return "#EF5350"; // red
}

// Lifecycle
onMounted(async () => {
  await refreshAll();

  // Start polling every 30 seconds
  pollingInterval.value = setInterval(() => {
    refreshAll();
  }, 30000);
});

onUnmounted(() => {
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value);
  }

  // Destroy all charts
  Object.values(chartInstances).forEach((chart) => chart?.destroy());
});
</script>

<style scoped>
.stats-view {
  max-width: 1800px;
  margin: 0 auto;
}

/* Custom scrollbar con colores PJ */
.stats-view::-webkit-scrollbar {
  width: 8px;
}

.stats-view::-webkit-scrollbar-track {
  background: #f2f2f2;
  border-radius: 4px;
}

.stats-view::-webkit-scrollbar-thumb {
  background: #736d5d;
  border-radius: 4px;
  transition: background 0.3s ease;
}

.stats-view::-webkit-scrollbar-thumb:hover {
  background: #8c0d0d;
}

canvas {
  max-height: 300px;
}
</style>
