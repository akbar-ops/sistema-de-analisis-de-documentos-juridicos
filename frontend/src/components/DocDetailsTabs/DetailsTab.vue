<template>
  <v-list density="compact">
    <!-- Tipo de Documento -->
    <v-list-item v-if="selected.doc_type?.name">
      <template #prepend>
        <v-icon size="small" color="primary">mdi-file-document</v-icon>
      </template>
      <v-list-item-title class="text-caption"
        >Tipo de Documento</v-list-item-title
      >
      <v-list-item-subtitle>{{ selected.doc_type.name }}</v-list-item-subtitle>
    </v-list-item>

    <!-- Área Legal -->
    <v-list-item v-if="selected.legal_area?.name">
      <template #prepend>
        <v-icon size="small" color="primary">mdi-scale-balance</v-icon>
      </template>
      <v-list-item-title class="text-caption">Área Legal</v-list-item-title>
      <v-list-item-subtitle>{{
        selected.legal_area.name
      }}</v-list-item-subtitle>
    </v-list-item>

    <!-- Materia Legal -->
    <v-list-item v-if="selected.legal_subject">
      <template #prepend>
        <v-icon size="small" color="primary">mdi-gavel</v-icon>
      </template>
      <v-list-item-title class="text-caption">Materia Legal</v-list-item-title>
      <v-list-item-subtitle>{{ selected.legal_subject }}</v-list-item-subtitle>
    </v-list-item>

    <!-- Nº Expediente -->
    <v-list-item v-if="selected.case_number">
      <template #prepend>
        <v-icon size="small" color="primary">mdi-folder-text</v-icon>
      </template>
      <v-list-item-title class="text-caption">Nº Expediente</v-list-item-title>
      <v-list-item-subtitle>{{ selected.case_number }}</v-list-item-subtitle>
    </v-list-item>

    <!-- Nº Resolución -->
    <v-list-item v-if="selected.resolution_number">
      <template #prepend>
        <v-icon size="small" color="primary">mdi-file-document-outline</v-icon>
      </template>
      <v-list-item-title class="text-caption">Nº Resolución</v-list-item-title>
      <v-list-item-subtitle>{{
        selected.resolution_number
      }}</v-list-item-subtitle>
    </v-list-item>

    <!-- Lugar de Emisión -->
    <v-list-item v-if="selected.issue_place">
      <template #prepend>
        <v-icon size="small" color="primary">mdi-map-marker</v-icon>
      </template>
      <v-list-item-title class="text-caption"
        >Lugar de Emisión</v-list-item-title
      >
      <v-list-item-subtitle>{{ selected.issue_place }}</v-list-item-subtitle>
    </v-list-item>

    <!-- Fecha del Documento -->
    <v-list-item v-if="selected.document_date">
      <template #prepend>
        <v-icon size="small" color="primary">mdi-calendar</v-icon>
      </template>
      <v-list-item-title class="text-caption"
        >Fecha del Documento</v-list-item-title
      >
      <v-list-item-subtitle>{{
        formatDocumentDate(selected.document_date)
      }}</v-list-item-subtitle>
    </v-list-item>

    <!-- Páginas -->
    <v-list-item v-if="selected.pages">
      <template #prepend>
        <v-icon size="small" color="primary">mdi-file</v-icon>
      </template>
      <v-list-item-title class="text-caption">Páginas</v-list-item-title>
      <v-list-item-subtitle>{{ selected.pages }}</v-list-item-subtitle>
    </v-list-item>

    <!-- Tamaño -->
    <v-list-item v-if="fileSizeMB && fileSizeMB !== '0.0'">
      <template #prepend>
        <v-icon size="small" color="primary">mdi-file-outline</v-icon>
      </template>
      <v-list-item-title class="text-caption">Tamaño</v-list-item-title>
      <v-list-item-subtitle>{{ fileSizeMB }} MB</v-list-item-subtitle>
    </v-list-item>

    <!-- Fecha de Carga -->
    <v-list-item>
      <template #prepend>
        <v-icon size="small" color="primary">mdi-clock-outline</v-icon>
      </template>
      <v-list-item-title class="text-caption">Fecha de Carga</v-list-item-title>
      <v-list-item-subtitle>{{ formattedDate }}</v-list-item-subtitle>
    </v-list-item>

    <!-- Estado -->
    <v-list-item>
      <template #prepend>
        <v-icon size="small" color="primary">mdi-information</v-icon>
      </template>
      <v-list-item-title class="text-caption">Estado</v-list-item-title>
      <template #append>
        <v-chip :color="statusColor" size="small" variant="flat">
          <v-icon start size="x-small">{{ statusIcon }}</v-icon>
          {{ statusText }}
        </v-chip>
      </template>
    </v-list-item>
  </v-list>
</template>

<script setup>
import { computed } from "vue";
import { formatDate } from "@/composables/useFormatting";
import { useColors } from "@/composables/useColors";

const { colors } = useColors();

const props = defineProps({
  selected: {
    type: Object,
    required: true,
  },
});

// Computed properties
const fileSizeMB = computed(() => props.selected?.file_size_mb ?? "0.0");

const formattedDate = computed(() =>
  props.selected?.created_at ? formatDate(props.selected.created_at) : "—"
);

const statusColor = computed(() => {
  const statusColors = {
    processed: colors.brownGrey,
    processing: colors.redLight,
    uploaded: "#999999",
    failed: colors.redPrimary,
  };
  return statusColors[props.selected?.status] || "#999999";
});

const statusIcon = computed(() => {
  const icons = {
    processed: "mdi-check-circle",
    processing: "mdi-loading mdi-spin",
    uploaded: "mdi-cloud-upload",
    failed: "mdi-alert-circle",
  };
  return icons[props.selected?.status] || "mdi-help-circle";
});

const statusText = computed(() => {
  const texts = {
    processed: "Procesado",
    processing: "Procesando",
    uploaded: "Subido",
    failed: "Error",
  };
  return texts[props.selected?.status] || props.selected?.status || "—";
});

// Methods
function formatDocumentDate(dateStr) {
  return dateStr ? formatDate(dateStr) : "—";
}
</script>
