<template>
  <div class="queue-view">
    <v-container fluid class="pa-0">
      <div class="d-flex align-center pa-4 border-b">
        <v-btn
          icon="mdi-arrow-left"
          variant="text"
          @click="$router.push('/')"
          class="me-4"
        />
        <h1 class="text-h5 font-weight-bold">Cola de Procesamiento</h1>
      </div>
      <TaskQueue />
    </v-container>
  </div>
</template>

<script setup>
import TaskQueue from "../components/TaskQueue.vue";
</script>

<style scoped>
.queue-view {
  height: calc(100vh - 64px);
  overflow: auto;
}

.border-b {
  border-bottom: 1px solid rgba(var(--v-border-color), 0.12);
}
</style>
