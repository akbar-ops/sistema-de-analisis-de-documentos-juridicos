"""
Document Metadata Extractor Service

Extracts comprehensive metadata from legal documents using LLM analysis.
Includes fallback mechanisms for robust extraction.
"""
import re
import logging
from typing import Dict, Optional
from datetime import datetime

from apps.core.services.ollama_agent.llm_service import LLMService
from apps.documents.models import LegalArea, DocumentType
from apps.documents.services.title_generator import TitleGenerator
from apps.documents.services.constants import (
    DOCUMENT_TYPES,
    LEGAL_AREAS,
    DOCUMENT_TYPE_KEYWORDS,
    LEGAL_AREA_KEYWORDS,
    CASE_NUMBER_PATTERN,
    JURISDICTIONAL_BODY_PATTERNS,
    LEGAL_SUBJECT_PATTERNS,
    MAX_TEXT_SAMPLE_LENGTH,
    TITLE_MIN_WORDS,
    TITLE_MAX_WORDS,
    LLM_TIMEOUT_METADATA,
)
from apps.documents.services.date_parser import date_parser

logger = logging.getLogger(__name__)


class DocumentMetadataExtractor:
    """
    Extracts comprehensive metadata from legal documents in a single LLM call.
    
    Extracted fields:
    - case_number: Número de expediente judicial
    - title: Título descriptivo del documento
    - doc_type: Tipo de documento (Sentencia, Demanda, etc.)
    - legal_area: Área legal (Penal, Civil, Laboral, etc.)
    - legal_subject: Materia específica del área legal
    - jurisdictional_body: Órgano jurisdiccional (Juzgado, Sala, Corte)
    - resolution_number: Número de resolución judicial
    - issue_place: Lugar de emisión del documento
    - document_date: Fecha de emisión del documento
    """
    
    def __init__(self):
        self.llm_service = LLMService()
        self.title_generator = TitleGenerator()
    
    def extract_metadata(self, text: str) -> Dict:
        """
        Extract all document metadata using LLM with fallback mechanisms.
        
        Args:
            text: Full document text
            
        Returns:
            Dictionary containing:
            - case_number (str|None)
            - title (str)
            - doc_type (DocumentType instance|None)
            - doc_type_name (str)
            - legal_area (LegalArea instance|None)
            - legal_area_name (str)
            - legal_subject (str|None)
            - jurisdictional_body (str|None)
            - resolution_number (str|None)
            - issue_place (str|None)
            - document_date (datetime.date|None)
        """
        try:
            text_sample = self._get_text_sample(text)
            
            # First, try to extract resolution info with regex (header usually at beginning)
            resolution_info = self._extract_resolution_info(text[:2000])
            
            # Build prompt for LLM extraction
            prompt = self._build_extraction_prompt(text_sample)
            
            # Get LLM response with extraction task type for longer output
            raw_response = self.llm_service.generate_response(
                prompt, 
                timeout=LLM_TIMEOUT_METADATA, 
                task_type="metadata_extraction"  # Específico para metadata
            )
            
            logger.info(f"LLM metadata response (first 200 chars): {raw_response[:200]}...")
            logger.debug(f"Full LLM response:\n{raw_response}")
            
            # Parse LLM response
            metadata = self._parse_llm_response(raw_response)
            
            # Merge regex resolution info with LLM results (regex takes priority if found)
            if resolution_info.get('resolution_number'):
                metadata['resolution_number'] = resolution_info['resolution_number']
            if resolution_info.get('issue_place'):
                metadata['issue_place'] = resolution_info['issue_place']
            if resolution_info.get('document_date'):
                metadata['document_date'] = resolution_info['document_date']
            
            # Apply fallback detection if needed
            metadata = self._apply_fallback_detection(metadata, text_sample)
            
            # Generate title if generic (passing text_sample for LLM generation)
            metadata = self._ensure_quality_title(metadata, text_sample)
            
            # Get database instances
            metadata['doc_type'] = self._get_document_type(metadata.get('doc_type_name'))
            metadata['legal_area'] = self._get_legal_area(metadata.get('legal_area_name'))
            
            logger.info(
                f"Final metadata - Type: {metadata.get('doc_type_name')}, "
                f"Area: {metadata.get('legal_area_name')}, "
                f"Subject: {metadata.get('legal_subject')}, "
                f"Case: {metadata.get('case_number')}, "
                f"Resolution: {metadata.get('resolution_number')}, "
                f"Place: {metadata.get('issue_place')}, "
                f"Date: {metadata.get('document_date')}"
            )
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}", exc_info=True)
            return self._get_default_metadata()
    
    def _get_text_sample(self, text: str) -> str:
        """Extract representative sample from document text."""
        if len(text) <= MAX_TEXT_SAMPLE_LENGTH:
            return text
        
        # Take first 70% and last 30% for better context
        first_part = text[:int(MAX_TEXT_SAMPLE_LENGTH * 0.7)]
        last_part = text[-int(MAX_TEXT_SAMPLE_LENGTH * 0.3):]
        return f"{first_part}\n\n[...contenido omitido...]\n\n{last_part}"
    
    def _normalize_resolution_number(self, resolution: str) -> str:
        """
        Normalize resolution number to a clean format.
        
        Examples:
        - "23-2025" → "23-2025" (mantener)
        - "Nro.TRES" → "TRES"
        - "RESOLUCIÓN N.° 9" → "9"
        - "  05  " → "05"
        - "DOSCIENTOS SETENTA Y NUEVE" → "DOSCIENTOS SETENTA Y NUEVE"
        """
        if not resolution:
            return resolution
        
        # Remove full prefix patterns that might come from LLM
        # First pass: Remove "RESOLUCIÓN" if present at start
        resolution = re.sub(r'^RESOLUCI[OÓ]N\s+', '', resolution, flags=re.IGNORECASE)
        
        # Second pass: Remove number prefixes like "N°", "Nro.", "N.°", "NÚMERO:", etc.
        resolution = re.sub(
            r'^N(?:RO?|ÚMERO|\.?°|\.?º)?\.?\s*[:.]?\s*',
            '',
            resolution,
            flags=re.IGNORECASE
        )
        
        # Clean whitespace
        resolution = re.sub(r'\s+', ' ', resolution).strip()
        
        # Remove trailing/leading separators
        resolution = resolution.strip('.:;,-/() ')
        
        # If empty after cleaning, return None
        if not resolution:
            return None
        
        # If it's all numbers with separators, keep it clean
        if re.match(r'^\d+[-/]\d+$', resolution):
            return resolution  # Like "23-2025" or "34/2025"
        
        # If it's just a number, keep it
        if resolution.isdigit():
            return resolution
        
        # If it's text in caps (like TRES, CINCO), keep it as is
        if resolution.isupper():
            return resolution
        
        # Mixed case - normalize to upper for consistency
        return resolution.upper()
    
    def _extract_resolution_info(self, text_header: str) -> Dict:
        """
        Extract resolution number, place and date from document header using regex.
        
        Examples:
        - Resolución Nro. 23-2025\nPuno, ocho de enero del año dos mil veinticinco.-
        - Resolución N° 5 (CINCO)\nLima, veintisiete de diciembre de dos mil veinticuatro
        - RESOLUCIÓN NÚMERO: TRES\nSanta Anita, veintinueve de julio de dos mil veinticuatro.
        """
        info = {
            'resolution_number': None,
            'issue_place': None,
            'document_date': None
        }
        
        try:
            # Pattern for resolution number
            # Must have RESOLUCIÓN followed by some variant, then actual number/text
            # Much stricter to avoid false positives
            
            # Split text into lines for better control
            lines = text_header.split('\n')
            
            for line in lines[:10]:  # Only check first 10 lines
                line = line.strip()
                
                # Must start with RESOLUCIÓN or Resolución
                if not re.match(r'^RESOLUCI[OÓ]N', line, re.IGNORECASE):
                    continue
                
                # Try to extract the number after the keyword
                # Simplified pattern: everything after RESOLUCIÓN and optional number prefix
                match = re.match(
                    r'^RESOLUCI[OÓ]N\s+(.+?)\s*$',
                    line,
                    re.IGNORECASE
                )
                
                if not match:
                    continue
                
                # Extract the full text after "RESOLUCIÓN"
                resolution = match.group(1).strip()
                
                # Basic validation: must have actual content (not just separators)
                resolution = resolution.strip('.:;,-/() ')
                
                if len(resolution) < 1:
                    continue
                
                # Check for false positive patterns (empty keywords)
                false_positives = ['NÚMERO', 'NUMERO', 'NRO', 'N°', 'Nº']
                if resolution.upper() in false_positives:
                    continue
                
                # Should have at least one digit OR be all caps text (like TRES, CINCO)
                has_digit = re.search(r'\d', resolution)
                is_all_caps_text = resolution.isupper() and len(resolution) >= 3
                
                if not (has_digit or is_all_caps_text):
                    continue
                
                # Clean and normalize
                resolution = re.sub(r'\s+', ' ', resolution)
                
                # Apply normalization
                resolution = self._normalize_resolution_number(resolution)
                
                if resolution:  # Check again after normalization
                    info['resolution_number'] = resolution
                    logger.info(f"✓ Regex extracted resolution: {info['resolution_number']}")
                    break
            
            # Pattern for place and date - MUST be near the top, after resolution
            # Expected format: "Lima, 10 de noviembre de 2023.-"
            place_date_lines = []
            lines = text_header.split('\n')
            
            # Buscar líneas que parecen contener lugar y fecha
            for i, line in enumerate(lines):
                if ',' in line and len(line) < 100:  # Líneas cortas con comas
                    # Check if it looks like a place-date line
                    parts = line.split(',', 1)
                    if len(parts) == 2:
                        potential_place = parts[0].strip()
                        # Validate place (city name - should be 1-2 words, letters only)
                        words = potential_place.split()
                        if 1 <= len(words) <= 3 and all(w[0].isupper() for w in words if w):
                            place_date_lines.append((i, line, parts[0].strip(), parts[1].strip()))
            
            # Process the most likely place-date line
            for idx, line, place, date_part1 in place_date_lines:
                # Get potential continuation line
                date_text = date_part1
                if idx + 1 < len(lines):
                    next_line = lines[idx + 1].strip()
                    # If next line looks like a date continuation (no uppercase start, has keywords)
                    if next_line and not next_line[0].isupper() and any(kw in next_line.lower() for kw in ['de', 'del', 'mil', 'dos', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']):
                        date_text = date_part1 + ' ' + next_line
                
                # Clean date text
                date_text = date_text.replace('.-', '').replace('.', '').replace('-', ' ').strip()
                
                # Validate and set place
                info['issue_place'] = place
                logger.info(f"✓ Regex extracted place: {info['issue_place']}")
                
                # Try to parse date
                if date_text:
                    try:
                        parsed_date = date_parser.parse(date_text)
                        if parsed_date:
                            info['document_date'] = parsed_date.date()
                            logger.info(f"✓ Regex extracted date: {date_text} → {info['document_date']}")
                            break  # Success, stop looking
                    except Exception as e:
                        logger.debug(f"Could not parse date '{date_text}': {e}")
        
        except Exception as e:
            logger.debug(f"Error extracting resolution info with regex: {e}")
        
        return info
    
    def _build_extraction_prompt(self, text: str) -> str:
        """Build unified prompt for metadata extraction with emphasis on unique, specific details."""
        
        prompt = f"""Eres un analista legal experto especializado en identificar LOS ASPECTOS MÁS ESPECÍFICOS Y ÚNICOS de cada documento judicial peruano.

IMPORTANTE: Responde en formato simple sin asteriscos, sin negritas, sin markdown.

INFORMACIÓN A EXTRAER:

EXPEDIENTE: [Número de expediente judicial completo]
RESOLUCION: [Número de resolución judicial, puede ser numérico como "23-2025" o en texto como "TRES", "DOSCIENTOS SETENTA Y NUEVE"]
LUGAR: [Lugar/ciudad de emisión del documento]
FECHA: [Fecha de emisión en texto tal como aparece en el documento]
PARTES: [Nombres de las partes principales del proceso:
   - En procesos PENALES: "Agraviado: [nombre] / Imputado: [nombre]" o "Ministerio Público vs [imputado]"
   - En procesos CIVILES/LABORALES: "Demandante: [nombre] / Demandado: [nombre]"
   - Usar los nombres COMPLETOS tal como aparecen en el documento
   - Si no están claros, dejar en blanco]
DECISION: [Decisión o fallo principal del documento:
   - "Fundada", "Infundada", "Improcedente", "Nulidad", "Condena a X años", "Absolución"
   - "Admite demanda", "Rechaza demanda", "Revoca", "Confirma", "Declara nulo"
   - Solo si el documento contiene una decisión final, sino dejar en blanco]
TIPO: [Tipo de documento: Sentencias, Autos, Decretos, Otros
   - SENTENCIAS: Resoluciones que resuelven el fondo del asunto y ponen fin al proceso
   - AUTOS: Resoluciones con contenido decisorio sobre puntos del proceso (admisión, saneamiento, etc.)
   - DECRETOS: Resoluciones de mero trámite sin contenido decisorio (téngase presente, remítase, etc.)]
AREA: [Especialidad/Área legal: Penal, Laboral, Familia Civil, Civil, Familia Tutelar, Comercial, Derecho Constitucional, Contencioso Administrativo, Familia Penal, Extension de Dominio, Otros
   - PENAL: Delitos, procesos penales
   - LABORAL: Despidos, beneficios sociales, relaciones laborales
   - FAMILIA CIVIL: Divorcio, separación de cuerpos, régimen patrimonial
   - CIVIL: Contratos, obligaciones, responsabilidad civil, propiedad
   - FAMILIA TUTELAR: Alimentos, tenencia, patria potestad, régimen de visitas
   - FAMILIA PENAL: Violencia familiar, omisión a la asistencia familiar
   - DERECHO CONSTITUCIONAL: Amparo, hábeas corpus, hábeas data
   - CONTENCIOSO ADMINISTRATIVO: Actos administrativos, procedimientos administrativos]
MATERIA: [Materia MUY ESPECÍFICA con detalles:
   - NO solo "Robo Agravado", sino "Robo Agravado con Arma de Fuego en Casa Habitada"
   - NO solo "Despido", sino "Despido Arbitrario de Trabajadora Gestante"
   - NO solo "Divorcio", sino "Divorcio por Causal de Violencia Familiar y Adulterio"
   - Incluir circunstancias agravantes, modalidades, y detalles únicos
   - Mínimo 4 palabras, máximo 15 palabras]
ORGANO: [Órgano jurisdiccional: nombre completo del juzgado, sala o corte]

REGLAS CRÍTICAS PARA ESPECIFICIDAD:
1. PARTES: Extraer nombres completos tal como aparecen, usar formato correcto según tipo de proceso
2. DECISION: Extraer el fallo o decisión principal si existe en el documento
3. MATERIA debe incluir todos los elementos distintivos (agravantes, modalidades, circunstancias)
4. Buscar detalles como: tipo de arma, lugar específico, momento, circunstancias especiales
5. Si hay múltiples delitos/causales, incluir los principales
6. TIPO: Si encuentra palabras como "SENTENCIA" y resuelve el fondo → "Sentencias"
   Si encuentra "AUTO" y decide sobre un punto procesal → "Autos"
   Si es solo trámite (téngase presente, remítase) → "Decretos"
7. AREA: Identificar la especialidad correcta del juzgado/sala
8. La RESOLUCION suele estar al inicio

EJEMPLOS DE BUENA ESPECIFICIDAD:
✅ PARTES: "Ministerio Público vs Juan García Pérez"
✅ DECISION: "Condena a 8 años de pena privativa de libertad"
✅ MATERIA: "Robo Agravado con Violencia, Arma de Fuego y en Casa Habitada"

DOCUMENTO:
{text}

Analiza el documento y extrae la información MÁS ESPECÍFICA posible. Responde SOLO con el formato indicado:"""
        
        return prompt
    
    def _parse_llm_response(self, response: str) -> Dict:
        """Parse metadata from LLM response."""
        metadata = {
            'case_number': None,
            'title': 'Documento Legal',
            'doc_type_name': 'Otros',
            'legal_area_name': 'Otros',
            'legal_subject': None,
            'jurisdictional_body': None,
            'resolution_number': None,
            'issue_place': None,
            'document_date': None,
            'partes': None,  # Temporal, para mejorar título
            'decision': None  # Temporal, para mejorar título
        }
        
        if not response:
            return metadata
        
        try:
            # Clean markdown formatting
            response = response.strip()
            response = re.sub(r'\*\*', '', response)
            response = re.sub(r'^\s*[\*\-#]+\s*', '', response, flags=re.MULTILINE)
            
            logger.debug(f"Cleaned response:\n{response[:500]}")
            
            lines = response.split('\n')
            current_field = None
            current_value = []
            
            field_keywords = [
                'EXPEDIENTE', 'NUMERO', 'RESOLUCION', 'RESOLUCIÓN', 
                'LUGAR', 'FECHA', 'TIPO', 
                'AREA', 'ÁREA', 'MATERIA', 'ORGANO', 'ÓRGANO',
                'PARTES', 'DECISION', 'DECISIÓN'
            ]
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                line_upper = line.upper()
                
                # Detect field with colon
                if ':' in line:
                    # Save previous field
                    if current_field and current_value:
                        value_str = ' '.join(current_value).strip()
                        # Clean trailing keywords
                        for keyword in field_keywords:
                            if value_str.upper().endswith(keyword):
                                value_str = value_str[:-(len(keyword))].strip()
                        logger.debug(f"Extracted {current_field}: {value_str}")
                        self._set_field(metadata, current_field, value_str)
                    
                    # Parse new field
                    parts = line.split(':', 1)
                    field_name = parts[0].strip().upper()
                    field_value = parts[1].strip() if len(parts) > 1 else ''
                    
                    current_field = self._identify_field(field_name)
                    current_value = [field_value] if field_value else []
                
                # Detect incomplete field (keyword without value)
                elif any(line_upper == kw or line_upper.startswith(kw + ' ') for kw in field_keywords):
                    if current_field and current_value:
                        value_str = ' '.join(current_value).strip()
                        logger.debug(f"Extracted {current_field}: {value_str}")
                        self._set_field(metadata, current_field, value_str)
                    
                    logger.warning(f"Found incomplete field: {line}")
                    current_field = None
                    current_value = []
                
                elif current_field:
                    # Continue current field value if not a keyword
                    if not any(kw in line_upper for kw in field_keywords):
                        current_value.append(line)
            
            # Save last field
            if current_field and current_value:
                value_str = ' '.join(current_value).strip()
                for keyword in field_keywords:
                    if value_str.upper().endswith(keyword):
                        value_str = value_str[:-(len(keyword))].strip()
                logger.debug(f"Extracted {current_field}: {value_str}")
                self._set_field(metadata, current_field, value_str)
            
            logger.info(f"Parsed - Type: {metadata['doc_type_name']}, Area: {metadata['legal_area_name']}")
                    
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}", exc_info=True)
        
        return metadata
    
    def _identify_field(self, field_name: str) -> Optional[str]:
        """Identify field type from field name."""
        if any(kw in field_name for kw in ['EXPEDIENTE', 'NUMERO']) and 'RESOLUCI' not in field_name:
            return 'case_number'
        elif 'RESOLUCI' in field_name or 'RESOLUCIÓN' in field_name:
            return 'resolution_number'
        elif 'LUGAR' in field_name:
            return 'issue_place'
        elif 'FECHA' in field_name:
            return 'document_date'
        elif 'PARTES' in field_name:
            return 'partes'
        elif 'DECISION' in field_name or 'DECISIÓN' in field_name:
            return 'decision'
        elif 'TIPO' in field_name:
            return 'doc_type'
        elif 'AREA' in field_name or 'ÁREA' in field_name:
            return 'legal_area'
        elif 'MATERIA' in field_name:
            return 'legal_subject'
        elif 'ORGANO' in field_name or 'ÓRGANO' in field_name:
            return 'jurisdictional_body'
        return None
    
    def _set_field(self, metadata: Dict, field: str, value: str):
        """Set metadata field with normalization and validation."""
        if not value:
            return
        
        # Clean value
        value = value.strip()
        value = re.sub(r'^\*+\s*', '', value)
        value = re.sub(r'\s*\*+$', '', value)
        value = re.sub(r'^[#\-_]+\s*', '', value)
        value = value.strip('"\'`')
        value = re.sub(r'\s+', ' ', value).strip()
        
        if not value or len(value) < 2:
            return
        
        if field == 'case_number':
            if not re.match(r'^(No\s+identificado|N/?A)$', value, re.IGNORECASE):
                metadata['case_number'] = value
        
        elif field == 'resolution_number':
            if not re.match(r'^(No\s+identificado|N/?A)$', value, re.IGNORECASE):
                normalized = self._normalize_resolution_number(value)
                if normalized:
                    metadata['resolution_number'] = normalized
        
        elif field == 'issue_place':
            if not re.match(r'^(No\s+identificado|N/?A)$', value, re.IGNORECASE):
                # Clean place - if it contains comma, take only the part before it
                # LLM sometimes extracts "Lima, 10 de noviembre..." instead of just "Lima"
                if ',' in value:
                    value = value.split(',')[0].strip()
                
                # Remove any trailing punctuation
                value = value.rstrip('.:;')
                
                # Validate: should be 1-3 words, all starting with capital
                words = value.split()
                if 1 <= len(words) <= 3 and all(w and w[0].isupper() for w in words):
                    metadata['issue_place'] = value
        
        elif field == 'document_date':
            # Try to parse the date text
            if not re.match(r'^(No\s+identificado|N/?A)$', value, re.IGNORECASE):
                try:
                    parsed_date = date_parser.parse(value)
                    if parsed_date:
                        metadata['document_date'] = parsed_date.date()
                        logger.info(f"✓ Parsed date: '{value}' → {metadata['document_date']}")
                    else:
                        logger.warning(f"Could not parse date: '{value}'")
                except Exception as e:
                    logger.error(f"Error parsing date '{value}': {e}")
        
        elif field == 'doc_type':
            value_lower = value.lower()
            best_match = None
            
            # Exact match
            for known_type in DOCUMENT_TYPES:
                if known_type.lower() == value_lower:
                    best_match = known_type
                    logger.info(f"✓ Exact doc_type match: '{value}' → '{best_match}'")
                    break
            
            # Partial match
            if not best_match:
                for known_type in DOCUMENT_TYPES:
                    if known_type.lower() in value_lower or value_lower in known_type.lower():
                        best_match = known_type
                        logger.info(f"✓ Partial doc_type match: '{value}' → '{best_match}'")
                        break
            
            if best_match:
                metadata['doc_type_name'] = best_match
            else:
                logger.warning(f"✗ No doc_type match for: '{value}', using 'Otros'")
        
        elif field == 'legal_area':
            value_lower = value.lower()
            best_match = None
            
            # Exact match
            for known_area in LEGAL_AREAS:
                if known_area.lower() == value_lower:
                    best_match = known_area
                    logger.info(f"✓ Exact legal_area match: '{value}' → '{best_match}'")
                    break
            
            # Partial match
            if not best_match:
                for known_area in LEGAL_AREAS:
                    if known_area.lower() in value_lower or value_lower in known_area.lower():
                        best_match = known_area
                        logger.info(f"✓ Partial legal_area match: '{value}' → '{best_match}'")
                        break
            
            if best_match:
                metadata['legal_area_name'] = best_match
            else:
                logger.warning(f"✗ No legal_area match for: '{value}', using 'Otros'")
        
        elif field == 'legal_subject':
            if not re.match(r'^(No\s+(especificado|identificado|aplica)|N/?A)$', value, re.IGNORECASE):
                metadata['legal_subject'] = value
        
        elif field == 'jurisdictional_body':
            if not re.match(r'^(No\s+(identificado|aplica)|N/?A)$', value, re.IGNORECASE):
                metadata['jurisdictional_body'] = value
        
        elif field == 'partes':
            if not re.match(r'^(No\s+(identificado|especificado)|N/?A)$', value, re.IGNORECASE):
                metadata['partes'] = value
        
        elif field == 'decision':
            if not re.match(r'^(No\s+(identificado|especificado|aplica)|N/?A)$', value, re.IGNORECASE):
                metadata['decision'] = value
    

    ############ CHECK
    def _apply_fallback_detection(self, metadata: Dict, text: str) -> Dict:
        """Apply keyword-based detection if LLM returned generic values."""
        if metadata['doc_type_name'] == 'Otros' or metadata['legal_area_name'] == 'Otros':
            logger.warning("Applying keyword-based fallback detection")
            fallback = self._detect_from_keywords(text)
            
            if metadata['doc_type_name'] == 'Otros' and fallback.get('doc_type_name') != 'Otros':
                metadata['doc_type_name'] = fallback['doc_type_name']
                logger.info(f"Fallback detected doc_type: {metadata['doc_type_name']}")
            
            if metadata['legal_area_name'] == 'Otros' and fallback.get('legal_area_name') != 'Otros':
                metadata['legal_area_name'] = fallback['legal_area_name']
                logger.info(f"Fallback detected legal_area: {metadata['legal_area_name']}")
        
        # Extract missing fields using regex
        if not metadata.get('legal_subject') or not metadata.get('jurisdictional_body'):
            logger.info("Extracting missing fields with regex")
            extra_fields = self._extract_with_regex(text)
            
            if not metadata.get('legal_subject') and extra_fields.get('legal_subject'):
                metadata['legal_subject'] = extra_fields['legal_subject']
                logger.info(f"Regex extracted legal_subject: {metadata['legal_subject']}")
            
            if not metadata.get('jurisdictional_body') and extra_fields.get('jurisdictional_body'):
                metadata['jurisdictional_body'] = extra_fields['jurisdictional_body']
                logger.info(f"Regex extracted jurisdictional_body: {metadata['jurisdictional_body']}")
        
        return metadata
    
    def _detect_from_keywords(self, text: str) -> Dict:
        """Detect document type and legal area using keyword matching."""
        text_lower = text.lower()
        
        # Detect document type
        doc_type = 'Otros'
        max_matches = 0
        for type_name, keywords in DOCUMENT_TYPE_KEYWORDS.items():
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            if matches > max_matches:
                max_matches = matches
                doc_type = type_name
        
        # Detect legal area
        legal_area = 'Otros'
        max_matches = 0
        for area_name, keywords in LEGAL_AREA_KEYWORDS.items():
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            if matches > max_matches:
                max_matches = matches
                legal_area = area_name
        
        logger.debug(f"Keyword detection: type={doc_type}, area={legal_area}")
        
        return {
            'doc_type_name': doc_type,
            'legal_area_name': legal_area
        }
    
    #############
    
    def _extract_with_regex(self, text: str) -> Dict:
        """Extract specific fields using regex patterns."""
        fields = {}
        
        # Extract legal subject
        for pattern in LEGAL_SUBJECT_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                subject = match.group(1).strip()
                if len(subject) > 10 and len(subject) < 200:
                    fields['legal_subject'] = subject
                    break
        
        # Extract jurisdictional body
        for pattern in JURISDICTIONAL_BODY_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                body = match.group(0).strip()
                if len(body) > 10:
                    fields['jurisdictional_body'] = body.upper()
                    break
        
        return fields
    
    def _ensure_quality_title(self, metadata: Dict, text_sample: str = None) -> Dict:
        """Generate quality title using dedicated title generation service."""
        if not text_sample:
            logger.warning("No text sample provided for title generation")
            metadata['title'] = 'Documento Legal'
            return metadata
        
        # Use dedicated title generator service
        logger.info("Generating title using dedicated TitleGenerator service")
        metadata['title'] = self.title_generator.generate_title(
            text_sample,
            doc_type=metadata.get('doc_type_name'),
            legal_area=metadata.get('legal_area_name'),
            legal_subject=metadata.get('legal_subject'),
            partes=metadata.get('partes'),
            decision=metadata.get('decision')
        )
        
        return metadata
    
    def _get_document_type(self, type_name: Optional[str]) -> Optional[DocumentType]:
        """Get DocumentType instance from database."""
        if not type_name:
            return None
        
        try:
            return DocumentType.objects.get(name=type_name, is_active=True)
        except DocumentType.DoesNotExist:
            logger.warning(f"DocumentType '{type_name}' not found in database")
            return None
    
    def _get_legal_area(self, area_name: Optional[str]) -> Optional[LegalArea]:
        """Get LegalArea instance from database."""
        if not area_name:
            return None
        
        try:
            return LegalArea.objects.get(name=area_name, is_active=True)
        except LegalArea.DoesNotExist:
            logger.warning(f"LegalArea '{area_name}' not found in database")
            return None
    
    def _get_default_metadata(self) -> Dict:
        """Return default metadata when extraction fails."""
        return {
            'case_number': None,
            'title': 'Documento Legal',
            'doc_type': None,
            'doc_type_name': 'Otros',
            'legal_area': None,
            'legal_area_name': 'Otros',
            'legal_subject': None,
            'jurisdictional_body': None,
            'resolution_number': None,
            'issue_place': None,
            'document_date': None
        }

    # ============================================================================
    # LIGHT MODE - Regex-Only Extraction (No LLM/Ollama)
    # ============================================================================
    
    def extract_metadata_regex_only(self, text: str) -> Dict:
        """
        Extract document metadata using ONLY regex and keyword detection.
        NO LLM/Ollama calls are made.
        
        This is useful for bulk uploads where speed is more important than
        perfect accuracy, or when Ollama is not available/desired.
        
        Args:
            text: Full document text
            
        Returns:
            Dictionary containing all metadata fields (same structure as extract_metadata)
        """
        logger.info("=== REGEX-ONLY METADATA EXTRACTION (No LLM) ===")
        
        try:
            # Start with default metadata
            metadata = self._get_default_metadata()
            
            # 1. Extract resolution info (number, place, date) from header
            resolution_info = self._extract_resolution_info(text[:3000])
            if resolution_info.get('resolution_number'):
                metadata['resolution_number'] = resolution_info['resolution_number']
                logger.info(f"Regex extracted resolution_number: {metadata['resolution_number']}")
            if resolution_info.get('issue_place'):
                metadata['issue_place'] = resolution_info['issue_place']
                logger.info(f"Regex extracted issue_place: {metadata['issue_place']}")
            if resolution_info.get('document_date'):
                metadata['document_date'] = resolution_info['document_date']
                logger.info(f"Regex extracted document_date: {metadata['document_date']}")
            
            # 2. Extract case number using regex patterns
            case_number = self._extract_case_number_regex(text[:5000])
            if case_number:
                metadata['case_number'] = case_number
                logger.info(f"Regex extracted case_number: {case_number}")
            
            # 3. Detect document type and legal area from keywords
            keyword_detection = self._detect_from_keywords(text)
            if keyword_detection.get('doc_type_name'):
                metadata['doc_type_name'] = keyword_detection['doc_type_name']
                logger.info(f"Keywords detected doc_type: {metadata['doc_type_name']}")
            if keyword_detection.get('legal_area_name'):
                metadata['legal_area_name'] = keyword_detection['legal_area_name']
                logger.info(f"Keywords detected legal_area: {metadata['legal_area_name']}")
            
            # 4. Extract legal_subject and jurisdictional_body with regex
            extra_fields = self._extract_with_regex(text)
            if extra_fields.get('legal_subject'):
                metadata['legal_subject'] = extra_fields['legal_subject']
                logger.info(f"Regex extracted legal_subject: {metadata['legal_subject']}")
            if extra_fields.get('jurisdictional_body'):
                metadata['jurisdictional_body'] = extra_fields['jurisdictional_body']
                logger.info(f"Regex extracted jurisdictional_body: {metadata['jurisdictional_body']}")
            
            # 5. Generate a basic title from available data (no LLM)
            metadata['title'] = self._generate_basic_title(metadata, text)
            logger.info(f"Generated basic title: {metadata['title']}")
            
            # 6. Get database instances for doc_type and legal_area
            metadata['doc_type'] = self._get_document_type(metadata['doc_type_name'])
            metadata['legal_area'] = self._get_legal_area(metadata['legal_area_name'])
            
            logger.info(f"=== REGEX-ONLY EXTRACTION COMPLETE ===")
            logger.info(f"  doc_type: {metadata['doc_type_name']}, legal_area: {metadata['legal_area_name']}")
            logger.info(f"  resolution: {metadata.get('resolution_number')}, date: {metadata.get('document_date')}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error in regex-only metadata extraction: {e}", exc_info=True)
            return self._get_default_metadata()
    
    def _extract_case_number_regex(self, text: str) -> Optional[str]:
        """
        Extract case/expediente number using regex patterns.
        
        Common formats:
        - Expediente N° 12345-2024
        - Exp. 2024-123
        - EXPEDIENTE: 00123-2024-0-1501-JR-CI-01
        """
        patterns = [
            # Standard expediente patterns
            r'(?:EXPEDIENTE|EXP\.?)\s*(?:N[°ºo]?\.?\s*)?[:\s]*(\d{1,6}[-/]\d{4}(?:[-/]\d+)?(?:[-/][A-Z0-9-]+)?)',
            # More detailed format
            r'(?:EXPEDIENTE|EXP\.?)\s*[:\s]*(\d{5,15}[-]\d{4}[-]\d[-]\d{4}[-][A-Z]{2,3}[-][A-Z]{2,3}[-]\d{2})',
            # Simple number format
            r'(?:EXPEDIENTE|EXP\.?)\s*[:\s]*N?[°ºo]?\s*(\d{4,10}[-/]?\d{0,4})',
        ]
        
        text_upper = text.upper()
        
        for pattern in patterns:
            match = re.search(pattern, text_upper, re.IGNORECASE)
            if match:
                case_num = match.group(1).strip()
                # Clean and validate
                if len(case_num) >= 4 and any(c.isdigit() for c in case_num):
                    return case_num
        
        return None
    
    def _generate_basic_title(self, metadata: Dict, text: str) -> str:
        """
        Generate a basic title from metadata without using LLM.
        
        Format: "[DocType] [Resolution] - [Subject/Area]"
        """
        parts = []
        
        # Add document type
        doc_type = metadata.get('doc_type_name', 'Documento')
        if doc_type and doc_type != 'Otros':
            parts.append(doc_type)
        else:
            parts.append('Documento')
        
        # Add resolution number if available
        if metadata.get('resolution_number'):
            parts.append(f"N° {metadata['resolution_number']}")
        
        # Add legal area or subject
        legal_area = metadata.get('legal_area_name')
        if legal_area and legal_area != 'Otros':
            parts.append(f"- {legal_area}")
        elif metadata.get('legal_subject'):
            # Truncate long subjects
            subject = metadata['legal_subject'][:50]
            if len(metadata['legal_subject']) > 50:
                subject += '...'
            parts.append(f"- {subject}")
        
        title = ' '.join(parts)
        
        # If title is too generic, add date or place for context
        if title == 'Documento':
            if metadata.get('document_date'):
                title = f"Documento del {metadata['document_date'].strftime('%d/%m/%Y')}"
            elif metadata.get('issue_place'):
                title = f"Documento de {metadata['issue_place']}"
        
        return title
