<template>
  <div class="document-preview">
    <!-- Título -->
    <div class="preview-section mb-4">
      <div class="section-label">
        <v-icon size="small" color="#736D5D">mdi-format-title</v-icon>
        Título
      </div>
      <div class="section-content font-weight-medium">
        {{ document.title || "Sin título" }}
      </div>
    </div>

    <!-- Tipo de Documento y Área Legal -->
    <div class="preview-section mb-4">
      <div class="section-label">
        <v-icon size="small" color="#736D5D">mdi-tag-outline</v-icon>
        Clasificación
      </div>
      <div class="d-flex gap-2 flex-wrap mt-2">
        <v-chip
          v-if="document.doc_type?.name"
          size="small"
          variant="flat"
          :color="isSimilar ? '#2e7d32' : '#736d5d'"
          class="text-white"
        >
          <v-icon start size="small">mdi-file-document-outline</v-icon>
          {{ document.doc_type.name }}
        </v-chip>
        <v-chip
          v-if="document.legal_area?.name"
          size="small"
          variant="flat"
          :color="isSimilar ? '#1976d2' : '#8c0d0d'"
          class="text-white"
        >
          <v-icon start size="small">mdi-scale-balance</v-icon>
          {{ document.legal_area.name }}
        </v-chip>
        <v-chip
          v-if="document.instance?.name"
          size="small"
          variant="outlined"
          color="#736D5D"
        >
          <v-icon start size="small">mdi-gavel</v-icon>
          {{ document.instance.name }}
        </v-chip>
      </div>
    </div>

    <!-- Fechas y Ubicación -->
    <div
      v-if="
        document.document_date || document.issue_place || document.created_at
      "
      class="preview-section mb-4"
    >
      <div class="section-label">
        <v-icon size="small" color="#736D5D">mdi-calendar-clock</v-icon>
        Información Temporal
      </div>
      <div class="d-flex flex-column gap-2 mt-2">
        <div v-if="document.document_date" class="info-item">
          <v-icon size="small" color="#736D5D">mdi-calendar</v-icon>
          <span class="text-caption">
            Fecha del Documento:
            <strong>{{ formatDate(document.document_date) }}</strong>
          </span>
        </div>
        <div v-if="document.issue_place" class="info-item">
          <v-icon size="small" color="#736D5D">mdi-map-marker</v-icon>
          <span class="text-caption">
            Lugar de Emisión: <strong>{{ document.issue_place }}</strong>
          </span>
        </div>
        <div v-if="document.created_at" class="info-item">
          <v-icon size="small" color="#736D5D">mdi-clock-outline</v-icon>
          <span class="text-caption">
            Cargado: <strong>{{ formatDate(document.created_at) }}</strong>
          </span>
        </div>
      </div>
    </div>

    <!-- Número de Caso -->
    <div v-if="document.case_number" class="preview-section mb-4">
      <div class="section-label">
        <v-icon size="small" color="#736D5D">mdi-file-document</v-icon>
        Número de Caso
      </div>
      <div class="section-content">
        <v-chip size="small" variant="outlined" color="#731414">
          {{ document.case_number }}
        </v-chip>
      </div>
    </div>

    <!-- Personas -->
    <div v-if="hasPersons" class="preview-section mb-4">
      <div class="section-label">
        <v-icon size="small" color="#736D5D">mdi-account-group</v-icon>
        Personas Involucradas ({{ validPersons.length }})
      </div>
      <div class="d-flex flex-column gap-2 mt-2">
        <div
          v-for="(person, idx) in displayedPersons"
          :key="idx"
          class="person-card pa-2"
          :class="isSimilar ? 'person-similar' : 'person-default'"
        >
          <div class="d-flex align-center gap-2">
            <v-icon size="small" :color="isSimilar ? '#2e7d32' : '#8c0d0d'">
              mdi-account-circle
            </v-icon>
            <div class="flex-grow-1">
              <div class="text-caption font-weight-bold">
                {{ person.name || person.person?.name }}
              </div>
              <div v-if="person.role" class="text-caption text-grey-darken-1">
                {{ person.role }}
              </div>
            </div>
          </div>
        </div>
        <v-btn
          v-if="validPersons.length > maxVisiblePersons"
          variant="text"
          size="x-small"
          :color="isSimilar ? '#2e7d32' : '#8c0d0d'"
          @click="togglePersons"
        >
          {{
            showAllPersons ? "Ver menos" : `Ver todas (${validPersons.length})`
          }}
        </v-btn>
      </div>
    </div>

    <!-- Resumen -->
    <div v-if="document.summary" class="preview-section mb-4">
      <div class="section-label">
        <v-icon size="small" color="#736D5D">mdi-text-box-outline</v-icon>
        Resumen del Documento
      </div>
      <div class="section-content text-caption summary-text">
        {{ truncatedSummary }}
      </div>
      <v-btn
        v-if="document.summary.length > summaryTruncateLength"
        variant="text"
        size="x-small"
        :color="isSimilar ? '#2e7d32' : '#8c0d0d'"
        class="mt-2"
        @click="toggleSummary"
      >
        {{ showFullSummary ? "Ver menos" : "Ver resumen completo" }}
      </v-btn>
    </div>

    <!-- Metadata Adicional -->
    <div
      v-if="document.file_name || document.file_path"
      class="preview-section mb-4"
    >
      <div class="section-label">
        <v-icon size="small" color="#736D5D">mdi-file-outline</v-icon>
        Archivo
      </div>
      <div class="d-flex flex-column gap-2 mt-2">
        <div v-if="document.file_name" class="info-item">
          <v-icon size="small" color="#736D5D">mdi-file-document</v-icon>
          <span class="text-caption">
            <strong>{{ document.file_name }}</strong>
          </span>
        </div>
        <v-chip
          v-if="document.file_path"
          size="x-small"
          variant="outlined"
          color="#736D5D"
        >
          <v-icon start size="x-small">mdi-paperclip</v-icon>
          Archivo disponible
        </v-chip>
      </div>
    </div>

    <!-- Estado -->
    <div class="preview-section">
      <div class="section-label">
        <v-icon size="small" color="#736D5D">mdi-information-outline</v-icon>
        Estado
      </div>
      <div class="mt-2">
        <v-chip
          :color="getStatusColor(document.status)"
          size="small"
          variant="flat"
          class="text-white"
        >
          {{ getStatusText(document.status) }}
        </v-chip>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { formatDate } from "@/composables/useFormatting";

// ============================================================================
// PROPS
// ============================================================================
const props = defineProps({
  document: {
    type: Object,
    required: true,
  },
  isSimilar: {
    type: Boolean,
    default: false,
  },
});

// ============================================================================
// STATE
// ============================================================================
const showFullSummary = ref(false);
const showAllPersons = ref(false);

// ============================================================================
// CONSTANTS
// ============================================================================
const maxVisiblePersons = 3;
const summaryTruncateLength = 400;

// ============================================================================
// COMPUTED
// ============================================================================
const validPersons = computed(() => {
  if (!props.document?.persons) return [];
  return props.document.persons.filter((p) => p.name || p.person?.name);
});

const hasPersons = computed(() => validPersons.value.length > 0);

const displayedPersons = computed(() => {
  if (showAllPersons.value) {
    return validPersons.value;
  }
  return validPersons.value.slice(0, maxVisiblePersons);
});

const truncatedSummary = computed(() => {
  if (!props.document.summary) return "Sin resumen disponible";
  if (
    showFullSummary.value ||
    props.document.summary.length <= summaryTruncateLength
  ) {
    return props.document.summary;
  }
  return props.document.summary.substring(0, summaryTruncateLength - 3) + "...";
});

// ============================================================================
// METHODS
// ============================================================================
function toggleSummary() {
  showFullSummary.value = !showFullSummary.value;
}

function togglePersons() {
  showAllPersons.value = !showAllPersons.value;
}

function getStatusColor(status) {
  const colors = {
    uploaded: "#757575",
    processing: "#1976d2",
    processed: "#2e7d32",
    error: "#d32f2f",
  };
  return colors[status] || "#757575";
}

function getStatusText(status) {
  const texts = {
    uploaded: "Cargado",
    processing: "Procesando",
    processed: "Procesado",
    error: "Error",
  };
  return texts[status] || status;
}
</script>

<style scoped lang="scss">
@import "@/styles/variables.scss";

.document-preview {
  min-height: 400px;
}

.preview-section {
  .section-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    color: #736d5d;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
  }

  .section-content {
    color: #424242;
    line-height: 1.6;
  }
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.summary-text {
  line-height: 1.7;
  color: #616161;
  white-space: pre-wrap;
  word-break: break-word;
}

.person-card {
  border-radius: 8px;
  border: 1px solid transparent;
  transition: all 0.2s ease;

  &.person-default {
    background-color: rgba(#8c0d0d, 0.05);
    border-color: rgba(#8c0d0d, 0.1);

    &:hover {
      background-color: rgba(#8c0d0d, 0.1);
      border-color: rgba(#8c0d0d, 0.2);
    }
  }

  &.person-similar {
    background-color: rgba(#2e7d32, 0.05);
    border-color: rgba(#2e7d32, 0.1);

    &:hover {
      background-color: rgba(#2e7d32, 0.1);
      border-color: rgba(#2e7d32, 0.2);
    }
  }
}
</style>
