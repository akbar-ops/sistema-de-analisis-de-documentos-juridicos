<template>
  <v-card class="document-metadata-card" elevation="2">
    <v-card-title class="d-flex align-center bg-grey-lighten-4">
      <v-icon class="me-2" color="primary">mdi-information-outline</v-icon>
      <span class="font-weight-bold">Información del Documento</span>
      <v-spacer />
      <v-btn
        v-if="hasExtendedMetadata"
        icon
        variant="text"
        size="small"
        @click="expanded = !expanded"
      >
        <v-icon>
          {{ expanded ? "mdi-chevron-up" : "mdi-chevron-down" }}
        </v-icon>
      </v-btn>
    </v-card-title>

    <v-card-text class="pa-4">
      <!-- Essential Metadata (Always Visible) -->
      <div class="metadata-grid">
        <!-- Document Type -->
        <div v-if="document.doc_type" class="metadata-item">
          <div class="metadata-label">
            <v-icon size="small" color="primary" class="me-1">
              mdi-file-document
            </v-icon>
            <span class="text-caption text-grey-darken-2">Tipo</span>
          </div>
          <div class="metadata-value text-body-2 font-weight-medium">
            {{ formatDocType(document.doc_type) }}
          </div>
        </div>

        <!-- Legal Area -->
        <div v-if="document.legal_area" class="metadata-item">
          <div class="metadata-label">
            <v-icon size="small" color="primary" class="me-1">
              mdi-scale-balance
            </v-icon>
            <span class="text-caption text-grey-darken-2">Área Legal</span>
          </div>
          <div class="metadata-value text-body-2 font-weight-medium">
            {{ formatLegalArea(document.legal_area) }}
          </div>
        </div>

        <!-- Legal Subject -->
        <div v-if="document.legal_subject" class="metadata-item">
          <div class="metadata-label">
            <v-icon size="small" color="primary" class="me-1">mdi-gavel</v-icon>
            <span class="text-caption text-grey-darken-2">Materia</span>
          </div>
          <div class="metadata-value text-body-2 font-weight-medium">
            {{ document.legal_subject }}
          </div>
        </div>

        <!-- Document Date -->
        <div v-if="document.document_date" class="metadata-item">
          <div class="metadata-label">
            <v-icon size="small" color="primary" class="me-1">
              mdi-calendar
            </v-icon>
            <span class="text-caption text-grey-darken-2">Fecha</span>
          </div>
          <div class="metadata-value text-body-2 font-weight-medium">
            {{ formatDate(document.document_date) }}
          </div>
        </div>

        <!-- Pages -->
        <div v-if="document.pages" class="metadata-item">
          <div class="metadata-label">
            <v-icon size="small" color="primary" class="me-1">
              mdi-file-multiple
            </v-icon>
            <span class="text-caption text-grey-darken-2">Páginas</span>
          </div>
          <div class="metadata-value text-body-2 font-weight-medium">
            {{ document.pages }}
          </div>
        </div>
      </div>

      <!-- Extended Metadata (Collapsible) -->
      <v-expand-transition>
        <div v-show="expanded" class="mt-3 pt-3 border-t">
          <div class="metadata-grid">
            <!-- Case Number -->
            <div v-if="document.case_number" class="metadata-item">
              <div class="metadata-label">
                <v-icon size="small" color="primary" class="me-1">
                  mdi-folder-text
                </v-icon>
                <span class="text-caption text-grey-darken-2">
                  Nº Expediente
                </span>
              </div>
              <div class="metadata-value text-body-2 font-weight-medium">
                {{ document.case_number }}
              </div>
            </div>

            <!-- Resolution Number -->
            <div v-if="document.resolution_number" class="metadata-item">
              <div class="metadata-label">
                <v-icon size="small" color="primary" class="me-1">
                  mdi-file-document-outline
                </v-icon>
                <span class="text-caption text-grey-darken-2">
                  Nº Resolución
                </span>
              </div>
              <div class="metadata-value text-body-2 font-weight-medium">
                {{ document.resolution_number }}
              </div>
            </div>

            <!-- Issue Place -->
            <div v-if="document.issue_place" class="metadata-item">
              <div class="metadata-label">
                <v-icon size="small" color="primary" class="me-1">
                  mdi-map-marker
                </v-icon>
                <span class="text-caption text-grey-darken-2">
                  Lugar de Emisión
                </span>
              </div>
              <div class="metadata-value text-body-2 font-weight-medium">
                {{ document.issue_place }}
              </div>
            </div>

            <!-- File Size -->
            <div v-if="fileSizeFormatted" class="metadata-item">
              <div class="metadata-label">
                <v-icon size="small" color="primary" class="me-1">
                  mdi-file-outline
                </v-icon>
                <span class="text-caption text-grey-darken-2">Tamaño</span>
              </div>
              <div class="metadata-value text-body-2 font-weight-medium">
                {{ fileSizeFormatted }}
              </div>
            </div>

            <!-- Upload Date -->
            <div v-if="document.created_at" class="metadata-item">
              <div class="metadata-label">
                <v-icon size="small" color="primary" class="me-1">
                  mdi-clock-outline
                </v-icon>
                <span class="text-caption text-grey-darken-2">
                  Fecha de Carga
                </span>
              </div>
              <div class="metadata-value text-body-2 font-weight-medium">
                {{ formatDate(document.created_at) }}
              </div>
            </div>

            <!-- Status -->
            <div v-if="document.status" class="metadata-item">
              <div class="metadata-label">
                <v-icon size="small" color="primary" class="me-1">
                  mdi-information
                </v-icon>
                <span class="text-caption text-grey-darken-2">Estado</span>
              </div>
              <div class="metadata-value">
                <v-chip :color="statusColor" size="small" variant="flat">
                  <v-icon start size="x-small">{{ statusIcon }}</v-icon>
                  {{ statusText }}
                </v-chip>
              </div>
            </div>
          </div>

          <!-- Persons (if available) -->
          <div
            v-if="document.persons && document.persons.length > 0"
            class="mt-3 pt-3 border-t"
          >
            <h4 class="text-subtitle-2 font-weight-bold mb-2">
              <v-icon size="small" class="me-1">mdi-account-multiple</v-icon>
              Personas Involucradas
            </h4>
            <div class="persons-chips">
              <v-chip
                v-for="(person, idx) in document.persons"
                :key="idx"
                size="small"
                :color="getRoleColor(person.role)"
                variant="outlined"
                class="me-1 mb-1"
              >
                {{ person.name || person.person?.name }}
                <span v-if="person.role" class="ms-1 text-caption">
                  ({{ person.role }})
                </span>
              </v-chip>
            </div>
          </div>
        </div>
      </v-expand-transition>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, computed } from "vue";

/* ========== PROPS ========== */
const props = defineProps({
  document: {
    type: Object,
    required: true,
  },
  defaultExpanded: {
    type: Boolean,
    default: false,
  },
});

/* ========== STATE ========== */
const expanded = ref(props.defaultExpanded);

/* ========== COMPUTED ========== */
const hasExtendedMetadata = computed(() => {
  return !!(
    props.document.case_number ||
    props.document.resolution_number ||
    props.document.issue_place ||
    props.document.file_size ||
    props.document.created_at ||
    props.document.status ||
    (props.document.persons && props.document.persons.length > 0)
  );
});

const fileSizeFormatted = computed(() => {
  if (!props.document.file_size) return null;
  const bytes = props.document.file_size;
  const mb = (bytes / (1024 * 1024)).toFixed(2);
  return `${mb} MB`;
});

const statusColor = computed(() => {
  switch (props.document.status) {
    case "processed":
      return "success";
    case "processing":
      return "warning";
    case "failed":
      return "error";
    default:
      return "grey";
  }
});

const statusIcon = computed(() => {
  switch (props.document.status) {
    case "processed":
      return "mdi-check-circle";
    case "processing":
      return "mdi-clock-outline";
    case "failed":
      return "mdi-alert-circle";
    default:
      return "mdi-file";
  }
});

const statusText = computed(() => {
  switch (props.document.status) {
    case "processed":
      return "Procesado";
    case "processing":
      return "Procesando";
    case "failed":
      return "Error";
    default:
      return "Pendiente";
  }
});

/* ========== METHODS ========== */
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

function formatDate(dateString) {
  if (!dateString) return "N/A";

  try {
    const date = new Date(dateString);
    return date.toLocaleDateString("es-ES", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  } catch (e) {
    return dateString;
  }
}

function getRoleColor(role) {
  const roleColors = {
    demandante: "blue",
    demandado: "orange",
    juez: "purple",
    testigo: "green",
    abogado: "indigo",
  };
  return roleColors[role?.toLowerCase()] || "grey";
}
</script>

<style scoped lang="scss">
.document-metadata-card {
  .metadata-grid {
    display: grid;
    gap: 1rem;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  }

  .metadata-item {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .metadata-label {
    display: flex;
    align-items: center;
    font-weight: 500;
  }

  .metadata-value {
    margin-left: 1.25rem;
  }

  .border-t {
    border-top: 1px solid rgba(0, 0, 0, 0.12);
  }

  .persons-chips {
    display: flex;
    flex-wrap: wrap;
  }
}

.v-theme--dark {
  .document-metadata-card {
    .border-t {
      border-top-color: rgba(255, 255, 255, 0.12);
    }
  }
}

@media (max-width: 600px) {
  .document-metadata-card {
    .metadata-grid {
      grid-template-columns: 1fr;
      gap: 0.75rem;
    }
  }
}
</style>
