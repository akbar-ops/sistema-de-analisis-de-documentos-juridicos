// ============================================================================
// useFormatting - Composable para formateo de datos generales
// ============================================================================

/**
 * Formatea una fecha al formato DD/MM/YYYY
 * @param {string} dateString - Fecha en formato ISO
 * @returns {string} Fecha formateada
 */
export function formatDate(dateString) {
  if (!dateString) return "-";

  try {
    const date = new Date(dateString);
    const day = String(date.getDate()).padStart(2, "0");
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const year = date.getFullYear();
    return `${day}/${month}/${year}`;
  } catch (error) {
    return dateString;
  }
}

/**
 * Trunca un texto a un número máximo de caracteres
 * @param {string} text - Texto a truncar
 * @param {number} maxLength - Longitud máxima
 * @returns {string} Texto truncado
 */
export function truncateText(text, maxLength = 100) {
  if (!text) return "";
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + "...";
}

/**
 * Capitaliza la primera letra de un string
 * @param {string} text - Texto a capitalizar
 * @returns {string} Texto capitalizado
 */
export function capitalize(text) {
  if (!text) return "";
  return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase();
}

/**
 * Formatea el tipo de documento para display
 * @param {string} type - Tipo de documento
 * @returns {string} Tipo formateado
 */
export function formatDocumentType(type) {
  if (!type) return "Sin tipo";

  const typeMap = {
    sentencia: "Sentencia",
    resolucion: "Resolución",
    auto: "Auto",
    decreto: "Decreto",
  };

  return typeMap[type.toLowerCase()] || capitalize(type);
}

/**
 * Formatea el área legal
 * @param {string} area - Área legal
 * @returns {string} Área formateada
 */
export function formatLegalArea(area) {
  if (!area) return "Sin área";

  const areaMap = {
    civil: "Civil",
    penal: "Penal",
    laboral: "Laboral",
    constitucional: "Constitucional",
    administrativo: "Administrativo",
  };

  return areaMap[area.toLowerCase()] || capitalize(area);
}

/**
 * Composable principal
 */
export function useFormatting() {
  return {
    formatDate,
    truncateText,
    capitalize,
    formatDocumentType,
    formatLegalArea,
  };
}
