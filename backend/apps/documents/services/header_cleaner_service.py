# apps/documents/services/header_cleaner_service.py
"""
Servicio para limpiar encabezados y pies de página repetitivos en documentos judiciales.

Los documentos judiciales del Poder Judicial del Perú típicamente contienen:
- Encabezados con logo y nombre de la institución
- Número de expediente repetido en cada página
- Números de página ("Página X de Y")
- Encabezados de sala/juzgado
- Información de procedencia

Este servicio detecta y elimina estos patrones repetitivos para mejorar:
1. La calidad del chunking
2. La precisión de los embeddings
3. La efectividad de la búsqueda semántica
"""

import re
import logging
from typing import List, Tuple, Set, Dict, Optional
from collections import Counter
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class HeaderCleanerService:
    """
    Servicio inteligente para limpiar encabezados/pies de página repetitivos.
    
    Estrategias:
    1. Detección de patrones conocidos (regex)
    2. Detección de líneas repetidas entre páginas
    3. Limpieza de artefactos de OCR/extracción
    4. Normalización de espacios y formato
    """
    
    # ============================================================
    # PATRONES REGEX PARA ENCABEZADOS CONOCIDOS
    # ============================================================
    
    # Patrones de encabezados de institución
    INSTITUTION_PATTERNS = [
        # Corte Superior de Justicia
        r'(?i)CORTE\s+SUPERIOR\s+(DE\s+)?JUSTICIA\s+(DE\s+)?\w+',
        r'(?i)C\s*O\s*R\s*T\s*E\s+S\s*U\s*P\s*E\s*R\s*I\s*O\s*R',  # Espaciado
        
        # Poder Judicial
        r'(?i)PODER\s+JUDICIAL\s+(DEL\s+)?PER[UÚ]',
        r'(?i)P\s*O\s*D\s*E\s*R\s+J\s*U\s*D\s*I\s*C\s*I\s*A\s*L',  # Espaciado
        
        # Salas específicas
        r'(?i)SALA\s+(LABORAL|PENAL|CIVIL|CONSTITUCIONAL)\s*(DE\s+)?(PUNO|APELACIONES)?',
        r'(?i)SALA\s+PENAL\s+DE\s+APELACIONES\s+EN\s+ADICI[OÓ]N.*',
        r'(?i)SALA\s+PENAL\s+LIQUIDADORA.*',
        r'(?i)SALA\s+ESPECIALIZADA.*',
        
        # Juzgados
        r'(?i)(PRIMER|SEGUNDO|TERCER|CUARTO|QUINTO|SEXTO)\s+JUZGADO\s+\w+',
        r'(?i)JUZGADO\s+(MIXTO|PENAL|CIVIL|LABORAL|ESPECIALIZADO).*',
        r'(?i)JUZGADO\s+PENAL\s+(UNIPERSONAL|COLEGIADO).*',
    ]
    
    # Patrones de metadatos repetitivos
    METADATA_PATTERNS = [
        # Número de expediente (múltiples formatos)
        # r'(?i)EXP\.?\s*N[°º.]?\s*:?\s*\d{4,5}-\d{4}-\d+-\d{4}-\w{2,3}-\w{2,3}-\d{2}',
        # r'(?i)EXPEDIENTE\s*(N[°º.]?)?\s*:?\s*\d{4,5}-\d{4}-\d+-\d{4}-\w+-\w+-\d+',
        # r'(?i)Expediente\s*N[°º]?\s*:?\s*\d{4,5}-\d{4}.*',
        
        # Número de página
        r'(?i)P[aá]gina\s+\d+\s+de\s+\d+',
        r'(?i)P[aá]g\.?\s*\d+\s*/\s*\d+',
        r'^\s*\d+\s*$',  # Solo número (pie de página)
        r'^\s*-\s*\d+\s*-\s*$',  # -1-
        
        # Procedencia
        r'(?i)PROCEDE\s*:\s*\w+(\s+\w+)?',
        r'(?i)PROCEDENCIA\s*:\s*.*',
        
        # Ponente repetido
        r'(?i)PONENTE\s*:\s*(J\.?S\.?|JUEZ)\s+\w+.*',
        r'(?i)J\.?S\.?\s+PONENTE\s*:\s*\w+.*',
    ]
    
    # Patrones de caracteres corruptos/OCR malo
    OCR_NOISE_PATTERNS = [
        r'/g\d+',  # Caracteres como /g3, /g19, etc.
        r'[\x00-\x08\x0b\x0c\x0e-\x1f]',  # Caracteres de control
        r'[^\x00-\x7F\xA0-\xFF\u0080-\u024F\u1E00-\u1EFF]+',  # Caracteres no latinos raros (con cuidado)
    ]
    
    # Líneas a eliminar completamente
    REMOVE_LINES_PATTERNS = [
        r'^\s*$',  # Líneas vacías
        r'^\s*[\-_=]{3,}\s*$',  # Separadores (---, ___, ===)
        r'^\s*[•●○◦▪▫]\s*$',  # Solo bullets
        r'^\s*\.\s*$',  # Solo punto
        r'^\s*,\s*$',  # Solo coma
    ]
    
    # ============================================================
    # CONFIGURACIÓN
    # ============================================================
    
    # Umbral de similitud para considerar líneas como "repetidas"
    SIMILARITY_THRESHOLD = 0.85
    
    # Mínimo de páginas donde debe aparecer para ser "encabezado"
    MIN_PAGES_FOR_HEADER = 2
    
    # Máximas líneas a considerar como encabezado (desde el inicio de página)
    MAX_HEADER_LINES = 10
    
    # Máximas líneas a considerar como pie de página (desde el final)
    MAX_FOOTER_LINES = 5
    
    # Longitud mínima de línea para ser contenido válido
    MIN_LINE_LENGTH = 10
    
    def __init__(self):    
        """Inicializa el servicio."""
        # Compilar patrones para eficiencia
        self._compiled_institution = [re.compile(p) for p in self.INSTITUTION_PATTERNS]
        self._compiled_metadata = [re.compile(p) for p in self.METADATA_PATTERNS]
        self._compiled_ocr_noise = [re.compile(p) for p in self.OCR_NOISE_PATTERNS]
        self._compiled_remove_lines = [re.compile(p) for p in self.REMOVE_LINES_PATTERNS]
        
        logger.info("HeaderCleanerService inicializado")
    
    def clean_document_text(self, text: str) -> str:
        """
        Limpia el texto completo de un documento.
        
        Este es el método principal. Aplica todas las limpiezas en orden:
        1. Limpieza de patrones conocidos
        2. Normalización de espacios
        3. Limpieza de artefactos OCR
        
        Args:
            text: Texto completo del documento
            
        Returns:
            Texto limpio
        """
        if not text or not text.strip():
            return ""
        
        # Paso 1: Limpiar artefactos OCR primero
        text = self._clean_ocr_artifacts(text)
        
        # Paso 2: Limpiar patrones de institución/encabezados
        text = self._clean_institution_headers(text)
        
        # Paso 3: Limpiar metadatos repetitivos
        text = self._clean_metadata_patterns(text)
        
        # Paso 4: Limpiar líneas vacías/separadores
        text = self._clean_empty_lines(text)
        
        # Paso 5: Normalizar espacios
        text = self._normalize_whitespace(text)
        
        return text.strip()
    
    def clean_pages_text(self, pages_text: List[Tuple[int, str]]) -> List[Tuple[int, str]]:
        """
        Limpia texto de múltiples páginas, detectando encabezados repetidos.
        
        Este método es más inteligente que clean_document_text porque:
        - Detecta qué líneas se repiten entre páginas
        - Elimina solo las líneas que aparecen en múltiples páginas
        
        Args:
            pages_text: Lista de tuplas (page_number, text)
            
        Returns:
            Lista de tuplas con texto limpio
        """
        if not pages_text:
            return []
        
        if len(pages_text) == 1:
            # Solo una página, aplicar limpieza simple
            page_num, text = pages_text[0]
            return [(page_num, self.clean_document_text(text))]
        
        # Paso 1: Detectar líneas que se repiten entre páginas
        repeated_headers, repeated_footers = self._detect_repeated_lines(pages_text)
        
        logger.info(f"Detectados {len(repeated_headers)} encabezados repetidos y {len(repeated_footers)} pies repetidos")
        
        # Paso 2: Limpiar cada página
        cleaned_pages = []
        for page_num, text in pages_text:
            cleaned_text = self._clean_page(
                text, 
                repeated_headers, 
                repeated_footers
            )
            cleaned_pages.append((page_num, cleaned_text))
        
        return cleaned_pages
    
    def _detect_repeated_lines(
        self, 
        pages_text: List[Tuple[int, str]]
    ) -> Tuple[Set[str], Set[str]]:
        """
        Detecta líneas que se repiten en múltiples páginas.
        
        Args:
            pages_text: Lista de (page_num, text)
            
        Returns:
            Tuple de (encabezados_repetidos, pies_repetidos)
        """
        header_candidates = Counter()
        footer_candidates = Counter()
        
        for page_num, text in pages_text:
            lines = text.split('\n')
            
            # Analizar encabezados (primeras líneas)
            header_lines = lines[:self.MAX_HEADER_LINES]
            for line in header_lines:
                normalized = self._normalize_line_for_comparison(line)
                if len(normalized) > 5:  # Ignorar líneas muy cortas
                    header_candidates[normalized] += 1
            
            # Analizar pies de página (últimas líneas)
            footer_lines = lines[-self.MAX_FOOTER_LINES:] if len(lines) > self.MAX_FOOTER_LINES else []
            for line in footer_lines:
                normalized = self._normalize_line_for_comparison(line)
                if len(normalized) > 5:
                    footer_candidates[normalized] += 1
        
        total_pages = len(pages_text)
        min_occurrences = min(self.MIN_PAGES_FOR_HEADER, total_pages - 1)
        min_occurrences = max(2, min_occurrences)  # Al menos 2
        
        # Líneas que aparecen en suficientes páginas son encabezados/pies
        repeated_headers = {
            line for line, count in header_candidates.items() 
            if count >= min_occurrences
        }
        
        repeated_footers = {
            line for line, count in footer_candidates.items() 
            if count >= min_occurrences
        }
        
        return repeated_headers, repeated_footers
    
    def _normalize_line_for_comparison(self, line: str) -> str:
        """
        Normaliza una línea para comparación.
        Elimina espacios extra, números de página, etc.
        """
        # Minúsculas
        normalized = line.lower().strip()
        
        # Eliminar números de página y expediente (varían por página)
        normalized = re.sub(r'\d+', '#', normalized)
        
        # Normalizar espacios
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized
    
    def _clean_page(
        self, 
        text: str, 
        repeated_headers: Set[str], 
        repeated_footers: Set[str]
    ) -> str:
        """
        Limpia una página individual eliminando encabezados/pies repetidos.
        """
        if not text:
            return ""
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for i, line in enumerate(lines):
            normalized = self._normalize_line_for_comparison(line)
            
            # Determinar si es encabezado (primeras líneas)
            is_header_position = i < self.MAX_HEADER_LINES
            # Determinar si es pie (últimas líneas)
            is_footer_position = i >= len(lines) - self.MAX_FOOTER_LINES
            
            # Verificar si coincide con encabezados/pies repetidos
            is_repeated_header = is_header_position and self._is_similar_to_any(normalized, repeated_headers)
            is_repeated_footer = is_footer_position and self._is_similar_to_any(normalized, repeated_footers)
            
            # Verificar patrones conocidos
            is_known_pattern = self._matches_known_pattern(line)
            
            # Mantener línea si no es repetida ni patrón conocido
            if not is_repeated_header and not is_repeated_footer and not is_known_pattern:
                cleaned_lines.append(line)
        
        # Aplicar limpieza adicional al resultado
        result = '\n'.join(cleaned_lines)
        result = self._clean_ocr_artifacts(result)
        result = self._normalize_whitespace(result)
        
        return result
    
    def _is_similar_to_any(self, line: str, candidates: Set[str]) -> bool:
        """Verifica si una línea es similar a alguna de las candidatas."""
        for candidate in candidates:
            ratio = SequenceMatcher(None, line, candidate).ratio()
            if ratio >= self.SIMILARITY_THRESHOLD:
                return True
        return False
    
    def _matches_known_pattern(self, line: str) -> bool:
        """Verifica si la línea coincide con patrones conocidos de encabezado."""
        # Verificar patrones de institución
        for pattern in self._compiled_institution:
            if pattern.search(line):
                return True
        
        # Verificar patrones de metadatos
        for pattern in self._compiled_metadata:
            if pattern.search(line):
                return True
        
        # Verificar si es línea a eliminar
        for pattern in self._compiled_remove_lines:
            if pattern.match(line):
                return True
        
        return False
    
    def _clean_institution_headers(self, text: str) -> str:
        """Elimina encabezados de institución."""
        for pattern in self._compiled_institution:
            text = pattern.sub('', text)
        return text
    
    def _clean_metadata_patterns(self, text: str) -> str:
        """Elimina patrones de metadatos repetitivos."""
        for pattern in self._compiled_metadata:
            text = pattern.sub('', text)
        return text
    
    def _clean_ocr_artifacts(self, text: str) -> str:
        """Limpia artefactos de OCR."""
        for pattern in self._compiled_ocr_noise:
            text = pattern.sub('', text)
        return text
    
    def _clean_empty_lines(self, text: str) -> str:
        """Elimina líneas vacías y separadores."""
        lines = text.split('\n')
        cleaned = []
        
        for line in lines:
            should_remove = False
            for pattern in self._compiled_remove_lines:
                if pattern.match(line):
                    should_remove = True
                    break
            
            if not should_remove:
                cleaned.append(line)
        
        return '\n'.join(cleaned)
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normaliza espacios en blanco."""
        # Reemplazar múltiples espacios por uno
        text = re.sub(r' +', ' ', text)
        
        # Reemplazar múltiples líneas vacías por máximo 2
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Limpiar espacios al inicio/final de líneas
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text.strip()
    
    def get_cleaning_stats(self, original: str, cleaned: str) -> Dict:
        """
        Obtiene estadísticas de la limpieza.
        
        Args:
            original: Texto original
            cleaned: Texto limpio
            
        Returns:
            Dict con estadísticas
        """
        original_chars = len(original)
        cleaned_chars = len(cleaned)
        
        original_lines = len(original.split('\n'))
        cleaned_lines = len(cleaned.split('\n'))
        
        original_words = len(original.split())
        cleaned_words = len(cleaned.split())
        
        return {
            'original_chars': original_chars,
            'cleaned_chars': cleaned_chars,
            'chars_removed': original_chars - cleaned_chars,
            'chars_removed_percent': round((original_chars - cleaned_chars) / original_chars * 100, 2) if original_chars > 0 else 0,
            'original_lines': original_lines,
            'cleaned_lines': cleaned_lines,
            'lines_removed': original_lines - cleaned_lines,
            'original_words': original_words,
            'cleaned_words': cleaned_words,
            'words_removed': original_words - cleaned_words,
        }


# Singleton para reutilización
_header_cleaner_instance: Optional[HeaderCleanerService] = None


def get_header_cleaner_service() -> HeaderCleanerService:
    """
    Obtiene instancia singleton del servicio de limpieza.
    
    Returns:
        HeaderCleanerService instance
    """
    global _header_cleaner_instance
    
    if _header_cleaner_instance is None:
        _header_cleaner_instance = HeaderCleanerService()
    
    return _header_cleaner_instance
