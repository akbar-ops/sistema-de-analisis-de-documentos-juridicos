"""
Constantes compartidas para los servicios de procesamiento de documentos legales.
Contiene catálogos de tipos de documentos, áreas legales y patrones de extracción.
"""

# ============== TIPOS DE DOCUMENTOS LEGALES ==============
# Decretos: Resoluciones de mero trámite, sin contenido decisorio
# Autos: Resoluciones con contenido decisorio sobre puntos del proceso
# Sentencias: Resoluciones que resuelven el fondo del asunto litigioso

DOCUMENT_TYPES = [
    'Sentencias',
    'Autos',
    'Decretos',
    'Otros'
]

# ============== ÁREAS LEGALES / ESPECIALIDADES ==============

LEGAL_AREAS = [
    'Penal',
    'Laboral',
    'Familia Civil',
    'Civil',
    'Familia Tutelar',
    'Comercial',
    'Derecho Constitucional',
    'Contencioso Administrativo',
    'Familia Penal',
    'Extension de Dominio',
    'Otros'
]

# ============== PALABRAS CLAVE POR TIPO DE DOCUMENTO ==============
# Cada tipo de documento tiene palabras clave asociadas para identificación automática

DOCUMENT_TYPE_KEYWORDS = {
    'Sentencias': [
        'sentencia', 'fallo', 'condena', 'absuelve', 'declara fundada',
        'declara infundada', 'sentencia de vista', 'sentencia de segundo grado',
        'resuelve el fondo', 'pone fin al proceso', 'decisión final',
        'resuelve la controversia', 'dispone'
    ],
    'Autos': [
        'auto', 'auto de saneamiento', 'auto de admisión',
        'auto de calificación', 'auto de vista', 'pronuncia sobre',
        'resuelve el pedido', 'decide sobre', 'admite', 'inadmite',
        'contenido decisorio', 'incidente'
    ],
    'Decretos': [
        'decreto', 'mero trámite', 'téngase presente', 'avóquese',
        'remítase', 'notifíquese', 'cúmplase', 'archívese',
        'devuélvase', 'impúlsese', 'trámite', 'sin contenido decisorio'
    ],
}

# ============== PALABRAS CLAVE POR ÁREA LEGAL ==============
# Cada área legal tiene palabras clave asociadas para clasificación automática

LEGAL_AREA_KEYWORDS = {
    'Penal': [
        'penal', 'delito', 'imputado', 'fiscal', 'código penal',
        'pena privativa', 'ministerio público', 'denuncia penal',
        'proceso penal', 'acusado', 'agraviado', 'sentencia condenatoria',
        'sentencia absolutoria', 'prisión preventiva', 'comparecencia'
    ],
    'Laboral': [
        'laboral', 'trabajador', 'empleador', 'despido', 'remuneración',
        'beneficios sociales', 'cts', 'gratificación', 'juzgado de trabajo',
        'relación laboral', 'contrato de trabajo', 'indemnización laboral',
        'vacaciones', 'horas extras', 'sunafil'
    ],
    'Familia Civil': [
        'familia civil', 'divorcio', 'separación de cuerpos', 'régimen patrimonial',
        'divorcio ulterior', 'sociedad de gananciales', 'separación de patrimonios',
        'invalidez del matrimonio', 'divorcio por mutuo acuerdo'
    ],
    'Civil': [
        'civil', 'obligación', 'contrato', 'código civil', 'acreedor',
        'deudor', 'indemnización', 'daños y perjuicios', 'responsabilidad civil',
        'nulidad de acto jurídico', 'resolución de contrato', 'rescisión',
        'mejor derecho de propiedad', 'reivindicación', 'prescripción adquisitiva'
    ],
    'Familia Tutelar': [
        'familia tutelar', 'alimentos', 'tenencia', 'régimen de visitas',
        'patria potestad', 'filiación', 'reconocimiento de paternidad',
        'suspensión de patria potestad', 'aumento de alimentos', 'reducción de alimentos',
        'exoneración de alimentos', 'tutela', 'curatela', 'adopción'
    ],
    'Comercial': [
        'comercial', 'mercantil', 'sociedad', 'empresa', 'quiebra',
        'código de comercio', 'letra de cambio', 'pagaré', 'sociedad anónima',
        'junta general de accionistas', 'directorio', 'gerencia',
        'obligaciones mercantiles', 'título valor', 'protesto'
    ],
    'Derecho Constitucional': [
        'constitucional', 'amparo', 'hábeas corpus', 'hábeas data',
        'tribunal constitucional', 'derechos fundamentales', 'acción de amparo',
        'acción de inconstitucionalidad', 'acción popular', 'acción de cumplimiento',
        'debido proceso', 'tutela procesal efectiva', 'garantías constitucionales'
    ],
    'Contencioso Administrativo': [
        'contencioso administrativo', 'acto administrativo', 'resolución administrativa',
        'proceso contencioso', 'nulidad de acto administrativo', 'silencio administrativo',
        'procedimiento administrativo', 'derecho administrativo'
    ],
    'Familia Penal': [
        'familia penal', 'violencia familiar', 'violencia contra la mujer',
        'medidas de protección', 'maltrato familiar', 'agresiones',
        'violencia física', 'violencia psicológica', 'violencia sexual',
        'incumplimiento de asistencia familiar', 'omisión a la asistencia familiar',
        'ley 30364'
    ],
    'Extension de Dominio': [
        'extensión de dominio', 'ampliación de demanda', 'acumulación',
        'extensión de competencia', 'continencia de la causa',
        'extensión de efectos', 'conexidad'
    ],
}

# ============== PATRONES DE EXTRACCIÓN ==============

# Patrón para número de expediente
CASE_NUMBER_PATTERN = r'\b\d{5}-\d{4}-\d{1,2}-\d{4}-[A-Z]{2,4}-[A-Z]{2,4}-\d{2}\b'

# Patrones para órgano jurisdiccional
JURISDICTIONAL_BODY_PATTERNS = [
    r'(?:CORTE\s+SUPERIOR[^\.]{0,100})',
    r'(?:SALA\s+(?:CIVIL|PENAL|LABORAL|CONSTITUCIONAL)[^\.]{0,100})',
    r'(?:JUZGADO\s+(?:CIVIL|PENAL|LABORAL|DE FAMILIA)[^\.]{0,100})',
    r'(?:TRIBUNAL\s+CONSTITUCIONAL)',
]

# Patrones para materia legal
LEGAL_SUBJECT_PATTERNS = [
    r'MATERIA\s*:\s*([^\n]{10,200})',
    r'ASUNTO\s*:\s*([^\n]{10,200})',
    r'(?:sobre|Sobre)\s+([^\n]{10,150})',
]

# ============== CONFIGURACIÓN DE PROMPTS ==============

# Longitud máxima de texto a enviar al LLM
MAX_TEXT_SAMPLE_LENGTH = 5000

# Rango de palabras para el título
TITLE_MIN_WORDS = 5
TITLE_MAX_WORDS = 70

# Timeout para llamadas al LLM (en segundos)
LLM_TIMEOUT_METADATA = 1800
LLM_TIMEOUT_SUMMARY = 1800
LLM_TIMEOUT_PERSONS = 1800
