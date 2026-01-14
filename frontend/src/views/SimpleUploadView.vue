<template>
  <div class="simple-upload-view">
    <!-- Main scrolleable content wrapper -->
    <div class="view-content">
      <!-- STEP 1: Upload Screen -->
      <div v-if="currentStep === 'upload'" class="upload-step">
        <v-container>
          <v-row justify="center">
            <v-col cols="12" md="8" lg="6">
              <div class="text-center mb-8">
                <h1
                  class="text-h3 font-weight-bold mb-3"
                  style="color: #731414"
                >
                  Análisis de Documentos Legales
                </h1>
                <p class="text-h6 text-grey-darken-1">
                  Sube tu documento y obtén análisis automático
                </p>
              </div>

              <v-card elevation="8" class="upload-card">
                <v-card-text class="pa-8">
                  <!-- Drop Zone -->
                  <div
                    class="drop-zone"
                    :class="{
                      'drag-over': isDragOver,
                      'has-file': selectedFile !== null,
                    }"
                    @drop.prevent="handleDrop"
                    @dragover.prevent="isDragOver = true"
                    @dragleave.prevent="isDragOver = false"
                    @click="triggerFileInput"
                  >
                    <v-icon
                      :size="selectedFile ? 80 : 120"
                      :color="selectedFile ? 'success' : 'primary'"
                      class="mb-4"
                    >
                      {{
                        selectedFile
                          ? "mdi-file-check-outline"
                          : "mdi-file-upload-outline"
                      }}
                    </v-icon>

                    <template v-if="!selectedFile">
                      <h3 class="text-h5 mb-2">Arrastra tu documento aquí</h3>
                      <p class="text-body-1 text-grey-darken-1 mb-4">
                        o haz clic para seleccionar
                      </p>
                      <v-chip color="primary" variant="outlined" size="large">
                        PDF, DOCX, DOC, TXT - Máx. 50MB
                      </v-chip>
                    </template>

                    <template v-else>
                      <h3 class="text-h5 mb-2 text-success">
                        {{ selectedFile.name }}
                      </h3>
                      <p class="text-body-1 text-grey-darken-1 mb-4">
                        {{ formatFileSize(selectedFile.size) }}
                      </p>
                      <v-btn
                        color="error"
                        variant="outlined"
                        @click.stop="clearFile"
                      >
                        <v-icon start>mdi-close</v-icon>
                        Cambiar archivo
                      </v-btn>
                    </template>
                  </div>

                  <input
                    ref="fileInput"
                    type="file"
                    accept=".pdf,.docx,.doc,.txt"
                    style="display: none"
                    @change="handleFileSelect"
                  />

                  <!-- Upload Button -->
                  <v-btn
                    v-if="selectedFile"
                    color="primary"
                    size="x-large"
                    block
                    class="mt-6"
                    elevation="4"
                    :loading="isUploading"
                    @click="uploadDocument"
                  >
                    <v-icon start>mdi-cloud-upload</v-icon>
                    Analizar Documento
                  </v-btn>

                  <!-- Error Message -->
                  <v-alert
                    v-if="uploadError"
                    type="error"
                    variant="tonal"
                    class="mt-4"
                    closable
                    @click:close="uploadError = null"
                  >
                    {{ uploadError }}
                  </v-alert>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </v-container>
      </div>

      <!-- STEP 2: Processing Screen -->
      <div v-if="currentStep === 'processing'" class="processing-step">
        <v-container>
          <v-row justify="center">
            <v-col cols="12" md="8" lg="6">
              <v-card elevation="8" class="processing-card">
                <v-card-text class="pa-8 text-center">
                  <v-progress-circular
                    :model-value="processingProgress"
                    :size="150"
                    :width="15"
                    color="primary"
                    class="mb-6"
                  >
                    <span class="text-h4 font-weight-bold">
                      {{ processingProgress }}%
                    </span>
                  </v-progress-circular>

                  <h2
                    class="text-h4 font-weight-bold mb-4"
                    style="color: #731414"
                  >
                    Analizando Documento
                  </h2>

                  <p class="text-h6 text-grey-darken-1 mb-6">
                    {{ processingMessage }}
                  </p>

                  <!-- Processing Steps Indicator -->
                  <v-stepper
                    v-model="processingStepIndex"
                    alt-labels
                    elevation="0"
                    class="mb-4"
                  >
                    <v-stepper-header>
                      <v-stepper-item
                        v-for="(step, index) in processingSteps"
                        :key="index"
                        :value="index + 1"
                        :complete="processingStepIndex > index + 1"
                        :color="
                          processingStepIndex === index + 1
                            ? 'primary'
                            : 'success'
                        "
                      >
                        <template #icon>
                          <v-icon v-if="processingStepIndex > index + 1">
                            mdi-check
                          </v-icon>
                          <v-progress-circular
                            v-else-if="processingStepIndex === index + 1"
                            indeterminate
                            size="24"
                            width="3"
                          />
                          <span v-else>{{ index + 1 }}</span>
                        </template>
                        <template #title>
                          <div class="text-caption">{{ step.title }}</div>
                        </template>
                      </v-stepper-item>
                    </v-stepper-header>
                  </v-stepper>

                  <!-- Fun Facts While Waiting -->
                  <v-card variant="tonal" color="primary" class="mt-6">
                    <v-card-text>
                      <div class="d-flex align-center">
                        <v-icon size="40" class="me-3"
                          >mdi-lightbulb-outline</v-icon
                        >
                        <div class="text-left">
                          <p class="text-subtitle-2 font-weight-bold mb-1">
                            ¿Sabías que...?
                          </p>
                          <p class="text-body-2">{{ currentFunFact }}</p>
                        </div>
                      </div>
                    </v-card-text>
                  </v-card>

                  <!-- Active Users Processing -->
                  <div v-if="activeProcessingCount > 1" class="mt-4">
                    <v-chip color="info" variant="outlined">
                      <v-icon start>mdi-account-multiple</v-icon>
                      {{ activeProcessingCount }} documentos en proceso
                    </v-chip>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </v-container>
      </div>

      <!-- STEP 3: Results Screen -->
      <div v-if="currentStep === 'results'" class="results-step">
        <!-- Centered Container -->
        <v-container class="results-container">
          <!-- Navigation Bar (always visible when viewing existing document) -->
          <div v-if="cameFromExternalView" class="navigation-bar mb-4">
            <!-- Left: Close Tab Button -->
            <v-tooltip location="bottom" text="Cerrar pestaña (ESC)">
              <template v-slot:activator="{ props }">
                <v-btn
                  v-bind="props"
                  variant="tonal"
                  color="grey-darken-1"
                  size="small"
                  @click="goBack"
                  class="close-btn"
                >
                  <v-icon size="18">mdi-close</v-icon>
                  <span class="ms-1 d-none d-sm-inline">Cerrar</span>
                </v-btn>
              </template>
            </v-tooltip>

            <v-divider vertical class="mx-3" />

            <!-- Center: History Navigation -->
            <div class="history-nav d-flex align-center">
              <v-tooltip location="bottom" text="Documento anterior (Alt+←)">
                <template v-slot:activator="{ props }">
                  <v-btn
                    v-bind="props"
                    icon
                    variant="text"
                    size="small"
                    :disabled="!canGoBack"
                    @click="navigateHistoryBack"
                    class="nav-btn"
                  >
                    <v-icon>mdi-chevron-left</v-icon>
                  </v-btn>
                </template>
              </v-tooltip>

              <!-- History Position Indicator -->
              <v-chip
                size="small"
                variant="outlined"
                color="primary"
                class="mx-2 history-indicator"
              >
                <v-icon start size="14">mdi-history</v-icon>
                {{ currentHistoryPosition }} / {{ totalHistoryItems }}
                <span class="text-caption text-grey-darken-1 ms-1"
                  >(máx {{ MAX_HISTORY_SIZE }})</span
                >
              </v-chip>

              <v-tooltip location="bottom" text="Documento siguiente (Alt+→)">
                <template v-slot:activator="{ props }">
                  <v-btn
                    v-bind="props"
                    icon
                    variant="text"
                    size="small"
                    :disabled="!canGoForward"
                    @click="navigateHistoryForward"
                    class="nav-btn"
                  >
                    <v-icon>mdi-chevron-right</v-icon>
                  </v-btn>
                </template>
              </v-tooltip>
            </div>

            <v-spacer />

            <!-- Right: Current Document Title -->
            <div class="current-doc-title text-truncate">
              <v-icon size="16" color="primary" class="me-1"
                >mdi-file-document</v-icon
              >
              <span class="text-body-2 font-weight-medium">
                {{ processedDocument?.title || "Documento" }}
              </span>
            </div>
          </div>

          <!-- Header with Actions -->
          <div class="results-header mb-6">
            <div
              class="d-flex align-center justify-space-between flex-wrap ga-3"
            >
              <div class="header-info">
                <div class="d-flex align-center ga-3 mb-2">
                  <v-icon size="32" color="#731414"
                    >mdi-file-document-check</v-icon
                  >
                  <div>
                    <h2
                      class="text-h5 text-md-h4 font-weight-bold"
                      style="color: #731414"
                    >
                      {{
                        isViewingExistingDocument
                          ? "Vista de Documento"
                          : "Análisis Completado"
                      }}
                    </h2>
                    <p
                      class="text-body-2 text-grey-darken-1 text-truncate"
                      style="max-width: 400px"
                    >
                      {{ processedDocument?.title || "Documento analizado" }}
                    </p>
                  </div>
                </div>
                <!-- Document metadata chips -->
                <div class="d-flex align-center flex-wrap ga-2 mt-2">
                  <v-chip
                    v-if="processedDocument?.extension"
                    size="small"
                    variant="tonal"
                    color="primary"
                  >
                    <v-icon start size="14">mdi-file</v-icon>
                    {{ processedDocument.extension.toUpperCase() }}
                  </v-chip>
                  <v-chip
                    v-if="processedDocument?.document_type_name"
                    size="small"
                    variant="tonal"
                    color="secondary"
                  >
                    <v-icon start size="14">mdi-tag</v-icon>
                    {{ processedDocument.document_type_name }}
                  </v-chip>
                  <v-chip
                    v-if="similarDocuments.length > 0"
                    size="small"
                    variant="tonal"
                    color="success"
                  >
                    <v-icon start size="14">mdi-file-multiple</v-icon>
                    {{ similarDocuments.length }} similares
                  </v-chip>
                </div>
              </div>
              <div class="header-actions d-flex ga-2">
                <!-- Manual AI Analysis Button (when no summary exists) -->
                <v-btn
                  v-if="!processedDocument?.summary && !generatingSummary"
                  color="secondary"
                  variant="tonal"
                  @click="generateAISummary"
                >
                  <v-icon start>mdi-robot</v-icon>
                  Generar Resumen IA
                </v-btn>
                <v-btn
                  v-if="generatingSummary"
                  color="secondary"
                  variant="tonal"
                  disabled
                >
                  <v-progress-circular
                    indeterminate
                    size="18"
                    width="2"
                    class="me-2"
                  />
                  Generando...
                </v-btn>
                <v-btn
                  color="primary"
                  variant="outlined"
                  @click="resetToUpload"
                >
                  <v-icon start>mdi-plus</v-icon>
                  Analizar Otro
                </v-btn>
              </div>
            </div>
          </div>

          <!-- Main Content Grid (60/40 split) -->
          <v-row class="results-grid">
            <!-- Left Side: Document Viewer (60%) -->
            <v-col cols="12" lg="7" class="document-column">
              <v-card elevation="4" class="document-viewer-card">
                <v-card-title class="d-flex align-center bg-grey-lighten-3">
                  <v-icon class="me-2" color="primary"
                    >mdi-file-document</v-icon
                  >
                  <span class="font-weight-bold">Documento Original</span>
                  <v-spacer />
                  <v-btn-group variant="outlined" density="compact">
                    <v-btn
                      v-if="processedDocument?.file_path"
                      size="small"
                      @click="openDocumentNewTab"
                    >
                      <v-icon size="small">mdi-open-in-new</v-icon>
                    </v-btn>
                    <v-btn
                      v-if="processedDocument?.file_path"
                      size="small"
                      @click="downloadDocument"
                    >
                      <v-icon size="small">mdi-download</v-icon>
                    </v-btn>
                  </v-btn-group>
                </v-card-title>

                <v-card-text class="pa-0">
                  <div class="document-preview">
                    <!-- Try iframe first, show error message if blocked -->
                    <div
                      v-if="documentUrl && !iframeError"
                      class="iframe-container"
                    >
                      <iframe
                        :src="documentUrl"
                        class="document-iframe"
                        frameborder="0"
                        @error="handleIframeError"
                      />
                    </div>

                    <!-- Fallback: Download button if iframe blocked -->
                    <div v-else-if="iframeError" class="preview-placeholder">
                      <v-icon size="100" color="primary">
                        mdi-file-pdf-box
                      </v-icon>
                      <p class="text-h6 text-grey-darken-2 mt-4">
                        Vista previa no disponible
                      </p>
                      <p class="text-body-2 text-grey mt-2 mb-4">
                        El navegador bloqueó la vista previa del PDF
                      </p>
                      <v-btn
                        color="primary"
                        size="large"
                        @click="downloadDocument"
                      >
                        <v-icon start>mdi-download</v-icon>
                        Descargar Documento
                      </v-btn>
                      <v-btn
                        color="primary"
                        variant="outlined"
                        size="large"
                        class="mt-3"
                        @click="openDocumentNewTab"
                      >
                        <v-icon start>mdi-open-in-new</v-icon>
                        Abrir en Nueva Pestaña
                      </v-btn>
                    </div>

                    <!-- No document available -->
                    <div v-else class="preview-placeholder">
                      <v-icon size="100" color="grey-lighten-1">
                        mdi-file-document-outline
                      </v-icon>
                      <p class="text-h6 text-grey mt-4">
                        Vista previa no disponible
                      </p>
                    </div>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>

            <!-- Right Side: Chat Analysis Panel (40%) -->
            <v-col cols="12" lg="5" class="analysis-column">
              <ChatAnalysisPanel
                v-if="processedDocument"
                :document="processedDocument"
                :similar-documents="similarDocuments"
                :loading-similar="loadingSimilar"
                :topic-keywords="topicKeywords"
                :loading-keywords="loadingKeywords"
                :show-metadata="true"
                @select-similar="viewSimilarDocument"
              />
            </v-col>
          </v-row>
        </v-container>
      </div>
    </div>
    <!-- Close view-content -->
  </div>
  <!-- Close simple-upload-view -->
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import axios from "axios";
import ChatAnalysisPanel from "../components/ChatAnalysisPanel.vue";

const route = useRoute();
const router = useRouter();

// Step control: 'upload' -> 'processing' -> 'results'
const currentStep = ref("upload");

const selectedFile = ref(null);
const isDragOver = ref(false);
const isUploading = ref(false);
const uploadError = ref(null);
const fileInput = ref(null);

// Processing state
const processingProgress = ref(0);
const processingMessage = ref("Iniciando análisis...");
const processingStepIndex = ref(1);
const documentId = ref(null);
const taskId = ref(null);
const pollingInterval = ref(null);
const activeProcessingCount = ref(1);

// Results state
const processedDocument = ref(null);
const similarDocuments = ref([]);
const loadingSimilar = ref(false);
const topicKeywords = ref(null);
const loadingKeywords = ref(false);
const generatingSummary = ref(false);
const documentUrl = ref(null);
const iframeError = ref(false);

// Processing steps for visual feedback (simplified - no Ollama)
const processingSteps = [
  { title: "Extrayendo texto", value: 0 },
  { title: "Creando chunks", value: 30 },
  { title: "Generando embeddings", value: 60 },
  { title: "Finalizando", value: 90 },
];

// Fun facts to show while processing
const funFacts = [
  "El sistema utiliza inteligencia artificial para comprender el contexto legal de los documentos.",
  "Nuestro análisis puede identificar partes involucradas, fechas clave y decisiones judiciales.",
  "La búsqueda de documentos similares utiliza algoritmos de similitud semántica avanzados.",
  "Los embeddings vectoriales nos permiten encontrar documentos con contenido similar aunque usen palabras diferentes.",
  "Los keywords del cluster ayudan a entender el tema principal del documento.",
  "Puedes chatear con el documento para hacer preguntas específicas sobre su contenido.",
];

const currentFunFact = ref(funFacts[0]);
let funFactInterval = null;

// Track if we came from another view (for back navigation)
const cameFromExternalView = ref(false);
const previousRoute = ref(null);

// Document navigation history (max 15 documents)
const MAX_HISTORY_SIZE = 15;
const documentHistory = ref([]); // Array of { id, title, timestamp }
const historyIndex = ref(-1); // Current position in history
const isNavigatingHistory = ref(false); // Flag to prevent adding to history when navigating

/* ========== COMPUTED ========== */

// Check if viewing an existing document (not freshly uploaded)
const isViewingExistingDocument = computed(() => {
  return !!route.params.id;
});

// Navigation computed properties
const canGoBack = computed(() => historyIndex.value > 0);
const canGoForward = computed(
  () => historyIndex.value < documentHistory.value.length - 1
);
const currentHistoryPosition = computed(() => historyIndex.value + 1);
const totalHistoryItems = computed(() => documentHistory.value.length);

/* ========== FILE HANDLING ========== */
function triggerFileInput() {
  fileInput.value?.click();
}

function handleFileSelect(event) {
  const file = event.target.files[0];
  if (file) {
    validateAndSetFile(file);
  }
}

function handleDrop(event) {
  isDragOver.value = false;
  const file = event.dataTransfer.files[0];
  if (file) {
    validateAndSetFile(file);
  }
}

function validateAndSetFile(file) {
  // Validate file type
  const allowedTypes = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain",
  ];

  if (!allowedTypes.includes(file.type)) {
    uploadError.value =
      "Tipo de archivo no soportado. Por favor sube PDF, DOCX, DOC o TXT.";
    return;
  }

  // Validate file size (50MB max)
  const maxSize = 50 * 1024 * 1024;
  if (file.size > maxSize) {
    uploadError.value = "El archivo es demasiado grande. Máximo 50MB.";
    return;
  }

  selectedFile.value = file;
  uploadError.value = null;
}

function clearFile() {
  selectedFile.value = null;
  if (fileInput.value) {
    fileInput.value.value = "";
  }
}

function formatFileSize(bytes) {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
}

/* ========== UPLOAD & PROCESSING ========== */
async function uploadDocument() {
  if (!selectedFile.value) return;

  isUploading.value = true;
  uploadError.value = null;

  try {
    const formData = new FormData();
    formData.append("file", selectedFile.value);

    // SIMPLIFIED: Only basic processing, NO Ollama/summary
    // - Basic upload extracts text and creates chunks
    // - Clean embedding generation (for similarity/clustering)
    // - NO analysis tasks - Ollama summary is MANUAL only (user can request later)
    formData.append("analyze_metadata", "false");
    formData.append("analyze_title", "false");
    formData.append("analyze_summary", "false"); // NO automatic Ollama
    formData.append("analyze_persons", "false");
    // No summarizer_type needed since analyze_summary is false

    const response = await axios.post("/api/documents/", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    // Backend returns: { document: {...}, upload_task: {...}, analysis_task: {...} }
    documentId.value = response.data.document.document_id;

    // If there's an analysis task, track that instead of upload task
    // because analysis includes summary and similar docs generation
    if (response.data.analysis_task) {
      taskId.value = response.data.analysis_task.task_id;
    } else {
      taskId.value = response.data.upload_task.task_id;
    }

    // Debug logging
    console.log("Upload successful:", {
      document_id: documentId.value,
      task_id: taskId.value,
      has_analysis: !!response.data.analysis_task,
      upload_task: response.data.upload_task,
      analysis_task: response.data.analysis_task,
      form_data: {
        analyze_metadata: "false",
        analyze_title: "false",
        analyze_summary: "false",
        analyze_persons: "false",
      },
    });

    // Switch to processing screen
    currentStep.value = "processing";
    startProcessingMonitoring();
    startFunFactRotation();
  } catch (error) {
    console.error("Upload error:", error);
    uploadError.value =
      error.response?.data?.error ||
      error.response?.data?.message ||
      "Error al subir el documento. Por favor intenta de nuevo.";
  } finally {
    isUploading.value = false;
  }
}

function startProcessingMonitoring() {
  // Poll task status every 2 seconds
  pollingInterval.value = setInterval(async () => {
    await checkTaskStatus();
  }, 2000);

  // Also check immediately
  checkTaskStatus();
}

async function checkTaskStatus() {
  if (!taskId.value) return;

  try {
    const response = await axios.get(`/api/tasks/${taskId.value}/`);
    const task = response.data;

    // Debug logging
    console.log("Task status update:", {
      task_id: taskId.value,
      status: task.status,
      progress: task.progress_percent,
      message: task.progress_message,
    });

    // Update progress
    processingProgress.value = task.progress_percent || 0;
    processingMessage.value = task.progress_message || "Procesando...";

    // Update step indicator based on progress
    // Backend progress (simplified): text=30%, chunks=60%, embeddings=90%, done=100%
    if (processingProgress.value < 30) {
      processingStepIndex.value = 1; // Extracting text (0-29%)
    } else if (processingProgress.value < 60) {
      processingStepIndex.value = 2; // Creating chunks (30-59%)
    } else if (processingProgress.value < 90) {
      processingStepIndex.value = 3; // Generating embeddings (60-89%)
    } else {
      processingStepIndex.value = 4; // Finalizing (90-100%)
    }

    // Check if completed
    if (task.status === "success") {
      stopProcessingMonitoring();
      await loadDocumentResults();
      await loadSimilarDocuments();
      await loadTopicKeywords();
      currentStep.value = "results";
    } else if (task.status === "failure") {
      stopProcessingMonitoring();
      uploadError.value =
        task.error_message || "Error al procesar el documento";
      currentStep.value = "upload";
    }

    // Get active processing count
    const statsResponse = await axios.get("/api/tasks/stats/");
    activeProcessingCount.value =
      (statsResponse.data.by_status?.started || 0) +
      (statsResponse.data.by_status?.progress || 0);
  } catch (error) {
    console.error("Error checking task status:", error);
    console.error("Error details:", {
      message: error.message,
      response: error.response?.data,
      status: error.response?.status,
    });

    // If task not found or other error, stop polling after several attempts
    if (error.response?.status === 404) {
      console.warn("Task not found, stopping polling");
      stopProcessingMonitoring();
      uploadError.value =
        "No se pudo encontrar la tarea. Por favor intenta de nuevo.";
      currentStep.value = "upload";
    }
  }
}

function stopProcessingMonitoring() {
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value);
    pollingInterval.value = null;
  }
  if (funFactInterval) {
    clearInterval(funFactInterval);
    funFactInterval = null;
  }
}

function startFunFactRotation() {
  let currentIndex = 0;
  funFactInterval = setInterval(() => {
    currentIndex = (currentIndex + 1) % funFacts.length;
    currentFunFact.value = funFacts[currentIndex];
  }, 8000); // Change every 8 seconds
}

async function loadDocumentResults() {
  try {
    // Load document details
    let docResponse = await axios.get(`/api/documents/${documentId.value}/`);
    processedDocument.value = docResponse.data;

    console.log("Document loaded (initial):", {
      id: processedDocument.value.document_id,
      has_summary: !!processedDocument.value.summary,
      has_summary_embedding: processedDocument.value.has_summary_embedding,
      has_enhanced_embedding: processedDocument.value.has_enhanced_embedding,
    });

    // Setup document URL for preview
    if (processedDocument.value.file_path) {
      documentUrl.value = processedDocument.value.file_path;
    }

    // If summary exists but embeddings don't, wait and retry (they're being generated)
    if (
      processedDocument.value.summary &&
      !processedDocument.value.has_summary_embedding &&
      !processedDocument.value.has_enhanced_embedding
    ) {
      console.log(
        "Summary exists but embeddings not ready yet. Waiting 2 seconds..."
      );
      await new Promise((resolve) => setTimeout(resolve, 2000));

      // Reload document to get fresh embeddings
      docResponse = await axios.get(`/api/documents/${documentId.value}/`);
      processedDocument.value = docResponse.data;

      console.log("Document reloaded after wait:", {
        has_summary_embedding: processedDocument.value.has_summary_embedding,
        has_enhanced_embedding: processedDocument.value.has_enhanced_embedding,
      });
    }

    // Switch to results screen
    currentStep.value = "results";

    console.log("🎯 Switching to results view", {
      currentStep: currentStep.value,
      hasProcessedDocument: !!processedDocument.value,
      documentId: processedDocument.value?.document_id,
      hasSummary: !!processedDocument.value?.summary,
      hasFormattedSummary: !!processedDocument.value?.formatted_summary,
    });

    // Load similar documents and keywords after switching to results
    await loadSimilarDocuments();
    await loadTopicKeywords();
  } catch (error) {
    console.error("Error loading document results:", error);
    uploadError.value = "Error al cargar los resultados del análisis";
    currentStep.value = "upload";
  }
}

// Load similar documents function (extracted for clarity)
async function loadSimilarDocuments() {
  loadingSimilar.value = true;

  try {
    // clean_embedding is ALWAYS generated (no Ollama required)
    // It's the primary embedding for similarity search
    if (
      processedDocument.value.has_clean_embedding ||
      processedDocument.value.has_summary_embedding ||
      processedDocument.value.has_enhanced_embedding
    ) {
      console.log("Loading similar documents with embeddings...");

      const similarResponse = await axios.get(
        `/api/documents/${documentId.value}/similar/?top_n=10&min_similarity=0.5&use_hybrid=true`
      );

      console.log("Similar documents API response:", {
        total_similar: similarResponse.data.total_similar,
        count: similarResponse.data.similar_documents?.length || 0,
      });

      similarDocuments.value = similarResponse.data.similar_documents || [];

      console.log(
        `✅ Found ${similarDocuments.value.length} similar documents`
      );
    } else {
      console.warn("⚠️ No embeddings available, skipping similarity search");
      similarDocuments.value = [];
    }
  } catch (error) {
    console.error("❌ Error loading similar documents:", error);
    console.error("Error details:", error.response?.data);
    similarDocuments.value = [];
  } finally {
    loadingSimilar.value = false;
  }
}

async function loadTopicKeywords() {
  loadingKeywords.value = true;

  try {
    console.log("🏷️ Loading topic keywords...");
    const keywordsResponse = await axios.get(
      `/api/documents/${documentId.value}/keywords/`
    );

    topicKeywords.value = keywordsResponse.data;

    if (keywordsResponse.data.has_topic) {
      console.log(
        `✅ Found topic: ${keywordsResponse.data.topic_label} with ${
          keywordsResponse.data.keywords?.length || 0
        } keywords`
      );
    } else {
      console.log(
        `ℹ️ Document has no topic assignment: ${keywordsResponse.data.message}`
      );
    }
  } catch (error) {
    console.error("❌ Error loading topic keywords:", error);
    topicKeywords.value = null;
  } finally {
    loadingKeywords.value = false;
  }
}

/* ========== RESULTS ACTIONS ========== */
function resetToUpload() {
  currentStep.value = "upload";
  selectedFile.value = null;
  processedDocument.value = null;
  similarDocuments.value = [];
  topicKeywords.value = null;
  documentId.value = null;
  taskId.value = null;
  processingProgress.value = 0;
  processingStepIndex.value = 1;
  uploadError.value = null;
  iframeError.value = false;

  // If we came from a document view (/document/:id), navigate back to /simple
  if (route.params.id) {
    router.push("/simple");
  }
}

function handleIframeError() {
  console.warn("Iframe loading failed, showing fallback");
  iframeError.value = true;
}

function openDocumentNewTab() {
  if (processedDocument.value?.file_path) {
    window.open(processedDocument.value.file_path, "_blank");
  }
}

function downloadDocument() {
  if (processedDocument.value?.file_path) {
    const link = document.createElement("a");
    link.href = processedDocument.value.file_path;
    link.download = processedDocument.value.title || "documento.pdf";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}

async function viewSimilarDocument(doc) {
  // Navigate to document using internal history (within same tab)
  if (doc.document_id) {
    await loadDocumentById(doc.document_id);
  } else if (doc.file_path) {
    // Fallback: open in new tab
    window.open(doc.file_path, "_blank");
  }
}

async function generateAISummary() {
  if (!documentId.value || generatingSummary.value) return;

  generatingSummary.value = true;

  try {
    console.log("🤖 Requesting AI summary generation...");

    // Call the analyze endpoint with summary part
    const response = await axios.post(
      `/api/documents/${documentId.value}/analyze/`,
      {
        parts: ["summary"],
        summarizer_type: "ollama", // Use Ollama for AI summary
      }
    );

    console.log("📋 Analysis task created:", response.data);

    // Start polling for task completion
    const analysisTaskId = response.data.analysis_task?.task_id;
    if (analysisTaskId) {
      await pollAnalysisTask(analysisTaskId);
    }
  } catch (error) {
    console.error("❌ Error generating AI summary:", error);
    generatingSummary.value = false;
  }
}

async function pollAnalysisTask(analysisTaskId) {
  const maxAttempts = 60; // Max 2 minutes (2s intervals)
  let attempts = 0;

  const pollInterval = setInterval(async () => {
    attempts++;

    try {
      const taskResponse = await axios.get(`/api/tasks/${analysisTaskId}/`);
      const task = taskResponse.data;

      console.log(
        `📊 Analysis task status: ${task.status} (${task.progress_percent}%)`
      );

      if (task.status === "success") {
        clearInterval(pollInterval);
        generatingSummary.value = false;

        // Reload document to get the new summary
        await reloadDocument();
        console.log("✅ AI summary generated successfully!");
      } else if (task.status === "failure") {
        clearInterval(pollInterval);
        generatingSummary.value = false;
        console.error("❌ AI summary generation failed:", task.error_message);
      } else if (attempts >= maxAttempts) {
        clearInterval(pollInterval);
        generatingSummary.value = false;
        console.warn("⚠️ Analysis task timeout");
      }
    } catch (error) {
      console.error("Error polling analysis task:", error);
      // Continue polling unless max attempts reached
      if (attempts >= maxAttempts) {
        clearInterval(pollInterval);
        generatingSummary.value = false;
      }
    }
  }, 2000); // Poll every 2 seconds
}

async function reloadDocument() {
  try {
    const response = await axios.get(`/api/documents/${documentId.value}/`);
    processedDocument.value = response.data;
    console.log("📄 Document reloaded with updated data");
  } catch (error) {
    console.error("Error reloading document:", error);
  }
}

function getSimilarityColor(similarity) {
  if (similarity >= 0.8) return "success";
  if (similarity >= 0.6) return "info";
  if (similarity >= 0.4) return "warning";
  return "error";
}

function formatDocType(type) {
  const types = {
    sentencia: "Sentencia",
    auto: "Auto",
    resolucion: "Resolución",
    decreto: "Decreto",
    providencia: "Providencia",
    otros: "Otros",
  };
  return types[type] || type;
}

function formatLegalArea(area) {
  const areas = {
    civil: "Civil",
    penal: "Penal",
    laboral: "Laboral",
    comercial: "Comercial",
    administrativo: "Administrativo",
    constitucional: "Constitucional",
    familia: "Familia",
    otros: "Otros",
  };
  return areas[area] || area;
}

/* ========== DOCUMENT HISTORY NAVIGATION ========== */

// Add document to navigation history
function addToHistory(doc) {
  if (isNavigatingHistory.value) {
    isNavigatingHistory.value = false;
    return;
  }

  const historyEntry = {
    id: doc.document_id || doc.id,
    title: doc.title || "Sin título",
    timestamp: Date.now(),
  };

  // If we're not at the end of history, truncate forward history
  if (historyIndex.value < documentHistory.value.length - 1) {
    documentHistory.value = documentHistory.value.slice(
      0,
      historyIndex.value + 1
    );
  }

  // Add new entry
  documentHistory.value.push(historyEntry);

  // Maintain max size
  if (documentHistory.value.length > MAX_HISTORY_SIZE) {
    documentHistory.value.shift();
  } else {
    historyIndex.value++;
  }

  // Update URL without full navigation
  const newUrl = `/document/${historyEntry.id}`;
  window.history.replaceState({ ...window.history.state }, "", newUrl);
}

// Navigate to previous document in history
async function navigateHistoryBack() {
  if (!canGoBack.value) return;

  isNavigatingHistory.value = true;
  historyIndex.value--;

  const doc = documentHistory.value[historyIndex.value];
  await loadDocumentById(doc.id);
}

// Navigate to next document in history
async function navigateHistoryForward() {
  if (!canGoForward.value) return;

  isNavigatingHistory.value = true;
  historyIndex.value++;

  const doc = documentHistory.value[historyIndex.value];
  await loadDocumentById(doc.id);
}

/* ========== LIFECYCLE ========== */

// Load existing document by ID (when navigating from clusters view)
async function loadDocumentById(docId) {
  try {
    console.log(`📄 Loading document by ID: ${docId}`);

    // Get document details
    const docResponse = await axios.get(`/api/documents/${docId}/`);
    processedDocument.value = docResponse.data;
    documentId.value = docId;

    console.log("Document loaded:", {
      id: processedDocument.value.document_id,
      title: processedDocument.value.title,
      has_summary: !!processedDocument.value.summary,
    });

    // Set document URL for preview
    if (processedDocument.value.file_path) {
      documentUrl.value = processedDocument.value.file_path;
    }

    // Switch to results view
    currentStep.value = "results";

    // Add to navigation history
    addToHistory(processedDocument.value);

    // Load similar documents and keywords
    await loadSimilarDocuments();
    await loadTopicKeywords();

    console.log("✅ Document view ready");
  } catch (error) {
    console.error("❌ Error loading document:", error);
    uploadError.value = "Error al cargar el documento";
    currentStep.value = "upload";
    // Navigate back to simple upload if document not found
    router.push("/simple");
  }
}

// Navigate back to previous view (external - closes tab)
const goBack = () => {
  window.close();
};

// Keyboard navigation - Arrow keys for history, Escape to close
const handleKeyDown = (e) => {
  if (currentStep.value !== "results") return;

  // Alt+Left or Backspace = Go back in history
  if (
    (e.altKey && e.key === "ArrowLeft") ||
    (e.key === "Backspace" && !e.target.matches("input, textarea"))
  ) {
    e.preventDefault();
    navigateHistoryBack();
    return;
  }

  // Alt+Right = Go forward in history
  if (e.altKey && e.key === "ArrowRight") {
    e.preventDefault();
    navigateHistoryForward();
    return;
  }

  // Escape = Close tab (only if came from external view)
  if (e.key === "Escape" && cameFromExternalView.value) {
    goBack();
  }
};

// Get human-readable origin name
const getOriginName = computed(() => {
  if (!previousRoute.value) return null;
  if (previousRoute.value.includes("clusters")) return "Clusters";
  if (previousRoute.value.includes("simple")) return "Upload";
  if (previousRoute.value === "/" || previousRoute.value.includes("home"))
    return "Inicio";
  return "Anterior";
});

onMounted(async () => {
  // Add keyboard listener for Escape key
  window.addEventListener("keydown", handleKeyDown);

  // Check if we're loading a specific document by ID
  if (route.params.id) {
    cameFromExternalView.value = true;
    // Try to get the previous route from history state
    const fromRoute = window.history.state?.back;
    if (fromRoute) {
      previousRoute.value = fromRoute;
    }
    await loadDocumentById(route.params.id);
  }
});

// Watch for route changes (if user navigates to different document)
watch(
  () => route.params.id,
  async (newId) => {
    if (newId) {
      await loadDocumentById(newId);
    }
  }
);

onUnmounted(() => {
  stopProcessingMonitoring();
  window.removeEventListener("keydown", handleKeyDown);
});
</script>

<style scoped>
/* View Container - Fixed height, controls scroll */
.simple-upload-view {
  height: calc(100vh - 64px); /* Full height minus navbar */
  overflow: hidden; /* Block scroll on container */
  position: relative;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

/* View Content - Scrolleable area */
.view-content {
  height: 100%;
  overflow-y: auto; /* Enable scroll on content */
  overflow-x: hidden; /* Prevent horizontal scroll */

  /* Custom scrollbar styling */
  &::-webkit-scrollbar {
    width: 10px;
  }

  &::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.05);
    border-radius: 5px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(115, 20, 20, 0.3);
    border-radius: 5px;

    &:hover {
      background: rgba(115, 20, 20, 0.5);
    }
  }
}

/* Upload Step */
.upload-step {
  padding-top: 4rem;
  padding-bottom: 2rem;
}

.upload-card {
  border-radius: 16px;
  background: white;
}

.drop-zone {
  border: 3px dashed #ccc;
  border-radius: 12px;
  padding: 4rem 2rem;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #fafafa;
}

.drop-zone:hover {
  border-color: #731414;
  background: #f5f5f5;
}

.drop-zone.drag-over {
  border-color: #731414;
  background: #fff8f8;
  transform: scale(1.02);
}

.drop-zone.has-file {
  border-color: #4caf50;
  background: #f1f8f4;
}

/* Processing Step */
.processing-step {
  padding-top: 4rem;
  padding-bottom: 2rem;
}

.processing-card {
  border-radius: 16px;
  background: white;
}

/* Results Step - IMPROVED LAYOUT */
.results-step {
  padding: 2rem 0;
  animation: fadeInUp 0.4s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.results-container {
  max-width: 1600px;
  margin: 0 auto;
  padding: 0 1.5rem;
}

/* Navigation Bar */
.navigation-bar {
  display: flex;
  align-items: center;
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 10px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 0, 0, 0.08);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.close-btn {
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: rgba(220, 53, 69, 0.1) !important;
  color: #dc3545 !important;
}

.history-nav {
  display: flex;
  align-items: center;
}

.nav-btn {
  transition: all 0.2s ease;
}

.nav-btn:not(:disabled):hover {
  background: rgba(115, 20, 20, 0.1) !important;
  color: #731414 !important;
}

.nav-btn:disabled {
  opacity: 0.4;
}

.history-indicator {
  min-width: 100px;
  justify-content: center;
}

.current-doc-title {
  max-width: 300px;
  display: flex;
  align-items: center;
  color: #666;
}

@media (max-width: 768px) {
  .navigation-bar {
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .current-doc-title {
    display: none;
  }
}

.header-info {
  flex: 1;
  min-width: 0;
}

.header-actions {
  flex-shrink: 0;
}

.results-header {
  text-align: left;
  margin-bottom: 1.5rem;
  background: rgba(255, 255, 255, 0.9);
  padding: 1.25rem;
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.results-grid {
  gap: 1.5rem;
  display: flex;
  flex-wrap: wrap;
  align-items: stretch; /* Changed from flex-start to stretch */
}

.document-column {
  display: flex;
  flex-direction: column;
  flex: 1 1 58%;
  min-width: 0;
}

.analysis-column {
  display: flex;
  flex-direction: column;
  flex: 1 1 38%;
  min-width: 0;
}

/* Let the ChatAnalysisPanel control its own height with clamp() */
/* No need to force height: 100% here */

/* Document Viewer Card Styles */
.document-viewer-card {
  border-radius: 12px;
  height: clamp(500px, calc(100vh - 300px), 800px);
  display: flex;
  flex-direction: column;
}

.document-viewer-card .v-card-text {
  flex: 1;
  overflow: hidden;
  padding: 0;
}

.document-preview {
  width: 100%;
  height: 100%;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.iframe-container {
  width: 100%;
  height: 100%;
  position: relative;
}

.document-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.preview-placeholder {
  text-align: center;
  padding: 2rem;
}

/* Legacy styles for compatibility */
.results-panels {
  max-height: calc(100vh - 200px);
  overflow-y: auto;
}

.summary-content {
  max-height: 400px;
  overflow-y: auto;
}

.metadata-grid {
  display: grid;
  gap: 0.75rem;
}

.metadata-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.similar-docs-list {
  max-height: 500px;
  overflow-y: auto;
}

.similar-doc-item {
  border-bottom: 1px solid #e0e0e0;
  transition: background-color 0.2s;
}

.similar-doc-item:hover {
  background-color: #f5f5f5;
}

.similar-doc-item:last-child {
  border-bottom: none;
}

/* Responsive Design */
@media (max-width: 1280px) {
  .results-grid {
    gap: 1rem;
    flex-direction: column;
  }

  .results-container {
    max-width: 100%;
    padding: 0 1rem;
  }

  .document-column,
  .analysis-column {
    flex: 1 1 100%;
    width: 100%;
  }

  .document-viewer-card {
    height: 500px;
    min-height: 450px;
  }
}

@media (max-width: 960px) {
  .upload-step,
  .processing-step {
    padding-top: 2rem;
  }

  .results-step {
    padding: 1rem 0;
  }

  .results-header {
    margin-bottom: 1rem !important;
  }

  .results-header h2 {
    font-size: 1.5rem !important;
  }

  .document-viewer-card {
    height: 450px;
    min-height: 400px;
    margin-bottom: 1rem;
  }

  .document-preview {
    min-height: 300px;
  }
}

@media (max-width: 600px) {
  .results-container {
    padding: 0 0.75rem;
  }

  .document-viewer-card {
    height: 400px;
    min-height: 350px;
  }

  .document-preview {
    min-height: 250px;
  }
}

@media (max-width: 600px) {
  .results-container {
    padding: 0 0.75rem;
  }

  .document-viewer-card {
    height: 350px;
    min-height: 300px;
  }

  .document-preview {
    min-height: 250px;
  }
}
</style>
