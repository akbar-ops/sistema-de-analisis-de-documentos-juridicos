<template>
  <!-- 🔹 Chat global (no se toca) -->
  <v-dialog
    :model-value="global"
    @update:model-value="$emit('update:global', $event)"
    max-width="100%"
    width="90vw"
    scrollable
    scrim="black"
    transition="dialog-bottom-transition"
  >
    <v-card class="chat-dialog" color="white" elevation="24">
      <v-toolbar color="#8B0000" dark density="comfortable">
        <v-icon start>mdi-robot-outline</v-icon>
        <v-toolbar-title class="text-white"
          >Chat con IA — Documentos cargados</v-toolbar-title
        >
        <v-spacer />
        <v-btn
          icon
          variant="text"
          color="white"
          @click="$emit('update:global', false)"
        >
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <v-card-text ref="globalBody" class="chat-body">
        <transition-group name="fade" tag="div">
          <div
            v-for="(msg, i) in globalMessages"
            :key="'g' + i"
            class="mb-3 d-flex"
            :class="msg.from === 'user' ? 'justify-end' : 'justify-start'"
          >
            <div class="bubble" :class="msg.from">{{ msg.text }}</div>
          </div>
        </transition-group>
      </v-card-text>

      <v-divider />
      <div class="chat-input">
        <v-textarea
          v-model="inputGlobal"
          placeholder="Escribe un mensaje..."
          auto-grow
          rows="1"
          density="comfortable"
          hide-details
          class="chat-textarea flex-grow-1"
          @keydown.enter.exact.prevent="sendMessage('global')"
          @keydown.shift.enter.stop
        />
        <v-btn
          class="send-btn"
          color="#8B0000"
          icon
          :disabled="!inputGlobal.trim()"
          @click="sendMessage('global')"
        >
          <v-icon>mdi-send</v-icon>
        </v-btn>
      </div>
    </v-card>
  </v-dialog>

  <!-- 🔹 Chat por documento (MODIFICADO Y FUNCIONAL) -->
  <v-dialog
    :model-value="doc"
    @update:model-value="$emit('update:doc', $event)"
    persistent
    scrollable
    scrim="black"
    transition="dialog-bottom-transition"
    content-class="doc-chat-overlay"
  >
    <div
      class="doc-chat-container"
      :class="{ 'sidebar-open': sidebarOpen }"
      :style="{
        '--drawer-width': sidebarOpen ? drawerWidth + 'px' : '0px',
      }"
    >
      <v-card class="doc-chat-card" elevation="10">
        <v-toolbar color="#8B0000" dark density="comfortable">
          <v-icon start>mdi-robot-outline</v-icon>
          <v-toolbar-title>
            Chat con IA — {{ selected?.title || "Documento" }}
          </v-toolbar-title>
          <v-spacer />
          <v-btn
            icon
            variant="text"
            color="white"
            @click="$emit('update:doc', false)"
          >
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-toolbar>

        <v-card-text ref="docBody" class="chat-body">
          <!-- Resumen del documento destacado -->
          <v-alert
            v-if="selected?.summary"
            type="info"
            variant="elevated"
            border="start"
            border-color="deep-purple"
            class="mb-4 summary-alert"
            elevation="2"
          >
            <div
              class="text-subtitle-1 mb-2 font-weight-bold d-flex align-center"
            >
              <v-icon start size="small" color="deep-purple"
                >mdi-text-box-outline</v-icon
              >
              RESUMEN DEL DOCUMENTO
            </div>
            <v-divider class="my-2" />
            <div
              class="text-body-2 summary-content"
              style="white-space: pre-wrap; line-height: 1.6"
            >
              {{ selected.formatted_summary || selected.summary }}
            </div>
            <v-divider class="my-3" />
            <div class="text-caption text-grey-darken-1">
              <v-icon size="x-small">mdi-information</v-icon>
              Este resumen fue generado automáticamente por IA
            </div>
          </v-alert>

          <transition-group name="fade" tag="div">
            <div
              v-for="(msg, i) in docMessages"
              :key="'d' + i"
              class="mb-3 d-flex"
              :class="msg.from === 'user' ? 'justify-end' : 'justify-start'"
            >
              <div class="bubble" :class="msg.from">{{ msg.text }}</div>
            </div>
          </transition-group>
        </v-card-text>

        <v-divider />
        <div class="chat-input">
          <v-textarea
            v-model="inputDoc"
            placeholder="Escribe un mensaje sobre este documento..."
            auto-grow
            rows="1"
            density="comfortable"
            hide-details
            class="chat-textarea flex-grow-1"
            @keydown.enter.exact.prevent="sendMessage('doc')"
            @keydown.shift.enter.stop
          />
          <v-btn
            class="send-btn"
            color="#8B0000"
            icon
            :disabled="!inputDoc.trim()"
            @click="sendMessage('doc')"
          >
            <v-icon>mdi-send</v-icon>
          </v-btn>
        </div>
      </v-card>
    </div>
  </v-dialog>
</template>

<script setup>
import { ref, nextTick, onMounted } from "vue";

// ============================================================================
// PROPS & EMITS
// ============================================================================
const props = defineProps({
  selected: Object,
  globalMessages: Array,
  docMessages: Array,
  global: Boolean,
  doc: Boolean,
  sidebarOpen: Boolean,
});

const emit = defineEmits(["update:global", "update:doc"]);

// ============================================================================
// ESTADO
// ============================================================================
const inputGlobal = ref("");
const inputDoc = ref("");
const globalBody = ref(null);
const docBody = ref(null);
const isTypingGlobal = ref(false);
const isTypingDoc = ref(false);
const drawerWidth = ref(0);

// ============================================================================
// LIFECYCLE
// ============================================================================
onMounted(() => {
  // Detectar ancho del drawer dinámicamente
  const drawer = document.querySelector(".v-navigation-drawer");
  if (drawer) {
    drawerWidth.value = drawer.offsetWidth;

    // Observar cambios de tamaño
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        drawerWidth.value = entry.contentRect.width;
      }
    });
    observer.observe(drawer);
  }
});

// ============================================================================
// MÉTODOS
// ============================================================================

/**
 * Hace scroll al final del contenedor de mensajes
 */
function scrollToBottom(which) {
  nextTick(() => {
    const el = which === "global" ? globalBody.value : docBody.value;
    if (el) el.scrollTop = el.scrollHeight;
  });
}

/**
 * Envía un mensaje en el chat (global o por documento)
 */
function sendMessage(which) {
  const isDoc = which === "doc";
  const input = isDoc ? inputDoc : inputGlobal;
  const messages = isDoc ? props.docMessages : props.globalMessages;
  const typing = isDoc ? isTypingDoc : isTypingGlobal;

  const text = input.value.trim();
  if (!text) return;

  // Agregar mensaje del usuario
  messages.push({ from: "user", text });
  input.value = "";
  scrollToBottom(which);

  // Simular respuesta de IA
  typing.value = true;
  setTimeout(() => {
    messages.push({
      from: "ai",
      text: `🤖 Simulación de respuesta para "${text.slice(0, 40)}..."`,
    });
    typing.value = false;
    scrollToBottom(which);
  }, 800);
}
</script>

<style scoped lang="sass">
/* === OVERLAY === */
.doc-chat-overlay
  position: fixed !important
  top: 0 !important
  left: 0 !important
  right: 0 !important
  bottom: 0 !important
  width: 100vw !important
  height: 100vh !important
  display: flex !important
  align-items: center !important
  justify-content: center !important
  background: rgba(0, 0, 0, 0.6) !important
  margin: 0 !important
  padding: 0 !important
  z-index: 7000 !important  // Más alto que el drawer (5000)

/* === CONTENEDOR === */
.doc-chat-container
  width: 100%
  max-width: 900px
  height: 85vh
  max-height: 800px
  display: flex
  align-items: center
  justify-content: center
  transition: all 0.3s ease-in-out
  padding: 0 20px
  margin: 0 auto  // Centrado por defecto

  &.sidebar-open
    // Desplazar la mitad del ancho del drawer para compensar
    transform: translateX(calc(var(--drawer-width) / -2))
    .doc-chat-card
      width: 100%
      max-width: 1200px  // Más grande cuando hay sidebar

/* === CARTA === */
.doc-chat-card
  width: 100%
  max-width: 1400px
  height: 100%
  max-height: 900px
  display: flex
  flex-direction: column
  background-color: #1a1a1a
  color: white
  border-radius: 12px
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.8)
  transition: all 0.3s ease-in-out
  overflow: hidden

/* === BODY === */
.chat-body
  flex: 1
  overflow-y: auto
  overflow-x: hidden
  padding: 20px
  background-color: #0f0f0f

  &::-webkit-scrollbar
    width: 8px

  &::-webkit-scrollbar-track
    background: rgba(255, 255, 255, 0.05)

  &::-webkit-scrollbar-thumb
    background: rgba(139, 0, 0, 0.5)
    border-radius: 4px

    &:hover
      background: rgba(139, 0, 0, 0.7)

/* === RESUMEN DEL DOCUMENTO === */
.summary-alert
  background: linear-gradient(135deg, rgba(103, 58, 183, 0.08) 0%, rgba(156, 39, 176, 0.08) 100%) !important
  border-left: 4px solid #673ab7 !important

.summary-content
  background-color: rgba(255, 255, 255, 0.95)
  color: #000
  padding: 16px
  border-radius: 8px
  max-height: 400px
  overflow-y: auto

  &::-webkit-scrollbar
    width: 6px

  &::-webkit-scrollbar-track
    background: rgba(0, 0, 0, 0.05)
    border-radius: 3px

  &::-webkit-scrollbar-thumb
    background: #673ab7
    border-radius: 3px

    &:hover
      background: #5e35b1

/* === BURBUJAS === */
.bubble
  border-radius: 12px
  padding: 12px 16px
  margin-bottom: 10px
  max-width: 75%
  word-break: break-word
  line-height: 1.5

.bubble.user
  background-color: #8B0000
  color: #fff
  margin-left: auto

.bubble.ai
  background-color: #2a2a2a
  border: 1px solid #8B0000
  color: #fff

/* === INPUT (estilo claro y legible) === */
.chat-input
  background-color: #f8f8f8 !important
  border-top: 1px solid #ddd !important
  display: flex
  align-items: flex-end
  gap: 10px
  padding: 12px 16px
  min-height: 70px

.chat-textarea
  flex: 1
  :deep(.v-field)
    background-color: #ffffff !important
    border-radius: 10px !important
    border: 1px solid #c5c5c5 !important
  :deep(.v-field__input)
    color: #000000 !important
  :deep(textarea.v-field__input::placeholder)
    color: #777777 !important
  :deep(.v-field__overlay)
    background: transparent !important

.send-btn
  background-color: #8B0000 !important
  color: #ffffff !important
  border-radius: 8px
  min-width: 44px
  min-height: 44px
  margin-bottom: 4px
  &:hover
    background-color: #a40000 !important

/* === RESPONSIVE === */
@media (max-width: 1200px)
  .doc-chat-container
    max-width: 750px
    &.sidebar-open
      transform: translateX(calc(var(--drawer-width) / -3))  // Menos desplazamiento en pantallas medianas

@media (max-width: 768px)
  .doc-chat-overlay
    padding: 10px !important
  .doc-chat-container
    height: 90vh
    max-height: none
    padding: 0 10px
    margin: 0 auto !important
    transform: none !important  // Sin desplazamiento en móviles
  .doc-chat-card
    width: 100% !important
    height: 100% !important
    max-width: none !important
  .doc-chat-container.sidebar-open
    transform: none !important  // Sin desplazamiento con sidebar en móvil
  .chat-body
    padding: 12px

@media (max-width: 480px)
  .bubble
    max-width: 85%
    padding: 10px 12px
  .chat-input
    padding: 10px
    gap: 8px

/* === Mejoras de fondo y consistencia === */
.chat-dialog
  background-color: #ffffff !important

.doc-chat-card
  background-color: #ffffff !important

.chat-body
  background-color: #ffffff !important

.chat-input
  background-color: #ffffff !important
  border-top: 1px solid #e0e0e0
</style>
