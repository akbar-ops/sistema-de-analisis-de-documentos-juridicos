<template>
  <v-card class="cluster-documents-list" elevation="2">
    <!-- Header -->
    <v-card-title class="bg-primary d-flex align-center justify-space-between">
      <div class="d-flex align-center">
        <v-avatar :color="clusterColor" size="40" class="mr-3">
          <span class="text-white font-weight-bold">{{ clusterId }}</span>
        </v-avatar>
        <div>
          <div class="text-h6">Cluster {{ clusterId }}</div>
          <div class="text-caption">
            {{ documents.length }} documento{{
              documents.length !== 1 ? "s" : ""
            }}
          </div>
        </div>
      </div>

      <v-btn
        icon="mdi-close"
        variant="text"
        color="white"
        @click="$emit('close')"
      ></v-btn>
    </v-card-title>

    <!-- Filters and Search -->
    <v-card-text class="pa-0">
      <v-expansion-panels variant="accordion">
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon class="mr-2">mdi-filter</v-icon>
            Filtros y Búsqueda
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-row dense>
              <!-- Search -->
              <v-col cols="12">
                <v-text-field
                  v-model="searchQuery"
                  prepend-inner-icon="mdi-magnify"
                  label="Buscar por título o expediente"
                  variant="outlined"
                  density="compact"
                  clearable
                  hide-details
                ></v-text-field>
              </v-col>

              <!-- Filter by Legal Area -->
              <v-col cols="12" md="6">
                <v-select
                  v-model="filterLegalArea"
                  :items="availableLegalAreas"
                  label="Filtrar por Área Legal"
                  variant="outlined"
                  density="compact"
                  clearable
                  hide-details
                  prepend-inner-icon="mdi-scale-balance"
                >
                  <template #item="{ props, item }">
                    <v-list-item v-bind="props">
                      <template #prepend>
                        <v-icon :color="getLegalAreaColor(item.value)">
                          {{ getLegalAreaIcon(item.value) }}
                        </v-icon>
                      </template>
                    </v-list-item>
                  </template>
                </v-select>
              </v-col>

              <!-- Filter by Document Type -->
              <v-col cols="12" md="6">
                <v-select
                  v-model="filterDocType"
                  :items="availableDocTypes"
                  label="Filtrar por Tipo de Documento"
                  variant="outlined"
                  density="compact"
                  clearable
                  hide-details
                  prepend-inner-icon="mdi-file-document"
                >
                  <template #item="{ props, item }">
                    <v-list-item v-bind="props">
                      <template #prepend>
                        <v-icon>{{ getDocumentIcon(item.value) }}</v-icon>
                      </template>
                    </v-list-item>
                  </template>
                </v-select>
              </v-col>
            </v-row>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>

      <v-divider></v-divider>

      <!-- Documents List -->
      <div
        class="documents-container"
        style="max-height: 60vh; overflow-y: auto"
      >
        <v-list v-if="filteredDocuments.length > 0" lines="three">
          <v-list-item
            v-for="doc in filteredDocuments"
            :key="doc.id"
            @click="$emit('view-document', doc.id)"
            class="document-item"
          >
            <!-- Icon based on document type -->
            <template #prepend>
              <v-avatar :color="getLegalAreaColor(doc.legal_area)" size="48">
                <v-icon color="white" size="28">
                  {{ getDocumentIcon(doc.doc_type) }}
                </v-icon>
              </v-avatar>
            </template>

            <!-- Document Info -->
            <v-list-item-title class="font-weight-medium mb-1">
              {{ doc.title || "Sin título" }}
            </v-list-item-title>

            <v-list-item-subtitle>
              <div class="d-flex flex-wrap gap-1 mb-1">
                <!-- Legal Area Chip -->
                <v-chip
                  v-if="doc.legal_area"
                  size="x-small"
                  :color="getLegalAreaColor(doc.legal_area)"
                  variant="flat"
                >
                  <v-icon start size="x-small">
                    {{ getLegalAreaIcon(doc.legal_area) }}
                  </v-icon>
                  {{ doc.legal_area }}
                </v-chip>

                <!-- Document Type Chip -->
                <v-chip v-if="doc.doc_type" size="x-small" variant="tonal">
                  <v-icon start size="x-small">
                    {{ getDocumentIcon(doc.doc_type) }}
                  </v-icon>
                  {{ doc.doc_type }}
                </v-chip>
              </div>

              <!-- Metadata -->
              <div class="text-caption">
                <v-icon size="x-small" class="mr-1">mdi-folder</v-icon>
                {{ doc.case_number || "Sin expediente" }}
                <span v-if="doc.document_date" class="ml-2">
                  <v-icon size="x-small" class="mr-1">mdi-calendar</v-icon>
                  {{ formatDate(doc.document_date) }}
                </span>
              </div>
            </v-list-item-subtitle>

            <!-- Actions -->
            <template #append>
              <div class="d-flex flex-column gap-1">
                <v-btn
                  icon="mdi-eye"
                  size="small"
                  variant="tonal"
                  color="primary"
                  @click.stop="$emit('view-document', doc.id)"
                >
                  <v-icon>mdi-eye</v-icon>
                  <v-tooltip activator="parent" location="left">
                    Ver documento
                  </v-tooltip>
                </v-btn>
              </div>
            </template>
          </v-list-item>

          <v-divider
            v-if="index < filteredDocuments.length - 1"
            :key="`divider-${doc.id}`"
          ></v-divider>
        </v-list>

        <!-- Empty State -->
        <v-alert v-else type="info" variant="tonal" class="ma-4">
          <div class="text-center">
            <v-icon size="64" color="info">mdi-file-search</v-icon>
            <div class="mt-2">
              No se encontraron documentos con los filtros aplicados
            </div>
          </div>
        </v-alert>
      </div>
    </v-card-text>

    <!-- Footer with Stats -->
    <v-divider></v-divider>
    <v-card-actions class="bg-grey-lighten-4">
      <v-spacer></v-spacer>
      <div class="text-caption text-grey-darken-1">
        Mostrando {{ filteredDocuments.length }} de
        {{ documents.length }} documentos
      </div>
    </v-card-actions>
  </v-card>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useDocumentIcons } from "@/composables/useDocumentIcons";

const props = defineProps({
  clusterId: {
    type: [Number, String],
    required: true,
  },
  documents: {
    type: Array,
    default: () => [],
  },
  clusterColor: {
    type: String,
    default: "primary",
  },
});

const emit = defineEmits(["close", "view-document"]);

// Composables
const { getDocumentIcon, getLegalAreaColor, getLegalAreaIcon } =
  useDocumentIcons();

// State
const searchQuery = ref("");
const filterLegalArea = ref(null);
const filterDocType = ref(null);

// Computed - Available filters
const availableLegalAreas = computed(() => {
  const areas = new Set(
    props.documents.map((doc) => doc.legal_area).filter((area) => area)
  );
  return Array.from(areas).sort();
});

const availableDocTypes = computed(() => {
  const types = new Set(
    props.documents.map((doc) => doc.doc_type).filter((type) => type)
  );
  return Array.from(types).sort();
});

// Computed - Filtered documents
const filteredDocuments = computed(() => {
  let filtered = [...props.documents];

  // Filter by search query
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    filtered = filtered.filter(
      (doc) =>
        (doc.title && doc.title.toLowerCase().includes(query)) ||
        (doc.case_number && doc.case_number.toLowerCase().includes(query)) ||
        (doc.summary && doc.summary.toLowerCase().includes(query))
    );
  }

  // Filter by legal area
  if (filterLegalArea.value) {
    filtered = filtered.filter(
      (doc) => doc.legal_area === filterLegalArea.value
    );
  }

  // Filter by document type
  if (filterDocType.value) {
    filtered = filtered.filter((doc) => doc.doc_type === filterDocType.value);
  }

  return filtered;
});

// Methods
const formatDate = (dateString) => {
  if (!dateString) return "";
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString("es-ES", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch (e) {
    return dateString;
  }
};

// Reset filters when cluster changes
watch(
  () => props.clusterId,
  () => {
    searchQuery.value = "";
    filterLegalArea.value = null;
    filterDocType.value = null;
  }
);
</script>

<style scoped>
.cluster-documents-list {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.documents-container {
  flex: 1;
  overflow-y: auto;
}

.document-item {
  cursor: pointer;
  transition: background-color 0.2s;
}

.document-item:hover {
  background-color: rgba(0, 0, 0, 0.04);
}

.gap-1 {
  gap: 4px;
}
</style>
