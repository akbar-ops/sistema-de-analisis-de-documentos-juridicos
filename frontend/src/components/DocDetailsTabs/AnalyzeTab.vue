<template>
  <div class="analyze-tab pa-3">
    <v-alert
      type="info"
      variant="tonal"
      density="compact"
      icon="mdi-information"
      class="mb-3"
    >
      <div class="text-caption">
        Puedes analizar partes específicas del documento de forma independiente.
      </div>
    </v-alert>

    <!-- Estado de cada análisis -->
    <div class="analysis-options mb-4">
      <v-card
        v-for="part in analysisParts"
        :key="part.id"
        variant="outlined"
        class="mb-2"
        :class="{ 'analysis-completed': getStatus(part.id) === 'completed' }"
      >
        <v-card-text class="pa-3">
          <div class="d-flex align-center justify-space-between">
            <div class="d-flex align-center flex-grow-1">
              <v-icon :color="getStatusColor(part.id)" class="me-2">
                {{ getStatusIcon(part.id) }}
              </v-icon>
              <div>
                <div class="text-subtitle-2">{{ part.title }}</div>
                <div class="text-caption text-medium-emphasis">
                  {{ part.description }}
                </div>
              </div>
            </div>
            <v-chip
              :color="getStatusColor(part.id)"
              size="small"
              variant="flat"
            >
              {{ getStatusText(part.id) }}
            </v-chip>
          </div>
        </v-card-text>
      </v-card>
    </div>

    <!-- Selección de análisis -->
    <div class="mb-3">
      <p class="text-caption font-weight-medium mb-2">
        Selecciona qué analizar:
      </p>
      <v-checkbox
        v-for="part in analysisParts"
        :key="`checkbox-${part.id}`"
        v-model="selectedParts"
        :value="part.id"
        :label="part.title"
        density="compact"
        hide-details
        class="mb-1"
      />
    </div>

    <!-- Selector de tipo de resumen (solo visible si "summary" está seleccionado) -->
    <v-expand-transition>
      <div v-if="selectedParts.includes('summary')" class="mb-3">
        <v-divider class="mb-3" />
        <p class="text-caption font-weight-medium mb-2">
          Tipo de generador de resumen:
        </p>
        <v-radio-group v-model="summarizerType" density="compact" hide-details>
          <v-radio value="ollama_hierarchical" class="mb-1">
            <template #label>
              <div>
                <div class="text-subtitle-2">
                  Ollama Jerárquico
                  <v-chip size="x-small" color="success" class="ml-1"
                    >NUEVO</v-chip
                  >
                </div>
                <div class="text-caption text-medium-emphasis">
                  Resume el documento completo usando chunks (recomendado)
                </div>
              </div>
            </template>
          </v-radio>
          <v-radio value="ollama" class="mb-1">
            <template #label>
              <div>
                <div class="text-subtitle-2">Ollama (LLM)</div>
                <div class="text-caption text-medium-emphasis">
                  Solo primeros 6000 caracteres del documento
                </div>
              </div>
            </template>
          </v-radio>
          <v-radio value="bart">
            <template #label>
              <div>
                <div class="text-subtitle-2">BART (Hugging Face)</div>
                <div class="text-caption text-medium-emphasis">
                  Resumen denso optimizado para embeddings y búsqueda por
                  similitud
                </div>
              </div>
            </template>
          </v-radio>
        </v-radio-group>
      </div>
    </v-expand-transition>

    <!-- Botón de análisis -->
    <v-btn
      block
      color="primary"
      :disabled="selectedParts.length === 0 || analyzing"
      :loading="analyzing"
      @click="handleAnalyze"
    >
      <v-icon start>mdi-brain</v-icon>
      Analizar
      {{ selectedParts.length > 0 ? `(${selectedParts.length})` : "" }}
      <span v-if="selectedParts.includes('summary')" class="text-caption ml-1">
        - {{ getSummarizerLabel() }}
      </span>
    </v-btn>

    <!-- Mensaje de progreso -->
    <v-alert
      v-if="analyzing"
      type="info"
      variant="tonal"
      density="compact"
      class="mt-3"
    >
      <v-progress-linear indeterminate color="primary" class="mb-2" />
      Analizando documento...
    </v-alert>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";

const props = defineProps({
  selected: {
    type: Object,
    required: true,
  },
  analyzing: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["analyze"]);

const selectedParts = ref([]);
const summarizerType = ref("ollama_hierarchical"); // Default: Jerárquico (documento completo)

const analysisParts = [
  {
    id: "metadata",
    title: "Metadatos",
    description: "Tipo, área legal, fecha, lugar, etc.",
  },
  {
    id: "title",
    title: "Título",
    description: "Título específico basado en partes y decisión",
  },
  {
    id: "summary",
    title: "Resumen",
    description: "Resumen ejecutivo del documento",
  },
  {
    id: "persons",
    title: "Personas",
    description: "Demandantes, demandados, jueces, etc.",
  },
];

function getStatus(partId) {
  return props.selected?.analysis_status?.[partId] || "pending";
}

function getStatusColor(partId) {
  const status = getStatus(partId);
  const colors = {
    pending: "grey",
    processing: "warning",
    completed: "success",
    failed: "error",
  };
  return colors[status] || "grey";
}

function getStatusIcon(partId) {
  const status = getStatus(partId);
  const icons = {
    pending: "mdi-clock-outline",
    processing: "mdi-loading mdi-spin",
    completed: "mdi-check-circle",
    failed: "mdi-alert-circle",
  };
  return icons[status] || "mdi-help-circle";
}

function getStatusText(partId) {
  const status = getStatus(partId);
  const texts = {
    pending: "Pendiente",
    processing: "Procesando...",
    completed: "Completado",
    failed: "Error",
  };
  return texts[status] || "Desconocido";
}

function getSummarizerLabel() {
  const labels = {
    ollama_hierarchical: "Jerárquico",
    ollama: "Ollama",
    bart: "BART",
  };
  return labels[summarizerType.value] || summarizerType.value;
}

function handleAnalyze() {
  if (selectedParts.value.length === 0) return;

  // Emitir evento con partes y tipo de resumen
  emit("analyze", {
    parts: selectedParts.value,
    summarizerType: summarizerType.value,
  });

  selectedParts.value = [];
}
</script>

<style scoped lang="scss">
.analysis-completed {
  background-color: rgba(var(--v-theme-success), 0.05);
  border-color: rgba(var(--v-theme-success), 0.3);
}
</style>
