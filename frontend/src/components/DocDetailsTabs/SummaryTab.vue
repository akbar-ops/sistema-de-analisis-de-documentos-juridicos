<template>
  <div class="summary-tab">
    <!-- Con resumen -->
    <div v-if="selected.summary" class="pa-3">
      <v-alert
        type="info"
        variant="tonal"
        density="compact"
        icon="mdi-information"
        class="mb-3"
      >
        <div class="text-caption">
          Este es el resumen generado automáticamente. Para el resumen completo
          y formateado, abre el <strong>chat</strong>.
        </div>
      </v-alert>

      <div class="summary-content">
        <p class="text-body-2" style="line-height: 1.6; white-space: pre-line">
          {{ selected.summary }}
        </p>
      </div>
    </div>

    <!-- Sin resumen -->
    <div v-else class="pa-3 text-center empty-state">
      <v-icon size="48" color="grey-lighten-1">mdi-text-box-remove</v-icon>
      <p class="text-caption text-grey mt-2">No hay resumen disponible</p>
    </div>
  </div>
</template>

<script setup>
defineProps({
  selected: {
    type: Object,
    required: true,
  },
});
</script>

<style scoped lang="scss">
.summary-content {
  max-height: 500px;
  overflow-y: auto;
  padding: 12px;
  background-color: rgba(var(--v-theme-surface-variant), 0.2);
  border-radius: 8px;

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: rgba(var(--v-theme-surface-variant), 0.3);
    border-radius: 3px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(var(--v-theme-primary), 0.4);
    border-radius: 3px;

    &:hover {
      background: rgba(var(--v-theme-primary), 0.6);
    }
  }
}

.empty-state {
  padding: 64px 32px;
}
</style>
