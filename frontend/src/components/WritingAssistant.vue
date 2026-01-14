<template>
  <v-dialog
    v-model="dialog"
    persistent
    scrollable
    scrim="black"
    transition="dialog-bottom-transition"
    content-class="writing-assistant-overlay"
  >
    <template v-slot:activator="{ props: activatorProps }">
      <v-btn
        v-bind="activatorProps"
        color="primary"
        prepend-icon="mdi-pencil-box-outline"
        variant="elevated"
        class="mb-4"
      >
        Asistente de Redacción
      </v-btn>
    </template>

    <div
      class="writing-assistant-container"
      :class="{ 'sidebar-open': sidebarOpen }"
      :style="{
        '--drawer-width': sidebarOpen ? drawerWidth + 'px' : '0px',
      }"
    >
      <v-card color="white" elevation="24" class="writing-assistant-card">
        <!-- Header con navegación -->
        <v-card-title
          class="d-flex align-center pa-4 bg-primary"
          style="position: sticky; top: 0; z-index: 10"
        >
          <!-- Botón atrás (solo en paso 2) -->
          <v-btn
            v-if="step === 2"
            icon
            @click="goBack"
            variant="text"
            class="mr-2"
          >
            <v-icon color="white">mdi-arrow-left</v-icon>
          </v-btn>

          <v-icon v-else class="mr-2" color="white"
            >mdi-pencil-box-outline</v-icon
          >

          <div class="d-flex flex-column">
            <span class="text-h6 text-white">Asistente de Redacción</span>
            <span class="text-caption text-white opacity-80">
              {{
                step === 1
                  ? "Selecciona y configura"
                  : `Resultados: ${selectedSection?.name || ""}`
              }}
            </span>
          </div>

          <v-spacer></v-spacer>

          <v-btn icon @click="closeDialog" variant="text">
            <v-icon color="white">mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-divider></v-divider>

        <!-- Content scrolleable -->
        <v-card-text
          class="pa-6"
          style="height: calc(85vh - 120px); overflow-y: auto"
        >
          <!-- PASO 1: Configuración + Selección de sección -->
          <div v-if="step === 1">
            <!-- Configuración de búsqueda (arriba) -->
            <v-card variant="outlined" class="mb-4">
              <v-card-title class="text-subtitle-1">
                ⚙️ Configuración de Búsqueda
              </v-card-title>
              <v-card-text>
                <v-row>
                  <v-col cols="12" md="4">
                    <v-slider
                      v-model="searchConfig.maxSuggestions"
                      label="Número de ejemplos"
                      :min="1"
                      :max="10"
                      :step="1"
                      thumb-label
                      color="primary"
                    ></v-slider>
                  </v-col>
                  <v-col cols="12" md="4">
                    <v-slider
                      v-model="searchConfig.minQuality"
                      label="Calidad mínima"
                      :min="0"
                      :max="1"
                      :step="0.1"
                      thumb-label
                      color="success"
                    >
                      <template v-slot:thumb-label="{ modelValue }">
                        {{ Math.round(modelValue * 100) }}%
                      </template>
                    </v-slider>
                  </v-col>
                  <v-col cols="12" md="4">
                    <v-slider
                      v-model="searchConfig.minSimilarity"
                      label="Similitud mínima"
                      :min="0"
                      :max="1"
                      :step="0.1"
                      thumb-label
                      color="info"
                    >
                      <template v-slot:thumb-label="{ modelValue }">
                        {{ Math.round(modelValue * 100) }}%
                      </template>
                    </v-slider>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>

            <!-- Selección de sección (abajo) -->
            <v-alert type="info" variant="tonal" class="mb-4">
              <div class="text-subtitle-1 font-weight-medium mb-2">
                ¿Qué sección deseas redactar?
              </div>
              <div class="text-body-2">
                Selecciona una sección. La búsqueda se ejecutará
                automáticamente.
              </div>
            </v-alert>

            <!-- Loading sections -->
            <v-progress-linear
              v-if="loadingSections"
              indeterminate
              color="primary"
              class="mb-4"
            ></v-progress-linear>

            <!-- Secciones disponibles -->
            <v-row
              v-if="!loadingSections && availableSections.length > 0"
              class="mb-4"
            >
              <v-col
                v-for="section in availableSections"
                :key="section.id"
                cols="12"
                md="6"
              >
                <v-card
                  @click="selectSection(section)"
                  :class="{
                    'border-primary': selectedSection?.id === section.id,
                  }"
                  class="section-card"
                  hover
                  variant="outlined"
                >
                  <v-card-text>
                    <div class="d-flex align-center mb-2">
                      <v-icon class="mr-2" color="primary"
                        >mdi-file-document-outline</v-icon
                      >
                      <span class="text-h6">{{ section.name }}</span>
                    </div>
                    <div class="text-caption text-grey-darken-1">
                      {{ section.description }}
                    </div>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>
          </div>

          <!-- PASO 2: Resultados -->
          <div v-if="step === 2">
            <!-- Loading -->
            <div v-if="loadingSuggestions" class="text-center py-12">
              <v-progress-circular
                indeterminate
                size="64"
                color="primary"
              ></v-progress-circular>
              <div class="text-h6 mt-4">
                Buscando ejemplos de buena redacción...
              </div>
              <div class="text-caption text-grey">
                Analizando documentos similares
              </div>
            </div>

            <!-- No results -->
            <v-alert
              v-else-if="suggestions.length === 0"
              type="warning"
              variant="tonal"
            >
              <div class="text-subtitle-1 font-weight-medium mb-2">
                No se encontraron ejemplos
              </div>
              <div class="text-body-2">
                No hay documentos similares con esta sección que cumplan los
                criterios de calidad. Intenta reducir los filtros de calidad o
                similitud.
              </div>
            </v-alert>

            <!-- Results -->
            <div v-else>
              <!-- Tips de estructura y estilo -->
              <v-row class="mb-4">
                <v-col cols="12" md="6" v-if="structureTips.length > 0">
                  <v-card variant="outlined" color="info">
                    <v-card-title class="text-subtitle-1 bg-info-lighten-5">
                      <v-icon class="mr-2">mdi-format-list-bulleted</v-icon>
                      Tips de Estructura
                    </v-card-title>
                    <v-card-text>
                      <ul class="text-body-2">
                        <li
                          v-for="(tip, index) in structureTips"
                          :key="index"
                          class="mb-2"
                        >
                          {{ tip }}
                        </li>
                      </ul>
                    </v-card-text>
                  </v-card>
                </v-col>
                <v-col cols="12" md="6" v-if="styleTips.length > 0">
                  <v-card variant="outlined" color="success">
                    <v-card-title class="text-subtitle-1 bg-success-lighten-5">
                      <v-icon class="mr-2">mdi-format-color-text</v-icon>
                      Tips de Estilo
                    </v-card-title>
                    <v-card-text>
                      <ul class="text-body-2">
                        <li
                          v-for="(tip, index) in styleTips"
                          :key="index"
                          class="mb-2"
                        >
                          {{ tip }}
                        </li>
                      </ul>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>

              <!-- Sugerencias encontradas -->
              <v-alert type="success" variant="tonal" class="mb-4">
                <div class="d-flex align-center">
                  <v-icon class="mr-2">mdi-check-circle</v-icon>
                  <span class="text-subtitle-1">
                    Se encontraron
                    <strong>{{ suggestions.length }}</strong> ejemplos de buena
                    redacción
                  </span>
                </div>
              </v-alert>

              <!-- Lista de sugerencias -->
              <v-expansion-panels
                v-model="expandedSuggestion"
                variant="accordion"
              >
                <v-expansion-panel
                  v-for="(suggestion, index) in suggestions"
                  :key="index"
                  class="mb-3"
                >
                  <v-expansion-panel-title>
                    <div
                      class="d-flex align-items-center justify-space-between w-100 pr-4"
                    >
                      <div class="flex-grow-1">
                        <div class="text-subtitle-1 font-weight-medium">
                          {{ suggestion.document_title }}
                        </div>
                        <div class="text-caption text-grey-darken-1 mt-1">
                          {{ suggestion.metadata.area_legal }} •
                          {{ suggestion.metadata.tipo_documento }}
                        </div>
                      </div>
                      <div class="d-flex gap-2">
                        <v-chip size="small" color="success" variant="flat">
                          <v-icon size="x-small" start>mdi-star</v-icon>
                          Calidad:
                          {{ Math.round(suggestion.quality_score * 100) }}%
                        </v-chip>
                        <v-chip size="small" color="primary" variant="flat">
                          <v-icon size="x-small" start
                            >mdi-lightning-bolt</v-icon
                          >
                          Similar:
                          {{ Math.round(suggestion.similarity_score * 100) }}%
                        </v-chip>
                      </div>
                    </div>
                  </v-expansion-panel-title>

                  <v-expansion-panel-text>
                    <!-- Frases clave -->
                    <div v-if="suggestion.key_phrases.length > 0" class="mb-4">
                      <div class="text-subtitle-2 mb-2 d-flex align-center">
                        <v-icon size="small" class="mr-1">mdi-key</v-icon>
                        Frases clave:
                      </div>
                      <v-chip
                        v-for="(phrase, pidx) in suggestion.key_phrases"
                        :key="pidx"
                        class="ma-1"
                        size="small"
                        variant="tonal"
                        color="info"
                      >
                        {{ phrase.substring(0, 80)
                        }}{{ phrase.length > 80 ? "..." : "" }}
                      </v-chip>
                    </div>

                    <!-- Contenido completo -->
                    <v-card variant="outlined" class="mb-3">
                      <v-card-text>
                        <div class="text-caption text-grey-darken-2 mb-2">
                          Contenido completo:
                        </div>
                        <div
                          class="section-content"
                          v-html="
                            formatSectionContent(suggestion.section_content)
                          "
                        ></div>
                      </v-card-text>
                    </v-card>

                    <!-- Acciones -->
                    <div class="d-flex gap-2">
                      <v-btn
                        size="small"
                        variant="outlined"
                        color="primary"
                        prepend-icon="mdi-content-copy"
                        @click="copySectionContent(suggestion.section_content)"
                      >
                        Copiar contenido
                      </v-btn>
                      <v-btn
                        size="small"
                        variant="outlined"
                        color="info"
                        prepend-icon="mdi-file-eye-outline"
                        @click="viewFullDocument(suggestion.document_id)"
                      >
                        Ver documento completo
                      </v-btn>
                    </div>
                  </v-expansion-panel-text>
                </v-expansion-panel>
              </v-expansion-panels>
            </div>
          </div>
        </v-card-text>
      </v-card>
    </div>

    <!-- Snackbar para copiar -->
    <v-snackbar v-model="copySnackbar" color="success" timeout="2000">
      <v-icon start>mdi-check</v-icon>
      Contenido copiado al portapapeles
    </v-snackbar>
  </v-dialog>
</template>

<script setup>
import { ref, onMounted, watch, toRefs } from "vue";
import axios from "axios";

const props = defineProps({
  documentId: {
    type: String,
    required: true,
  },
  sidebarOpen: {
    type: Boolean,
    default: false,
  },
});

const { sidebarOpen } = toRefs(props);

const emit = defineEmits(["view-document", "dialog-opened"]);

// Sidebar state
const drawerWidth = ref(0);

// State
const dialog = ref(false);
const step = ref(1);
const loadingSections = ref(false);
const loadingSuggestions = ref(false);
const copySnackbar = ref(false);

const availableSections = ref([]);
const selectedSection = ref(null);
const expandedSuggestion = ref(null);

const searchConfig = ref({
  maxSuggestions: 5,
  minQuality: 0.6,
  minSimilarity: 0.6,
});

const suggestions = ref([]);
const structureTips = ref([]);
const styleTips = ref([]);

// Methods
const loadAvailableSections = async () => {
  loadingSections.value = true;
  try {
    const response = await axios.get(
      `/api/writing-assistant/${props.documentId}/available-sections/`
    );
    availableSections.value = response.data.sections;
  } catch (error) {
    console.error("Error loading sections:", error);
  } finally {
    loadingSections.value = false;
  }
};

const selectSection = (section) => {
  selectedSection.value = section;
  searchAndGoToStep2(); // Auto-execute search and go to step 2
};

const goBack = () => {
  step.value = 1;
};

const searchAndGoToStep2 = async () => {
  step.value = 2;
  await getSuggestions();
};

const nextStep = () => {
  if (step.value < 3) {
    step.value++;
  }
};

const previousStep = () => {
  if (step.value > 1) {
    step.value--;
  }
};

const getSuggestions = async () => {
  loadingSuggestions.value = true;
  // Ya no cambiamos de step, mostramos resultados en step 2

  try {
    const response = await axios.post(
      `/api/writing-assistant/${props.documentId}/get-suggestions/`,
      {
        section_type: selectedSection.value.id,
        max_suggestions: searchConfig.value.maxSuggestions,
        min_quality: searchConfig.value.minQuality,
        min_similarity: searchConfig.value.minSimilarity,
      }
    );

    suggestions.value = response.data.suggestions;
    structureTips.value = response.data.structure_tips || [];
    styleTips.value = response.data.style_tips || [];
  } catch (error) {
    console.error("Error getting suggestions:", error);
    suggestions.value = [];
  } finally {
    loadingSuggestions.value = false;
  }
};

const formatSectionContent = (content) => {
  // Convertir saltos de línea a <br>
  // Resaltar títulos en mayúsculas
  let formatted = content.replace(/\n\n/g, "<br><br>").replace(/\n/g, "<br>");

  // Resaltar secciones numeradas (PRIMERO:, SEGUNDO:, etc.)
  formatted = formatted.replace(
    /(PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO|SEXTO|S[ÉE]PTIMO|OCTAVO|NOVENO|D[ÉE]CIMO)(\s*:)/gi,
    '<strong class="text-primary">$1$2</strong>'
  );

  return formatted;
};

const copySectionContent = async (content) => {
  try {
    await navigator.clipboard.writeText(content);
    copySnackbar.value = true;
  } catch (error) {
    console.error("Error copying to clipboard:", error);
  }
};

const viewFullDocument = (documentId) => {
  emit("view-document", documentId);
  dialog.value = false;
};

const closeDialog = () => {
  dialog.value = false;
  // Reset después de cerrar
  setTimeout(() => {
    step.value = 1;
    selectedSection.value = null;
    suggestions.value = [];
    structureTips.value = [];
    styleTips.value = [];
  }, 300);
};

// Watchers
watch(dialog, (newVal, oldVal) => {
  // Cuando se abre el diálogo
  if (newVal && !oldVal) {
    emit("dialog-opened");
    if (availableSections.value.length === 0) {
      loadAvailableSections();
    }
  }
});

// Exponer método para que el componente padre pueda cerrar el diálogo
defineExpose({
  close: closeDialog,
});

// Lifecycle
onMounted(() => {
  // Detectar ancho del drawer dinámicamente
  const drawer = document.querySelector(".v-navigation-drawer");
  if (drawer) {
    drawerWidth.value = drawer.offsetWidth;

    // Observar cambios de tamaño
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        drawerWidth.value = entry.contentRect.width;
      }
    });
    observer.observe(drawer);
  }
});
</script>

<style scoped>
/* Sidebar-aware dialog positioning */
.writing-assistant-overlay {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}

.writing-assistant-container {
  max-width: 1400px;
  width: 100%;
  height: 85vh;
  max-height: 900px;
  transition: transform 0.3s ease-in-out;
  padding: 0 20px;
  margin: 0 auto;
}

.writing-assistant-container.sidebar-open {
  transform: translateX(calc(var(--drawer-width) / -2));
}

.writing-assistant-card {
  max-width: 1400px !important;
  width: 100% !important;
  height: 100% !important;
  max-height: 900px !important;
  display: flex !important;
  flex-direction: column !important;
  background-color: #ffffff !important;
}

/* Responsive adjustments */
@media (max-width: 1200px) {
  .writing-assistant-container {
    max-width: 750px;
  }

  .writing-assistant-container.sidebar-open {
    transform: translateX(calc(var(--drawer-width) / -3));
  }
}

@media (max-width: 768px) {
  .writing-assistant-container {
    height: 90vh;
    max-height: none;
    padding: 0 10px;
    margin: 0 auto !important;
    transform: none !important;
  }

  .writing-assistant-container.sidebar-open {
    transform: none !important;
  }

  .writing-assistant-card {
    width: 100% !important;
    height: 100% !important;
    max-width: none !important;
  }
}

/* Fix completo para diálogo transparente */
:deep(.v-dialog) {
  background-color: white !important;
}

:deep(.v-dialog .v-card) {
  background-color: white !important;
  opacity: 1 !important;
}

:deep(.v-card-text) {
  background-color: white !important;
}

:deep(.v-overlay__scrim) {
  opacity: 0.6 !important;
}

:deep(.v-alert) {
  background-color: rgba(var(--v-theme-info), 0.1) !important;
}

:deep(.v-expansion-panel) {
  background-color: white !important;
}

:deep(.v-expansion-panel-title) {
  background-color: #f5f5f5 !important;
}

:deep(.v-expansion-panel-text) {
  background-color: white !important;
}

.section-card {
  cursor: pointer;
  transition: all 0.3s ease;
  background-color: white !important;
}

.section-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.border-primary {
  border: 2px solid rgb(var(--v-theme-primary)) !important;
  background-color: rgba(var(--v-theme-primary), 0.05) !important;
}

.section-content {
  white-space: pre-wrap;
  word-wrap: break-word;
  line-height: 1.8;
  padding: 16px;
  background-color: #f5f5f5 !important;
  border-radius: 8px;
  font-family: "Times New Roman", serif;
  font-size: 14px;
}

.gap-2 {
  gap: 8px;
}

/* Asegurar fondo sólido en todo el componente */
.v-card {
  background-color: #ffffff !important;
}

.v-card-text {
  background-color: #ffffff !important;
}

.v-card-actions {
  background-color: #ffffff !important;
  border-top: 1px solid #e0e0e0;
}

.v-card-title {
  background-color: rgb(var(--v-theme-primary)) !important;
}
</style>
