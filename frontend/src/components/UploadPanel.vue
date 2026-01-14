<template>
  <v-card class="mb-4" elevation="2">
    <v-card-title class="d-flex align-center bg-surface py-3">
      <v-icon class="me-2" color="primary">mdi-cloud-upload-outline</v-icon>
      <span class="font-weight-medium">Subir Documentos</span>
    </v-card-title>

    <v-card-text class="pt-4">
      <!-- Área de drag & drop mejorada para múltiples archivos -->
      <div
        class="drop-zone pa-6 text-center rounded-lg mb-4"
        :class="{
          'bg-primary-lighten-5 border-primary': isDragOver,
          'bg-grey-lighten-4': !isDragOver,
        }"
        @drop="onDrop"
        @dragover.prevent="isDragOver = true"
        @dragleave="isDragOver = false"
        @dragend="isDragOver = false"
        @click="$refs.fileInput.click()"
      >
        <v-icon size="48" color="primary" class="mb-3"
          >mdi-file-cloud-outline</v-icon
        >
        <p class="text-body-1 font-weight-medium text-grey-darken-3 mb-1">
          Arrastra tus documentos aquí
        </p>
        <p class="text-caption text-grey-darken-1 mb-3">
          o haz clic para seleccionar (máximo 10 archivos)
        </p>

        <v-chip variant="outlined" color="primary" size="small" class="mb-2">
          <v-icon start size="small">mdi-information</v-icon>
          PDF, DOCX, DOC, TXT - Máx. 50MB por archivo
        </v-chip>
      </div>

      <!-- Input de archivo oculto para múltiples archivos -->
      <input
        ref="fileInput"
        type="file"
        accept=".pdf,.docx,.doc,.txt"
        multiple
        style="display: none"
        @change="onFileSelected"
      />

      <!-- Lista de archivos seleccionados -->
      <div v-if="selectedFiles.length > 0" class="mb-4">
        <div class="d-flex align-center justify-space-between mb-2">
          <span class="text-body-2 font-weight-medium text-grey-darken-2">
            {{ selectedFiles.length }} archivo(s) seleccionado(s)
          </span>
          <v-btn
            variant="text"
            size="small"
            color="error"
            @click="clearAllFiles"
          >
            <v-icon start size="small">mdi-close-circle</v-icon>
            Limpiar todo
          </v-btn>
        </div>

        <v-card
          v-for="(file, index) in selectedFiles"
          :key="index"
          variant="outlined"
          class="mb-2 bg-green-lighten-5"
        >
          <v-card-text class="d-flex align-center pa-3">
            <v-icon size="32" :color="getFileIconColor(file.name)" class="me-3">
              {{ getFileIcon(file.name) }}
            </v-icon>

            <div class="flex-grow-1">
              <p class="text-body-2 font-weight-medium text-grey-darken-3 mb-1">
                {{ file.name }}
              </p>
              <p class="text-caption text-grey-darken-1">
                {{ formatFileSize(file.size) }}
              </p>
            </div>

            <v-btn
              icon
              size="small"
              variant="text"
              color="error"
              @click.stop="removeFile(index)"
            >
              <v-icon>mdi-close</v-icon>
            </v-btn>
          </v-card-text>
        </v-card>
      </div>

      <!-- Opciones de análisis -->
      <v-card variant="outlined" class="mb-4">
        <v-card-title class="text-subtitle-2 py-2 px-3">
          <v-icon start size="small">mdi-cog-outline</v-icon>
          Modo de Procesamiento
        </v-card-title>
        <v-card-text class="pt-2">
          <!-- Selector de modo de procesamiento -->
          <v-radio-group
            v-model="processingMode"
            density="compact"
            class="mb-3"
          >
            <v-radio value="quick" class="mb-2">
              <template #label>
                <div class="d-flex align-center">
                  <v-icon color="success" class="me-2"
                    >mdi-lightning-bolt</v-icon
                  >
                  <div>
                    <span class="font-weight-bold">Modo Rápido</span>
                    <span class="text-caption text-grey-darken-1 d-block">
                      Solo extracción y similitud (sin Ollama) - Ideal para
                      subidas masivas
                    </span>
                  </div>
                  <v-chip
                    size="x-small"
                    color="success"
                    variant="flat"
                    class="ml-2"
                    >RECOMENDADO</v-chip
                  >
                </div>
              </template>
            </v-radio>
            <v-radio value="full">
              <template #label>
                <div class="d-flex align-center">
                  <v-icon color="primary" class="me-2">mdi-robot</v-icon>
                  <div>
                    <span class="font-weight-bold">Análisis Completo</span>
                    <span class="text-caption text-grey-darken-1 d-block">
                      Incluye resumen y metadatos con Ollama (más lento)
                    </span>
                  </div>
                </div>
              </template>
            </v-radio>
          </v-radio-group>

          <v-divider class="mb-3"></v-divider>

          <!-- Opciones de análisis (solo visibles en modo completo) -->
          <v-expand-transition>
            <div v-if="processingMode === 'full'">
              <p class="text-caption text-grey-darken-1 mb-3">
                Selecciona qué análisis realizar con Ollama:
              </p>

              <v-checkbox
                v-model="analysisOptions.metadata"
                label="Analizar Metadatos"
                density="compact"
                hide-details
                class="mb-1"
              >
                <template #label>
                  <span class="text-body-2">
                    <v-icon start size="small" color="primary"
                      >mdi-tag-multiple</v-icon
                    >
                    Metadatos (tipo, área legal, fecha, lugar, etc.)
                  </span>
                </template>
              </v-checkbox>

              <v-checkbox
                v-model="analysisOptions.title"
                label="Generar Título"
                density="compact"
                hide-details
                class="mb-1"
              >
                <template #label>
                  <span class="text-body-2">
                    <v-icon start size="small" color="primary"
                      >mdi-format-title</v-icon
                    >
                    Título Específico (basado en partes y decisión)
                  </span>
                </template>
              </v-checkbox>

              <v-checkbox
                v-model="analysisOptions.summary"
                label="Generar Resumen"
                density="compact"
                hide-details
                class="mb-1"
              >
                <template #label>
                  <span class="text-body-2">
                    <v-icon start size="small" color="primary">mdi-text</v-icon>
                    Resumen del Documento
                  </span>
                </template>
              </v-checkbox>

              <!-- Selector de tipo de resumen (solo visible si summary está marcado) -->
              <v-expand-transition>
                <div v-if="analysisOptions.summary" class="ml-8 mt-2 mb-3">
                  <p class="text-caption text-grey-darken-2 mb-2">
                    Tipo de generador:
                  </p>
                  <v-radio-group
                    v-model="summarizerType"
                    density="compact"
                    hide-details
                  >
                    <v-radio value="ollama_hierarchical" class="mb-1">
                      <template #label>
                        <div class="text-caption">
                          <span class="font-weight-medium"
                            >Ollama Jerárquico</span
                          >
                          - Documento completo (recomendado)
                          <v-chip size="x-small" color="success" class="ml-1"
                            >NUEVO</v-chip
                          >
                        </div>
                      </template>
                    </v-radio>
                    <v-radio value="ollama" class="mb-1">
                      <template #label>
                        <div class="text-caption">
                          <span class="font-weight-medium">Ollama (LLM)</span> -
                          Primeros 6000 caracteres
                        </div>
                      </template>
                    </v-radio>
                    <v-radio value="bart">
                      <template #label>
                        <div class="text-caption">
                          <span class="font-weight-medium">BART</span> -
                          Optimizado para similitud
                        </div>
                      </template>
                    </v-radio>
                  </v-radio-group>
                </div>
              </v-expand-transition>

              <v-checkbox
                v-model="analysisOptions.persons"
                label="Extraer Personas"
                density="compact"
                hide-details
              >
                <template #label>
                  <span class="text-body-2">
                    <v-icon start size="small" color="primary"
                      >mdi-account-multiple</v-icon
                    >
                    Personas y Roles (demandantes, demandados, etc.)
                  </span>
                </template>
              </v-checkbox>

              <v-alert
                v-if="!anyAnalysisSelected && processingMode === 'full'"
                type="info"
                variant="tonal"
                density="compact"
                class="mt-3"
              >
                Los documentos se subirán sin análisis de IA. Podrás analizarlos
                después.
              </v-alert>
            </div>
          </v-expand-transition>

          <!-- Info para modo rápido -->
          <v-alert
            v-if="processingMode === 'quick'"
            type="success"
            variant="tonal"
            density="compact"
            class="mt-2"
          >
            <v-icon start size="small">mdi-information</v-icon>
            Los documentos se procesarán rápidamente. Podrás ver similitudes y
            hacer clustering. El análisis con Ollama se puede hacer después si
            lo necesitas.
          </v-alert>
        </v-card-text>
      </v-card>

      <!-- Alertas de error -->
      <v-alert
        v-if="localError || error"
        type="error"
        variant="tonal"
        class="mt-3"
        closable
        @click:close="localError = null"
        border="start"
        density="compact"
      >
        <template #prepend>
          <v-icon color="error">mdi-alert-circle</v-icon>
        </template>
        {{ localError || error }}
      </v-alert>

      <!-- Botones de acción -->
      <div class="d-flex gap-2 mt-3">
        <v-btn
          block
          color="primary"
          :disabled="selectedFiles.length === 0 || loading"
          :loading="loading"
          @click="uploadFiles"
          size="large"
          elevation="2"
          :prepend-icon="loading ? undefined : 'mdi-cloud-upload'"
        >
          <template v-if="loading">
            <v-progress-circular
              indeterminate
              size="20"
              width="2"
              color="white"
              class="me-2"
            />
            Subiendo {{ uploadProgress.current }}/{{ uploadProgress.total }}...
          </template>
          <template v-else>
            Subir
            {{
              selectedFiles.length > 1
                ? `${selectedFiles.length} documentos`
                : "documento"
            }}
          </template>
        </v-btn>
      </div>

      <!-- Indicador de progreso -->
      <div v-if="loading" class="mt-4">
        <v-progress-linear
          :model-value="uploadProgressPercentage"
          color="primary"
          height="6"
          rounded
        />
        <p class="text-caption text-center mt-2 text-grey-darken-2">
          <v-icon size="small" class="me-1">mdi-robot-outline</v-icon>
          {{ uploadStatusText }}
        </p>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, watch, computed, toRaw } from "vue";
import axios from "axios";

const props = defineProps({
  loading: Boolean,
  error: String,
});

const emit = defineEmits(["file-uploaded", "files-uploaded"]);

const selectedFiles = ref([]);
const localError = ref(null);
const isDragOver = ref(false);
const fileInput = ref(null);

// Modo de procesamiento: 'quick' (solo extracción) o 'full' (con Ollama)
const processingMode = ref("quick");

// Opciones de análisis (solo para modo 'full')
const analysisOptions = ref({
  metadata: true,
  title: true,
  summary: true,
  persons: true,
});

// Tipo de generador de resumen (por defecto el nuevo jerárquico)
const summarizerType = ref("ollama_hierarchical");

// Progreso de subida
const uploadProgress = ref({
  current: 0,
  total: 0,
});

const anyAnalysisSelected = computed(() => {
  return (
    analysisOptions.value.metadata ||
    analysisOptions.value.title ||
    analysisOptions.value.summary ||
    analysisOptions.value.persons
  );
});

const uploadProgressPercentage = computed(() => {
  if (uploadProgress.value.total === 0) return 0;
  return (uploadProgress.value.current / uploadProgress.value.total) * 100;
});

const uploadStatusText = computed(() => {
  if (uploadProgress.value.total === 0) return "Preparando subida...";
  return `Procesando documento ${uploadProgress.value.current} de ${uploadProgress.value.total}`;
});

// Sincronizar errores del padre
watch(
  () => props.error,
  (newError) => {
    if (newError) {
      localError.value = newError;
    }
  }
);

// Funciones auxiliares para UI
function getFileIcon(filename) {
  const ext = filename.split(".").pop()?.toLowerCase();
  const icons = {
    pdf: "mdi-file-pdf-box",
    docx: "mdi-file-word-box",
    doc: "mdi-file-word-box",
    txt: "mdi-file-document-outline",
  };
  return icons[ext] || "mdi-file-outline";
}

function getFileIconColor(filename) {
  const ext = filename.split(".").pop()?.toLowerCase();
  const colors = {
    pdf: "red-darken-2",
    docx: "blue-darken-2",
    doc: "blue-darken-2",
    txt: "grey-darken-2",
  };
  return colors[ext] || "primary";
}

function formatFileSize(bytes) {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

// Manejo de drag & drop
function onDrop(event) {
  event.preventDefault();
  isDragOver.value = false;

  const files = Array.from(event.dataTransfer.files);
  if (files.length > 0) {
    handleFileSelection(files);
  }
}

// Manejo de selección de archivo
function onFileSelected(event) {
  const files = Array.from(event.target.files);
  if (files.length > 0) {
    handleFileSelection(files);
  }
}

function handleFileSelection(files) {
  localError.value = null;

  // Validar número de archivos
  const totalFiles = selectedFiles.value.length + files.length;
  if (totalFiles > 10) {
    localError.value = "No puedes subir más de 10 archivos a la vez";
    return;
  }

  // Validar cada archivo
  const allowedTypes = [".pdf", ".docx", ".doc", ".txt"];
  const maxSize = 50 * 1024 * 1024; // 50MB

  for (const file of files) {
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!allowedTypes.includes(ext)) {
      localError.value = `Formato no permitido: ${file.name}. Solo se permiten PDF, DOCX, DOC y TXT.`;
      return;
    }

    if (file.size > maxSize) {
      localError.value = `El archivo ${file.name} es demasiado grande. Máximo 50MB por archivo.`;
      return;
    }
  }

  // Agregar archivos a la lista
  selectedFiles.value.push(...files);
}

function removeFile(index) {
  selectedFiles.value.splice(index, 1);
  localError.value = null;
}

function clearAllFiles() {
  selectedFiles.value = [];
  localError.value = null;
  if (fileInput.value) {
    fileInput.value.value = "";
  }
}

// Subir archivos
async function uploadFiles() {
  if (selectedFiles.value.length === 0) return;

  localError.value = null;
  uploadProgress.value = {
    current: 0,
    total: selectedFiles.value.length,
  };

  try {
    if (selectedFiles.value.length === 1) {
      // Subir archivo individual
      await uploadSingleFile(selectedFiles.value[0]);
    } else {
      // Subir múltiples archivos
      await uploadBulkFiles();
    }

    // Limpiar después de subida exitosa
    clearAllFiles();
  } catch (error) {
    console.error("Error uploading files:", error);
    localError.value =
      error.response?.data?.error ||
      error.message ||
      "Error al subir los archivos";
  }
}

async function uploadSingleFile(file) {
  // Asegurarse de que file es un File real, no un proxy de Vue
  const actualFile = toRaw(file);

  const formData = new FormData();
  formData.append("file", actualFile);

  // En modo rápido, no enviar opciones de análisis (o enviar todas como false)
  const isQuickMode = processingMode.value === "quick";
  formData.append(
    "analyze_metadata",
    isQuickMode ? false : analysisOptions.value.metadata
  );
  formData.append(
    "analyze_title",
    isQuickMode ? false : analysisOptions.value.title
  );
  formData.append(
    "analyze_summary",
    isQuickMode ? false : analysisOptions.value.summary
  );
  formData.append(
    "analyze_persons",
    isQuickMode ? false : analysisOptions.value.persons
  );
  formData.append("summarizer_type", summarizerType.value);

  // Parámetro para indicar si es modo rápido (solo embedding, sin Ollama)
  formData.append("quick_mode", isQuickMode);

  uploadProgress.value.current = 1;

  // No especificar Content-Type - axios lo maneja automáticamente con FormData
  const response = await axios.post("/api/documents/", formData);

  emit("file-uploaded", response.data);
}

async function uploadBulkFiles() {
  const formData = new FormData();

  // Agregar todos los archivos (usar toRaw para obtener Files reales)
  selectedFiles.value.forEach((file) => {
    const actualFile = toRaw(file);
    formData.append("files", actualFile);
  });

  // En modo rápido, no enviar opciones de análisis
  const isQuickMode = processingMode.value === "quick";
  formData.append(
    "analyze_metadata",
    isQuickMode ? false : analysisOptions.value.metadata
  );
  formData.append(
    "analyze_title",
    isQuickMode ? false : analysisOptions.value.title
  );
  formData.append(
    "analyze_summary",
    isQuickMode ? false : analysisOptions.value.summary
  );
  formData.append(
    "analyze_persons",
    isQuickMode ? false : analysisOptions.value.persons
  );
  formData.append("summarizer_type", summarizerType.value);

  // Parámetro para indicar si es modo rápido
  formData.append("quick_mode", isQuickMode);

  // No especificar Content-Type - axios lo maneja automáticamente con FormData
  const response = await axios.post("/api/documents/bulk_upload/", formData, {
    onUploadProgress: (progressEvent) => {
      // Actualizar progreso basado en la carga
      const percentCompleted = Math.round(
        (progressEvent.loaded * 100) / progressEvent.total
      );
      uploadProgress.value.current = Math.ceil(
        (percentCompleted / 100) * selectedFiles.value.length
      );
    },
  });

  emit("files-uploaded", response.data);
}
</script>

<style scoped>
.drop-zone {
  border: 2px dashed rgba(var(--v-border-color), 0.4);
  cursor: pointer;
  transition: all 0.3s ease;
}

.drop-zone:hover {
  border-color: rgb(var(--v-theme-primary));
  background-color: rgba(var(--v-theme-primary), 0.05);
}

.border-primary {
  border-color: rgb(var(--v-theme-primary)) !important;
  border-width: 2px;
  border-style: dashed;
}
</style>
