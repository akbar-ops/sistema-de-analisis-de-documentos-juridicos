// ============================================================================
// useSearch - Composable para búsqueda de documentos
// ============================================================================
import { ref, computed } from "vue";
import axios from "axios";

const API_BASE_URL = "http://localhost:8000/api";

export function useSearch() {
  const searchQuery = ref("");
  const semanticSearch = ref(true);
  const loading = ref(false);
  const searchPerformed = ref(false);
  const results = ref([]);
  const allDocuments = ref([]);

  // Tipo de embedding a usar para búsqueda semántica
  const embeddingField = ref("clean_embedding");

  const pagination = ref({
    currentPage: 1,
    pageSize: 10,
    totalPages: 1,
    totalCount: 0,
    totalItems: 0,
    hasNext: false,
    hasPrevious: false,
  });

  const filters = ref({
    legalArea: null,
    docType: null,
    status: null,
    dateFrom: null,
    dateTo: null,
  });

  // Computed
  const activeFiltersCount = computed(() => {
    return Object.values(filters.value).filter((v) => v !== null && v !== "")
      .length;
  });

  const displayDocuments = computed(() => {
    return searchPerformed.value ? results.value : allDocuments.value;
  });

  const hasDocuments = computed(() => {
    return displayDocuments.value.length > 0;
  });

  // Methods
  async function fetchDocuments(page = 1, pageSize = 10) {
    loading.value = true;
    try {
      const url = `${API_BASE_URL}/documents/?page=${page}&page_size=${pageSize}`;
      const response = await axios.get(url);

      allDocuments.value = response.data.results || [];
      const totalCount = response.data.count || 0;
      const totalPages = Math.ceil(totalCount / pageSize);

      pagination.value = {
        currentPage: page,
        pageSize: pageSize,
        totalPages: totalPages,
        totalCount: totalCount,
        totalItems: totalCount, // Alias para compatibilidad
        hasNext: page < totalPages,
        hasPrevious: page > 1,
      };
    } catch (error) {
      console.error("Error fetching documents:", error);
      throw error;
    } finally {
      loading.value = false;
    }
  }

  async function searchDocuments(searchParams = {}) {
    const query = searchParams.query || searchQuery.value;

    if (!query || !query.trim()) {
      return;
    }

    loading.value = true;
    searchPerformed.value = true;

    try {
      if (semanticSearch.value) {
        // Usar nuevo endpoint de búsqueda semántica
        const response = await axios.post(
          `${API_BASE_URL}/documents/semantic_search/`,
          {
            query: query,
            top_n: 20,
            min_similarity: 0.3,
            embedding_field: embeddingField.value,
            legal_area_id:
              searchParams.legal_area_id || filters.value.legalArea || null,
            doc_type_id:
              searchParams.doc_type_id || filters.value.docType || null,
          }
        );
        results.value = response.data.results || [];
      } else {
        // Búsqueda avanzada con filtros
        const response = await axios.post(
          `${API_BASE_URL}/documents/advanced_search/`,
          {
            query: query,
            semantic_search: false,
            case_number: searchParams.case_number || null,
            resolution_number: searchParams.resolution_number || null,
            legal_area_id:
              searchParams.legal_area_id || filters.value.legalArea || null,
            doc_type_id:
              searchParams.doc_type_id || filters.value.docType || null,
            issue_place: searchParams.issue_place || null,
            date_from: searchParams.date_from || filters.value.dateFrom || null,
            date_to: searchParams.date_to || filters.value.dateTo || null,
          }
        );
        results.value = response.data.results || response.data || [];
      }
    } catch (error) {
      console.error("Error searching documents:", error);
      results.value = [];
      throw error;
    } finally {
      loading.value = false;
    }
  }

  function clearSearch() {
    searchQuery.value = "";
    results.value = [];
    searchPerformed.value = false;
  }

  function clearFilters() {
    filters.value = {
      legalArea: null,
      docType: null,
      status: null,
      dateFrom: null,
      dateTo: null,
    };
  }

  function handlePageChange(page) {
    fetchDocuments(page, pagination.value.pageSize);
  }

  function setEmbeddingField(field) {
    if (field === "clean_embedding" || field === "enhanced_embedding") {
      embeddingField.value = field;
    }
  }

  return {
    // State
    searchQuery,
    semanticSearch,
    loading,
    searchPerformed,
    results,
    allDocuments,
    pagination,
    filters,
    embeddingField,

    // Computed
    activeFiltersCount,
    displayDocuments,
    hasDocuments,

    // Methods
    fetchDocuments,
    searchDocuments,
    clearSearch,
    clearFilters,
    handlePageChange,
    setEmbeddingField,
  };
}
