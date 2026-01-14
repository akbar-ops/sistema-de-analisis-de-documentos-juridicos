<template>
  <div class="similar-tab">
    <!-- Selector de tipo de embedding -->
    <div class="pa-3 pb-0">
      <div class="text-caption text-grey-darken-1 mb-2">
        Tipo de embedding para similitud:
      </div>
      <v-btn-toggle
        :model-value="embeddingField"
        @update:model-value="$emit('update:embedding-field', $event)"
        mandatory
        density="compact"
        color="deep-purple"
        variant="outlined"
        class="mb-2"
      >
        <v-btn value="clean_embedding" size="x-small">
          <v-icon start size="x-small">mdi-broom</v-icon>
          Limpio
        </v-btn>
        <v-btn value="enhanced_embedding" size="x-small">
          <v-icon start size="x-small">mdi-auto-fix</v-icon>
          Mejorado
        </v-btn>
        <v-btn value="summary_embedding" size="x-small">
          <v-icon start size="x-small">mdi-text-box-outline</v-icon>
          Resumen
        </v-btn>
      </v-btn-toggle>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="pa-3 text-center">
      <v-progress-circular indeterminate size="32" style="color: #8c0d0d" />
      <p class="text-caption mt-2 text-medium-emphasis">
        Buscando similares...
      </p>
    </div>

    <!-- Error -->
    <v-alert
      v-else-if="error"
      type="warning"
      variant="tonal"
      density="compact"
      class="ma-3"
    >
      {{ error }}
      <template #append>
        <v-btn size="small" variant="text" @click="$emit('load-similar')">
          Reintentar
        </v-btn>
      </template>
    </v-alert>

    <!-- Lista de documentos similares -->
    <div v-else class="similar-docs-container pa-2">
      <!-- Advertencia de baja similaridad -->
      <v-alert
        v-if="hasLowSimilarity"
        type="warning"
        variant="tonal"
        density="compact"
        class="mb-3"
      >
        <div class="d-flex align-center">
          <v-icon start>mdi-alert-circle-outline</v-icon>
          <span class="text-caption">
            Los siguientes documentos tienen <strong>baja similaridad</strong>.
            Los resultados pueden no ser muy relevantes.
          </span>
        </div>
      </v-alert>
      <v-card
        v-for="(doc, idx) in similarDocs"
        :key="idx"
        class="similar-doc-card mb-3"
        variant="outlined"
        @click="$emit('compare-document', doc)"
      >
        <v-tooltip activator="parent" location="top">
          Clic para comparar documentos
        </v-tooltip>
        <v-card-text class="pa-3">
          <!-- Similarity Badges -->
          <div
            class="d-flex justify-space-between align-start mb-3 flex-wrap gap-2"
          >
            <div class="d-flex gap-1 flex-wrap">
              <!-- Hybrid Score (principal) -->
              <v-chip
                v-if="doc.hybrid_score"
                :color="getSimilarityColor(doc.hybrid_score)"
                size="small"
                variant="flat"
                class="similarity-chip font-weight-bold text-white"
              >
                <v-icon start size="small">mdi-chart-line</v-icon>
                {{ (doc.hybrid_score * 100).toFixed(1) }}% Score
              </v-chip>

              <!-- Semantic Score -->
              <v-chip
                v-if="doc.semantic_score || doc.similarity_score"
                color="#736D5D"
                size="small"
                variant="outlined"
                class="font-weight-medium"
              >
                <v-icon start size="x-small">mdi-brain</v-icon>
                Sem:
                {{
                  ((doc.semantic_score || doc.similarity_score) * 100).toFixed(
                    1
                  )
                }}%
              </v-chip>

              <!-- BM25 Score -->
              <v-chip
                v-if="doc.bm25_score"
                color="#736D5D"
                size="small"
                variant="outlined"
                class="font-weight-medium"
              >
                <v-icon start size="x-small">mdi-text-search</v-icon>
                BM25: {{ doc.bm25_score.toFixed(2) }}
              </v-chip>

              <!-- Metadata Boost -->
              <v-chip
                v-if="doc.metadata_boost && doc.metadata_boost > 0"
                color="green-darken-1"
                size="small"
                variant="tonal"
                class="font-weight-medium"
              >
                <v-icon start size="x-small">mdi-arrow-up-circle</v-icon>
                +{{ (doc.metadata_boost * 100).toFixed(1) }}%
              </v-chip>

              <!-- Penalties -->
              <v-chip
                v-if="doc.penalties && doc.penalties < 0"
                color="orange-darken-2"
                size="small"
                variant="tonal"
                class="font-weight-medium"
              >
                <v-icon start size="x-small">mdi-arrow-down-circle</v-icon>
                {{ (doc.penalties * 100).toFixed(1) }}%
              </v-chip>
            </div>

            <v-icon size="small" color="#8c0d0d">mdi-arrow-expand-right</v-icon>
          </div>

          <!-- Título -->
          <div class="similar-title text-subtitle-2 font-weight-medium mb-2">
            {{ doc.title }}
          </div>

          <!-- Similarity Reasons -->
          <div
            v-if="doc.similarity_reasons && doc.similarity_reasons.length > 0"
            class="mb-3"
          >
            <div
              class="text-caption mb-1 font-weight-medium"
              style="color: #8c0d0d"
            >
              <v-icon size="small" class="mr-1">mdi-information-outline</v-icon>
              ¿Por qué es similar?
            </div>
            <div class="d-flex flex-column gap-2">
              <div
                v-for="(reason, ridx) in formatSimilarityReasons(
                  doc.similarity_reasons
                )"
                :key="ridx"
                class="reason-item px-3 py-2"
                :class="reason.isPenalty ? 'reason-penalty' : 'reason-boost'"
              >
                <div class="d-flex align-start gap-2">
                  <v-icon
                    :size="16"
                    :color="reason.isPenalty ? '#D9A3A3' : '#736D5D'"
                    class="mt-1 flex-shrink-0"
                  >
                    {{
                      reason.isPenalty
                        ? "mdi-alert-circle-outline"
                        : "mdi-check-circle-outline"
                    }}
                  </v-icon>
                  <div class="flex-grow-1">
                    <div
                      class="text-caption font-weight-medium mb-1"
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
                      :style="{
                        backgroundColor: reason.isPenalty
                          ? '#D9A3A3'
                          : '#736D5D',
                        color: 'white',
                      }"
                      variant="flat"
                      class="mt-1"
                    >
                      {{ reason.isPenalty ? "" : "+"
                      }}{{ (reason.weight * 100).toFixed(1) }}%
                    </v-chip>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Metadata -->
          <div class="d-flex gap-2 flex-wrap">
            <v-chip
              v-if="doc.doc_type?.name"
              size="x-small"
              variant="flat"
              style="background-color: #736d5d"
              class="text-white"
            >
              <v-icon start size="x-small">mdi-file-document-outline</v-icon>
              {{ doc.doc_type.name }}
            </v-chip>
            <v-chip
              v-if="doc.legal_area?.name"
              size="x-small"
              variant="flat"
              style="background-color: #8c0d0d"
              class="text-white"
            >
              <v-icon start size="x-small">mdi-scale-balance</v-icon>
              {{ doc.legal_area.name }}
            </v-chip>
            <v-chip
              v-if="doc.document_date"
              size="x-small"
              variant="outlined"
              color="#736D5D"
            >
              <v-icon start size="x-small">mdi-calendar-outline</v-icon>
              {{ formatDate(doc.document_date) }}
            </v-chip>
          </div>
        </v-card-text>
      </v-card>
    </div>
  </div>
</template>

<script setup>
import { getSimilarityColor } from "@/composables/useColors";
import { formatDate } from "@/composables/useFormatting";
import { computed } from "vue";

const props = defineProps({
  selected: {
    type: Object,
    required: true,
  },
  similarDocs: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
  error: {
    type: String,
    default: null,
  },
  embeddingField: {
    type: String,
    default: "clean_embedding",
  },
});

defineEmits(["compare-document", "load-similar", "update:embedding-field"]);

/**
 * Verifica si todos los documentos similares tienen baja similaridad
 * (hybrid_score < 0.5)
 */
const hasLowSimilarity = computed(() => {
  if (!props.similarDocs || props.similarDocs.length === 0) return false;

  // Si todos los documentos tienen hybrid_score < 0.5, mostrar advertencia
  const lowThreshold = 0.5;
  return props.similarDocs.every(
    (doc) => (doc.hybrid_score || 0) < lowThreshold
  );
});

/**
 * Formatea las razones de similitud para mostrarlas de forma legible
 */
function formatSimilarityReasons(reasons) {
  if (!reasons || !Array.isArray(reasons)) {
    return [];
  }

  // Mapeo de categorías a nombres profesionales
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

  return reasons.map((reason) => {
    // Si ya es un string simple, retornar formato básico
    if (typeof reason === "string") {
      return {
        category: "Similitud General",
        detail: reason,
        weight: null,
        isPenalty: false,
      };
    }

    // Si es un objeto con estructura completa
    if (typeof reason === "object" && reason !== null) {
      const categoryKey = reason.category || "unknown";
      const categoryName =
        categoryNames[categoryKey] || categoryKey.replace(/_/g, " ");

      // Acortar detalles muy largos
      let detail = reason.detail || "Sin detalles";
      if (detail.length > 150) {
        detail = detail.substring(0, 147) + "...";
      }

      // Detectar si es penalización (varios formatos posibles)
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

    // Fallback
    return {
      category: "Información",
      detail: JSON.stringify(reason),
      weight: null,
      isPenalty: false,
    };
  });
}
</script>

<style scoped lang="scss">
@import "@/styles/variables.scss";

.similar-docs-container {
  max-height: calc(100vh - 400px);
  overflow-y: auto;
  @include scrollbar-pj;
}

.similar-doc-card {
  cursor: pointer;
  border-radius: $border-radius-md;
  transition: all $transition-base;
  border: 1px solid rgba($pj-brown-grey, 0.2);
  background-color: white;

  &:hover {
    transform: translateY(-1px);
    box-shadow: $shadow-pj-md;
    border-color: $pj-red-primary;
    background-color: rgba($pj-grey-light, 0.5);

    .similar-title {
      color: $pj-red-primary;
    }
  }

  &:active {
    transform: translateY(0);
    box-shadow: $shadow-pj-sm;
  }
}

.similar-title {
  line-height: 1.4;
  transition: color $transition-fast;
  @include truncate-text(2);
}

.similarity-chip {
  font-weight: 600;
  letter-spacing: 0.3px;
}

.empty-state {
  padding: $spacing-3xl $spacing-xl;
}

.reason-item {
  border-radius: $border-radius-sm;
  transition: all $transition-fast;

  &.reason-boost {
    background-color: rgba($pj-brown-grey, 0.08);
    border-left: 3px solid $pj-brown-grey;
  }

  &.reason-penalty {
    background-color: rgba($pj-red-light, 0.15);
    border-left: 3px solid $pj-red-dark;
  }

  &:hover {
    background-color: rgba($pj-grey-light, 0.8);
    transform: translateX(2px);
  }
}
</style>
