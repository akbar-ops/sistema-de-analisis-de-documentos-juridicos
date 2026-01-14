<template>
  <div class="doc-details-panel" :class="{ 'is-open': isOpen }">
    <!-- Botón Toggle -->
    <v-btn
      v-if="!isOpen"
      icon
      class="toggle-btn"
      color="primary"
      size="small"
      elevation="4"
      @click="openPanel"
      :disabled="!selected"
    >
      <v-icon>mdi-chevron-left</v-icon>
    </v-btn>

    <!-- Panel Container -->
    <div class="panel-container">
      <!-- Header con botón cerrar -->
      <div class="panel-header">
        <v-btn
          icon
          size="small"
          variant="text"
          @click="closePanel"
          class="close-btn"
        >
          <v-icon>mdi-chevron-right</v-icon>
        </v-btn>
      </div>

      <!-- Contenido -->
      <div class="panel-content">
        <!-- Sin documento seleccionado -->
        <div v-if="!selected" class="empty-state">
          <v-icon size="64" color="grey-lighten-1"
            >mdi-file-document-outline</v-icon
          >
          <p class="text-h6 text-grey mt-4">No hay documento seleccionado</p>
          <p class="text-caption text-grey">
            Selecciona un documento de la lista para ver sus detalles
          </p>
        </div>

        <!-- Con documento seleccionado -->
        <div v-else class="document-content">
          <!-- Título destacado -->
          <v-card variant="flat" class="mb-4" style="background-color: #f2f2f2">
            <v-card-text class="pa-3">
              <div
                class="text-overline mb-1"
                style="font-size: 0.65rem; color: #736d5d"
              >
                DOCUMENTO SELECCIONADO
              </div>
              <div
                class="text-subtitle-2 font-weight-bold"
                style="color: #731414"
              >
                {{ selected.title }}
              </div>
            </v-card-text>
          </v-card>
          <!-- Botones de acción -->
          <div class="action-buttons mb-4">
            <v-btn
              v-if="selected.file_path"
              block
              size="small"
              variant="flat"
              prepend-icon="mdi-file-eye-outline"
              @click="openPreview"
              class="mb-2"
              style="background-color: #736d5d; color: white"
            >
              Ver documento
            </v-btn>

            <v-tooltip
              location="bottom"
              text="Abrir en nueva pestaña para analizar con IA"
            >
              <template v-slot:activator="{ props }">
                <v-btn
                  v-bind="props"
                  block
                  size="small"
                  variant="flat"
                  prepend-icon="mdi-chat-processing-outline"
                  @click="navigateToDocumentChat"
                  style="background-color: #8c0d0d; color: white"
                >
                  Chat con Documento
                  <v-icon end size="x-small">mdi-open-in-new</v-icon>
                </v-btn>
              </template>
            </v-tooltip>
          </div>

          <!-- Tabs -->
          <v-tabs
            v-model="activeTab"
            color="primary"
            density="compact"
            class="mb-3"
          >
            <v-tab value="details">
              <v-icon start size="small">mdi-text-box-outline</v-icon>
              Detalles
            </v-tab>
            <v-tab value="summary">
              <v-icon start size="small">mdi-file-document-outline</v-icon>
              Resumen
            </v-tab>
            <v-tab value="persons">
              <v-icon start size="small">mdi-account-group-outline</v-icon>
              Personas
              <v-badge
                v-if="validPersonsCount > 0"
                :content="validPersonsCount"
                inline
                class="ml-1"
                style="--v-badge-background-color: #8c0d0d"
              />
            </v-tab>
            <v-tab value="analyze">
              <v-icon start size="small">mdi-file-chart-outline</v-icon>
              Analizar
            </v-tab>
            <v-tab value="similar">
              <v-icon start size="small">mdi-file-compare</v-icon>
              Similares
            </v-tab>
            <v-tab value="cluster" v-if="selected.status === 'processed'">
              <v-icon start size="small">mdi-graph-outline</v-icon>
              Cluster
            </v-tab>
            <v-tab value="writing" v-if="selected.status === 'processed'">
              <v-icon start size="small">mdi-pen</v-icon>
              Redacción
            </v-tab>
          </v-tabs>

          <!-- Tab Content -->
          <div class="tabs-content">
            <v-window v-model="activeTab">
              <!-- TAB 1: DETALLES -->
              <v-window-item value="details">
                <DetailsTab :selected="selected" />
              </v-window-item>

              <!-- TAB 2: RESUMEN -->
              <v-window-item value="summary">
                <SummaryTab :selected="selected" />
              </v-window-item>

              <!-- TAB 3: PERSONAS -->
              <v-window-item value="persons">
                <PersonsTab
                  :persons="validPersons"
                  :has-persons="hasValidPersons"
                />
              </v-window-item>

              <!-- TAB 4: ANÁLISIS -->
              <v-window-item value="analyze">
                <AnalyzeTab
                  :selected="selected"
                  :analysis-parts="analysisParts"
                  :analyzing="analyzingDocument"
                  @analyze="handleAnalyze"
                />
              </v-window-item>

              <!-- TAB 5: SIMILARES -->
              <v-window-item value="similar">
                <SimilarTab
                  :selected="selected"
                  :similar-docs="similarDocs"
                  :loading="loadingSimilar"
                  :error="similarError"
                  :embedding-field="similarEmbeddingField"
                  @compare-document="handleCompareDocument"
                  @load-similar="loadSimilarDocs"
                  @update:embedding-field="handleEmbeddingFieldChange"
                />
              </v-window-item>

              <!-- TAB 6: CLUSTER -->
              <v-window-item
                value="cluster"
                v-if="selected.status === 'processed'"
              >
                <ClusterTab :selected="selected" />
              </v-window-item>

              <!-- TAB 7: REDACCIÓN -->
              <v-window-item
                value="writing"
                v-if="selected.status === 'processed'"
              >
                <WritingTab :selected="selected" />
              </v-window-item>
            </v-window>
          </div>
        </div>
      </div>
    </div>

    <!-- Comparison Dialog -->
    <ComparisonDialog
      v-model="showComparisonDialog"
      :current-doc="selected"
      :similar-doc="selectedSimilarDoc"
      @navigate-to-similar="handleNavigateToSimilar"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from "vue";
import { useRouter } from "vue-router";
import axios from "axios";

// Importar sub-componentes
import DetailsTab from "./DocDetailsTabs/DetailsTab.vue";
import SummaryTab from "./DocDetailsTabs/SummaryTab.vue";
import PersonsTab from "./DocDetailsTabs/PersonsTab.vue";
import AnalyzeTab from "./DocDetailsTabs/AnalyzeTab.vue";
import SimilarTab from "./DocDetailsTabs/SimilarTab.vue";
import ClusterTab from "./DocDetailsTabs/ClusterTab.vue";
import WritingTab from "./DocDetailsTabs/WritingTab.vue";
import ComparisonDialog from "./ComparisonDialog.vue";

const router = useRouter();

// ============================================================================
// PROPS & EMITS
// ============================================================================
const props = defineProps({
  selected: Object,
});

const emit = defineEmits([
  "open-chat",
  "close-chat",
  "toggle-panel",
  "select-document",
]);

// ============================================================================
// STATE
// ============================================================================
const isOpen = ref(false);
const activeTab = ref("details");

// Estados para documentos similares
const similarDocs = ref([]);
const loadingSimilar = ref(false);
const similarError = ref(null);
const similarEmbeddingField = ref("clean_embedding"); // Tipo de embedding para similares

// Estados para análisis
const analysisParts = ref([]);
const analyzingDocument = ref(false);

// Estados para comparación de documentos
const showComparisonDialog = ref(false);
const selectedSimilarDoc = ref(null);

// ============================================================================
// COMPUTED
// ============================================================================
const validPersons = computed(() => {
  if (!props.selected?.persons) return [];
  return props.selected.persons.filter((p) => p.name || p.person?.name);
});

const validPersonsCount = computed(() => validPersons.value.length);

const hasValidPersons = computed(() => validPersonsCount.value > 0);

// ============================================================================
// WATCHERS
// ============================================================================

// Auto-abrir panel y limpiar datos cuando se selecciona un documento
watch(
  () => props.selected,
  (newDoc, oldDoc) => {
    if (newDoc && newDoc !== oldDoc) {
      // NO cerrar el diálogo aquí - dejar que se cierre naturalmente
      // solo limpiar si no hay diálogo abierto
      if (!showComparisonDialog.value) {
        selectedSimilarDoc.value = null;
      }

      // Limpiar datos del documento anterior
      similarDocs.value = [];
      similarError.value = null;
      analysisParts.value = [];

      // Abrir panel si está cerrado
      if (!isOpen.value) {
        openPanel();
      }

      // Si el tab de similares está activo, cargar los nuevos
      if (activeTab.value === "similar") {
        loadSimilarDocs();
      }
    } else if (!newDoc) {
      // Si no hay documento seleccionado, cerrar todo
      showComparisonDialog.value = false;
      selectedSimilarDoc.value = null;
      closePanel();
    }
  }
);

watch(isOpen, (newVal) => {
  emit("toggle-panel", newVal);
});

// Auto-cargar similares cuando se abre el tab
watch(activeTab, async (newVal) => {
  if (
    newVal === "similar" &&
    props.selected &&
    similarDocs.value.length === 0
  ) {
    await loadSimilarDocs();
  }
});

// ============================================================================
// METHODS - PANEL CONTROL
// ============================================================================
function openPanel() {
  if (!props.selected) return;
  isOpen.value = true;
  activeTab.value = "details";
}

function closePanel() {
  isOpen.value = false;
}

function togglePanel() {
  if (isOpen.value) {
    closePanel();
  } else {
    openPanel();
  }
}

// ============================================================================
// METHODS - ACTIONS
// ============================================================================
function openPreview() {
  if (!props.selected?.file_path) return;
  const url = `http://localhost:8000${props.selected.file_path}`;
  window.open(url, "_blank");
}

function handleOpenChat() {
  emit("open-chat");
}

// Navigate to document chat view (opens in new tab to preserve state)
function navigateToDocumentChat() {
  if (!props.selected?.document_id) {
    console.warn("No document selected");
    return;
  }

  // Open in new tab to preserve current view state
  const url = `/document/${props.selected.document_id}`;
  window.open(url, "_blank");
}

function handleCompareDocument(doc) {
  selectedSimilarDoc.value = doc;
  showComparisonDialog.value = true;
}

function handleNavigateToSimilar() {
  if (selectedSimilarDoc.value) {
    // Primero guardamos el documento a navegar
    const docToNavigate = selectedSimilarDoc.value;

    console.log("🔄 Navigating to similar document:", {
      document_id: docToNavigate.document_id,
      title: docToNavigate.title,
      fullDoc: docToNavigate,
    });

    // Emitir PRIMERO el evento de navegación
    console.log("✅ Emitting select-document event");
    emit("select-document", docToNavigate);

    // Luego cerrar el diálogo y limpiar después de un pequeño delay
    setTimeout(() => {
      showComparisonDialog.value = false;
      selectedSimilarDoc.value = null;
    }, 50);
  } else {
    console.warn("⚠️ No similar document selected");
  }
}

function handleSelectSimilar(doc) {
  emit("select-document", doc);
}

// ============================================================================
// METHODS - SIMILAR DOCS
// ============================================================================
async function loadSimilarDocs() {
  if (!props.selected?.document_id) return;

  loadingSimilar.value = true;
  similarError.value = null;

  try {
    const response = await axios.get(
      `http://localhost:8000/api/documents/${props.selected.document_id}/similar/`,
      {
        params: {
          top_n: 3,
          min_similarity: 0.0, // Siempre obtener top 3, sin importar el score
          embedding_field: similarEmbeddingField.value,
        },
      }
    );
    similarDocs.value = response.data.similar_documents || [];
  } catch (err) {
    console.error("Error loading similar documents:", err);
    similarError.value =
      err.response?.data?.error || "Error al cargar documentos similares";
  } finally {
    loadingSimilar.value = false;
  }
}

// Manejar cambio de tipo de embedding
function handleEmbeddingFieldChange(newValue) {
  similarEmbeddingField.value = newValue;
  loadSimilarDocs(); // Recargar con el nuevo tipo de embedding
}

// ============================================================================
// METHODS - ANALYZE
// ============================================================================
async function handleAnalyze(options) {
  if (!props.selected?.document_id) return;

  // Soportar tanto el formato nuevo { parts, summarizerType } como el antiguo (solo array)
  const parts = Array.isArray(options) ? options : options.parts;
  const summarizerType = Array.isArray(options)
    ? "ollama"
    : options.summarizerType;

  analyzingDocument.value = true;

  try {
    const response = await axios.post(
      `http://localhost:8000/api/documents/${props.selected.document_id}/analyze/`,
      {
        parts,
        summarizer_type: summarizerType,
      }
    );

    if (response.data.status === "success") {
      analysisParts.value = parts;
      // Recargar el documento para obtener los datos actualizados
      emit("select-document", { ...props.selected });
    }
  } catch (err) {
    console.error("Error analyzing document:", err);
  } finally {
    analyzingDocument.value = false;
  }
}

// ============================================================================
// EXPOSE (para acceso desde parent)
// ============================================================================
defineExpose({
  openPanel,
  closePanel,
  togglePanel,
  isOpen,
});
</script>

<style scoped lang="scss">
@import "@/styles/variables.scss";

/* ===== 🎨 Panel Container ===== */
.doc-details-panel {
  position: fixed;
  top: 64px;
  right: 0;
  bottom: 0;
  width: 500px;
  z-index: $z-modal;
  pointer-events: none;

  &.is-open {
    pointer-events: all;

    .panel-container {
      transform: translateX(0);
    }
  }

  @include responsive(xl) {
    width: 400px;
  }

  @include responsive(md) {
    width: 100%;
  }
}

/* ===== 🔘 Toggle Button ===== */
.toggle-btn {
  position: absolute;
  top: $spacing-md;
  left: -56px;
  z-index: $z-dropdown;
  pointer-events: all;
  box-shadow: $shadow-md;
  transition: all $transition-slow;

  &:hover {
    transform: scale(1.1);
    box-shadow: $shadow-lg;
  }

  &:disabled {
    opacity: 0.4;
  }
}

/* ===== 📦 Panel Container ===== */
.panel-container {
  height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
  background-color: white;
  border-left: 1px solid rgba($pj-brown-grey, 0.2);
  box-shadow: $shadow-pj-lg;
  transform: translateX(100%);
  transition: transform $transition-slow;
}

/* ===== 🎯 Header ===== */
.panel-header {
  padding: $spacing-sm;
  border-bottom: 1px solid rgba($pj-brown-grey, 0.1);
  display: flex;
  justify-content: flex-start;

  .close-btn {
    opacity: 0.7;
    transition: opacity $transition-fast;

    &:hover {
      opacity: 1;
    }
  }
}

/* ===== 📄 Content ===== */
.panel-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  @include scrollbar-pj;
}

/* ===== 🚫 Empty State ===== */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: $spacing-xl;
  text-align: center;
}

/* ===== 📝 Document Content ===== */
.document-content {
  padding: $spacing-md;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.tabs-content {
  margin-top: $spacing-md;
}

/* ===== 📱 Responsive ===== */
@include responsive(md) {
  .toggle-btn {
    left: -50px;
  }

  .document-content {
    padding: $spacing-sm;
  }
}
</style>
