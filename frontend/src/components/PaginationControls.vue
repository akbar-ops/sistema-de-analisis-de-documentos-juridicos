<template>
  <v-card v-if="totalPages > 1" variant="flat" :class="className">
    <v-card-text class="pa-3">
      <div class="d-flex align-center justify-space-between flex-wrap gap-3">
        <!-- Información de página -->
        <div class="text-caption text-grey-darken-1">
          Mostrando {{ startItem }} - {{ endItem }} de {{ totalItems }}
          {{ itemLabel }}
        </div>

        <!-- Controles de navegación -->
        <div class="d-flex align-center gap-2">
          <!-- Selector de items por página -->
          <v-select
            v-if="showPageSizeSelector"
            :model-value="pageSize"
            :items="pageSizeOptions"
            label="Por página"
            density="compact"
            variant="outlined"
            hide-details
            style="max-width: 120px"
            @update:model-value="$emit('update:pageSize', $event)"
          />

          <!-- Botones de navegación -->
          <v-btn-group variant="outlined" density="compact">
            <v-btn
              :disabled="!hasPrevious"
              icon="mdi-chevron-left"
              @click="$emit('previous')"
              title="Página anterior"
            />

            <v-btn disabled class="px-4">
              {{ currentPage }} / {{ totalPages }}
            </v-btn>

            <v-btn
              :disabled="!hasNext"
              icon="mdi-chevron-right"
              @click="$emit('next')"
              title="Página siguiente"
            />
          </v-btn-group>

          <!-- Ir a página específica (opcional) -->
          <v-text-field
            v-if="showGoToPage"
            :model-value="currentPage"
            type="number"
            label="Ir a"
            density="compact"
            variant="outlined"
            hide-details
            style="max-width: 80px"
            :min="1"
            :max="totalPages"
            @update:model-value="handleGoToPage"
          />
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  currentPage: {
    type: Number,
    required: true,
    default: 1,
  },
  pageSize: {
    type: Number,
    required: true,
    default: 20,
  },
  totalItems: {
    type: Number,
    required: true,
    default: 0,
  },
  totalPages: {
    type: Number,
    required: true,
    default: 1,
  },
  hasNext: {
    type: Boolean,
    default: false,
  },
  hasPrevious: {
    type: Boolean,
    default: false,
  },
  itemLabel: {
    type: String,
    default: "items",
  },
  pageSizeOptions: {
    type: Array,
    default: () => [10, 20, 50, 100],
  },
  showPageSizeSelector: {
    type: Boolean,
    default: true,
  },
  showGoToPage: {
    type: Boolean,
    default: false,
  },
  className: {
    type: String,
    default: "mt-4",
  },
});

const emit = defineEmits(["next", "previous", "goToPage", "update:pageSize"]);

// Computed
const startItem = computed(() => {
  return (props.currentPage - 1) * props.pageSize + 1;
});

const endItem = computed(() => {
  return Math.min(props.currentPage * props.pageSize, props.totalItems);
});

// Methods
function handleGoToPage(value) {
  const page = parseInt(value);
  if (page >= 1 && page <= props.totalPages) {
    emit("goToPage", page);
  }
}
</script>

<style scoped>
/* Estilos adicionales si es necesario */
</style>
