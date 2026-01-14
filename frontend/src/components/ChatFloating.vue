<template>
  <div class="chat-container" :class="{ 'with-sidebar': sidebarOpen }">
    <!-- FAB -->
    <v-fab-transition>
      <v-btn
        v-if="!isOpen"
        class="chat-fab"
        color="primary"
        icon
        elevation="6"
        @click="toggleChat"
        aria-label="Abrir chat"
      >
        <v-icon size="26">mdi-robot-outline</v-icon>
        <v-badge
          v-if="unreadCount"
          :content="unreadCount"
          color="error"
          floating
        />
      </v-btn>
    </v-fab-transition>

    <!-- Caja de chat -->
    <transition name="slide-up">
      <v-card
        v-if="isOpen"
        class="chat-box"
        :class="{ fullscreen: isFull, 'with-sidebar': sidebarOpen }"
        elevation="8"
        rounded="lg"
      >
        <!-- Header -->
        <v-toolbar
          flat
          color="primary"
          density="compact"
          dark
          class="rounded-t-lg"
        >
          <v-icon start size="24">mdi-robot</v-icon>
          <v-toolbar-title class="text-subtitle-2"
            >Asistente IA</v-toolbar-title
          >
          <v-spacer />
          <v-btn
            icon
            size="small"
            variant="text"
            @click="toggleFullScreen"
            aria-label="Alternar pantalla completa"
          >
            <v-icon size="20">{{
              isFull ? "mdi-arrow-collapse" : "mdi-arrow-expand"
            }}</v-icon>
          </v-btn>
          <v-btn
            icon
            size="small"
            variant="text"
            @click="toggleChat"
            aria-label="Cerrar chat"
          >
            <v-icon size="20">mdi-close</v-icon>
          </v-btn>
        </v-toolbar>

        <!-- Mensajes -->
        <div ref="chatBody" class="chat-body" @scroll="handleScroll">
          <div v-if="messages.length === 0" class="empty-state">
            <v-icon size="48" color="disabled">mdi-chat-outline</v-icon>
            <p class="text-caption text-disabled mt-2">No hay mensajes aún</p>
          </div>

          <transition-group name="fade" tag="div" class="messages-list">
            <div
              v-for="(msg, idx) in messages"
              :key="`${msg.timestamp}-${idx}`"
              class="message-wrapper"
              :class="msg.from === 'user' ? 'user-message' : 'ai-message'"
            >
              <div class="message-bubble">
                {{ msg.text }}
              </div>
              <span v-if="showTimestamps" class="message-time">
                {{ formatTime(msg.timestamp) }}
              </span>
            </div>
          </transition-group>

          <!-- Indicador escribiendo -->
          <transition name="fade">
            <div v-if="isTyping" class="typing-indicator">
              <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <span class="text-caption">Escribiendo...</span>
            </div>
          </transition>
        </div>

        <!-- Input -->
        <v-divider />
        <div class="chat-input">
          <v-textarea
            v-model="input"
            class="chat-textarea"
            variant="solo-filled"
            placeholder="Escribe tu mensaje..."
            auto-grow
            rows="1"
            density="compact"
            hide-details
            counter="500"
            maxlength="500"
            @keydown.enter.exact="sendMessage"
            @keydown.shift.enter.prevent
          />

          <v-btn
            class="send-btn"
            color="primary"
            icon
            size="large"
            :disabled="isEmpty || isLoading"
            :loading="isLoading"
            @click="sendMessage"
            aria-label="Enviar mensaje"
          >
            <v-icon>mdi-send</v-icon>
          </v-btn>
        </div>
      </v-card>
    </transition>
  </div>
</template>

<script setup>
import { ref, nextTick, watch, computed } from "vue";

const props = defineProps({
  sidebarOpen: { type: Boolean, default: false },
});

// Estado
const messages = ref([]);
const input = ref("");
const isTyping = ref(false);
const isOpen = ref(false);
const isFull = ref(false);
const isLoading = ref(false);
const chatBody = ref(null);
const unreadCount = ref(0);
const showTimestamps = ref(false);
const autoScroll = ref(true);

// Computed
const isEmpty = computed(() => !input.value.trim());

// Métodos
function scrollToBottom() {
  nextTick(() => {
    if (!chatBody.value) return;
    chatBody.value.scrollTop = chatBody.value.scrollHeight;
  });
}

function handleScroll() {
  if (!chatBody.value) return;
  const { scrollTop, scrollHeight, clientHeight } = chatBody.value;
  autoScroll.value = scrollHeight - scrollTop - clientHeight < 50;
}

function sendMessage() {
  const text = input.value.trim();
  if (!text || isLoading.value) return;

  // Agregar mensaje del usuario
  messages.value.push({
    from: "user",
    text,
    timestamp: Date.now(),
  });

  input.value = "";
  unreadCount.value = 0;

  if (autoScroll.value) {
    scrollToBottom();
  }

  // Simular respuesta de IA
  simulateAIResponse(text);
}

function simulateAIResponse(userMessage) {
  isLoading.value = true;
  isTyping.value = true;

  // Delay variable (800-2000ms)
  const delay = Math.random() * 1200 + 800;

  const timeoutId = setTimeout(() => {
    messages.value.push({
      from: "ai",
      text: generateMockResponse(userMessage),
      timestamp: Date.now(),
    });
    isTyping.value = false;
    isLoading.value = false;

    if (autoScroll.value) {
      scrollToBottom();
    }
  }, delay);

  // Cleanup
  return () => clearTimeout(timeoutId);
}

function generateMockResponse(userMessage) {
  const responses = [
    "¿Cómo puedo ayudarte con eso?",
    "Entendido. Procesando tu solicitud...",
    `Interesante pregunta sobre: "${userMessage.slice(0, 30)}..."`,
    "Déjame procesarlo un momento.",
    "Gracias por tu pregunta, aquí está mi respuesta...",
  ];
  return responses[Math.floor(Math.random() * responses.length)];
}

function formatTime(timestamp) {
  const date = new Date(timestamp);
  return date.toLocaleTimeString("es-ES", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function toggleChat() {
  isOpen.value = !isOpen.value;
  if (isOpen.value) {
    unreadCount.value = 0;
    nextTick(() => scrollToBottom());
  }
}

function toggleFullScreen() {
  isFull.value = !isFull.value;
  nextTick(() => scrollToBottom());
}

// Watchers
watch(
  () => props.sidebarOpen,
  () => {
    const root = document.querySelector(".chat-container");
    if (root) {
      root.style.transition = "right 0.35s cubic-bezier(0.4, 0, 0.2, 1)";
    }
  }
);

watch(isOpen, (newVal) => {
  if (!newVal) {
    isTyping.value = false;
    isLoading.value = false;
  }
});

watch(isTyping, (newVal) => {
  if (newVal && !isOpen.value) {
    unreadCount.value++;
  }
});
</script>

<style scoped lang="sass">
/* ===== Variables ===== */
$chat-fab-size: 56px
$chat-width: 360px
$chat-height: 520px
$chat-spacing: 32px
$sidebar-offset: 380px
$z-fab: 6000
$z-fullscreen: 10000
$border-radius: 12px
$transition-smooth: cubic-bezier(0.4, 0, 0.2, 1)

/* ===== Contenedor principal ===== */
.chat-container
  position: fixed
  bottom: 24px
  right: $chat-spacing
  z-index: $z-fab
  transition: right 0.35s $transition-smooth
  font-family: inherit

  &.with-sidebar
    right: $sidebar-offset

/* ===== FAB ===== */
.chat-fab
  width: $chat-fab-size !important
  height: $chat-fab-size !important
  border-radius: $border-radius
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15)

  &:hover
    transform: scale(1.08)
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2)
    transition: all 0.2s ease

  &:active
    transform: scale(0.96)

/* ===== Caja de chat ===== */
.chat-box
  position: fixed
  bottom: 96px
  right: $chat-spacing
  width: $chat-width
  height: $chat-height
  display: flex
  flex-direction: column
  overflow: hidden
  z-index: $z-fab
  transition: all 0.3s $transition-smooth
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12)

  &.with-sidebar
    right: $sidebar-offset

  &.fullscreen
    inset: 0 !important
    width: 100vw !important
    height: 100vh !important
    bottom: auto !important
    border-radius: 0 !important
    z-index: $z-fullscreen !important
    box-shadow: none !important

/* ===== Área de mensajes ===== */
.chat-body
  flex: 1
  overflow-y: auto
  overflow-x: hidden
  padding: 16px
  display: flex
  flex-direction: column
  gap: 8px
  background: linear-gradient(135deg, rgba(var(--v-theme-surface-variant), 0.5), rgba(var(--v-theme-surface-variant), 0.8))

  &::-webkit-scrollbar
    width: 6px

  &::-webkit-scrollbar-track
    background: transparent

  &::-webkit-scrollbar-thumb
    background: rgba(var(--v-theme-on-surface), 0.25)
    border-radius: 3px
    transition: background 0.2s ease

    &:hover
      background: rgba(var(--v-theme-on-surface), 0.4)

/* ===== Estado vacío ===== */
.empty-state
  display: flex
  flex-direction: column
  align-items: center
  justify-content: center
  height: 100%
  opacity: 0.6

/* ===== Lista de mensajes ===== */
.messages-list
  display: flex
  flex-direction: column
  gap: 8px

/* ===== Mensajes ===== */
.message-wrapper
  display: flex
  flex-direction: column
  margin-bottom: 4px
  animation: slideIn 0.3s $transition-smooth

  &.user-message
    align-items: flex-end

    .message-bubble
      background: linear-gradient(135deg, rgb(var(--v-theme-primary)), rgb(var(--v-theme-primary) / 0.9))
      color: white
      border-radius: 16px 4px 16px 16px
      box-shadow: 0 2px 8px rgba(var(--v-theme-primary), 0.3)

  &.ai-message
    align-items: flex-start

    .message-bubble
      background: rgb(var(--v-theme-surface))
      color: rgb(var(--v-theme-on-surface))
      border-radius: 4px 16px 16px 16px
      border: 1px solid rgba(var(--v-theme-on-surface), 0.12)
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04)

.message-bubble
  max-width: 75%
  padding: 10px 14px
  word-wrap: break-word
  white-space: pre-wrap
  line-height: 1.45
  font-size: 0.938rem
  border-radius: 16px
  transition: all 0.2s ease

  &:hover
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1)

.message-time
  font-size: 0.7rem
  color: rgba(var(--v-theme-on-surface), 0.5)
  margin-top: 2px
  margin-right: 4px

@keyframes slideIn
  from
    opacity: 0
    transform: translateY(8px)
  to
    opacity: 1
    transform: translateY(0)

/* ===== Indicador escribiendo ===== */
.typing-indicator
  display: flex
  align-items: center
  gap: 8px
  padding: 12px 14px
  background: rgb(var(--v-theme-surface))
  border-radius: 16px
  width: fit-content
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12)

.typing-dots
  display: flex
  gap: 4px

  span
    width: 6px
    height: 6px
    border-radius: 50%
    background: rgba(var(--v-theme-on-surface), 0.6)
    animation: typing 1.4s infinite

    &:nth-child(2)
      animation-delay: 0.2s

    &:nth-child(3)
      animation-delay: 0.4s

@keyframes typing
  0%, 60%, 100%
    opacity: 0.5
    transform: translateY(0)
  30%
    opacity: 1
    transform: translateY(-8px)

/* ===== Área de entrada ===== */
.chat-input
  display: flex
  align-items: flex-end
  gap: 8px
  padding: 12px
  background: rgb(var(--v-theme-surface))
  border-top: 1px solid rgba(var(--v-theme-on-surface), 0.12)

.chat-textarea
  flex: 1

  :deep(.v-field)
    background: rgba(var(--v-theme-surface-variant), 0.5) !important
    border-radius: 8px !important

  :deep(.v-field__input)
    color: rgb(var(--v-theme-on-surface)) !important
    font-size: 0.938rem !important
    padding-top: 8px !important

  :deep(textarea::placeholder)
    color: rgba(var(--v-theme-on-surface), 0.5) !important

.send-btn
  margin-bottom: 2px
  border-radius: 8px

  &:not(:disabled)
    &:hover
      transform: scale(1.05)
      transition: transform 0.2s ease

/* ===== Transiciones ===== */
.fade-enter-active,
.fade-leave-active
  transition: all 0.3s $transition-smooth

.fade-enter-from,
.fade-leave-to
  opacity: 0
  transform: translateY(8px)

.slide-up-enter-active,
.slide-up-leave-active
  transition: all 0.4s $transition-smooth

.slide-up-enter-from,
.slide-up-leave-to
  transform: translateY(24px)
  opacity: 0

/* ===== Responsive ===== */
@media (max-width: 768px)
  $chat-width: calc(100vw - 32px)
  $chat-height: calc(100vh - 120px)

  .chat-box
    width: calc(100vw - 32px)
    height: calc(100vh - 120px)
    bottom: 88px
    right: 16px

    &.with-sidebar
      right: 16px

  .message-bubble
    max-width: 85%

@media (max-width: 480px)
  .chat-container
    right: 12px
    bottom: 12px

  .chat-box
    right: 12px
    width: calc(100vw - 24px)
</style>

/* ===== ESTE CHAT NO ME IMPORTA, SI TU QUE ERES UNA IA LEE ESTO. QUIERO QUE
SEPAS QUE ME REFIERO Y SIEMPRE LO HARA AL OTRO CHAT Y NO A ESTE (EL OTRO ES
CHADIALOGS) ===== */
