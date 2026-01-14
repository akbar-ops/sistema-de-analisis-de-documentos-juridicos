"""
Hierarchical Document Summarizer Service

Implementa resumen jerárquico "map-reduce" para documentos largos:
1. Divide el documento en chunks manejables
2. Resume cada chunk con Ollama
3. Combina los resúmenes en un resumen final

Simplificado: usa la respuesta del LLM directamente sin parsing complejo.
"""
import logging
import re
from typing import Dict, List, Optional
from dataclasses import dataclass

from apps.core.services.ollama_agent.llm_service import LLMService

logger = logging.getLogger(__name__)


@dataclass
class ChunkSummary:
    """Representa el resumen de un chunk individual"""
    chunk_index: int
    original_length: int
    summary: str


class HierarchicalSummarizer:
    """
    Genera resúmenes jerárquicos de documentos largos usando estrategia map-reduce.
    
    Flujo simplificado:
    1. MAP: Dividir documento → resumir cada chunk
    2. REDUCE: Combinar resúmenes → resumen final
    
    La respuesta del LLM se usa directamente sin parsing de secciones.
    """
    
    MAX_CHUNK_SIZE = 2500
    MAX_COMBINED_SUMMARIES_SIZE = 6000
    MIN_CHUNK_SIZE = 150
    CHUNK_TIMEOUT = 60
    FINAL_TIMEOUT = 300

    
    def __init__(self):
        self.llm_service = LLMService()
        logger.info("HierarchicalSummarizer initialized")
    
    def generate_hierarchical_summary(
        self,
        text: str,
        doc_type_name: str,
        legal_area_name: str,
        legal_subject: Optional[str] = None
    ) -> Dict:
        """Genera un resumen completo del documento."""
        try:
            # Si el documento es corto, usar resumen directo
            if len(text) <= self.MAX_CHUNK_SIZE:
                logger.info(f"Document is short ({len(text)} chars), using direct summary")
                return self._generate_direct_summary(text, doc_type_name, legal_area_name, legal_subject)
            
            logger.info(f"Document is long ({len(text)} chars), using hierarchical summary")
            
            # PASO 1: Dividir en chunks
            chunks = self._split_into_chunks(text)
            logger.info(f"Split document into {len(chunks)} chunks")
            
            # PASO 2: MAP - Resumir cada chunk
            chunk_summaries = self._summarize_chunks(chunks)
            logger.info(f"Generated {len(chunk_summaries)} chunk summaries")
            
            # PASO 3: REDUCE - Combinar resúmenes
            final_summary = self._combine_summaries(
                chunk_summaries, doc_type_name, legal_area_name, legal_subject, text
            )
            
            logger.info("Successfully generated hierarchical summary")
            return final_summary
            
        except Exception as e:
            logger.error(f"Error in hierarchical summarization: {e}", exc_info=True)
            return self._generate_fallback_summary(doc_type_name, legal_area_name)
    
    def _split_into_chunks(self, text: str) -> List[str]:
        """Divide el texto en chunks respetando límites semánticos."""
        chunks = []
        current_chunk = ""
        
        paragraphs = re.split(r'\n\s*\n', text)
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if len(current_chunk) + len(para) + 2 <= self.MAX_CHUNK_SIZE:
                current_chunk += ("\n\n" if current_chunk else "") + para
            else:
                if len(current_chunk) >= self.MIN_CHUNK_SIZE:
                    chunks.append(current_chunk)
                
                if len(para) > self.MAX_CHUNK_SIZE:
                    sentences = re.split(r'(?<=[.!?])\s+', para)
                    current_chunk = ""
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) + 1 <= self.MAX_CHUNK_SIZE:
                            current_chunk += (" " if current_chunk else "") + sentence
                        else:
                            if len(current_chunk) >= self.MIN_CHUNK_SIZE:
                                chunks.append(current_chunk)
                            current_chunk = sentence
                else:
                    current_chunk = para
        
        if len(current_chunk) >= self.MIN_CHUNK_SIZE:
            chunks.append(current_chunk)
        
        if not chunks:
            for i in range(0, len(text), self.MAX_CHUNK_SIZE):
                chunk = text[i:i + self.MAX_CHUNK_SIZE]
                if len(chunk) >= self.MIN_CHUNK_SIZE:
                    chunks.append(chunk)
        
        return chunks
    
    def _summarize_chunks(self, chunks: List[str]) -> List[ChunkSummary]:
        """Resume cada chunk individualmente."""
        chunk_summaries = []
        
        for idx, chunk in enumerate(chunks):
            logger.info(f"Summarizing chunk {idx + 1}/{len(chunks)} ({len(chunk)} chars)")
            
            try:
                prompt = f"""Resume esta parte {idx + 1}/{len(chunks)} del documento legal en 2-3 oraciones.
Incluye: hechos principales, nombres, fechas, decisiones si las hay.

Texto:
{chunk}

Resumen conciso:"""

                response = self.llm_service.generate_response(
                    prompt,
                    timeout=self.CHUNK_TIMEOUT,
                    task_type="chunk_summary"
                )
                
                chunk_summaries.append(ChunkSummary(
                    chunk_index=idx + 1,
                    original_length=len(chunk),
                    summary=response.strip() if response else chunk[:300] + "..."
                ))
            except Exception as e:
                logger.error(f"Error summarizing chunk {idx + 1}: {e}")
                chunk_summaries.append(ChunkSummary(
                    chunk_index=idx + 1,
                    original_length=len(chunk),
                    summary=chunk[:300] + "..."
                ))
        
        return chunk_summaries
    
    def _combine_summaries(
        self,
        chunk_summaries: List[ChunkSummary],
        doc_type_name: str,
        legal_area_name: str,
        legal_subject: Optional[str],
        original_text: str
    ) -> Dict:
        """Combina los resúmenes de chunks en un resumen final estructurado."""
        
        # Construir texto combinado
        parts = [f"Parte {cs.chunk_index}: {cs.summary}" for cs in chunk_summaries]
        combined_text = "\n".join(parts)
        
        if len(combined_text) > self.MAX_COMBINED_SUMMARIES_SIZE:
            combined_text = combined_text[:self.MAX_COMBINED_SUMMARIES_SIZE]
        
        subject_info = f", Materia: {legal_subject}" if legal_subject else ""
        
        # Prompt simplificado y directo para modelos pequeños
        prompt = f"""Analiza este documento legal y genera un resumen con EXACTAMENTE el formato dado:

---
Documento: {doc_type_name} ({legal_area_name}{subject_info})

Contenido:
{combined_text}
---
FORMATO

RESUMEN EJECUTIVO:
[Resumen de 3 parrafos del contenido, que debe mencionar entidades o personas involucradas (demandado, demandante) y contexto entero entendible]

FECHAS IMPORTANTES:
[Lista con guiones, ej: - 15/03/2020: descripción del evento]

DECISIÓN/FALLO:
[Qué se decidió: fundada/infundada/improcedente y consecuencias]

KEYWORDS:
[8-12 términos separados por comas]


NO INCLUYAS NADA MÁS A PARTE DEL RESUMEN EJECUTIVO, FECHAS IMPORTANTES, DECISIÓN/FALLO Y KEYWORDS
"""

        response = self.llm_service.generate_response(
            prompt,
            timeout=self.FINAL_TIMEOUT,
            task_type="final_summary"
        )
        
        if not response:
            return self._generate_fallback_summary(doc_type_name, legal_area_name)
        
        # Parsear la respuesta estructurada del LLM
        summary_data = self._parse_structured_response(response)
        summary_data['summary_text'] = response.strip()
        
        return summary_data
    
    def _generate_direct_summary(
        self,
        text: str,
        doc_type_name: str,
        legal_area_name: str,
        legal_subject: Optional[str] = None
    ) -> Dict:
        """Genera resumen directo estructurado para documentos cortos."""
        subject_info = f", Materia: {legal_subject}" if legal_subject else ""
        
        # Prompt simplificado y directo para modelos pequeños
        prompt = f"""Analiza este documento legal y genera un resumen con EXACTAMENTE el formato dado:

---
Documento: {doc_type_name} ({legal_area_name}{subject_info})

Contenido:
{text}
---
FORMATO

RESUMEN EJECUTIVO:
[Resumen de 3 parrafos del contenido, que debe mencionar entidades o personas involucradas (demandado, demandante) y contexto entero entendible]

FECHAS IMPORTANTES:
[Lista con guiones, ej: - 15/03/2020: descripción del evento]

DECISIÓN/FALLO:
[Qué se decidió: fundada/infundada/improcedente y consecuencias]

KEYWORDS:
[8-12 términos separados por comas]

NO INCLUYAS NADA MÁS A PARTE DEL RESUMEN EJECUTIVO, FECHAS IMPORTANTES, DECISIÓN/FALLO Y KEYWORDS
"""

        response = self.llm_service.generate_response(
            prompt,
            timeout=self.FINAL_TIMEOUT,
            task_type="final_summary"
        )
        
        if not response:
            return self._generate_fallback_summary(doc_type_name, legal_area_name)
        
        # Parsear la respuesta estructurada del LLM
        summary_data = self._parse_structured_response(response)
        summary_data['summary_text'] = response.strip()
        
        return summary_data
    
    def _extract_dates_regex(self, text: str) -> List[str]:
        """Extrae fechas del texto usando regex."""
        dates = set()
        
        # Patrón: DD de mes de YYYY
        pattern1 = r'(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de(?:l)?\s+(\d{4})'
        for match in re.finditer(pattern1, text, re.IGNORECASE):
            day, month, year = match.groups()
            month_num = {
                'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
                'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
                'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
            }.get(month.lower(), '01')
            dates.add(f"{day.zfill(2)}/{month_num}/{year}")
        
        # Patrón: DD/MM/YYYY o DD-MM-YYYY
        pattern2 = r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})'
        for match in re.finditer(pattern2, text):
            day, month, year = match.groups()
            if 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
                dates.add(f"{day.zfill(2)}/{month.zfill(2)}/{year}")
        
        return sorted(list(dates))[:10]
    
    def _parse_structured_response(self, response: str) -> Dict:
        """
        Parsea la respuesta estructurada del LLM.
        Maneja variaciones comunes en el formato de respuesta.
        """
        summary_data = {
            'executive_summary': '',
            'important_dates': None,
            'decision': None,
            'keywords': ''
        }
        
        if not response:
            return summary_data
        
        try:
            # Patrones más flexibles para extraer cada sección
            # Manejan mayúsculas, minúsculas y variaciones comunes
            sections = {
                'executive_summary': [
                    r'RESUMEN\s*EJECUTIVO[:\s]*\n?(.*?)(?=\n\s*(?:FECHAS|DECISIÓN|DECISION|KEYWORDS|PALABRAS|Fechas|Decisión|Decision|Keywords|Resolución|$))',
                ],
                'important_dates': [
                    r'FECHAS\s*IMPORTANTES[:\s]*\n?(.*?)(?=\n\s*(?:DECISIÓN|DECISION|KEYWORDS|PALABRAS|Decisión|Decision|Keywords|Resolución|$))',
                    r'Fechas\s*importantes[:\s]*\n?(.*?)(?=\n\s*(?:DECISIÓN|DECISION|KEYWORDS|PALABRAS|Decisión|Decision|Keywords|Resolución|$))',
                ],
                'decision': [
                    r'DECISIÓN[/\s]*FALLO[:\s]*\n?(.*?)(?=\n\s*(?:KEYWORDS|PALABRAS|Keywords|$))',
                    r'DECISION[/\s]*FALLO[:\s]*\n?(.*?)(?=\n\s*(?:KEYWORDS|PALABRAS|Keywords|$))',
                    r'Decisión[/\s]*[Ff]allo[:\s]*\n?(.*?)(?=\n\s*(?:KEYWORDS|PALABRAS|Keywords|$))',
                    r'Resolución[:\s]*\n?(.*?)(?=\n\s*(?:KEYWORDS|PALABRAS|Keywords|Nombres|$))',
                ],
                'keywords': [
                    r'KEYWORDS[:\s]*\n?(.*?)$',
                    r'Keywords[:\s]*\n?(.*?)$',
                    r'PALABRAS\s*CLAVE[:\s]*\n?(.*?)$',
                    r'Palabras\s*clave[:\s]*\n?(.*?)$',
                ]
            }
            
            for field, patterns in sections.items():
                for pattern in patterns:
                    match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        
                        # Limpiar valores vacíos o placeholder
                        if self._is_empty_value(value):
                            summary_data[field] = None if field in ['important_dates', 'decision'] else ''
                        else:
                            # Limpiar el valor
                            value = self._clean_section_value(value, field)
                            summary_data[field] = value
                        break
            
            # Si no se extrajo executive_summary, usar todo el texto antes de FECHAS
            if not summary_data['executive_summary']:
                # Buscar todo el contenido hasta la primera sección conocida
                first_section = re.search(
                    r'^(.*?)(?=\n\s*(?:FECHAS|DECISIÓN|DECISION|KEYWORDS|PALABRAS|Fechas|Decisión|Resolución))',
                    response, re.DOTALL | re.IGNORECASE
                )
                if first_section:
                    summary_data['executive_summary'] = first_section.group(1).strip()
                else:
                    # Usar los primeros párrafos como resumen
                    paragraphs = response.split('\n\n')
                    summary_data['executive_summary'] = '\n\n'.join(paragraphs[:3]).strip()
            
            logger.debug(f"Parsed summary sections: {[k for k, v in summary_data.items() if v]}")
                    
        except Exception as e:
            logger.error(f"Error parsing summary response: {e}", exc_info=True)
            # En caso de error, usar la respuesta completa como resumen
            summary_data['executive_summary'] = response.strip()[:2000]
        
        return summary_data
    
    def _clean_section_value(self, value: str, field: str) -> str:
        """Limpia el valor de una sección extraída."""
        if not value:
            return value
        
        # Remover líneas vacías múltiples
        value = re.sub(r'\n{3,}', '\n\n', value)
        
        # Para keywords, limpiar el formato
        if field == 'keywords':
            # Remover bullets y guiones al inicio de líneas
            value = re.sub(r'^[-•*]\s*', '', value, flags=re.MULTILINE)
            # Convertir saltos de línea en comas
            value = re.sub(r'\n+', ', ', value)
            # Limpiar comas múltiples
            value = re.sub(r',\s*,', ',', value)
            value = value.strip(' ,')
        
        return value.strip()
    
    def _is_empty_value(self, value: str) -> bool:
        """Verifica si un valor extraído está vacío o es placeholder."""
        if not value or len(value) < 3:
            return True
        
        empty_patterns = [
            r'^no\s+(se\s+)?(identificaron?|encontraron?|hay)',
            r'^no\s+disponible',
            r'^n/?a\s*$',
            r'^-\s*$',
            r'^pendiente',
            r'^\[.*\]$',  # Placeholder como [texto]
        ]
        
        value_lower = value.lower().strip()
        return any(re.match(pattern, value_lower) for pattern in empty_patterns)
    
    def _extract_keywords_regex(self, text: str, doc_type: str, legal_area: str) -> List[str]:
        """Extrae keywords del texto usando regex y términos legales."""
        keywords = set()
        text_lower = text.lower()
        
        # Agregar tipo y área
        keywords.add(doc_type.lower())
        keywords.add(legal_area.lower())
        
        # Términos legales comunes
        legal_terms = [
            'demanda', 'sentencia', 'resolución', 'apelación', 'recurso',
            'demandante', 'demandado', 'fiscal', 'juez',
            'laboral', 'civil', 'penal', 'administrativo', 'constitucional',
            'despido', 'reincorporación', 'indemnización',
            'pensión', 'bonificación', 'remuneración',
            'nulidad', 'infundada', 'fundada', 'improcedente',
            'municipalidad', 'gobierno', 'ministerio'
        ]
        
        for term in legal_terms:
            if term in text_lower:
                keywords.add(term)
        
        # Buscar decretos y leyes
        decree_pattern = r'decreto\s+(?:legislativo|supremo|de urgencia)?\s*n[°º]?\s*[\d\-]+'
        for match in re.finditer(decree_pattern, text_lower):
            keywords.add(match.group(0).strip())
        
        # Buscar leyes
        law_pattern = r'ley\s+n[°º]?\s*[\d]+'
        for match in re.finditer(law_pattern, text_lower):
            keywords.add(match.group(0).strip())
        
        return list(keywords)[:15]
    
    def _generate_fallback_summary(self, doc_type: str, legal_area: str) -> Dict:
        """Genera resumen mínimo cuando falla el proceso."""
        executive_summary = f"Documento de tipo {doc_type} en área {legal_area}. El contenido no pudo ser procesado completamente."
        keywords = f"{doc_type}, {legal_area}, documento legal"
        
        summary_text = f"""RESUMEN EJECUTIVO:
{executive_summary}

FECHAS IMPORTANTES:
No se identificaron fechas específicas

DECISION O FALLO:
No disponible

KEYWORDS:
{keywords}"""
        
        return {
            'summary_text': summary_text,
            'executive_summary': executive_summary,
            'important_dates': None,
            'decision': None,
            'keywords': keywords
        }
