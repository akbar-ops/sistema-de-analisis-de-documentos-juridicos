<template>
  <v-container fluid class="task-queue-container pa-4">
    <!-- Header -->
    <v-row>
      <v-col cols="12">
        <div class="d-flex align-center justify-space-between mb-4">
          <div>
            <p class="text-subtitle-1 text-medium-emphasis">
              Monitoreo de tareas de documentos en tiempo real
            </p>
          </div>
          <div class="d-flex align-center gap-2">
            <v-chip
              :color="tasksStats.active > 0 ? 'warning' : 'success'"
              size="large"
              variant="flat"
            >
              <v-icon start>
                {{
                  tasksStats.active > 0
                    ? "mdi-progress-clock"
                    : "mdi-check-circle"
                }}
              </v-icon>
              {{ tasksStats.active }} activas
            </v-chip>
          </div>
        </div>
      </v-col>
    </v-row>

    <!-- Stats Cards -->
    <v-row>
      <v-col cols="12" sm="6" md="3">
        <v-card variant="tonal" color="warning">
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon size="40" class="me-3">mdi-clock-outline</v-icon>
              <div>
                <div class="text-caption">Pendientes</div>
                <div class="text-h5 font-weight-bold">
                  {{ tasksStats.by_status?.pending || 0 }}
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
              <v-icon size="40" class="me-3">mdi-progress-clock</v-icon>
              <div>
                <div class="text-caption">En Proceso</div>
                <div class="text-h5 font-weight-bold">
                  {{
                    (tasksStats.by_status?.started || 0) +
                    (tasksStats.by_status?.progress || 0)
                  }}
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
              <v-icon size="40" class="me-3">mdi-check-circle</v-icon>
              <div>
                <div class="text-caption">Completadas</div>
                <div class="text-h5 font-weight-bold">
                  {{ tasksStats.by_status?.success || 0 }}
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card variant="tonal" color="error">
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon size="40" class="me-3">mdi-alert-circle</v-icon>
              <div>
                <div class="text-caption">Fallidas</div>
                <div class="text-h5 font-weight-bold">
                  {{ tasksStats.by_status?.failure || 0 }}
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Filters and Tabs -->
    <v-row>
      <v-col cols="12">
        <!-- Filters -->
        <v-card class="mb-4" variant="outlined">
          <v-card-text>
            <v-row dense>
              <v-col cols="12" md="4">
                <v-select
                  v-model="filters.status"
                  :items="statusOptions"
                  label="Filtrar por estado"
                  density="compact"
                  clearable
                  prepend-inner-icon="mdi-filter"
                  @update:model-value="applyFilters"
                />
              </v-col>
              <v-col cols="12" md="4">
                <v-select
                  v-model="filters.taskType"
                  :items="taskTypeOptions"
                  label="Filtrar por tipo"
                  density="compact"
                  clearable
                  prepend-inner-icon="mdi-file-document"
                  @update:model-value="applyFilters"
                />
              </v-col>
              <v-col cols="12" md="4">
                <v-text-field
                  v-model="filters.search"
                  label="Buscar documento"
                  density="compact"
                  clearable
                  prepend-inner-icon="mdi-magnify"
                  @update:model-value="applyFilters"
                />
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>

        <v-tabs v-model="activeTab" color="primary" class="mb-4">
          <v-tab value="active">
            <v-icon start>mdi-progress-clock</v-icon>
            Activas
            <v-badge
              v-if="filteredActiveTasks.length > 0"
              :content="filteredActiveTasks.length"
              color="warning"
              inline
              class="ml-2"
            />
          </v-tab>
          <v-tab value="completed">
            <v-icon start>mdi-check-all</v-icon>
            Historial
            <v-badge
              v-if="filteredCompletedTasks.length > 0"
              :content="filteredCompletedTasks.length"
              inline
              class="ml-2"
            />
          </v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
          <!-- Active Tasks Tab -->
          <v-window-item value="active">
            <v-card>
              <v-card-text class="pa-0">
                <!-- Loading -->
                <div v-if="loading" class="text-center py-8">
                  <v-progress-circular
                    indeterminate
                    size="64"
                    color="primary"
                  />
                  <p class="mt-4 text-medium-emphasis">Cargando tareas...</p>
                </div>

                <!-- Empty State -->
                <div
                  v-else-if="filteredActiveTasks.length === 0"
                  class="text-center py-12"
                >
                  <v-icon size="80" color="grey-lighten-1">
                    mdi-check-circle-outline
                  </v-icon>
                  <p class="text-h6 mt-4">No hay tareas activas</p>
                  <p class="text-caption text-medium-emphasis">
                    Todas las tareas han sido procesadas
                  </p>
                </div>

                <!-- Active Tasks List with Scroll -->
                <div
                  v-else
                  class="tasks-scroll-container"
                  :style="{ maxHeight: scrollHeight + 'px' }"
                >
                  <v-card
                    v-for="task in paginatedActiveTasks"
                    :key="task.task_id"
                    class="ma-3"
                    variant="outlined"
                  >
                    <v-card-text>
                      <div
                        class="d-flex align-start justify-space-between mb-2"
                      >
                        <div class="flex-grow-1">
                          <div class="d-flex align-center mb-1">
                            <v-chip
                              :color="getTaskTypeColor(task.task_type)"
                              size="small"
                              variant="flat"
                              class="me-2"
                            >
                              {{ task.task_type_display }}
                            </v-chip>
                            <v-chip
                              :color="getStatusColor(task.status)"
                              size="small"
                              variant="flat"
                            >
                              <v-icon
                                start
                                size="x-small"
                                :class="{
                                  rotate:
                                    task.status === 'started' ||
                                    task.status === 'progress',
                                }"
                              >
                                {{ getStatusIcon(task.status) }}
                              </v-icon>
                              {{ task.status_display }}
                            </v-chip>
                          </div>

                          <div class="text-subtitle-1 font-weight-medium">
                            {{ task.document_title }}
                          </div>

                          <div
                            v-if="
                              task.analysis_parts &&
                              task.analysis_parts.length > 0
                            "
                            class="text-caption text-medium-emphasis mt-1"
                          >
                            Análisis: {{ task.analysis_parts.join(", ") }}
                          </div>
                        </div>

                        <v-btn
                          v-if="task.status === 'pending'"
                          icon="mdi-close-circle"
                          size="small"
                          color="error"
                          variant="text"
                          @click="revokeTask(task.task_id)"
                        />
                      </div>

                      <!-- Progress Bar -->
                      <div class="mt-3">
                        <div
                          class="d-flex justify-space-between align-center mb-1"
                        >
                          <span class="text-caption">{{
                            task.progress_message || "Procesando..."
                          }}</span>
                          <span class="text-caption font-weight-bold"
                            >{{ task.progress_percent }}%</span
                          >
                        </div>
                        <v-progress-linear
                          :model-value="task.progress_percent"
                          :color="getStatusColor(task.status)"
                          height="8"
                          rounded
                        />
                      </div>

                      <!-- Task Info -->
                      <div
                        class="d-flex justify-space-between mt-2 text-caption text-medium-emphasis"
                      >
                        <span>
                          <v-icon size="x-small" class="me-1"
                            >mdi-clock-outline</v-icon
                          >
                          Creada: {{ formatDate(task.created_at) }}
                        </span>
                        <span v-if="task.started_at">
                          <v-icon size="x-small" class="me-1">mdi-play</v-icon>
                          Iniciada: {{ formatDate(task.started_at) }}
                        </span>
                      </div>
                    </v-card-text>
                  </v-card>
                </div>
              </v-card-text>

              <!-- Pagination for Active Tasks -->
              <v-card-actions
                v-if="filteredActiveTasks.length > activePage.itemsPerPage"
                class="justify-center"
              >
                <v-pagination
                  v-model="activePage.current"
                  :length="activePageCount"
                  :total-visible="7"
                  density="comfortable"
                />
              </v-card-actions>
            </v-card>
          </v-window-item>

          <!-- Completed Tasks Tab -->
          <v-window-item value="completed">
            <v-card>
              <v-card-text class="pa-0">
                <!-- Loading -->
                <div v-if="loading" class="text-center py-8">
                  <v-progress-circular
                    indeterminate
                    size="64"
                    color="primary"
                  />
                  <p class="mt-4 text-medium-emphasis">Cargando historial...</p>
                </div>

                <!-- Empty State -->
                <div
                  v-else-if="filteredCompletedTasks.length === 0"
                  class="text-center py-12"
                >
                  <v-icon size="80" color="grey-lighten-1">
                    mdi-history
                  </v-icon>
                  <p class="text-h6 mt-4">No hay tareas completadas</p>
                  <p class="text-caption text-medium-emphasis">
                    El historial aparecerá aquí
                  </p>
                </div>

                <!-- Completed Tasks List with Scroll -->
                <div
                  v-else
                  class="tasks-scroll-container"
                  :style="{ maxHeight: scrollHeight + 'px' }"
                >
                  <v-card
                    v-for="task in paginatedCompletedTasks"
                    :key="task.task_id"
                    class="ma-3"
                    variant="outlined"
                  >
                    <v-card-text>
                      <div class="d-flex align-start justify-space-between">
                        <div class="flex-grow-1">
                          <div class="d-flex align-center mb-1">
                            <v-chip
                              :color="getTaskTypeColor(task.task_type)"
                              size="small"
                              variant="flat"
                              class="me-2"
                            >
                              {{ task.task_type_display }}
                            </v-chip>
                            <v-chip
                              :color="getStatusColor(task.status)"
                              size="small"
                              variant="flat"
                            >
                              <v-icon start size="x-small">
                                {{ getStatusIcon(task.status) }}
                              </v-icon>
                              {{ task.status_display }}
                            </v-chip>
                          </div>

                          <div class="text-subtitle-1 font-weight-medium">
                            {{ task.document_title }}
                          </div>

                          <div
                            v-if="task.error_message"
                            class="text-caption text-error mt-1"
                          >
                            <v-icon size="x-small" class="me-1"
                              >mdi-alert</v-icon
                            >
                            {{ task.error_message }}
                          </div>
                        </div>
                      </div>

                      <!-- Task Info -->
                      <div
                        class="d-flex justify-space-between mt-2 text-caption text-medium-emphasis"
                      >
                        <span>
                          <v-icon size="x-small" class="me-1"
                            >mdi-clock-outline</v-icon
                          >
                          {{ formatDate(task.created_at) }}
                        </span>
                        <span v-if="task.duration_seconds">
                          <v-icon size="x-small" class="me-1"
                            >mdi-timer-outline</v-icon
                          >
                          {{ formatDuration(task.duration_seconds) }}
                        </span>
                      </div>
                    </v-card-text>
                  </v-card>
                </div>
              </v-card-text>

              <!-- Pagination for Completed Tasks -->
              <v-card-actions
                v-if="
                  filteredCompletedTasks.length > completedPage.itemsPerPage
                "
                class="justify-center"
              >
                <v-pagination
                  v-model="completedPage.current"
                  :length="completedPageCount"
                  :total-visible="7"
                  density="comfortable"
                />
              </v-card-actions>
            </v-card>
          </v-window-item>
        </v-window>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from "vue";
import axios from "axios";
import { formatDate } from "@/composables/useFormatting";

// ============================================================================
// STATE
// ============================================================================
const activeTab = ref("active");
const activeTasks = ref([]);
const completedTasks = ref([]);
const tasksStats = ref({
  total: 0,
  active: 0,
  completed: 0,
  by_status: {},
});
const loading = ref(false);
const pollingInterval = ref(null);

// Filters
const filters = ref({
  status: null,
  taskType: null,
  search: "",
});

// Pagination
const activePage = ref({
  current: 1,
  itemsPerPage: 10,
});

const completedPage = ref({
  current: 1,
  itemsPerPage: 10,
});

// Scroll height
const scrollHeight = ref(500);

// Filter options
const statusOptions = [
  { title: "Pendiente", value: "pending" },
  { title: "Iniciado", value: "started" },
  { title: "En Progreso", value: "progress" },
  { title: "Exitoso", value: "success" },
  { title: "Fallido", value: "failure" },
  { title: "Revocado", value: "revoked" },
];

const taskTypeOptions = [
  { title: "Carga", value: "upload" },
  { title: "Análisis de Metadatos", value: "analysis_metadata" },
  { title: "Generación de Título", value: "analysis_title" },
  { title: "Análisis de Resumen", value: "analysis_summary" },
  { title: "Análisis de Personas", value: "analysis_persons" },
  { title: "Análisis Completo", value: "analysis_full" },
];

// ============================================================================
// COMPUTED
// ============================================================================

// Filtered tasks
const filteredActiveTasks = computed(() => {
  return filterTasks(activeTasks.value);
});

const filteredCompletedTasks = computed(() => {
  return filterTasks(completedTasks.value);
});

// Pagination
const activePageCount = computed(() => {
  return Math.ceil(
    filteredActiveTasks.value.length / activePage.value.itemsPerPage
  );
});

const completedPageCount = computed(() => {
  return Math.ceil(
    filteredCompletedTasks.value.length / completedPage.value.itemsPerPage
  );
});

const paginatedActiveTasks = computed(() => {
  const start = (activePage.value.current - 1) * activePage.value.itemsPerPage;
  const end = start + activePage.value.itemsPerPage;
  return filteredActiveTasks.value.slice(start, end);
});

const paginatedCompletedTasks = computed(() => {
  const start =
    (completedPage.value.current - 1) * completedPage.value.itemsPerPage;
  const end = start + completedPage.value.itemsPerPage;
  return filteredCompletedTasks.value.slice(start, end);
});

// ============================================================================
// METHODS - FILTERS
// ============================================================================

function filterTasks(tasks) {
  let filtered = tasks;

  // Filter by status
  if (filters.value.status) {
    filtered = filtered.filter((task) => task.status === filters.value.status);
  }

  // Filter by task type
  if (filters.value.taskType) {
    filtered = filtered.filter(
      (task) => task.task_type === filters.value.taskType
    );
  }

  // Filter by search
  if (filters.value.search) {
    const searchLower = filters.value.search.toLowerCase();
    filtered = filtered.filter(
      (task) =>
        task.document_title?.toLowerCase().includes(searchLower) ||
        task.task_id?.toLowerCase().includes(searchLower)
    );
  }

  return filtered;
}

function applyFilters() {
  // Reset to first page when filters change
  activePage.value.current = 1;
  completedPage.value.current = 1;
}

// ============================================================================
// METHODS - API CALLS
// ============================================================================

async function fetchActiveTasks() {
  try {
    const response = await axios.get("http://localhost:8000/api/tasks/active/");
    activeTasks.value = response.data.tasks || [];
  } catch (error) {
    console.error("Error fetching active tasks:", error);
  }
}

async function fetchCompletedTasks() {
  try {
    const response = await axios.get(
      "http://localhost:8000/api/tasks/completed/",
      {
        params: { limit: 50 },
      }
    );
    completedTasks.value = response.data.tasks || [];
  } catch (error) {
    console.error("Error fetching completed tasks:", error);
  }
}

async function fetchStats() {
  try {
    const response = await axios.get("http://localhost:8000/api/tasks/stats/");
    tasksStats.value = response.data;
  } catch (error) {
    console.error("Error fetching stats:", error);
  }
}

async function revokeTask(taskId) {
  try {
    await axios.post(`http://localhost:8000/api/tasks/${taskId}/revoke/`);
    // Refresh data
    await fetchActiveTasks();
    await fetchStats();
  } catch (error) {
    console.error("Error revoking task:", error);
  }
}

async function refreshData() {
  await Promise.all([fetchActiveTasks(), fetchCompletedTasks(), fetchStats()]);
}

// ============================================================================
// METHODS - UTILITIES
// ============================================================================

function getStatusColor(status) {
  const colors = {
    pending: "warning",
    started: "info",
    progress: "info",
    success: "success",
    failure: "error",
    revoked: "grey",
  };
  return colors[status] || "grey";
}

function getStatusIcon(status) {
  const icons = {
    pending: "mdi-clock-outline",
    started: "mdi-loading",
    progress: "mdi-loading",
    success: "mdi-check-circle",
    failure: "mdi-alert-circle",
    revoked: "mdi-cancel",
  };
  return icons[status] || "mdi-help-circle";
}

function getTaskTypeColor(taskType) {
  const colors = {
    upload: "primary",
    analysis_metadata: "blue",
    analysis_title: "teal",
    analysis_summary: "purple",
    analysis_persons: "orange",
    analysis_full: "deep-purple",
  };
  return colors[taskType] || "grey";
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

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(async () => {
  loading.value = true;
  await refreshData();
  loading.value = false;

  // Start polling every 3 seconds
  pollingInterval.value = setInterval(() => {
    refreshData();
  }, 3000);
});

onUnmounted(() => {
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value);
  }
});
</script>

<style scoped lang="sass">
.task-queue-container
  max-width: 1400px
  margin: 0 auto

.tasks-scroll-container
  overflow-y: auto
  overflow-x: hidden
  padding-right: 4px

  /* Custom scrollbar */
  &::-webkit-scrollbar
    width: 8px

  &::-webkit-scrollbar-track
    background: rgba(0, 0, 0, 0.05)
    border-radius: 4px

  &::-webkit-scrollbar-thumb
    background: rgba(0, 0, 0, 0.2)
    border-radius: 4px

    &:hover
      background: rgba(0, 0, 0, 0.3)

.rotate
  animation: rotate 2s linear infinite

@keyframes rotate
  from
    transform: rotate(0deg)
  to
    transform: rotate(360deg)
</style>
