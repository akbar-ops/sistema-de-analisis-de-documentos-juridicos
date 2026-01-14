<template>
  <v-card class="search-panel elevation-2 rounded-lg">
    <v-card-title class="d-flex align-center px-4 py-3 bg-gradient">
      <v-icon class="me-2" color="white" size="large"
        >mdi-file-search-outline</v-icon
      >
      <span class="text-h6 text-white font-weight-bold"
        >Búsqueda Avanzada de Documentos</span
      >
    </v-card-title>

    <v-card-text class="pt-4 pb-4">
      <!-- Campo de búsqueda principal -->
      <div class="search-box mb-4">
        <v-text-field
          v-model="searchQuery"
          label="Buscar documentos por contenido..."
          placeholder="Ej: Robo agravado en Lima, despido arbitrario, derechos laborales..."
          prepend-inner-icon="mdi-text-search"
          variant="solo"
          density="comfortable"
          clearable
          bg-color="grey-lighten-4"
          @keyup.enter="performSearch"
          hide-details
        >
          <template #append-inner>
            <v-chip
              v-if="semanticSearch"
              size="small"
              color="deep-purple"
              variant="flat"
              class="me-2"
            >
              <v-icon start size="small">mdi-brain</v-icon>
              IA
            </v-chip>
          </template>
        </v-text-field>
      </div>

      <!-- Switch búsqueda semántica con mejor diseño -->
      <v-card variant="tonal" color="deep-purple" class="mb-4 pa-3">
        <div class="d-flex align-center justify-space-between">
          <div class="d-flex align-center">
            <v-icon color="deep-purple-darken-2" class="me-2">mdi-brain</v-icon>
            <div>
              <div class="text-subtitle-2 font-weight-bold">
                Búsqueda Semántica (IA)
              </div>
              <div class="text-caption text-grey-darken-1">
                Encuentra documentos por significado, no solo por palabras
                exactas
              </div>
            </div>
          </div>
          <v-switch
            v-model="semanticSearch"
            color="deep-purple"
            hide-details
            inset
          />
        </div>

        <!-- Selector de tipo de embedding (solo visible si búsqueda semántica activa) -->
        <v-expand-transition>
          <div
            v-if="semanticSearch"
            class="mt-3 pt-3 border-t border-deep-purple-lighten-4"
          >
            <div class="text-caption text-grey-darken-1 mb-2">
              Tipo de representación vectorial:
            </div>
            <v-btn-toggle
              v-model="embeddingField"
              mandatory
              density="compact"
              color="deep-purple"
              variant="outlined"
              class="flex-wrap"
            >
              <v-btn value="clean_embedding" size="small">
                <v-icon start size="small">mdi-broom</v-icon>
                Limpio (768d)
              </v-btn>
              <v-btn value="enhanced_embedding" size="small">
                <v-icon start size="small">mdi-auto-fix</v-icon>
                Mejorado (384d)
              </v-btn>
              <v-btn value="summary_embedding" size="small">
                <v-icon start size="small">mdi-text-box-outline</v-icon>
                Resumen
              </v-btn>
            </v-btn-toggle>
            <div class="text-caption text-grey mt-1">
              <span v-if="embeddingField === 'clean_embedding'">
                Embedding de texto limpio con stopwords removidos (768
                dimensiones)
              </span>
              <span v-else-if="embeddingField === 'enhanced_embedding'">
                Embedding mejorado con metadatos (384 dimensiones)
              </span>
              <span v-else> Embedding basado en el resumen del documento </span>
            </div>
          </div>
        </v-expand-transition>
      </v-card>

      <!-- Panel de filtros mejorado -->
      <v-expansion-panels variant="accordion" class="mb-4">
        <v-expansion-panel elevation="0" class="border">
          <v-expansion-panel-title class="font-weight-medium">
            <template #default="{ expanded }">
              <div class="d-flex align-center">
                <v-icon
                  :class="{ 'rotate-180': expanded }"
                  class="me-2 transition-all"
                >
                  mdi-filter-variant
                </v-icon>
                <span>Filtros Adicionales</span>
                <v-chip
                  v-if="activeFiltersCount > 0"
                  size="small"
                  color="primary"
                  variant="flat"
                  class="ml-2"
                >
                  {{ activeFiltersCount }} activos
                </v-chip>
              </div>
            </template>
          </v-expansion-panel-title>

          <v-expansion-panel-text>
            <v-row dense class="mt-2">
              <!-- Número de expediente -->
              <v-col cols="12" md="6">
                <v-text-field
                  v-model="filters.caseNumber"
                  label="Nº Expediente"
                  placeholder="Ej: 12345-2024"
                  prepend-inner-icon="mdi-folder-text"
                  density="compact"
                  variant="outlined"
                  clearable
                  hide-details
                />
              </v-col>

              <!-- Número de resolución -->
              <v-col cols="12" md="6">
                <v-text-field
                  v-model="filters.resolutionNumber"
                  label="Nº Resolución"
                  placeholder="Ej: 279-2024"
                  prepend-inner-icon="mdi-file-document-outline"
                  density="compact"
                  variant="outlined"
                  clearable
                  hide-details
                />
              </v-col>

              <!-- Área legal -->
              <v-col cols="12" md="6">
                <v-select
                  v-model="filters.legalAreaId"
                  :items="legalAreas"
                  item-title="name"
                  item-value="area_id"
                  label="Área Legal"
                  prepend-inner-icon="mdi-scale-balance"
                  density="compact"
                  variant="outlined"
                  clearable
                  hide-details
                />
              </v-col>

              <!-- Tipo de documento -->
              <v-col cols="12" md="6">
                <v-select
                  v-model="filters.docTypeId"
                  :items="docTypes"
                  item-title="name"
                  item-value="type_id"
                  label="Tipo de Documento"
                  prepend-inner-icon="mdi-file-multiple"
                  density="compact"
                  variant="outlined"
                  clearable
                  hide-details
                />
              </v-col>

              <!-- Lugar de emisión -->
              <v-col cols="12" md="6">
                <v-text-field
                  v-model="filters.issuePlace"
                  label="Lugar de Emisión"
                  placeholder="Ej: Lima, Puno, Arequipa"
                  prepend-inner-icon="mdi-map-marker"
                  density="compact"
                  variant="outlined"
                  clearable
                  hide-details
                />
              </v-col>

              <!-- Rango de fechas -->
              <v-col cols="12" md="3">
                <v-text-field
                  v-model="filters.dateFrom"
                  label="Fecha Desde"
                  type="date"
                  prepend-inner-icon="mdi-calendar-start"
                  density="compact"
                  variant="outlined"
                  clearable
                  hide-details
                />
              </v-col>

              <v-col cols="12" md="3">
                <v-text-field
                  v-model="filters.dateTo"
                  label="Fecha Hasta"
                  type="date"
                  prepend-inner-icon="mdi-calendar-end"
                  density="compact"
                  variant="outlined"
                  clearable
                  hide-details
                />
              </v-col>
            </v-row>

            <!-- Botón limpiar filtros -->
            <v-row dense class="mt-3">
              <v-col>
                <v-btn
                  block
                  variant="outlined"
                  color="error"
                  @click="localClearFilters"
                  :disabled="activeFiltersCount === 0"
                >
                  <v-icon start>mdi-filter-remove</v-icon>
                  Limpiar todos los filtros
                </v-btn>
              </v-col>
            </v-row>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>

      <!-- Botón de búsqueda principal mejorado -->
      <v-btn
        color="primary"
        block
        size="x-large"
        elevation="2"
        @click="performSearch"
        :loading="loading"
        class="text-h6 font-weight-bold mb-4"
      >
        <v-icon start size="large">mdi-magnify</v-icon>
        {{ loading ? "Buscando..." : "Buscar Documentos" }}
      </v-btn>

      <!-- Resultados mejorados -->
      <div v-if="searchPerformed || hasDocuments">
        <v-divider class="my-4" />

        <div class="d-flex align-center justify-space-between mb-3">
          <div class="d-flex align-center">
            <v-icon color="primary" class="me-2"
              >mdi-file-document-multiple</v-icon
            >
            <h3 class="text-h6 font-weight-bold">
              {{
                searchPerformed
                  ? "Resultados de Búsqueda"
                  : "Todos los Documentos"
              }}
            </h3>
            <v-chip size="small" color="primary" variant="flat" class="ml-2">
              {{ displayDocuments.length }}
            </v-chip>
          </div>

          <v-btn
            v-if="searchPerformed"
            size="small"
            variant="text"
            color="grey"
            @click="localClearResults"
          >
            <v-icon start>mdi-close</v-icon>
            Limpiar búsqueda
          </v-btn>
        </div>

        <!-- Loading State -->
        <LoadingState
          v-if="loading"
          variant="large"
          message="Cargando documentos..."
        />

        <!-- Empty State -->
        <EmptyState
          v-else-if="displayDocuments.length === 0"
          :icon="
            searchPerformed ? 'mdi-file-search' : 'mdi-file-document-outline'
          "
          icon-size="64"
          icon-color="grey-darken-1"
          :title="
            searchPerformed
              ? 'No se encontraron documentos'
              : 'No hay documentos cargados'
          "
          :message="
            searchPerformed
              ? 'Intenta ajustar los filtros o cambiar el término de búsqueda'
              : 'Sube documentos para comenzar'
          "
        />

        <!-- Results List -->
        <div v-else class="results-container">
          <v-card
            v-for="(doc, idx) in displayDocuments"
            :key="idx"
            class="result-card mb-3 transition-all"
            elevation="2"
            hover
            @click="selectDocument(doc)"
          >
            <v-card-text class="pa-4">
              <div class="d-flex align-start">
                <v-avatar color="primary" size="56" class="me-3 flex-shrink-0">
                  <v-icon color="white" size="x-large"
                    >mdi-file-document</v-icon
                  >
                </v-avatar>

                <div class="flex-grow-1">
                  <!-- Título y similitud -->
                  <div class="d-flex align-center justify-space-between mb-2">
                    <h4 class="text-h6 font-weight-bold text-primary mb-0">
                      {{ doc.title }}
                    </h4>
                    <v-chip
                      v-if="doc.similarity_score"
                      size="default"
                      :color="getSimilarityColor(doc.similarity_score)"
                      variant="flat"
                      class="ml-2 flex-shrink-0"
                    >
                      <v-icon start size="small">mdi-percent</v-icon>
                      {{ Math.round(doc.similarity_score * 100) }}%
                    </v-chip>
                  </div>

                  <!-- Metadata principal -->
                  <div class="d-flex flex-wrap gap-2 mb-3">
                    <v-chip
                      v-if="doc.legal_area?.name"
                      size="small"
                      color="blue"
                      variant="flat"
                      prepend-icon="mdi-scale-balance"
                    >
                      {{ doc.legal_area.name }}
                    </v-chip>
                    <v-chip
                      v-if="doc.doc_type?.name"
                      size="small"
                      color="green"
                      variant="flat"
                      prepend-icon="mdi-file-outline"
                    >
                      {{ doc.doc_type.name }}
                    </v-chip>
                    <v-chip
                      v-if="doc.legal_subject"
                      size="small"
                      color="purple"
                      variant="outlined"
                      prepend-icon="mdi-gavel"
                    >
                      {{ doc.legal_subject }}
                    </v-chip>
                  </div>

                  <!-- Información de caso -->
                  <div
                    v-if="
                      doc.case_number ||
                      doc.resolution_number ||
                      doc.issue_place ||
                      doc.document_date ||
                      doc.jurisdictional_body ||
                      doc.created_at
                    "
                    class="mb-2"
                  >
                    <v-chip
                      v-if="doc.case_number"
                      size="small"
                      variant="outlined"
                      prepend-icon="mdi-folder-text"
                      class="me-1 mb-1"
                    >
                      Exp: {{ doc.case_number }}
                    </v-chip>
                    <v-chip
                      v-if="doc.resolution_number"
                      size="small"
                      variant="outlined"
                      prepend-icon="mdi-file-document-outline"
                      class="me-1 mb-1"
                    >
                      Res: {{ doc.resolution_number }}
                    </v-chip>
                    <v-chip
                      v-if="doc.jurisdictional_body"
                      size="small"
                      variant="outlined"
                      prepend-icon="mdi-gavel"
                      class="me-1 mb-1"
                    >
                      {{ doc.jurisdictional_body }}
                    </v-chip>
                    <v-chip
                      v-if="doc.issue_place"
                      size="small"
                      variant="outlined"
                      prepend-icon="mdi-map-marker"
                      class="me-1 mb-1"
                    >
                      {{ doc.issue_place }}
                    </v-chip>
                    <v-chip
                      v-if="doc.document_date"
                      size="small"
                      variant="outlined"
                      prepend-icon="mdi-calendar"
                      class="me-1 mb-1"
                    >
                      Emitido: {{ formatDate(doc.document_date) }}
                    </v-chip>
                    <v-chip
                      v-if="doc.created_at"
                      size="small"
                      variant="tonal"
                      color="grey"
                      prepend-icon="mdi-clock-outline"
                      class="me-1 mb-1"
                    >
                      Subido: {{ formatDate(doc.created_at) }}
                    </v-chip>
                  </div>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- Controles de Paginación -->
        <PaginationControls
          v-if="!searchPerformed && pagination.totalPages > 1"
          :current-page="pagination.currentPage"
          :page-size="pagination.pageSize"
          :total-items="pagination.totalItems"
          :total-pages="pagination.totalPages"
          :has-next="pagination.hasNext"
          :has-previous="pagination.hasPrevious"
          item-label="documentos"
          @next="nextPage"
          @previous="previousPage"
          @update:page-size="changePageSize"
        />
      </div>
      <!-- Cierre de searchPerformed || hasDocuments -->
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, onMounted, watch } from "vue";
import axios from "axios";
import PaginationControls from "./PaginationControls.vue";
import LoadingState from "./shared/LoadingState.vue";
import EmptyState from "./shared/EmptyState.vue";
import { useSearch } from "@/composables/useSearch";
import { useCatalogs } from "@/composables/useCatalogs";
import { getSimilarityColor } from "@/composables/useColors";
import { formatDate } from "@/composables/useFormatting";
import { debounce } from "@/utils/performance";

const emit = defineEmits(["select-document"]);

// Usar composables
const {
  searchQuery,
  semanticSearch,
  embeddingField,
  loading,
  searchPerformed,
  results,
  allDocuments,
  pagination,
  filters: searchFilters,
  activeFiltersCount,
  displayDocuments,
  hasDocuments,
  fetchDocuments,
  searchDocuments,
  clearSearch,
  clearFilters: clearSearchFilters,
  handlePageChange,
} = useSearch();

const { legalAreas, docTypes, fetchAll: fetchCatalogs } = useCatalogs();

// Filtros adicionales específicos de este componente
const filters = ref({
  caseNumber: null,
  resolutionNumber: null,
  legalAreaId: null,
  docTypeId: null,
  issuePlace: null,
  dateFrom: null,
  dateTo: null,
});

// Exponer método para recargar desde el padre
defineExpose({
  reload: fetchDocuments,
});

// ===============================
// MÉTODOS
// ===============================

// Limpiar filtros locales
function localClearFilters() {
  filters.value = {
    caseNumber: null,
    resolutionNumber: null,
    legalAreaId: null,
    docTypeId: null,
    issuePlace: null,
    dateFrom: null,
    dateTo: null,
  };
}

// Búsqueda con filtros del componente
async function performSearch() {
  await searchDocuments({
    query: searchQuery.value || null,
    case_number: filters.value.caseNumber || null,
    resolution_number: filters.value.resolutionNumber || null,
    legal_area_id: filters.value.legalAreaId || null,
    doc_type_id: filters.value.docTypeId || null,
    issue_place: filters.value.issuePlace || null,
    date_from: filters.value.dateFrom || null,
    date_to: filters.value.dateTo || null,
  });
}

// Limpiar resultados y filtros
function localClearResults() {
  clearSearch();
  localClearFilters();
}

// Pagination handlers usando composable
function nextPage() {
  handlePageChange(pagination.value.currentPage + 1);
}

function previousPage() {
  handlePageChange(pagination.value.currentPage - 1);
}

function changePageSize(newSize) {
  pagination.value.pageSize = newSize;
  handlePageChange(1);
}

// Seleccionar documento
function selectDocument(doc) {
  emit("select-document", doc);
}

// ===============================
// WATCHERS CON DEBOUNCE
// ===============================

// Debounce automático en cambios de búsqueda (300ms)
const debouncedSearch = debounce(() => {
  if (searchQuery.value && searchQuery.value.length >= 3) {
    performSearch();
  }
}, 300);

// Watch para búsqueda automática
watch(searchQuery, () => {
  if (searchQuery.value && searchQuery.value.length >= 3) {
    debouncedSearch();
  }
});

onMounted(async () => {
  await fetchCatalogs(); // Cargar áreas legales y tipos de documento
  await fetchDocuments(); // Cargar todos los documentos al inicio
});
</script>

<style scoped lang="scss">
@import "@/styles/variables.scss";

.search-panel {
  margin-bottom: $spacing-md;
}

.bg-gradient {
  background: linear-gradient(135deg, $pj-red-primary 0%, $pj-red-dark 100%);
}

.result-card {
  cursor: pointer;
  border-radius: $border-radius-lg;
  border: 1px solid rgba($pj-brown-grey, 0.2);
  transition: all $transition-slow;

  &:hover {
    transform: translateY(-4px);
    box-shadow: $shadow-pj-lg;
    border-color: $pj-red-primary;
  }
}

.summary-preview {
  background-color: rgba($pj-grey-light, 0.8);
  padding: $spacing-sm;
  border-radius: $border-radius-md;
  border-left: 3px solid $pj-red-primary;
}

.results-container {
  max-height: 700px;
  overflow-y: auto;
  padding-right: 4px;
  @include scrollbar-pj;
}

.gap-1 {
  gap: $spacing-xs;
}

.gap-2 {
  gap: $spacing-sm;
}

.border-t {
  border-top: 1px solid rgba(0, 0, 0, 0.1);
}

.rotate-180 {
  transform: rotate(180deg);
}

.transition-all {
  transition: all $transition-slow;
}

.border {
  border: 1px solid rgba($pj-brown-grey, 0.12);
}
</style>
