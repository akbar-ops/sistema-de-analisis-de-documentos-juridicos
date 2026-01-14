// ============================================================================
// useSimilarity - Composable para formateo de datos de similitud
// ============================================================================
import { computed } from "vue";
import { getSimilarityColor } from "./useColors";

/**
 * Formatea un puntaje de similitud
 * @param {number} score - Puntaje entre 0 y 100
 * @returns {string} Puntaje formateado con 1 decimal
 */
export function formatScore(score) {
  return typeof score === "number" ? score.toFixed(1) : "0.0";
}

/**
 * Formatea el boost de metadata
 * @param {number} boost - Valor del boost
 * @returns {string} Boost formateado con signo +
 */
export function formatBoost(boost) {
  return boost > 0 ? `+${boost.toFixed(1)}%` : "";
}

/**
 * Formatea las penalizaciones
 * @param {number} penalty - Valor de la penalización
 * @returns {string} Penalización formateada con signo -
 */
export function formatPenalty(penalty) {
  return penalty > 0 ? `-${penalty.toFixed(1)}%` : "";
}

/**
 * Obtiene las primeras N razones de similitud
 * @param {Array} reasons - Array de razones
 * @param {number} limit - Número máximo de razones
 * @returns {Array} Razones limitadas
 */
export function getLimitedReasons(reasons, limit = 3) {
  if (!Array.isArray(reasons)) return [];
  return reasons.slice(0, limit);
}

/**
 * Composable principal para similitud
 * @param {Object} similarDoc - Documento similar
 */
export function useSimilarity(similarDoc) {
  const score = computed(() => similarDoc.value?.score || 0);

  const color = computed(() => getSimilarityColor(score.value));

  const formattedScore = computed(() => formatScore(score.value));

  const boost = computed(() => similarDoc.value?.metadata_boost || 0);

  const formattedBoost = computed(() => formatBoost(boost.value));

  const penalties = computed(() => similarDoc.value?.penalties || 0);

  const formattedPenalty = computed(() => formatPenalty(penalties.value));

  const reasons = computed(() =>
    getLimitedReasons(similarDoc.value?.similarity_reasons)
  );

  const hasBoost = computed(() => boost.value > 0);

  const hasPenalty = computed(() => penalties.value > 0);

  return {
    score,
    color,
    formattedScore,
    boost,
    formattedBoost,
    penalties,
    formattedPenalty,
    reasons,
    hasBoost,
    hasPenalty,
  };
}
