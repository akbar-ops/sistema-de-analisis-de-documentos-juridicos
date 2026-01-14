"""
Document Summarizer Service

Generates structured summaries of legal documents with key information extraction.
Supports multiple backends:
- Ollama: LLM-based structured summary with specific format
- Ollama Hierarchical: Map-reduce summarization for long documents
- BART: Hugging Face transformer model for dense summaries optimized for embeddings
"""
import re
import logging
from typing import Dict, Optional

from apps.core.services.ollama_agent.llm_service import LLMService
from apps.documents.services.constants import LLM_TIMEOUT_SUMMARY

logger = logging.getLogger(__name__)


class DocumentSummarizer:
    """
    Generates comprehensive structured summaries of legal documents.
    
    Supports multiple backends:
    - ollama: LLM-based structured summary (uses first 6000 chars only)
    - ollama_hierarchical: Map-reduce approach for FULL document summarization
      - Divides document into chunks
      - Summarizes each chunk
      - Combines summaries into final structured summary
    - BART: Hugging Face transformer model for dense summaries
    
    Extracted information:
    - executive_summary: Concise overview of the document
    - important_dates: Key dates and their descriptions
    - decision: Final ruling or current status
    - keywords: Relevant legal terms and concepts
    """
    
    MAX_TEXT_LENGTH = 6000  # Solo usado para ollama directo
    MIN_CONTENT_LENGTH = 100
    REPETITION_THRESHOLD = 0.3
    
    def __init__(self):
        self.llm_service = LLMService()
        self.bart_summarizer = None
        self.hierarchical_summarizer = None
    
    def _ensure_bart_loaded(self):
        """Carga BART solo cuando se necesita (lazy loading)."""
        if self.bart_summarizer is None:
            try:
                from apps.core.services.bart_summarizer import BARTSummarizer
                logger.info("Initializing BART summarizer...")
                self.bart_summarizer = BARTSummarizer()
                logger.info("✓ BART summarizer ready")
            except Exception as e:
                logger.error(f"Error loading BART: {e}")
                raise
    
    def _ensure_hierarchical_loaded(self):
        """Carga HierarchicalSummarizer solo cuando se necesita (lazy loading)."""
        if self.hierarchical_summarizer is None:
            try:
                from apps.documents.services.hierarchical_summarizer import HierarchicalSummarizer
                logger.info("Initializing Hierarchical summarizer...")
                self.hierarchical_summarizer = HierarchicalSummarizer()
                logger.info("✓ Hierarchical summarizer ready")
            except Exception as e:
                logger.error(f"Error loading HierarchicalSummarizer: {e}")
                raise
    
    def generate_summary(
        self, 
        text: str, 
        doc_type_name: str,
        legal_area_name: str,
        legal_subject: Optional[str] = None,
        summarizer_type: str = 'ollama'
    ) -> Dict:
        """
        Generate structured summary with fallback for invalid content.
        
        Args:
            text: Full document text
            doc_type_name: Type of document (Sentencia, Demanda, etc.)
            legal_area_name: Legal area (Penal, Civil, etc.)
            legal_subject: Specific legal subject/matter
            summarizer_type: 
                - 'ollama' (default): Uses first 6000 chars only
                - 'ollama_hierarchical': Map-reduce for FULL document (recommended)
                - 'bart': Hugging Face BART model
            
        Returns:
            Dictionary containing:
            - summary_text: Full formatted summary
            - executive_summary: Main summary paragraph
            - important_dates: Formatted dates list
            - decision: Decision or ruling text
            - keywords: Comma-separated keywords
        """
        try:
            # Para bart y ollama directo, usar muestra truncada
            # Para jerárquico, usar texto completo
            if summarizer_type == 'ollama_hierarchical':
                text_to_process = text  # Texto completo
            else:
                text_to_process = self._get_text_sample(text)  # Muestra truncada
            
            # Validate content quality
            if not self._is_valid_legal_content(text_to_process[:self.MAX_TEXT_LENGTH]):
                logger.warning("Document has insufficient legal content")
                return self._generate_fallback_summary(doc_type_name, legal_area_name)
            
            # Decidir qué backend usar según el parámetro
            if summarizer_type == 'bart':
                logger.info("Using BART for summary generation")
                self._ensure_bart_loaded()
                return self._generate_summary_with_bart(
                    text_to_process, doc_type_name, legal_area_name, legal_subject
                )
            elif summarizer_type == 'ollama_hierarchical':
                logger.info(f"Using Ollama HIERARCHICAL for FULL document ({len(text)} chars)")
                self._ensure_hierarchical_loaded()
                return self.hierarchical_summarizer.generate_hierarchical_summary(
                    text_to_process, doc_type_name, legal_area_name, legal_subject
                )
            else:
                logger.info(f"Using Ollama DIRECT for summary ({len(text_to_process)} chars)")
                return self._generate_summary_with_ollama(
                    text_to_process, doc_type_name, legal_area_name, legal_subject
                )
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}", exc_info=True)
            return self._generate_fallback_summary(doc_type_name, legal_area_name)
    
    def _get_text_sample(self, text: str) -> str:
        """Extract representative sample from document text."""
        if len(text) <= self.MAX_TEXT_LENGTH:
            return text
        
        # Take first 67% and last 33% for better context
        first_part = text[:int(self.MAX_TEXT_LENGTH * 0.67)]
        last_part = text[-int(self.MAX_TEXT_LENGTH * 0.33):]
        return f"{first_part}\n\n[...contenido omitido...]\n\n{last_part}"
    
    def _generate_summary_with_bart(
        self,
        text: str,
        doc_type_name: str,
        legal_area_name: str,
        legal_subject: Optional[str] = None
    ) -> Dict:
        """
        Genera resumen usando BART (mBART-50 multilingual) optimizado para embeddings.
        
        BART genera un resumen denso, detallado y sin formato, ideal para:
        - Generar embeddings de alta calidad
        - Búsqueda por similitud
        - Capturar toda la información relevante del documento
        """
        try:
            logger.info("Generating dense summary with BART (optimized for embeddings)...")
            
            # Este método genera el mejor resumen posible adaptándose al hardware
            bart_summary = self.bart_summarizer.generate_dense_summary_for_embeddings(text)
            
            logger.info(f"Generated dense summary: {len(bart_summary)} characters")
            
            # Para mantener compatibilidad con el sistema actual,
            # retornamos el resumen tanto en summary_text como en executive_summary
            # El resumen NO tiene formato estructurado, es texto corrido optimizado para embeddings
            
            return {
                'summary_text': bart_summary,  # Resumen sin formato
                'executive_summary': bart_summary,  # Mismo resumen
                'important_dates': None,  # No extraemos estructura
                'decision': None,  # No extraemos estructura
                'keywords': f"{doc_type_name}, {legal_area_name}" + (f", {legal_subject}" if legal_subject else "")
            }
            
        except Exception as e:
            logger.error(f"Error with BART summarization: {e}", exc_info=True)
            # Fallback a Ollama si falla BART
            return self._generate_summary_with_ollama(
                text, doc_type_name, legal_area_name, legal_subject
            )
    
    def _generate_summary_with_ollama(
        self,
        text: str,
        doc_type_name: str,
        legal_area_name: str,
        legal_subject: Optional[str] = None
    ) -> Dict:
        """Genera resumen usando Ollama (método original)."""
        try:
            # Build and send prompt
            prompt = self._build_summary_prompt(
                text, 
                doc_type_name, 
                legal_area_name,
                legal_subject
            )
            
            raw_response = self.llm_service.generate_response(
                prompt, 
                timeout=LLM_TIMEOUT_SUMMARY, 
                task_type="summary_generation"
            )
            
            logger.debug(f"LLM summary response (first 200 chars): {raw_response[:200]}...")
            
            # Check for LLM rejection
            if self._is_llm_rejection(raw_response):
                logger.warning("LLM unable to generate summary")
                return self._generate_fallback_summary(doc_type_name, legal_area_name)
            
            # Parse structured response
            summary_data = self._parse_summary_response(raw_response)
            summary_data['summary_text'] = raw_response
            
            logger.info("Successfully generated structured summary with Ollama")
            
            return summary_data
            
        except Exception as e:
            logger.error(f"Error with Ollama summarization: {e}", exc_info=True)
            return self._generate_fallback_summary(doc_type_name, legal_area_name)
    
    def _is_valid_legal_content(self, text: str) -> bool:
        """Validate that document contains sufficient legal content."""
        # Check minimum length
        if len(text.strip()) < self.MIN_CONTENT_LENGTH:
            return False
        
        # Check for excessive repetition
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if len(lines) < 5:
            return False
        
        unique_lines = set(lines)
        repetition_ratio = len(unique_lines) / len(lines)
        
        if repetition_ratio < self.REPETITION_THRESHOLD:
            logger.debug(
                f"Document has excessive repetition: "
                f"{len(unique_lines)}/{len(lines)} unique lines (ratio: {repetition_ratio:.2f})"
            )
            return False
        
        return True
    
    def _extract_dates_from_text(self, text: str) -> Optional[str]:
        """
        Extrae fechas importantes del texto usando expresiones regulares.
        Útil para BART que no estructura la información.
        """
        try:
            # Patrones de fecha comunes en documentos legales peruanos
            date_patterns = [
                # DD de MMMM de YYYY
                r'(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})',
                # DD/MM/YYYY o DD-MM-YYYY
                r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',
                # YYYY-MM-DD (formato ISO)
                r'(\d{4})-(\d{1,2})-(\d{1,2})',
            ]
            
            found_dates = []
            for pattern in date_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    date_str = match.group(0)
                    # Buscar contexto alrededor de la fecha
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    context = text[start:end].strip()
                    
                    # Limpiar contexto
                    context = context.replace('\n', ' ')
                    context = re.sub(r'\s+', ' ', context)
                    
                    found_dates.append(f"- {date_str}: {context}")
                    
                    # Limitar a 10 fechas
                    if len(found_dates) >= 10:
                        break
                
                if len(found_dates) >= 10:
                    break
            
            if found_dates:
                return "\n".join(found_dates[:10])
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error extracting dates: {e}")
            return None
    
    def _extract_decision_from_text(self, text: str) -> Optional[str]:
        """
        Extrae la decisión/fallo del documento.
        Busca secciones típicas de decisiones legales.
        """
        try:
            # Patrones de decisión/fallo
            decision_markers = [
                r'(?:SE\s+)?RESUELVE[:\s]+(.*?)(?=\n\n|\n[A-Z]{3,}|$)',
                r'(?:SE\s+)?DECIDE[:\s]+(.*?)(?=\n\n|\n[A-Z]{3,}|$)',
                r'FALLA[:\s]+(.*?)(?=\n\n|\n[A-Z]{3,}|$)',
                r'SENTENCIA[:\s]+(.*?)(?=\n\n|\n[A-Z]{3,}|$)',
                r'DECISIÓN[:\s]+(.*?)(?=\n\n|\n[A-Z]{3,}|$)',
                r'(?:SE\s+)?DISPONE[:\s]+(.*?)(?=\n\n|\n[A-Z]{3,}|$)',
            ]
            
            for pattern in decision_markers:
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    decision_text = match.group(1).strip()
                    # Limpiar y truncar
                    decision_text = decision_text.replace('\n', ' ')
                    decision_text = re.sub(r'\s+', ' ', decision_text)
                    
                    # Tomar primeros 500 caracteres
                    if len(decision_text) > 500:
                        decision_text = decision_text[:500] + "..."
                    
                    return decision_text
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting decision: {e}")
            return None
    
    def _generate_keywords_from_text(
        self, 
        summary: str, 
        doc_type: str, 
        legal_area: str
    ) -> str:
        """
        Genera keywords del resumen usando frecuencia de términos.
        """
        try:
            # Keywords base
            base_keywords = [doc_type, legal_area]
            
            # Términos legales comunes importantes
            legal_terms = [
                'sentencia', 'demanda', 'apelación', 'recurso', 'casación',
                'nulidad', 'prescripción', 'sobreseimiento', 'condena',
                'absolución', 'indemnización', 'daños', 'perjuicios',
                'penal', 'civil', 'laboral', 'constitucional', 'administrativo',
                'robo', 'hurto', 'estafa', 'violación', 'homicidio',
                'lesiones', 'tráfico', 'lavado', 'corrupción', 'cohecho',
                'delito', 'falta', 'infracción', 'contrato', 'propiedad',
                'reivindicación', 'desalojo', 'alimentos', 'divorcio',
                'régimen', 'tenencia', 'patria', 'tutela', 'curatela'
            ]
            
            # Buscar términos en el resumen
            summary_lower = summary.lower()
            found_terms = []
            
            for term in legal_terms:
                if term in summary_lower:
                    found_terms.append(term)
            
            # Combinar keywords
            all_keywords = base_keywords + found_terms[:10]  # Máximo 10 términos extra
            
            return ', '.join(all_keywords)
            
        except Exception as e:
            logger.error(f"Error generating keywords: {e}")
            return f"{doc_type}, {legal_area}"
    
    def _build_structured_summary(
        self,
        executive_summary: str,
        dates: Optional[str],
        decision: Optional[str],
        keywords: str
    ) -> str:
        """
        Construye un resumen estructurado en formato similar al de Ollama.
        """
        parts = []
        
        parts.append("RESUMEN EJECUTIVO:")
        parts.append(executive_summary)
        parts.append("")
        
        parts.append("FECHAS IMPORTANTES:")
        if dates:
            parts.append(dates)
        else:
            parts.append("No se identificaron fechas específicas.")
        parts.append("")
        
        parts.append("DECISIÓN/FALLO:")
        if decision:
            parts.append(decision)
        else:
            parts.append("Información no disponible.")
        parts.append("")
        
        parts.append("KEYWORDS:")
        parts.append(keywords)
        
        return "\n".join(parts)
    
    def _is_llm_rejection(self, response: str) -> bool:
        """Detect if LLM rejected generating content."""
        if not response:
            return True
        
        rejection_patterns = [
            r'lo siento.*no puedo',
            r'i cannot',
            r'i apologize.*cannot',
            r'i\'m sorry.*cannot',
            r'no puedo generar',
            r'no puedo ayudar',
            r'no puedo crear',
            r'cannot generate',
            r'unable to',
        ]
        
        response_lower = response.lower()
        return any(re.search(pattern, response_lower) for pattern in rejection_patterns)
    
    def _build_summary_prompt(
        self, 
        text: str, 
        doc_type: str, 
        legal_area: str,
        legal_subject: Optional[str] = None
    ) -> str:
        """Build structured prompt for highly specific summary generation."""
        
        subject_info = f"\n- Materia: {legal_subject}" if legal_subject else ""
        
        prompt = f"""Eres un experto en análisis de documentos legales del sistema judicial peruano especializado en capturar LOS DETALLES ÚNICOS Y ESPECÍFICOS de cada caso.

INFORMACIÓN DEL DOCUMENTO:
- Tipo: {doc_type}
- Área Legal: {legal_area}{subject_info}

INSTRUCCIONES: Genera un resumen estructurado usando EXACTAMENTE este formato (sin markdown):

RESUMEN EJECUTIVO:
[Escribe 5-8 oraciones ALTAMENTE ESPECÍFICAS incluyendo:
- Hechos PARTICULARES del caso (fechas, lugares, circunstancias exactas)
- Nombres completos de partes involucradas
- Asunto central con todos los DETALLES DISTINTIVOS
- Agravantes, modalidades, circunstancias especiales
- Montos, cantidades, duraciones si aplica
- Contexto relevante ÚNICO de este caso
- Elementos probatorios principales
- NO uses frases genéricas - cada oración debe aportar información ESPECÍFICA
Ejemplo BUENO: "El acusado Juan Pérez robó el 15/03/2023 con arma blanca tipo cuchillo en vivienda ubicada en Av. Principal 123, aprovechando la oscuridad nocturna, sustrayendo bienes por S/5,000"
Ejemplo MALO: "Se trata de un caso de robo agravado donde el acusado sustrajo bienes"]

FECHAS IMPORTANTES:
[Lista TODAS las fechas clave con formato:
- DD/MM/AAAA: Descripción ESPECÍFICA del evento con detalles
- Incluir: fecha del hecho, denuncia, detención, audiencias, notificaciones
- NO omitir fechas menores - todas son importantes para identificar el caso
Si no hay fechas, escribe "No se identificaron fechas específicas"]

DECISIÓN/FALLO:
[Describe la decisión o resolución CON MÁXIMO DETALLE:
- Tipo exacto de decisión (fundada, infundada, improcedente, etc.)
- Qué ESPECÍFICAMENTE se decidió o resolvió (penas, montos, plazos exactos)
- Fundamentos jurídicos PRINCIPALES citados (artículos, normas)
- Razonamiento central del juez/tribunal
- Consecuencias concretas (años de prisión, montos exactos, prohibiciones)
Si no hay decisión final, describir ESPECÍFICAMENTE el estado actual del proceso]

KEYWORDS:
[Lista 8-15 términos MUY ESPECÍFICOS separados por comas:
- Delitos/materias con TODOS sus agravantes
- Conceptos jurídicos ESPECÍFICOS aplicados
- Tipos de pruebas presentadas
- Figuras legales invocadas
- Modalidades y circunstancias
- NO usar términos genéricos como "robo", usar "robo agravado con violencia nocturna"
- Incluir términos que hacen este caso ÚNICO
Ejemplo: "robo agravado, casa habitada, arma blanca, nocturnidad, flagrancia, pluralidad de agentes, despoblado"]

DOCUMENTO:
{text}

RECUERDA: La clave es ESPECIFICIDAD MÁXIMA. Cada detalle (nombres, fechas, montos, lugares, modalidades) hace este documento ÚNICO y facilita encontrar casos realmente similares.

Genera el resumen siguiendo el formato exacto:"""
        
        return prompt
    
    def _parse_summary_response(self, response: str) -> Dict:
        """Parse structured summary from LLM response."""
        summary_data = {
            'executive_summary': '',
            'important_dates': None,
            'decision': None,
            'keywords': ''
        }
        
        if not response:
            return summary_data
        
        try:
            # Extract sections using markers
            sections = {
                'executive_summary': [
                    r'RESUMEN EJECUTIVO:\s*\n(.*?)(?=\n\s*(?:FECHAS|DECISIÓN|KEYWORDS|$))',
                    r'Resumen Ejecutivo:\s*\n(.*?)(?=\n\s*(?:Fechas|Decisión|Keywords|$))'
                ],
                'important_dates': [
                    r'FECHAS IMPORTANTES:\s*\n(.*?)(?=\n\s*(?:DECISIÓN|KEYWORDS|$))',
                    r'Fechas Importantes:\s*\n(.*?)(?=\n\s*(?:Decisión|Keywords|$))'
                ],
                'decision': [
                    r'DECISIÓN/FALLO:\s*\n(.*?)(?=\n\s*(?:KEYWORDS|$))',
                    r'Decisión/Fallo:\s*\n(.*?)(?=\n\s*(?:Keywords|$))'
                ],
                'keywords': [
                    r'KEYWORDS:\s*\n(.*?)$',
                    r'Keywords:\s*\n(.*?)$',
                    r'PALABRAS CLAVE:\s*\n(.*?)$'
                ]
            }
            
            for field, patterns in sections.items():
                for pattern in patterns:
                    match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        
                        # Clean empty/not found values
                        if self._is_empty_value(value):
                            summary_data[field] = None if field in ['important_dates', 'decision'] else ''
                        else:
                            summary_data[field] = value
                        break
            
            logger.debug(f"Parsed summary sections: {list(summary_data.keys())}")
                    
        except Exception as e:
            logger.error(f"Error parsing summary response: {e}", exc_info=True)
        
        return summary_data
    
    def _is_empty_value(self, value: str) -> bool:
        """Check if extracted value is empty or placeholder."""
        if not value or len(value) < 3:
            return True
        
        empty_patterns = [
            r'^no\s+(se\s+)?(identificaron?|encontraron?|hay)',
            r'^no\s+disponible',
            r'^n/?a\s*$',
            r'^-\s*$',
            r'^pendiente',
        ]
        
        value_lower = value.lower().strip()
        return any(re.match(pattern, value_lower) for pattern in empty_patterns)
    
    def _generate_fallback_summary(self, doc_type: str, legal_area: str) -> Dict:
        """Generate minimal summary when LLM fails or content is invalid."""
        summary_text = f"""RESUMEN EJECUTIVO:
Este es un documento de tipo {doc_type} perteneciente al área legal de {legal_area}. 
El contenido específico no pudo ser procesado completamente.

FECHAS IMPORTANTES:
No se identificaron fechas específicas.

DECISIÓN/FALLO:
Información no disponible.

KEYWORDS:
{doc_type}, {legal_area}, documento legal
"""
        
        return {
            'summary_text': summary_text,
            'executive_summary': f"Documento de tipo {doc_type} en área {legal_area}.",
            'important_dates': None,
            'decision': None,
            'keywords': f"{doc_type}, {legal_area}, documento legal"
        }
