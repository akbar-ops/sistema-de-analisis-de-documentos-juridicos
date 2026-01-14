// ============================================================================
// Performance Utilities - Optimización de rendimiento
// ============================================================================

/**
 * Debounce function - Retrasa la ejecución hasta que pasen X ms sin llamadas
 * @param {Function} func - Función a debounce
 * @param {number} wait - Milisegundos de espera
 * @returns {Function} Función debounced
 */
export function debounce(func, wait = 300) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Throttle function - Limita ejecución a una vez cada X ms
 * @param {Function} func - Función a throttle
 * @param {number} limit - Milisegundos mínimos entre ejecuciones
 * @returns {Function} Función throttled
 */
export function throttle(func, limit = 300) {
  let inThrottle;
  return function executedFunction(...args) {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

/**
 * Memoize function - Cachea resultados de funciones puras
 * @param {Function} func - Función a memoize
 * @returns {Function} Función memoized
 */
export function memoize(func) {
  const cache = new Map();

  return function memoized(...args) {
    const key = JSON.stringify(args);

    if (cache.has(key)) {
      return cache.get(key);
    }

    const result = func(...args);
    cache.set(key, result);
    return result;
  };
}

/**
 * Lazy load de imágenes
 * @param {HTMLImageElement} img - Elemento imagen
 * @param {string} src - Source de la imagen
 */
export function lazyLoadImage(img, src) {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        img.src = src;
        observer.unobserve(img);
      }
    });
  });

  observer.observe(img);
}

/**
 * Batch updates - Agrupa múltiples actualizaciones
 * @param {Function} callback - Función a ejecutar
 */
export function batchUpdate(callback) {
  requestAnimationFrame(() => {
    callback();
  });
}
