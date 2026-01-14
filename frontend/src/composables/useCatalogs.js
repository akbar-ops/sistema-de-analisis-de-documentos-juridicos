// ============================================================================
// useCatalogs - Composable para catálogos (áreas legales, tipos de docs)
// ============================================================================
import { ref } from "vue";
import axios from "axios";

const API_BASE_URL = "http://localhost:8000/api";

export function useCatalogs() {
  const legalAreas = ref([]);
  const docTypes = ref([]);
  const loading = ref(false);

  async function fetchLegalAreas() {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/documents/legal-areas/`
      );
      legalAreas.value = response.data || [];
    } catch (error) {
      console.error("Error fetching legal areas:", error);
      legalAreas.value = [];
    }
  }

  async function fetchDocTypes() {
    try {
      const response = await axios.get(`${API_BASE_URL}/documents/doc-types/`);
      docTypes.value = response.data || [];
    } catch (error) {
      console.error("Error fetching doc types:", error);
      docTypes.value = [];
    }
  }

  async function fetchAll() {
    loading.value = true;
    try {
      await Promise.all([fetchLegalAreas(), fetchDocTypes()]);
    } finally {
      loading.value = false;
    }
  }

  return {
    legalAreas,
    docTypes,
    loading,
    fetchLegalAreas,
    fetchDocTypes,
    fetchAll,
  };
}
