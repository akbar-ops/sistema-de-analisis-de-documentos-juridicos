<template>
  <div class="writing-tab pa-4">
    <!-- Explicación del Asistente -->
    <v-card variant="outlined" class="mb-4 info-card">
      <v-card-text class="pa-4">
        <div class="d-flex align-start gap-3 mb-3">
          <v-icon size="40" style="color: #8c0d0d" class="flex-shrink-0">
            mdi-file-document-edit-outline
          </v-icon>
          <div>
            <h3 class="text-h6 mb-2" style="color: #8c0d0d">
              Asistente Inteligente de Redacción
            </h3>
            <p class="text-body-2 text-grey-darken-2 mb-0">
              Herramienta avanzada que te ayuda a redactar secciones legales
              utilizando inteligencia artificial y ejemplos de documentos
              similares.
            </p>
          </div>
        </div>

        <v-divider class="my-3"></v-divider>

        <!-- Características -->
        <div class="features-grid">
          <div class="feature-item">
            <v-icon size="20" style="color: #736d5d" class="mr-2">
              mdi-file-search-outline
            </v-icon>
            <div>
              <div class="text-subtitle-2 font-weight-medium">
                Búsqueda Inteligente
              </div>
              <div class="text-caption text-grey-darken-1">
                Encuentra documentos similares automáticamente
              </div>
            </div>
          </div>

          <div class="feature-item">
            <v-icon size="20" style="color: #8c0d0d" class="mr-2">
              mdi-brain
            </v-icon>
            <div>
              <div class="text-subtitle-2 font-weight-medium">
                IA Generativa
              </div>
              <div class="text-caption text-grey-darken-1">
                Genera texto basado en precedentes legales
              </div>
            </div>
          </div>

          <div class="feature-item">
            <v-icon size="20" style="color: #731414" class="mr-2">
              mdi-text-box-edit-outline
            </v-icon>
            <div>
              <div class="text-subtitle-2 font-weight-medium">
                Secciones Específicas
              </div>
              <div class="text-caption text-grey-darken-1">
                Redacta Hechos, Fundamentos, Decisión, etc.
              </div>
            </div>
          </div>

          <div class="feature-item">
            <v-icon size="20" style="color: #736d5d" class="mr-2">
              mdi-cog-outline
            </v-icon>
            <div>
              <div class="text-subtitle-2 font-weight-medium">
                Personalizable
              </div>
              <div class="text-caption text-grey-darken-1">
                Ajusta calidad, similitud y número de ejemplos
              </div>
            </div>
          </div>
        </div>

        <v-divider class="my-3"></v-divider>

        <!-- Cómo funciona -->
        <div class="mb-3">
          <div
            class="text-subtitle-2 font-weight-medium mb-2"
            style="color: #736d5d"
          >
            Proceso de Uso:
          </div>
          <div class="steps-list">
            <div class="step-item">
              <span class="step-number">1</span>
              <span class="text-caption"
                >Selecciona la sección que deseas redactar</span
              >
            </div>
            <div class="step-item">
              <span class="step-number">2</span>
              <span class="text-caption"
                >Configura los parámetros de búsqueda</span
              >
            </div>
            <div class="step-item">
              <span class="step-number">3</span>
              <span class="text-caption">Revisa los ejemplos encontrados</span>
            </div>
            <div class="step-item">
              <span class="step-number">4</span>
              <span class="text-caption"
                >Genera el texto con IA o copia ejemplos</span
              >
            </div>
          </div>
        </div>

        <v-alert
          type="info"
          variant="tonal"
          density="compact"
          class="mt-3"
          style="border-left: 4px solid #8c0d0d"
        >
          <div class="text-caption">
            <v-icon size="small" class="mr-1">mdi-information-outline</v-icon>
            <strong>Beneficio:</strong> Ahorra tiempo y mantén consistencia con
            precedentes legales
          </div>
        </v-alert>
      </v-card-text>
    </v-card>

    <!-- Botón de Activación -->
    <WritingAssistant
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
import WritingAssistant from "../WritingAssistant.vue";

defineProps({
  selected: {
    type: Object,
    required: true,
  },
});
</script>

<style scoped lang="scss">
@import "@/styles/variables.scss";

.writing-tab {
  max-height: calc(100vh - 300px);
  overflow-y: auto;
  @include scrollbar-pj;
}

.info-card {
  border: 2px solid rgba($pj-brown-grey, 0.2);
  background: linear-gradient(135deg, rgba($pj-grey-light, 0.3) 0%, white 100%);

  &:hover {
    border-color: rgba($pj-red-primary, 0.3);
    box-shadow: $shadow-pj-sm;
  }
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: $spacing-md;
}

.feature-item {
  display: flex;
  align-items: start;
  gap: $spacing-xs;
  padding: $spacing-sm;
  border-radius: $border-radius-sm;
  background-color: rgba($pj-grey-light, 0.5);
  transition: all $transition-fast;

  &:hover {
    background-color: rgba($pj-brown-grey, 0.1);
    transform: translateY(-2px);
  }
}

.steps-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.step-item {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-xs $spacing-sm;
  background-color: white;
  border-radius: $border-radius-sm;
  border-left: 3px solid $pj-red-primary;
}

.step-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background-color: $pj-red-primary;
  color: white;
  font-size: 12px;
  font-weight: bold;
  flex-shrink: 0;
}
</style>
