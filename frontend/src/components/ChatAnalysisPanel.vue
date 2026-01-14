<template>
  <v-card class="chat-analysis-panel" elevation="2">
    <!-- Header -->
    <v-card-title class="d-flex align-center bg-primary chat-header">
      <v-icon class="me-2" color="white">mdi-robot-outline</v-icon>
      <span class="font-weight-bold text-white">Análisis con IA</span>

      <!-- Mode Indicator -->
      <v-chip
        size="x-small"
        class="ms-2"
        :color="chatMode === 'rag' ? 'success' : 'warning'"
        variant="flat"
      >
        <v-icon start size="12">{{
          chatMode === "rag" ? "mdi-magnify-scan" : "mdi-file-document-outline"
        }}</v-icon>
        {{ chatMode === "rag" ? "RAG" : "Normal" }}
      </v-chip>

      <v-spacer />

      <!-- Metadata Button -->
      <v-dialog v-model="showMetadataDialog" max-width="600">
        <template #activator="{ props: dialogProps }">
          <v-btn
            icon
            variant="text"
            color="white"
            size="small"
            v-bind="dialogProps"
            class="me-1"
          >
            <v-badge
              v-if="document"
              color="success"
              dot
              offset-x="-2"
              offset-y="-2"
            >
              <v-icon>mdi-information-outline</v-icon>
            </v-badge>
            <v-icon v-else>mdi-information-outline</v-icon>
          </v-btn>
        </template>

        <v-card>
          <v-card-title class="d-flex align-center bg-primary">
            <v-icon class="me-2" color="white">mdi-information</v-icon>
            <span class="text-white">Información del Documento</span>
            <v-spacer />
            <v-btn
              icon
              variant="text"
              color="white"
              size="small"
              @click="showMetadataDialog = false"
            >
              <v-icon>mdi-close</v-icon>
            </v-btn>
          </v-card-title>
          <v-card-text class="pa-4">
            <DocumentMetadataCard
              v-if="document"
              :document="document"
              :default-expanded="true"
            />
          </v-card-text>
        </v-card>
      </v-dialog>

      <!-- Options Menu -->
      <v-menu>
        <template #activator="{ props }">
          <v-btn icon variant="text" color="white" size="small" v-bind="props">
            <v-icon>mdi-dots-vertical</v-icon>
          </v-btn>
        </template>
        <v-list>
          <!-- Chat Mode Selection -->
          <v-list-subheader>Modo de búsqueda</v-list-subheader>
          <v-list-item
            @click="setChatMode('rag')"
            :class="{ 'v-list-item--active': chatMode === 'rag' }"
          >
            <template #prepend>
              <v-icon :color="chatMode === 'rag' ? 'primary' : ''"
                >mdi-magnify-scan</v-icon
              >
            </template>
            <v-list-item-title>RAG Semántico</v-list-item-title>
            <v-list-item-subtitle class="text-caption">
              Busca fragmentos relevantes a tu pregunta
            </v-list-item-subtitle>
          </v-list-item>
          <v-list-item
            @click="setChatMode('normal')"
            :class="{ 'v-list-item--active': chatMode === 'normal' }"
          >
            <template #prepend>
              <v-icon :color="chatMode === 'normal' ? 'primary' : ''"
                >mdi-file-document-outline</v-icon
              >
            </template>
            <v-list-item-title>Normal (6000 chars)</v-list-item-title>
            <v-list-item-subtitle class="text-caption">
              Usa los primeros 6000 caracteres
            </v-list-item-subtitle>
          </v-list-item>

          <v-divider class="my-2" />

          <v-list-item @click="resetChat">
            <template #prepend>
              <v-icon>mdi-refresh</v-icon>
            </template>
            <v-list-item-title>Reiniciar chat</v-list-item-title>
          </v-list-item>
          <v-list-item @click="clearChat">
            <template #prepend>
              <v-icon>mdi-broom</v-icon>
            </template>
            <v-list-item-title>Limpiar conversación</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
    </v-card-title>

    <!-- Chat Body -->
    <v-card-text ref="chatBodyRef" class="chat-body pa-4">
      <!-- Empty State -->
      <div v-if="messages.length === 0" class="empty-chat-state">
        <v-icon size="64" color="grey-lighten-1">mdi-robot-outline</v-icon>
        <p class="text-h6 text-grey-darken-1 mt-4 mb-2">Análisis con IA</p>
        <p class="text-body-2 text-grey">
          Selecciona un documento para comenzar el análisis
        </p>
      </div>

      <!-- Messages -->
      <div v-else class="messages-container">
        <transition-group name="message-fade" tag="div">
          <div
            v-for="(msg, idx) in messages"
            :key="`msg-${idx}`"
            class="message-wrapper mb-3"
            :class="msg.from === 'user' ? 'user-message' : 'assistant-message'"
          >
            <!-- Assistant Avatar -->
            <v-avatar
              v-if="msg.from === 'assistant'"
              size="32"
              color="primary"
              class="me-2 flex-shrink-0"
            >
              <v-icon size="small" color="white">mdi-robot</v-icon>
            </v-avatar>

            <!-- Message Bubble -->
            <div
              class="message-bubble"
              :class="{ summary: msg.type === 'summary', error: msg.error }"
            >
              <!-- Summary Header (if it's a summary message) -->
              <div
                v-if="msg.type === 'summary'"
                class="summary-header mb-3 pb-2 border-bottom"
              >
                <div class="d-flex align-center">
                  <v-icon size="18" color="primary" class="me-2">
                    mdi-file-document-outline
                  </v-icon>
                  <span class="text-caption font-weight-bold text-primary">
                    RESUMEN DEL DOCUMENTO
                  </span>
                </div>
              </div>

              <!-- Message Text -->
              <div class="message-text" v-html="formatMessageText(msg.text)" />

              <!-- Timestamp -->
              <div
                class="message-timestamp text-caption text-grey-darken-1 mt-2"
              >
                {{ formatTime(msg.timestamp) }}
              </div>
            </div>

            <!-- User Avatar -->
            <v-avatar
              v-if="msg.from === 'user'"
              size="32"
              color="grey-darken-1"
              class="ms-2 flex-shrink-0"
            >
              <v-icon size="small" color="white">mdi-account</v-icon>
            </v-avatar>
          </div>
        </transition-group>

        <!-- Typing Indicator -->
        <div v-if="isLoading" class="message-wrapper assistant-message mb-3">
          <v-avatar size="32" color="primary" class="me-2">
            <v-icon size="small" color="white">mdi-robot</v-icon>
          </v-avatar>
          <div class="message-bubble typing-indicator">
            <div class="typing-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      </div>
    </v-card-text>

    <!-- Topic Keywords Section (BERTopic) -->
    <div v-if="hasTopicKeywords" class="keywords-section">
      <v-divider />
      <div class="pa-4">
        <div class="d-flex align-center mb-3">
          <v-icon color="secondary" class="me-2">mdi-tag-multiple</v-icon>
          <h3 class="text-subtitle-1 font-weight-bold">
            Palabras clave del tema
          </h3>
          <v-tooltip location="top">
            <template v-slot:activator="{ props }">
              <v-icon v-bind="props" size="small" class="ms-2" color="grey"
                >mdi-information-outline</v-icon
              >
            </template>
            <span
              >Keywords extraídos automáticamente del tópico asignado por
              análisis de contenido</span
            >
          </v-tooltip>
        </div>
        <v-skeleton-loader v-if="loadingKeywords" type="chip, chip, chip" />
        <div v-else class="keywords-container">
          <v-chip
            v-for="(keyword, index) in displayKeywords"
            :key="index"
            size="small"
            variant="tonal"
            :color="getKeywordColor(index)"
            class="ma-1"
          >
            {{ keyword }}
          </v-chip>
          <v-chip
            v-if="topicKeywords?.topic_label"
            size="small"
            variant="outlined"
            color="primary"
            class="ma-1"
          >
            <v-icon start size="x-small">mdi-folder-outline</v-icon>
            {{ topicKeywords.topic_label }}
          </v-chip>
        </div>
      </div>
    </div>

    <!-- Similar Documents Section (Outside chat, before input) -->
    <div v-if="hasSimilarDocuments" class="similar-docs-section">
      <v-divider />
      <div class="pa-4">
        <div class="d-flex align-center mb-3">
          <v-icon color="primary" class="me-2">mdi-file-star-outline</v-icon>
          <h3 class="text-subtitle-1 font-weight-bold">Te puede interesar</h3>
        </div>
        <p class="text-caption text-grey-darken-1 mb-3">
          Documentos similares basados en contenido y contexto legal
        </p>
        <SimilarDocumentsSection
          :similar-documents="similarDocuments"
          :loading="loadingSimilar"
          :max-visible="3"
          :compact="true"
          @select-document="$emit('select-similar', $event)"
        />
      </div>
    </div>

    <!-- Chat Input -->
    <v-divider />
    <div class="chat-input pa-3">
      <div class="d-flex align-center gap-2">
        <v-textarea
          v-model="inputMessage"
          placeholder="Pregunta sobre este documento..."
          auto-grow
          rows="1"
          max-rows="4"
          variant="outlined"
          density="comfortable"
          hide-details
          class="flex-grow-1 chat-input-field"
          :disabled="!document || isLoading"
          @keydown.enter.exact.prevent="sendMessage"
          @keydown.shift.enter.stop
        >
          <template #prepend-inner>
            <v-icon size="small" color="primary"
              >mdi-message-text-outline</v-icon
            >
          </template>
        </v-textarea>
        <v-btn
          color="primary"
          icon
          size="large"
          elevation="0"
          :disabled="!inputMessage.trim() || isLoading || !document"
          :loading="isLoading"
          class="send-btn"
          @click="sendMessage"
        >
          <v-icon>mdi-send</v-icon>
        </v-btn>
      </div>
      <div class="text-caption text-grey mt-2 d-flex align-center">
        <v-icon size="14" class="me-1">mdi-keyboard-outline</v-icon>
        <span>Enter para enviar • Shift+Enter para nueva línea</span>
      </div>
    </div>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import useChatAnalysis from "../composables/useChatAnalysis.js";
import SimilarDocumentsSection from "./SimilarDocumentsSection.vue";
import DocumentMetadataCard from "./DocumentMetadataCard.vue";

/* ========== PROPS ========== */
const props = defineProps({
  document: {
    type: Object,
    required: true,
  },
  similarDocuments: {
    type: Array,
    default: () => [],
  },
  loadingSimilar: {
    type: Boolean,
    default: false,
  },
  showMetadata: {
    type: Boolean,
    default: true,
  },
  topicKeywords: {
    type: Object,
    default: () => null,
  },
  loadingKeywords: {
    type: Boolean,
    default: false,
  },
});

/* ========== EMITS ========== */
const emit = defineEmits(["select-similar"]);

/* ========== STATE ========== */
const showMetadataDialog = ref(false);

/* ========== DEBUG ========== */
console.log("💬 ChatAnalysisPanel mounted", {
  hasDocument: !!props.document,
  documentId: props.document?.document_id,
  hasSummary: !!props.document?.summary,
  similarDocsCount: props.similarDocuments?.length || 0,
});

watch(
  () => props.document,
  (newDoc) => {
    console.log("💬 ChatAnalysisPanel document changed", {
      hasDocument: !!newDoc,
      documentId: newDoc?.document_id,
      hasSummary: !!newDoc?.summary,
    });
  }
);

/* ========== COMPOSABLES ========== */
const {
  messages,
  inputMessage,
  isLoading,
  chatBodyRef,
  chatMode,
  sendMessage,
  clearChat,
  resetChat,
  setChatMode,
} = useChatAnalysis(computed(() => props.document));

/* ========== COMPUTED ========== */
const hasSimilarDocuments = computed(() => {
  return props.similarDocuments && props.similarDocuments.length > 0;
});

const hasTopicKeywords = computed(() => {
  return (
    props.topicKeywords?.has_topic && props.topicKeywords?.keywords?.length > 0
  );
});

const displayKeywords = computed(() => {
  if (!props.topicKeywords?.keywords) return [];
  // Limit to 8 keywords for display
  return props.topicKeywords.keywords.slice(0, 8);
});

/* ========== METHODS ========== */
const keywordColors = ["primary", "secondary", "success", "info", "warning"];

function getKeywordColor(index) {
  return keywordColors[index % keywordColors.length];
}
/* ========== METHODS ========== */
function formatMessageText(text) {
  if (!text) return "";

  // Convert line breaks to <br>
  let formatted = text.replace(/\n/g, "<br>");

  // Basic markdown-like formatting
  // Bold: **text** or __text__
  formatted = formatted.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  formatted = formatted.replace(/__(.+?)__/g, "<strong>$1</strong>");

  // Italic: *text* or _text_
  formatted = formatted.replace(/\*(.+?)\*/g, "<em>$1</em>");
  formatted = formatted.replace(/_(.+?)_/g, "<em>$1</em>");

  // Lists: lines starting with - or *
  formatted = formatted.replace(
    /^[\-\*]\s+(.+)$/gm,
    '<div style="margin-left: 1em;">• $1</div>'
  );

  return formatted;
}

function formatTime(timestamp) {
  if (!timestamp) return "";

  const date = new Date(timestamp);
  return date.toLocaleTimeString("es-ES", {
    hour: "2-digit",
    minute: "2-digit",
  });
}
</script>

<style scoped lang="scss">
.chat-analysis-panel {
  display: flex;
  flex-direction: column;
  height: clamp(500px, calc(100vh - 300px), 800px);

  .chat-header {
    flex-shrink: 0;
    padding: 10px 14px;
  }

  .chat-body {
    flex: 1;
    overflow-y: auto;
    min-height: 0;
    max-height: 400px; // Limit height so chat doesn't grow infinitely
    // Chat body will grow/shrink with panel, but has internal scroll

    &::-webkit-scrollbar {
      width: 8px;
    }

    &::-webkit-scrollbar-track {
      background: rgba(0, 0, 0, 0.05);
      border-radius: 4px;
    }

    &::-webkit-scrollbar-thumb {
      background: rgba(0, 0, 0, 0.2);
      border-radius: 4px;

      &:hover {
        background: rgba(0, 0, 0, 0.3);
      }
    }
  }

  .keywords-section {
    flex-shrink: 0;
    background: rgba(var(--v-theme-secondary), 0.03);

    .keywords-container {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
    }
  }

  .similar-docs-section {
    flex-shrink: 0;
    background: rgba(var(--v-theme-surface), 0.5);
    max-height: 200px;
    overflow-y: auto;

    &::-webkit-scrollbar {
      width: 6px;
    }

    &::-webkit-scrollbar-track {
      background: rgba(0, 0, 0, 0.03);
    }

    &::-webkit-scrollbar-thumb {
      background: rgba(0, 0, 0, 0.15);
      border-radius: 3px;

      &:hover {
        background: rgba(0, 0, 0, 0.25);
      }
    }
  }

  .messages-container {
    min-height: 200px;
  }

  .empty-chat-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 300px;
    text-align: center;
    padding: 2rem;
  }

  .message-wrapper {
    display: flex;
    align-items: flex-start;
    animation: slideIn 0.3s ease-out;

    &.user-message {
      justify-content: flex-end;

      .message-bubble {
        background: linear-gradient(
          135deg,
          rgb(var(--v-theme-primary)),
          rgb(var(--v-theme-secondary))
        );
        color: white;
        margin-left: auto;
        box-shadow: 0 2px 8px rgba(var(--v-theme-primary), 0.3);
      }
    }

    &.assistant-message {
      justify-content: flex-start;

      .message-bubble {
        background: white;
        color: rgb(var(--v-theme-on-surface));
        border: 1px solid rgba(0, 0, 0, 0.08);
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);

        &.summary {
          background: linear-gradient(
            135deg,
            rgba(var(--v-theme-primary), 0.03),
            rgba(var(--v-theme-secondary), 0.03)
          );
          border: 1px solid rgba(var(--v-theme-primary), 0.15);
          box-shadow: 0 2px 8px rgba(var(--v-theme-primary), 0.1);
        }

        &.error {
          background: rgba(var(--v-theme-error), 0.05);
          border: 1px solid rgba(var(--v-theme-error), 0.2);
        }
      }
    }
  }

  .message-bubble {
    max-width: 75%;
    padding: 0.875rem 1.125rem;
    border-radius: 16px;
    word-wrap: break-word;
    transition: all 0.2s ease;

    &:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
    }

    .summary-header {
      .border-bottom {
        border-bottom: 1px solid rgba(0, 0, 0, 0.08);
      }
    }

    .message-text {
      line-height: 1.6;
      white-space: pre-wrap;
      font-size: 0.9375rem;

      :deep(strong) {
        font-weight: 600;
        color: rgb(var(--v-theme-primary));
      }

      :deep(em) {
        font-style: italic;
        color: rgba(0, 0, 0, 0.75);
      }

      :deep(ul),
      :deep(ol) {
        margin: 0.5rem 0;
        padding-left: 1.5rem;
      }

      :deep(li) {
        margin: 0.25rem 0;
      }
    }

    .message-timestamp {
      font-size: 0.6875rem;
      margin-top: 0.5rem;
      opacity: 0.6;
      font-weight: 500;
    }
  }

  .typing-indicator {
    padding: 1rem;

    .typing-dots {
      display: flex;
      gap: 0.25rem;

      span {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: rgb(var(--v-theme-primary));
        animation: typing 1.4s infinite;

        &:nth-child(2) {
          animation-delay: 0.2s;
        }

        &:nth-child(3) {
          animation-delay: 0.4s;
        }
      }
    }
  }

  .chat-input {
    flex-shrink: 0;
    background: rgb(var(--v-theme-surface));
    border-top: 1px solid rgba(0, 0, 0, 0.06);

    .chat-input-field {
      :deep(.v-field) {
        border-radius: 24px;
        background: white;
        transition: all 0.2s ease;

        &:hover {
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }

        &.v-field--focused {
          box-shadow: 0 4px 12px rgba(var(--v-theme-primary), 0.15);
        }
      }

      :deep(.v-field__outline) {
        --v-field-border-opacity: 0.2;
      }
    }

    .send-btn {
      transition: all 0.2s ease;

      &:not(:disabled):hover {
        transform: scale(1.05);
        box-shadow: 0 4px 12px rgba(var(--v-theme-primary), 0.3);
      }

      &:not(:disabled):active {
        transform: scale(0.95);
      }
    }
  }

  .gap-2 {
    gap: 0.5rem;
  }

  .border-top {
    border-top: 1px solid rgba(0, 0, 0, 0.12);
  }
}

/* Animations */
@keyframes typing {
  0%,
  60%,
  100% {
    transform: translateY(0);
    opacity: 0.7;
  }
  30% {
    transform: translateY(-10px);
    opacity: 1;
  }
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(15px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-fade-enter-active,
.message-fade-leave-active {
  transition: all 0.3s ease;
}

.message-fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.message-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* Dark Theme */
.v-theme--dark {
  .chat-analysis-panel {
    .chat-body {
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

    .message-wrapper {
      &.assistant-message {
        .message-bubble {
          background: rgb(var(--v-theme-grey-darken-3));
        }
      }
    }

    .border-top {
      border-top-color: rgba(255, 255, 255, 0.12);
    }
  }
}

/* Responsive */
@media (max-width: 1280px) {
  .chat-analysis-panel {
    height: 500px;
    min-height: 450px;
  }

  .chat-body {
    max-height: 260px;
  }

  .similar-docs-section {
    max-height: 160px;
  }
}

@media (max-width: 960px) {
  .chat-analysis-panel {
    height: 450px;
    min-height: 400px;
  }

  .chat-body {
    max-height: 220px;
  }

  .message-bubble {
    max-width: 85%;
  }

  .similar-docs-section {
    max-height: 140px;
  }
}

@media (max-width: 600px) {
  .chat-analysis-panel {
    height: 400px;
    min-height: 350px;
  }

  .chat-body {
    max-height: 180px;
  }

  .message-bubble {
    max-width: 90%;
    padding: 0.5rem 0.75rem;
  }

  .similar-docs-section {
    max-height: 120px;
  }
}
</style>
