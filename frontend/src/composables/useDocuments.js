import { ref, reactive, toRaw } from "vue";

// ============================================================================
// CONSTANTES
// ============================================================================
const API_BASE = "/api/documents";
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000;

// ============================================================================
// UTILIDADES
// ============================================================================

/**
 * Realiza una petición fetch con reintentos automáticos
 * Solo reintenta errores de red o errores 5xx del servidor
 * No reintenta errores 4xx (errores del cliente)
 * @param {string} url - URL de la petición
 * @param {object} options - Opciones de fetch
 * @param {number} retries - Número de reintentos restantes
 * @returns {Promise<Response>}
 */
async function fetchWithRetry(url, options = {}, retries = MAX_RETRIES) {
  try {
    const response = await fetch(url, options);

    // Si la respuesta es un error 4xx (error del cliente), no reintentar
    if (!response.ok && response.status >= 400 && response.status < 500) {
      throw new Error(`HTTP ${response.status}`);
    }

    // Si es otro tipo de error y tenemos reintentos, reintentar
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    return response;
  } catch (error) {
    // Solo reintentar si es un error de red o error 5xx y quedan reintentos
    const isNetworkError =
      error.message.includes("Failed to fetch") ||
      error.message.includes("NetworkError");
    const isServerError = error.message.includes("HTTP 5");

    if ((isNetworkError || isServerError) && retries > 0) {
      console.log(`Reintentando... ${retries} intentos restantes`);
      await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY));
      return fetchWithRetry(url, options, retries - 1);
    }
    throw error;
  }
}

// ============================================================================
// COMPOSABLE
// ============================================================================

export default function useDocuments() {
  // Estado
  const documents = ref([]);
  const selected = ref(null);
  const loading = ref(false);
  const error = ref(null);

  // Estado de paginación
  const pagination = reactive({
    currentPage: 1,
    pageSize: 20,
    totalItems: 0,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
  });

  const modals = reactive({
    globalChat: false,
    docChat: false,
    preview: false,
  });

  const globalMessages = ref([]);
  const docMessages = ref([]);

  // ============================================================================
  // MÉTODOS - CARGAR DATOS
  // ============================================================================

  /**
   * Carga la lista de documentos con paginación desde el backend
   * @param {number} page - Número de página (por defecto 1)
   * @param {number} pageSize - Items por página (por defecto 20)
   */
  async function loadDocuments(page = 1, pageSize = 20) {
    loading.value = true;
    error.value = null;

    try {
      const url = `${API_BASE}/?page=${page}&page_size=${pageSize}`;
      const response = await fetchWithRetry(url);
      const data = await response.json();

      // Actualizar documentos con los resultados paginados
      documents.value = data.results || [];

      // Actualizar información de paginación
      pagination.currentPage = data.current_page || page;
      pagination.pageSize = data.page_size || pageSize;
      pagination.totalItems = data.count || 0;
      pagination.totalPages = data.total_pages || 1;
      pagination.hasNext = !!data.next;
      pagination.hasPrevious = !!data.previous;

      // Actualizar documento seleccionado si existe en la nueva lista
      if (selected.value) {
        const updatedSelected = documents.value.find(
          (d) => d.document_id === selected.value.document_id
        );
        if (updatedSelected) selected.value = updatedSelected;
      }
    } catch (e) {
      console.error("Error cargando documentos:", e);
      error.value =
        "No se pudieron cargar los documentos. Verifica tu conexión.";
    } finally {
      loading.value = false;
    }
  }

  /**
   * Cambia a la página siguiente
   */
  async function nextPage() {
    if (pagination.hasNext) {
      await loadDocuments(pagination.currentPage + 1, pagination.pageSize);
    }
  }

  /**
   * Cambia a la página anterior
   */
  async function previousPage() {
    if (pagination.hasPrevious) {
      await loadDocuments(pagination.currentPage - 1, pagination.pageSize);
    }
  }

  /**
   * Cambia a una página específica
   * @param {number} page - Número de página
   */
  async function goToPage(page) {
    if (page >= 1 && page <= pagination.totalPages) {
      await loadDocuments(page, pagination.pageSize);
    }
  }

  /**
   * Cambia el tamaño de página
   * @param {number} size - Nuevo tamaño de página
   */
  async function changePageSize(size) {
    await loadDocuments(1, size);
  }

  /**
   * Carga los detalles completos de un documento específico
   * @param {string} documentId - ID del documento
   */
  async function loadDocumentDetail(documentId) {
    loading.value = true;
    error.value = null;

    try {
      const response = await fetchWithRetry(`${API_BASE}/${documentId}/`);
      if (!response.ok)
        throw new Error("Error al cargar detalles del documento");

      const data = await response.json();
      selected.value = data;

      // Actualizar también en la lista
      const index = documents.value.findIndex(
        (d) => d.document_id === documentId
      );
      if (index !== -1) {
        documents.value[index] = data;
      }

      return data;
    } catch (e) {
      console.error("Error cargando detalle del documento:", e);
      error.value = e.message;
      return null;
    } finally {
      loading.value = false;
    }
  }

  // ============================================================================
  // MÉTODOS - SELECCIÓN
  // ============================================================================

  /**
   * Selecciona un documento. Si es el mismo, marca como re-selección para toggle
   * @param {object|string} docOrId - Documento a seleccionar o su ID
   */
  async function selectDoc(docOrId) {
    console.log("📌 selectDoc called with:", docOrId);

    // Si se pasa un ID (string o number), buscar el documento o cargarlo
    if (typeof docOrId === "string" || typeof docOrId === "number") {
      const documentId = docOrId;

      console.log("🔍 Searching for document ID:", documentId);

      // Re-selección del mismo documento por ID: marcar para toggle
      if (selected.value?.document_id === documentId) {
        selected.value = { ...selected.value, _reselected: Date.now() };
        return;
      }

      // Buscar en la lista actual de documentos
      let doc = documents.value.find((d) => d.document_id === documentId);

      // Si no está en la lista, cargar desde el backend
      if (!doc) {
        console.log("📥 Document not in list, loading from backend...");
        doc = await loadDocumentDetail(documentId);
        if (!doc) {
          error.value = "No se pudo cargar el documento";
          return;
        }
      }

      // Seleccionar el documento encontrado/cargado
      console.log("✅ Document found/loaded, selecting:", doc.title);
      selected.value = doc;

      // Si no tiene summary, cargar detalles completos
      if (!doc.summary) {
        await loadDocumentDetail(documentId);
      }

      return;
    }

    // Si se pasa un objeto documento
    const doc = docOrId;

    console.log("📄 Selecting document object:", {
      document_id: doc?.document_id,
      title: doc?.title,
    });

    // Re-selección del mismo documento: marcar para toggle
    if (selected.value?.document_id === doc?.document_id) {
      selected.value = { ...selected.value, _reselected: Date.now() };
      return;
    }

    // Documento diferente: seleccionar y cargar detalles si es necesario
    selected.value = doc;
    if (doc && !doc.summary && doc.document_id) {
      console.log("📥 Loading full details for document...");
      await loadDocumentDetail(doc.document_id);
    }
  }

  // ============================================================================
  // MÉTODOS - OPERACIONES CRUD
  // ============================================================================

  /**
   * Sube un archivo al backend
   * @param {File} file - Archivo a subir
   */
  async function handleFile(file) {
    loading.value = true;
    error.value = null;

    try {
      // Extraer el File real del proxy de Vue
      const actualFile = toRaw(file);
      console.log(
        "📤 Uploading file:",
        actualFile.name,
        actualFile.type,
        actualFile.size
      );

      const formData = new FormData();
      formData.append("file", actualFile);

      // Debug: ver qué contiene el FormData
      console.log("FormData entries:");
      for (let [key, value] of formData.entries()) {
        console.log(
          `  ${key}:`,
          value instanceof File ? `File(${value.name})` : value
        );
      }

      const response = await fetchWithRetry(`${API_BASE}/`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        let errorMessage = "Error al subir el documento";
        let errorData = null;
        try {
          errorData = await response.json();
          console.error("❌ Backend error response:", errorData);
          errorMessage =
            errorData.error || errorData.detail || JSON.stringify(errorData);
        } catch {
          errorMessage = `Error ${response.status}: ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      const newDoc = await response.json();

      // Agregar al inicio y seleccionar
      documents.value.unshift(newDoc);
      selected.value = newDoc;

      return newDoc;
    } catch (e) {
      console.error("❌ Error subiendo archivo:", e);
      error.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  }

  /**
   * Elimina el documento seleccionado
   */
  async function deleteSelected() {
    if (!selected.value) return;

    loading.value = true;
    error.value = null;

    try {
      const response = await fetchWithRetry(
        `${API_BASE}/${selected.value.document_id}/`,
        { method: "DELETE" }
      );

      if (!response.ok) throw new Error("Error al eliminar el documento");

      documents.value = documents.value.filter(
        (d) => d.document_id !== selected.value.document_id
      );
      selected.value = null;
    } catch (e) {
      console.error("Error eliminando documento:", e);
      error.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  }

  // ============================================================================
  // RETORNO
  // ============================================================================

  return {
    // Estado
    documents,
    selected,
    modals,
    globalMessages,
    docMessages,
    loading,
    error,
    pagination,

    // Métodos
    loadDocuments,
    loadDocumentDetail,
    selectDoc,
    handleFile,
    deleteSelected,

    // Métodos de paginación
    nextPage,
    previousPage,
    goToPage,
    changePageSize,
  };
}
