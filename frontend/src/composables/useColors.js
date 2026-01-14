// ============================================================================
// useColors - Composable para gestión de colores del Poder Judicial
// ============================================================================

/**
 * Colores oficiales del Poder Judicial del Perú
 */
const PJ_COLORS = {
  brownGrey: "#736D5D",
  redPrimary: "#8C0D0D",
  redDark: "#731414",
  redLight: "#D9A3A3",
  greyLight: "#F2F2F2",
};

/**
 * Colores por Área Legal (actualizados según el sistema actual)
 * Colores vibrantes y distinguibles para visualización
 */
const LEGAL_AREA_COLORS = {
  // Áreas principales
  Penal: "#D32F2F", // Rojo fuerte
  Laboral: "#1976D2", // Azul
  Civil: "#388E3C", // Verde
  Constitucional: "#7B1FA2", // Púrpura
  "Contencioso Administrativo": "#F57C00", // Naranja
  Comercial: "#0097A7", // Cyan

  // Áreas de familia
  "Familia Civil": "#E91E63", // Rosa fuerte/Magenta
  "Familia Tutelar": "#F06292", // Rosa claro
  "Familia Penal": "#AD1457", // Rosa oscuro

  // Áreas especializadas
  "Extension de Dominio": "#5E35B1", // Violeta profundo
  Tributario: "#558B2F", // Verde oliva
  Ambiental: "#00796B", // Verde azulado
  Electoral: "#5D4037", // Marrón
  Internacional: "#00838F", // Azul petróleo

  // Default
  Otros: "#757575",
  "Sin área": "#9E9E9E",
};

/**
 * Obtiene el color según el puntaje de similitud
 * @param {number} score - Puntaje entre 0 y 100
 * @returns {string} Color hexadecimal
 */
export function getSimilarityColor(score) {
  if (score >= 80) return PJ_COLORS.redPrimary;
  if (score >= 60) return PJ_COLORS.redDark;
  if (score >= 40) return PJ_COLORS.redLight;
  return PJ_COLORS.brownGrey;
}

/**
 * Obtiene el color según el tipo de chip/badge
 * @param {string} type - 'type' | 'area' | 'date'
 * @returns {string} Color hexadecimal
 */
export function getChipColor(type) {
  const colors = {
    type: PJ_COLORS.brownGrey,
    area: PJ_COLORS.redPrimary,
    date: PJ_COLORS.brownGrey,
  };
  return colors[type] || PJ_COLORS.brownGrey;
}

/**
 * Obtiene el color para un área legal específica
 * @param {string} legalArea - Nombre del área legal
 * @returns {string} Color hexadecimal
 */
export function getLegalAreaColor(legalArea) {
  if (!legalArea) return LEGAL_AREA_COLORS["Sin área"];

  // Buscar coincidencia exacta
  if (LEGAL_AREA_COLORS[legalArea]) {
    return LEGAL_AREA_COLORS[legalArea];
  }

  // Buscar coincidencia parcial
  const match = Object.keys(LEGAL_AREA_COLORS).find((key) =>
    legalArea.toLowerCase().includes(key.toLowerCase())
  );

  return match ? LEGAL_AREA_COLORS[match] : LEGAL_AREA_COLORS["Otros"];
}

/**
 * Obtiene color para clusters (paleta de colores diferenciables)
 * @param {number} clusterId - ID del cluster
 * @returns {string} Color hexadecimal
 */
export function getClusterColor(clusterId) {
  const clusterPalette = [
    "#1976D2", // Azul
    "#388E3C", // Verde
    "#D32F2F", // Rojo
    "#7B1FA2", // Púrpura
    "#F57C00", // Naranja
    "#0097A7", // Cyan
    "#E91E63", // Rosa
    "#5E35B1", // Violeta
    "#00796B", // Verde azulado
    "#5D4037", // Marrón
  ];

  // Para cluster -1 (ruido), usar gris
  if (clusterId === -1) return "#757575";

  return clusterPalette[Math.abs(clusterId) % clusterPalette.length];
}

/**
 * Composable principal
 */
export function useColors() {
  return {
    colors: PJ_COLORS,
    legalAreaColors: LEGAL_AREA_COLORS,
    getSimilarityColor,
    getChipColor,
    getLegalAreaColor,
    getClusterColor,
  };
}
