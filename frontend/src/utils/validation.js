// ============================================================================
// Validation Utilities - Utilidades de validación
// ============================================================================

/**
 * Valida si un string es email válido
 * @param {string} email - Email a validar
 * @returns {boolean}
 */
export function isValidEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Valida si un string no está vacío
 * @param {string} value - Valor a validar
 * @returns {boolean}
 */
export function isNotEmpty(value) {
  return value !== null && value !== undefined && value.trim().length > 0;
}

/**
 * Valida si un número está en un rango
 * @param {number} num - Número a validar
 * @param {number} min - Mínimo
 * @param {number} max - Máximo
 * @returns {boolean}
 */
export function isInRange(num, min, max) {
  return num >= min && num <= max;
}

/**
 * Valida fecha
 * @param {string} dateString - Fecha en string
 * @returns {boolean}
 */
export function isValidDate(dateString) {
  const date = new Date(dateString);
  return date instanceof Date && !isNaN(date);
}

/**
 * Sanitiza HTML para prevenir XSS
 * @param {string} html - HTML a sanitizar
 * @returns {string}
 */
export function sanitizeHTML(html) {
  const temp = document.createElement("div");
  temp.textContent = html;
  return temp.innerHTML;
}
