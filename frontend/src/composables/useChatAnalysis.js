import { ref, watch, nextTick } from "vue";
import axios from "axios";

/**
 * Composable para manejar el chat de análisis de documentos
 * Integra la funcionalidad del chat con Ollama y el contexto del documento
 *
 * Modos disponibles:
 * - 'rag': Búsqueda semántica de chunks relevantes (recomendado)
 * - 'normal': Usa los primeros 6000 caracteres del documento
 */
export default function useChatAnalysis(document) {
  // Estado del chat
  const messages = ref([]);
  const inputMessage = ref("");
  const isLoading = ref(false);
  const chatBodyRef = ref(null);
  const chatMode = ref("rag"); // 'rag' o 'normal'

  /**
   * Inicializa el chat con un mensaje de bienvenida y el resumen del documento
   */
  const initializeChat = () => {
    if (!document.value) {
      console.log(
        "⚠️ useChatAnalysis: No document provided, skipping initialization"
      );
      return;
    }

    console.log("🚀 useChatAnalysis: Initializing chat", {
      documentId: document.value.document_id,
      hasSummary: !!document.value.summary,
      hasFormattedSummary: !!document.value.formatted_summary,
    });

    // Limpiar mensajes anteriores
    messages.value = [];

    // Mensaje de bienvenida del asistente
    const welcomeMessage = {
      from: "assistant",
      text: "¡Hola! Soy tu asistente de análisis legal. He analizado el documento y puedo ayudarte a comprenderlo mejor. A continuación te presento el resumen:",
      timestamp: new Date(),
    };

    messages.value.push(welcomeMessage);

    // Agregar el resumen como mensaje del asistente
    if (document.value.formatted_summary || document.value.summary) {
      const summaryMessage = {
        from: "assistant",
        text: document.value.formatted_summary || document.value.summary,
        timestamp: new Date(),
        type: "summary",
      };

      messages.value.push(summaryMessage);
      console.log("✅ useChatAnalysis: Summary message added");
    } else {
      console.warn("⚠️ useChatAnalysis: No summary available");
    }

    // Mensaje adicional ofreciendo ayuda
    const helpMessage = {
      from: "assistant",
      text: "¿Tienes alguna pregunta sobre este documento? Puedo ayudarte a entender mejor su contenido, las partes involucradas, fechas importantes, o cualquier aspecto legal que te interese.",
      timestamp: new Date(),
    };

    messages.value.push(helpMessage);

    console.log(
      `✅ useChatAnalysis: Chat initialized with ${messages.value.length} messages`
    );
  };

  /**
   * Envía un mensaje al chat
   */
  const sendMessage = async () => {
    const messageText = inputMessage.value.trim();
    if (!messageText || !document.value) return;

    // Agregar mensaje del usuario
    messages.value.push({
      from: "user",
      text: messageText,
      timestamp: new Date(),
    });

    // Limpiar input
    inputMessage.value = "";

    // Scroll al final
    await nextTick();
    scrollToBottom();

    // Mostrar indicador de typing
    isLoading.value = true;

    try {
      // Llamar al endpoint de chat con Ollama
      const response = await axios.post("/api/chat/document/", {
        document_id: document.value.document_id,
        message: messageText,
        mode: chatMode.value, // 'rag' o 'normal'
        history: messages.value
          .filter((m) => m.type !== "summary") // No incluir el resumen en el historial
          .slice(-10) // Solo últimos 10 mensajes para no saturar el contexto
          .map((m) => ({
            from: m.from,
            text: m.text,
          })),
      });

      console.log("✅ Chat response received:", {
        mode: chatMode.value,
        response: response.data.response?.substring(0, 100) + "...",
        context_used: response.data.context_used,
      });

      // Agregar respuesta del asistente
      messages.value.push({
        from: "assistant",
        text: response.data.response || response.data.message,
        timestamp: new Date(),
      });
    } catch (error) {
      console.error("❌ Error sending message:", error);

      let errorMessage =
        "Lo siento, ha ocurrido un error al procesar tu mensaje.";

      // Handle specific error cases
      if (error.response) {
        if (error.response.status === 503) {
          errorMessage =
            "El servicio de IA no está disponible. Por favor verifica que Ollama esté ejecutándose.";
        } else if (error.response.data?.response) {
          // Backend returned a fallback response
          errorMessage = error.response.data.response;
        } else if (error.response.data?.error) {
          errorMessage = error.response.data.error;
        }
      } else if (error.request) {
        errorMessage =
          "No se pudo conectar con el servidor. Por favor verifica tu conexión.";
      }

      // Mensaje de error
      messages.value.push({
        from: "assistant",
        text: errorMessage,
        timestamp: new Date(),
        error: true,
      });
    } finally {
      isLoading.value = false;
      await nextTick();
      scrollToBottom();
    }
  };

  /**
   * Scroll automático al final del chat
   */
  const scrollToBottom = () => {
    if (chatBodyRef.value) {
      const element = chatBodyRef.value;
      element.scrollTop = element.scrollHeight;
    }
  };

  /**
   * Limpia el chat
   */
  const clearChat = () => {
    messages.value = [];
    inputMessage.value = "";
  };

  /**
   * Reinicia el chat con el documento actual
   */
  const resetChat = () => {
    clearChat();
    initializeChat();
  };

  /**
   * Cambia el modo del chat
   * @param {string} mode - 'rag' o 'normal'
   */
  const setChatMode = (mode) => {
    if (mode === "rag" || mode === "normal") {
      chatMode.value = mode;
      console.log(`🔄 Chat mode changed to: ${mode}`);
    }
  };

  // Observar cambios en el documento para reinicializar el chat
  watch(
    () => document.value,
    (newDoc) => {
      if (newDoc) {
        initializeChat();
      }
    },
    { immediate: true }
  );

  return {
    messages,
    inputMessage,
    isLoading,
    chatBodyRef,
    chatMode,
    sendMessage,
    clearChat,
    resetChat,
    initializeChat,
    scrollToBottom,
    setChatMode,
  };
}
