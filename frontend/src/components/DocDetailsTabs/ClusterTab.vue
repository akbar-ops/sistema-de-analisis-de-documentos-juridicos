<template>
  <div class="cluster-tab pa-3">
    <ClusterView
      v-if="selected?.document_id"
      :document-id="String(selected.document_id)"
    />
    <div v-else class="text-center pa-4 text-grey">
      <v-icon size="48">mdi-alert-circle-outline</v-icon>
      <p class="mt-2">No hay documento seleccionado</p>
    </div>
  </div>
</template>

<script setup>
import ClusterView from "../ClusterView.vue";

defineProps({
  selected: {
    type: Object,
    required: true,
  },
});
</script>
