<template>
  <div class="similar-documents-section">
    <!-- Section Header (hide in compact mode) -->
    <div v-if="!compact" class="section-header mb-3">
      <div class="d-flex align-center">
        <v-icon color="primary" class="me-2">mdi-lightbulb-on-outline</v-icon>
        <h3 class="text-h6 font-weight-bold">Te puede interesar</h3>
      </div>
      <p class="text-caption text-grey-darken-1 mt-1">
        Documentos similares basados en contenido y contexto legal
      </p>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-6">
      <v-progress-circular indeterminate size="32" color="primary" />
      <p class="text-caption mt-2 text-medium-emphasis">
        Buscando documentos similares...
      </p>
    </div>

    <!-- Empty State -->
    <div
      v-else-if="!similarDocuments || similarDocuments.length === 0"
      class="text-center py-6"
    >
      <v-icon size="48" color="grey-lighten-1">mdi-file-search-outline</v-icon>
      <p class="text-body-2 text-grey-darken-1 mt-2">
        No se encontraron documentos similares
      </p>
    </div>

    <!-- Similar Documents Cards -->
    <div v-else class="similar-docs-grid">
      <v-card
        v-for="(doc, idx) in displayedDocuments"
        :key="doc.document_id || idx"
        class="similar-doc-card"
        variant="outlined"
        hover
        @click="$emit('select-document', doc)"
      >
        <v-card-text class="pa-3">
          <!-- Similarity Score Badge -->
          <div class="d-flex justify-space-between align-start mb-2">
            <v-chip
              :color="getSimilarityColor(doc.hybrid_score ?? doc.similarity)"
              size="small"
              variant="flat"
              class="font-weight-bold text-white"
            >
              <v-icon start size="x-small">mdi-chart-line</v-icon>
              {{ ((doc.hybrid_score ?? doc.similarity) * 100).toFixed(0) }}%
              similar
            </v-chip>
            <v-icon size="small" color="primary">mdi-open-in-new</v-icon>
          </div>

          <!-- Document Title -->
          <h4 class="text-subtitle-2 font-weight-medium mb-2 line-clamp-2">
            {{ doc.title || "Documento sin título" }}
          </h4>

          <!-- Document Metadata -->
          <div class="d-flex flex-wrap gap-1">
            <v-chip
              v-if="doc.doc_type?.name || doc.doc_type"
              size="x-small"
              variant="flat"
              color="#736d5d"
              class="text-white"
            >
              <v-icon start size="x-small">mdi-file-document</v-icon>
              {{ formatDocType(doc.doc_type) }}
            </v-chip>
            <v-chip
              v-if="doc.legal_area?.name || doc.legal_area"
              size="x-small"
              variant="flat"
              color="#8c0d0d"
              class="text-white"
            >
              <v-icon start size="x-small">mdi-scale-balance</v-icon>
              {{ formatLegalArea(doc.legal_area) }}
            </v-chip>
            <v-chip
              v-if="doc.document_date"
              size="x-small"
              variant="outlined"
              color="#736D5D"
            >
              <v-icon start size="x-small">mdi-calendar</v-icon>
              {{ doc.document_date }}
            </v-chip>
          </div>

          <!-- Additional Score Details (Optional) -->
          <div
            v-if="showDetails"
            class="mt-2 pt-2 border-t border-grey-lighten-2"
          >
            <div class="d-flex gap-1 flex-wrap">
              <v-chip
                v-if="doc.semantic_score || doc.similarity_score"
                size="x-small"
                variant="outlined"
                color="deep-purple"
              >
                <v-icon start size="x-small">mdi-brain</v-icon>
                IA:
                {{
                  ((doc.semantic_score || doc.similarity_score) * 100).toFixed(
                    0
                  )
                }}%
              </v-chip>
              <v-chip
                v-if="doc.bm25_score"
                size="x-small"
                variant="outlined"
                color="blue"
              >
                <v-icon start size="x-small">mdi-text-search</v-icon>
                Texto: {{ doc.bm25_score.toFixed(1) }}
              </v-chip>
            </div>
          </div>
        </v-card-text>
      </v-card>
    </div>

    <!-- Show More Button -->
    <div
      v-if="
        !loading &&
        similarDocuments &&
        similarDocuments.length > maxVisible &&
        !showAll
      "
      class="text-center mt-3"
    >
      <v-btn
        variant="outlined"
        color="primary"
        size="small"
        @click="showAll = true"
      >
        Ver más documentos ({{ similarDocuments.length - maxVisible }} más)
      </v-btn>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";

/* ========== PROPS ========== */
const props = defineProps({
  similarDocuments: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
  maxVisible: {
    type: Number,
    default: 3,
  },
  showDetails: {
    type: Boolean,
    default: false,
  },
  compact: {
    type: Boolean,
    default: false,
  },
});

/* ========== EMITS ========== */
const emit = defineEmits(["select-document"]);

/* ========== STATE ========== */
const showAll = ref(false);

/* ========== COMPUTED ========== */
const displayedDocuments = computed(() => {
  if (showAll.value) {
    return props.similarDocuments;
  }
  return props.similarDocuments.slice(0, props.maxVisible);
});

/* ========== METHODS ========== */
function getSimilarityColor(similarity) {
  if (!similarity) return "grey";
  if (similarity >= 0.8) return "success";
  if (similarity >= 0.6) return "info";
  if (similarity >= 0.4) return "warning";
  return "orange";
}

function formatDocType(type) {
  if (typeof type === "object" && type?.name) {
    return type.name;
  }

  const types = {
    sentencia: "Sentencia",
    auto: "Auto",
    resolucion: "Resolución",
    decreto: "Decreto",
    providencia: "Providencia",
    otros: "Otros",
  };
  return types[type] || type || "N/A";
}

function formatLegalArea(area) {
  if (typeof area === "object" && area?.name) {
    return area.name;
  }

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
  return areas[area] || area || "N/A";
}
</script>

<style scoped lang="scss">
.similar-documents-section {
  .section-header {
    h3 {
      color: rgb(var(--v-theme-on-surface));
    }
  }

  .similar-docs-grid {
    display: grid;
    gap: 0.75rem;
  }

  .similar-doc-card {
    cursor: pointer;
    transition: all 0.2s ease;
    border-left: 3px solid transparent;

    &:hover {
      border-left-color: rgb(var(--v-theme-primary));
      transform: translateX(4px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
  }

  .line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .gap-1 {
    gap: 0.25rem;
  }

  .gap-2 {
    gap: 0.5rem;
  }

  .border-t {
    border-top-width: 1px;
    border-top-style: solid;
  }

  .border-grey-lighten-2 {
    border-color: rgb(var(--v-theme-grey-lighten-2));
  }
}

@media (max-width: 600px) {
  .similar-docs-grid {
    gap: 0.5rem;
  }

  .similar-doc-card {
    &:hover {
      transform: none;
    }
  }
}
</style>
