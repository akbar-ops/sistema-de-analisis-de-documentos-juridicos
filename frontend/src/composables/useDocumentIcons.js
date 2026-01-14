/**
 * Composable para obtener iconos y colores de tipos de documentos legales
 * Usa Material Design Icons (MDI) para consistencia con Vuetify
 */

export function useDocumentIcons() {
  /**
   * Mapeo de tipos de documentos a iconos MDI
   * Iconos profesionales que representan cada tipo de documento legal
   */
  const documentTypeIcons = {
    // Sentencias
    Sentencias: "mdi-gavel",
    Sentencia: "mdi-gavel",
    "Sentencia de Vista": "mdi-gavel",
    "Sentencia de Casación": "mdi-scale-balance",

    // Autos
    Autos: "mdi-file-document-check",
    Auto: "mdi-file-document-check",
    "Auto de Vista": "mdi-file-document-check-outline",
    "Auto Directoral": "mdi-file-certificate",

    // Decretos
    Decretos: "mdi-file-sign",
    Decreto: "mdi-file-sign",
    "Decreto Judicial": "mdi-file-sign",

    // Resoluciones
    Resoluciones: "mdi-file-document-edit",
    Resolución: "mdi-file-document-edit",
    "Resolución Administrativa": "mdi-briefcase-check",
    "Resolución Directoral": "mdi-briefcase-edit",
    "Resolución Jefatural": "mdi-briefcase-account",

    // Dictámenes
    Dictámenes: "mdi-file-chart",
    Dictamen: "mdi-file-chart",
    "Dictamen Fiscal": "mdi-account-tie",

    // Otros documentos
    Actas: "mdi-file-document-multiple",
    Acta: "mdi-file-document-multiple",
    Oficios: "mdi-email-seal",
    Oficio: "mdi-email-seal",
    Providencias: "mdi-file-clock",
    Providencia: "mdi-file-clock",
    Demandas: "mdi-file-send",
    Demanda: "mdi-file-send",
    Recursos: "mdi-file-restore",
    Recurso: "mdi-file-restore",
    Apelación: "mdi-file-restore",
    Casación: "mdi-scale-balance",
    Queja: "mdi-alert-circle",

    // Contratos y acuerdos
    Contratos: "mdi-handshake",
    Contrato: "mdi-handshake",
    Convenios: "mdi-file-sign",
    Convenio: "mdi-file-sign",

    // Informes y pericias
    Informes: "mdi-file-chart-outline",
    Informe: "mdi-file-chart-outline",
    Pericias: "mdi-microscope",
    Pericia: "mdi-microscope",

    // Default
    Otros: "mdi-file-document-outline",
    Otro: "mdi-file-document-outline",
  };

  /**
   * Mapeo de áreas legales a colores
   * Colores vibrantes y profesionales que se distinguen fácilmente
   */
  const legalAreaColors = {
    // Áreas principales - colores vibrantes
    Penal: "#D32F2F", // Rojo fuerte
    Laboral: "#1976D2", // Azul
    Civil: "#388E3C", // Verde
    Constitucional: "#7B1FA2", // Púrpura
    "Contencioso Administrativo": "#F57C00", // Naranja
    Comercial: "#0097A7", // Cyan

    // Áreas de familia - tonos rosados/magentas
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
    Otros: "#757575", // Gris
    "Sin área": "#9E9E9E", // Gris claro
  };

  /**
   * Mapeo de áreas legales a iconos
   */
  const legalAreaIcons = {
    Penal: "mdi-shield-alert",
    Laboral: "mdi-account-hard-hat",
    Civil: "mdi-scale-balance",
    Constitucional: "mdi-book-open-variant",
    "Contencioso Administrativo": "mdi-office-building",
    Comercial: "mdi-cart",
    "Familia Civil": "mdi-account-multiple",
    "Familia Tutelar": "mdi-account-child",
    "Familia Penal": "mdi-home-alert",
    "Extension de Dominio": "mdi-map-marker-radius",
    Tributario: "mdi-calculator",
    Ambiental: "mdi-tree",
    Electoral: "mdi-vote",
    Internacional: "mdi-earth",
    Otros: "mdi-folder",
    "Sin área": "mdi-help-circle",
  };

  /**
   * Colores por tipo de documento (secundarios, para leyendas)
   */
  const documentTypeColors = {
    Sentencias: "#1565C0",
    Autos: "#2E7D32",
    Decretos: "#F57C00",
    Resoluciones: "#5E35B1",
    Dictámenes: "#00838F",
    Otros: "#616161",
  };

  /**
   * Obtiene el icono para un tipo de documento
   * @param {string} docType - Tipo de documento
   * @returns {string} - Nombre del icono MDI
   */
  const getDocumentIcon = (docType) => {
    if (!docType) return documentTypeIcons["Otros"];

    // Buscar coincidencia exacta
    if (documentTypeIcons[docType]) {
      return documentTypeIcons[docType];
    }

    // Buscar coincidencia parcial (case-insensitive)
    const lowerType = docType.toLowerCase();
    const match = Object.keys(documentTypeIcons).find((key) =>
      lowerType.includes(key.toLowerCase())
    );

    return match ? documentTypeIcons[match] : documentTypeIcons["Otros"];
  };

  /**
   * Obtiene el color para un área legal
   * @param {string} legalArea - Área legal
   * @returns {string} - Color hexadecimal
   */
  const getLegalAreaColor = (legalArea) => {
    if (!legalArea) return legalAreaColors["Sin área"];

    // Buscar coincidencia exacta
    if (legalAreaColors[legalArea]) {
      return legalAreaColors[legalArea];
    }

    // Buscar coincidencia parcial
    const match = Object.keys(legalAreaColors).find((key) =>
      legalArea.toLowerCase().includes(key.toLowerCase())
    );

    return match ? legalAreaColors[match] : legalAreaColors["Otros"];
  };

  /**
   * Obtiene el icono para un área legal
   * @param {string} legalArea - Área legal
   * @returns {string} - Nombre del icono MDI
   */
  const getLegalAreaIcon = (legalArea) => {
    if (!legalArea) return legalAreaIcons["Sin área"];

    if (legalAreaIcons[legalArea]) {
      return legalAreaIcons[legalArea];
    }

    const match = Object.keys(legalAreaIcons).find((key) =>
      legalArea.toLowerCase().includes(key.toLowerCase())
    );

    return match ? legalAreaIcons[match] : legalAreaIcons["Otros"];
  };

  /**
   * Obtiene el color para un tipo de documento
   * @param {string} docType - Tipo de documento
   * @returns {string} - Color hexadecimal
   */
  const getDocumentTypeColor = (docType) => {
    if (!docType) return documentTypeColors["Otros"];

    const match = Object.keys(documentTypeColors).find((key) =>
      docType.toLowerCase().includes(key.toLowerCase())
    );

    return match ? documentTypeColors[match] : documentTypeColors["Otros"];
  };

  /**
   * Obtiene forma/símbolo para un tipo de documento (para grafos)
   * @param {string} docType - Tipo de documento
   * @returns {string} - Tipo de forma: 'circle', 'rect', 'triangle', 'diamond'
   */
  const getDocumentShape = (docType) => {
    if (!docType) return "circle";

    const lowerType = docType.toLowerCase();

    if (lowerType.includes("sentencia")) return "circle";
    if (lowerType.includes("auto")) return "triangle";
    if (lowerType.includes("decreto")) return "diamond";
    if (lowerType.includes("resolución")) return "rect";

    return "circle";
  };

  /**
   * Obtiene todas las áreas legales con sus colores e iconos
   * @returns {Array} - Array de objetos con área, color e icono
   */
  const getAllLegalAreas = () => {
    return Object.keys(legalAreaColors)
      .filter((area) => area !== "Otros" && area !== "Sin área")
      .map((area) => ({
        name: area,
        color: legalAreaColors[area],
        icon: legalAreaIcons[area],
      }));
  };

  /**
   * Obtiene todos los tipos de documentos con sus iconos
   * @returns {Array} - Array de objetos con tipo e icono
   */
  const getAllDocumentTypes = () => {
    const mainTypes = [
      "Sentencias",
      "Autos",
      "Decretos",
      "Resoluciones",
      "Dictámenes",
    ];
    return mainTypes.map((type) => ({
      name: type,
      icon: documentTypeIcons[type],
      color: documentTypeColors[type] || documentTypeColors["Otros"],
    }));
  };

  return {
    // Getters individuales
    getDocumentIcon,
    getLegalAreaColor,
    getLegalAreaIcon,
    getDocumentTypeColor,
    getDocumentShape,

    // Getters de listas
    getAllLegalAreas,
    getAllDocumentTypes,

    // Mapeos completos (para uso directo si se necesita)
    documentTypeIcons,
    legalAreaColors,
    legalAreaIcons,
    documentTypeColors,
  };
}
