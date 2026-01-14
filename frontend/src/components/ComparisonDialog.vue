<template>
  <v-dialog v-model="isOpen" max-width="1400px" scrollable :persistent="false">
    <v-card v-if="currentDoc && similarDoc">
      <!-- Header -->
      <v-card-title class="d-flex align-center justify-space-between pa-4">
        <div class="d-flex align-center gap-3">
          <v-icon color="#8c0d0d" size="32">mdi-file-compare</v-icon>
          <div>
            <div class="text-h6 font-weight-bold" style="color: #731414">
              Comparar Documentos
            </div>
            <div class="text-caption text-grey-darken-1">
              Revisa las diferencias y similitudes entre documentos
            </div>
          </div>
        </div>
        <v-btn icon variant="text" @click="closeDialog">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-divider />

      <!-- Content -->
      <v-card-text class="pa-4" style="max-height: 70vh">
        <div class="comparison-container">
          <!-- Documento Actual (Izquierda) -->
          <div class="document-column">
            <v-card variant="outlined" class="h-100 d-flex flex-column">
              <v-card-title
                class="text-subtitle-1 font-weight-bold pa-3 d-flex align-center justify-space-between"
                style="background-color: #f2f2f2; color: #731414"
              >
                <div class="d-flex align-center">
                  <v-icon start color="#731414">mdi-file-document</v-icon>
                  Documento Actual
                </div>
                <v-tooltip location="bottom" text="Abrir en nueva pestaña">
                  <template v-slot:activator="{ props }">
                    <v-btn
                      v-bind="props"
                      size="small"
                      variant="tonal"
                      color="#731414"
                      prepend-icon="mdi-chat-processing"
                      @click="navigateToChatCurrent"
                    >
                      Chat
                      <v-icon end size="x-small">mdi-open-in-new</v-icon>
                    </v-btn>
                  </template>
                </v-tooltip>
              </v-card-title>
              <v-divider />
              <v-card-text class="pa-4 flex-grow-1">
                <DocumentPreview :document="currentDoc" />
              </v-card-text>
            </v-card>
          </div>

          <!-- Divider -->
          <div class="comparison-divider">
            <v-divider vertical />
            <div class="divider-icon">
              <v-icon color="#8c0d0d">mdi-compare-horizontal</v-icon>
            </div>
          </div>

          <!-- Documento Similar (Derecha) -->
          <div class="document-column">
            <v-card variant="outlined" class="h-100 d-flex flex-column">
              <v-card-title
                class="text-subtitle-1 font-weight-bold pa-3 d-flex align-center justify-space-between"
                style="background-color: #e8f5e9; color: #2e7d32"
              >
                <div class="d-flex align-center">
                  <v-icon start color="#2e7d32"
                    >mdi-file-document-outline</v-icon
                  >
                  Documento Similar
                </div>
                <v-tooltip location="bottom" text="Abrir en nueva pestaña">
                  <template v-slot:activator="{ props }">
                    <v-btn
                      v-bind="props"
                      size="small"
                      variant="tonal"
                      color="#2e7d32"
                      prepend-icon="mdi-chat-processing"
                      @click="navigateToChatSimilar"
                    >
                      Chat
                      <v-icon end size="x-small">mdi-open-in-new</v-icon>
                    </v-btn>
                  </template>
                </v-tooltip>
              </v-card-title>
              <v-divider />
              <v-card-text class="pa-4 flex-grow-1">
                <DocumentPreview :document="similarDoc" :is-similar="true" />
              </v-card-text>
            </v-card>
          </div>
        </div>

        <!-- Similarity Score Section -->
        <v-card v-if="similarDoc" variant="tonal" class="mt-4" color="#736D5D">
          <v-card-text class="pa-3">
            <div
              class="d-flex align-center justify-space-between flex-wrap gap-3"
            >
              <div>
                <div class="text-caption font-weight-medium text-grey-darken-3">
                  PUNTUACIÓN DE SIMILITUD
                </div>
                <div
                  class="text-h5 font-weight-bold mt-1"
                  style="color: #731414"
                >
                  {{
                    similarDoc.hybrid_score
                      ? (similarDoc.hybrid_score * 100).toFixed(1)
                      : "0.0"
                  }}%
                </div>
              </div>
              <div class="d-flex gap-2 flex-wrap">
                <v-chip
                  v-if="similarDoc.semantic_score"
                  color="#736D5D"
                  size="small"
                  variant="flat"
                  class="text-white"
                >
                  <v-icon start size="small">mdi-brain</v-icon>
                  Sem: {{ (similarDoc.semantic_score * 100).toFixed(1) }}%
                </v-chip>
                <v-chip
                  v-if="similarDoc.bm25_score"
                  color="#736D5D"
                  size="small"
                  variant="flat"
                  class="text-white"
                >
                  <v-icon start size="small">mdi-text-search</v-icon>
                  BM25: {{ similarDoc.bm25_score.toFixed(2) }}
                </v-chip>
              </div>
            </div>
          </v-card-text>
        </v-card>

        <!-- Similarity Reasons -->
        <div
          v-if="
            similarDoc &&
            similarDoc.similarity_reasons &&
            similarDoc.similarity_reasons.length > 0
          "
          class="mt-4"
        >
          <div
            class="text-subtitle-2 font-weight-bold mb-2"
            style="color: #731414"
          >
            <v-icon start color="#731414">mdi-information-outline</v-icon>
            ¿Por qué son similares?
          </div>
          <div class="d-flex flex-column gap-2">
            <v-card
              v-for="(reason, idx) in formattedReasons"
              :key="idx"
              variant="outlined"
              :class="reason.isPenalty ? 'reason-penalty' : 'reason-boost'"
            >
              <v-card-text class="pa-3">
                <div class="d-flex align-start gap-2">
                  <v-icon
                    :color="reason.isPenalty ? '#D9A3A3' : '#736D5D'"
                    size="20"
                  >
                    {{
                      reason.isPenalty
                        ? "mdi-alert-circle-outline"
                        : "mdi-check-circle-outline"
                    }}
                  </v-icon>
                  <div class="flex-grow-1">
                    <div
                      class="text-body-2 font-weight-medium mb-1"
                      :style="{
                        color: reason.isPenalty ? '#731414' : '#736D5D',
                      }"
                    >
                      {{ reason.category }}
                    </div>
                    <div class="text-caption text-grey-darken-2">
                      {{ reason.detail }}
                    </div>
                    <v-chip
                      v-if="reason.weight"
                      size="x-small"
                      :color="reason.isPenalty ? '#D9A3A3' : '#736D5D'"
                      variant="flat"
                      class="mt-1 text-white"
                    >
                      {{ reason.isPenalty ? "" : "+"
                      }}{{ (reason.weight * 100).toFixed(1) }}%
                    </v-chip>
                  </div>
                </div>
              </v-card-text>
            </v-card>
          </div>
        </div>
      </v-card-text>

      <v-divider />

      <!-- Actions -->
      <v-card-actions class="pa-4">
        <v-btn variant="text" @click="closeDialog"> Cerrar </v-btn>
        <v-spacer />
        <v-btn
          variant="flat"
          color="#8c0d0d"
          prepend-icon="mdi-arrow-right-circle"
          @click="navigateToSimilar"
        >
          Ir al Documento Similar
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useRouter } from "vue-router";
import DocumentPreview from "./shared/DocumentPreview.vue";

const router = useRouter();

// ============================================================================
// PROPS & EMITS
// ============================================================================
const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  currentDoc: {
    type: Object,
    default: null,
  },
  similarDoc: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(["update:modelValue", "navigate-to-similar"]);

// ============================================================================
// STATE
// ============================================================================
const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit("update:modelValue", value),
});

// ============================================================================
// COMPUTED
// ============================================================================
const formattedReasons = computed(() => {
  if (
    !props.similarDoc ||
    !props.similarDoc.similarity_reasons ||
    !Array.isArray(props.similarDoc.similarity_reasons)
  ) {
    return [];
  }

  const categoryNames = {
    legal_classification: "Clasificación Legal",
    document_type: "Tipo de Documento",
    temporal_proximity: "Proximidad Temporal",
    parties_overlap: "Partes Coincidentes",
    semantic_similarity: "Similitud Semántica",
    text_similarity: "Similitud de Texto",
    metadata_match: "Metadatos Coincidentes",
    subject_overlap: "Materia Legal Relacionada",
  };

  return props.similarDoc.similarity_reasons.map((reason) => {
    if (typeof reason === "string") {
      return {
        category: "Similitud General",
        detail: reason,
        weight: null,
        isPenalty: false,
      };
    }

    if (typeof reason === "object" && reason !== null) {
      const categoryKey = reason.category || "unknown";
      const categoryName =
        categoryNames[categoryKey] || categoryKey.replace(/_/g, " ");

      let detail = reason.detail || "Sin detalles";
      if (detail.length > 200) {
        detail = detail.substring(0, 197) + "...";
      }

      const isPenalty =
        reason.is_penalty === true ||
        reason.is_penalty === "true" ||
        reason.is_penalty === 1 ||
        (reason.weight && reason.weight < 0);

      return {
        category: categoryName,
        detail: detail,
        weight: reason.weight || 0,
        isPenalty: isPenalty,
      };
    }

    return {
      category: "Información",
      detail: JSON.stringify(reason),
      weight: null,
      isPenalty: false,
    };
  });
});

// ============================================================================
// METHODS
// ============================================================================
function closeDialog() {
  isOpen.value = false;
}

function navigateToSimilar() {
  // Cerrar el diálogo primero
  isOpen.value = false;

  // Emitir evento de navegación después de un breve delay
  // para permitir que el diálogo se cierre completamente
  setTimeout(() => {
    emit("navigate-to-similar");
  }, 100);
}

// Navigate to chat view for current document (opens in new tab)
function navigateToChatCurrent() {
  if (!props.currentDoc?.document_id) {
    console.warn("No current document available");
    return;
  }

  // Open in new tab to preserve current view state
  const url = `/document/${props.currentDoc.document_id}`;
  window.open(url, "_blank");
}

// Navigate to chat view for similar document (opens in new tab)
function navigateToChatSimilar() {
  if (!props.similarDoc?.document_id) {
    console.warn("No similar document available");
    return;
  }

  // Open in new tab to preserve current view state
  const url = `/document/${props.similarDoc.document_id}`;
  window.open(url, "_blank");
}
</script>

<style scoped lang="scss">
@import "@/styles/variables.scss";

.comparison-container {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 16px;
  min-height: 400px;

  @media (max-width: 960px) {
    grid-template-columns: 1fr;
    gap: 24px;

    .comparison-divider {
      display: none;
    }
  }
}

.document-column {
  min-height: 400px;
}

.comparison-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;

  .divider-icon {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    background: white;
    padding: 8px;
    border-radius: 50%;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }
}

.reason-boost {
  border-left: 3px solid $pj-brown-grey;
  background-color: rgba($pj-brown-grey, 0.05);
}

.reason-penalty {
  border-left: 3px solid $pj-red-dark;
  background-color: rgba($pj-red-light, 0.1);
}
</style>
