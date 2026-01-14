<template>
  <div class="home-container">
    <!-- Contenido Principal -->
    <div class="main-content-area">
      <div class="content-wrapper pa-4 pa-md-6">
        <!-- Panel de Subida de Documentos -->
        <UploadPanel
          @file-uploaded="handleFileUpload"
          @files-uploaded="handleFilesUpload"
          :loading="loading"
          :error="error"
          class="mb-4"
        />

        <!-- Panel de Búsqueda y Lista de Documentos -->
        <SearchPanel ref="searchPanelRef" @select-document="selectDoc" />
      </div>
    </div>

    <!-- Panel de Detalles (Fixed Right) -->
    <DocDetailsPanel
      :selected="selected"
      @open-chat="openDocChat"
      @close-chat="closeDocChat"
      @toggle-panel="handlePanelToggle"
      @select-document="selectDoc"
    />

    <!-- Diálogos y Modales -->
    <ChatDialogs
      v-model:global="modals.globalChat"
      v-model:doc="modals.docChat"
      :selected="selected"
      :global-messages="globalMessages"
      :doc-messages="docMessages"
      :sidebar-open="panelOpen"
    />

    <!-- Botón Flotante de Chat Global -->
    <ChatFloating
      :sidebar-open="panelOpen"
      @open-global-chat="modals.globalChat = true"
    />

    <!-- Snackbar de Errores -->
    <v-snackbar
      v-model="showError"
      color="error"
      :timeout="5000"
      location="top"
    >
      {{ error }}
      <template #actions>
        <v-btn variant="text" @click="showError = false">Cerrar</v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from "vue";
import useDocuments from "../composables/useDocuments.js";

// Import all components directly (avoid async issues with router transitions)
import SearchPanel from "../components/SearchPanel.vue";
import UploadPanel from "../components/UploadPanel.vue";
import DocDetailsPanel from "../components/DocDetailsPanel.vue";
import ChatDialogs from "../components/ChatDialogs.vue";
import ChatFloating from "../components/ChatFloating.vue";

/* ------------------ Referencias ------------------ */
const searchPanelRef = ref(null);

/* ------------------ Estado global ------------------ */
const {
  selected,
  documents,
  modals,
  globalMessages,
  docMessages,
  loading,
  error,
  handleFile,
  deleteSelected,
  selectDoc,
} = useDocuments();

const showError = ref(false);

/* ------------------ Panel lateral ------------------ */
const panelOpen = ref(false);
function handlePanelToggle(isOpen) {
  panelOpen.value = isOpen;
}

/* ------------------ Manejo de archivo subido ------------------ */
async function handleFileUpload(uploadedDocument) {
  // El documento ya fue subido por UploadPanel
  // Solo necesitamos actualizar la lista y seleccionar el documento
  console.log("📄 Document uploaded successfully:", uploadedDocument);

  // Agregar el documento a la lista si no está
  if (
    uploadedDocument &&
    !documents.value.find((d) => d.document_id === uploadedDocument.document_id)
  ) {
    documents.value.unshift(uploadedDocument);
  }

  // Seleccionar el documento recién subido
  selected.value = uploadedDocument;

  // Recargar la lista de documentos en SearchPanel para refrescar
  if (searchPanelRef.value) {
    await searchPanelRef.value.reload();
  }
}

async function handleFilesUpload(response) {
  // response contiene { total_uploaded, total_errors, documents, errors }
  if (response.documents && response.documents.length > 0) {
    // Recargar la lista de documentos en SearchPanel
    if (searchPanelRef.value) {
      await searchPanelRef.value.reload();
    }

    // Seleccionar el primer documento subido
    if (response.documents[0]) {
      selectDoc(response.documents[0]);
    }
  }
}

/* ------------------ Observadores ------------------ */
watch(error, (newError) => {
  if (newError) {
    console.error("❌ Error:", newError);
    showError.value = true;
  }
});

/* ------------------ Acciones ------------------ */
function openDocChat() {
  if (!selected.value) {
    alert("Selecciona un documento antes de abrir el chat.");
    return;
  }
  modals.docChat = true;
}

function closeDocChat() {
  modals.docChat = false;
}
</script>

<style scoped lang="scss">
.home-container {
  min-height: calc(100vh - 64px - 200px); /* viewport - header - footer aprox */
  overflow: visible;
  position: relative;
}

.main-content-area {
  min-height: 100%;
  overflow-y: visible;
  background-color: rgb(var(--v-theme-background));

  &::-webkit-scrollbar {
    width: 10px;
  }

  &::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.05);
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(0, 0, 0, 0.2);
    border-radius: 5px;

    &:hover {
      background: rgba(0, 0, 0, 0.3);
    }
  }
}

.content-wrapper {
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

.v-theme--dark {
  .main-content-area {
    &::-webkit-scrollbar-track {
      background: rgba(255, 255, 255, 0.05);
    }

    &::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.2);

      &:hover {
        background: rgba(255, 255, 255, 0.3);
      }
    }
  }
}

@media (max-width: 960px) {
  .content-wrapper {
    padding: 16px !important;
  }
}
</style>
