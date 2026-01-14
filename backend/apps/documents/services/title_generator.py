"""
Title Generator Service

Generates specific, detailed titles for legal documents using dedicated LLM analysis.
Operates independently from metadata extraction for better quality and focus.
"""
import re
import logging
from typing import Optional

from apps.core.services.ollama_agent.llm_service import LLMService

logger = logging.getLogger(__name__)


class TitleGenerator:
    """
    Generates specific, detailed titles for legal documents.
    
    Uses a dedicated LLM call with highly focused prompt to create titles
    that include: specific facts + parties + decision/ruling.
    
    Format: [Specific Matter] - [Parties] - [Decision]
    Example: "Robo Agravado con Arma - García vs MP - Condena 8 años"
    """
    
    def __init__(self):
        self.llm_service = LLMService()
    
    def generate_title(self, text: str, doc_type: Optional[str] = None,
                      legal_area: Optional[str] = None, legal_subject: Optional[str] = None,
                      partes: Optional[str] = None, decision: Optional[str] = None) -> str:
        """
        Generate specific title for legal document.
        
        Args:
            text: Full or sample document text
            doc_type: Document type (Sentencia, Auto, etc.)
            legal_area: Legal area (Penal, Civil, etc.)
            legal_subject: Specific legal subject/matter
            partes: Parties involved in the case
            decision: Decision or ruling
            
        Returns:
            Specific title with format: [Matter] - [Parties] - [Decision]
            Falls back to generic title if LLM fails.
        """
        try:
            # Try LLM generation first
            llm_title = self._generate_with_llm(text, doc_type, legal_area, legal_subject, partes, decision)
            
            if llm_title and llm_title != 'Documento Legal' and len(llm_title) > 10:
                logger.info(f"✓ LLM generated title: {llm_title}")
                return llm_title
            
            # Fallback to programmatic generation
            logger.warning("LLM title generation failed or returned generic title, using fallback")
            return self._generate_fallback(doc_type, legal_area, legal_subject, partes, decision)
            
        except Exception as e:
            logger.error(f"Error generating title: {e}", exc_info=True)
            return self._generate_fallback(doc_type, legal_area, legal_subject, partes, decision)
    
    def _generate_with_llm(self, text: str, doc_type: Optional[str],
                           legal_area: Optional[str], legal_subject: Optional[str],
                           partes: Optional[str], decision: Optional[str]) -> Optional[str]:
        """
        Generate title using dedicated LLM call with ultra-specific prompt.
        """
        try:
            # Build context from metadata
            context_parts = []
            if doc_type and doc_type != 'Otros':
                context_parts.append(f"Tipo de documento: {doc_type}")
            if legal_area and legal_area != 'Otros':
                context_parts.append(f"Área legal: {legal_area}")
            if legal_subject:
                context_parts.append(f"Materia específica: {legal_subject}")
            if partes:
                context_parts.append(f"Partes del proceso: {partes}")
            if decision:
                context_parts.append(f"Decisión/Fallo: {decision}")
            
            context = "\n".join(context_parts) if context_parts else "No hay contexto previo disponible"
            
            # Truncate text if too long - SHORTER for speed
            text_sample = text[:1500] if len(text) > 1500 else text
            
            # Build OPTIMIZED prompt (shorter = faster)
            prompt = f"""Eres experto legal. Crea UN TÍTULO ESPECÍFICO (máximo 30 palabras).

CONTEXTO:
{context}

FORMATO: [Materia Específica] - [Partes] - [Decisión]

EJEMPLOS BUENOS:
"Robo Agravado con Arma - García vs MP - Condena 8 años"
"Despido Arbitrario Represalia Sindical - López vs ABC - Fundada"
"Divorcio Violencia Familiar - Martínez vs Rodríguez - Fundada"
"Homicidio Calificado Alevosía - MP vs Pérez - 25 años"

REGLAS:
✓ Máximo 30 palabras
✓ Materia específica (con agravantes/detalles)
✓ Apellidos de partes (no nombres completos)
✓ Decisión breve
✓ Sin números de expediente ni fechas
✓ Sin markdown ni asteriscos

DOCUMENTO:
{text_sample}

TÍTULO:"""

            # Call LLM with title_generation task type
            response = self.llm_service.generate_response(
                prompt,
                timeout=1800,  # Reduced timeout for faster generation
                task_type="title_generation"
            )
            
            if not response or len(response) < 10:
                return None
            
            # Clean response
            title = self._clean_title(response)
            
            # Validate title
            if not self._validate_title(title):
                logger.warning(f"Generated title failed validation: '{title}'")
                return None
            
            return title
            
        except Exception as e:
            logger.error(f"Error in LLM title generation: {e}", exc_info=True)
            return None
    
    def _clean_title(self, response: str) -> str:
        """Clean LLM response to extract clean title."""
        title = response.strip()
        
        # Remove quotes
        title = title.strip('"\'`')
        
        # Remove common prefixes
        title = re.sub(r'^\s*T[IÍ]TULO:\s*', '', title, flags=re.IGNORECASE)
        title = re.sub(r'^\s*TITULO:\s*', '', title, flags=re.IGNORECASE)
        title = re.sub(r'^\s*T[ÍI]tulo:\s*', '', title, flags=re.IGNORECASE)
        
        # Remove markdown formatting
        title = re.sub(r'\*\*', '', title)  # Bold
        title = re.sub(r'^\*+\s*', '', title)  # List markers
        title = re.sub(r'\s*\*+$', '', title)
        
        # Normalize whitespace
        title = re.sub(r'\s+', ' ', title)
        title = title.strip()
        
        # Truncate if too long (max 30 words)
        # words = title.split()
        # if len(words) > 30:
        #     title = ' '.join(words[:30]) + '...'
        # if len(words) > 20:
        #     title = ' '.join(words[:20])
        
        if len(title) > 200:
            title = title[:197] + "..."
        
        return title
    
    def _validate_title(self, title: str) -> bool:
        """
        Validate that title meets quality standards.
        
        Returns True if title is acceptable, False otherwise.
        """
        if not title or len(title) < 10:
            return False
        
        # Check for generic/invalid titles
        invalid_titles = [
            'documento legal',
            'sin título',
            'sin titulo',
            'n/a',
            'no disponible',
            'documento judicial',
            'sentencia',
            'auto',
            'resolución',
            'resolucion'
        ]
        
        title_lower = title.lower()
        if title_lower in invalid_titles:
            return False
        
        # Should have at least 3 words for specificity
        words = title.split()
        if len(words) < 3:
            return False
        
        return True
    
    def _generate_fallback(self, doc_type: Optional[str], legal_area: Optional[str],
                          legal_subject: Optional[str], partes: Optional[str],
                          decision: Optional[str]) -> str:
        """
        Generate title programmatically when LLM fails.
        
        This is a fallback method that constructs title from available metadata.
        """
        parts = []
        
        # Add document type if available
        if doc_type and doc_type != 'Otros':
            parts.append(doc_type)
        
        # Add legal subject (most important)
        if legal_subject:
            # Limit to max 10 words for speed
            subject_words = legal_subject.split()
            if len(subject_words) > 10:
                legal_subject = ' '.join(subject_words[:10])
            parts.append(f"- {legal_subject}" if parts else legal_subject)
        elif legal_area and legal_area != 'Otros':
            # Only use area if no subject
            parts.append(f"- Área {legal_area}" if parts else f"Área {legal_area}")
        
        # Add simplified partes if available
        if partes:
            partes_simplified = self._simplify_partes(partes)
            if partes_simplified:
                parts.append(f"- {partes_simplified}")
        
        # Add decision if available
        if decision:
            # Shorten decision if too long
            decision_short = decision if len(decision) < 30 else decision[:27] + "..."
            parts.append(f"- {decision_short}")
        
        if not parts:
            return "Documento Legal Sin Clasificar"
        
        title = ' '.join(parts)
        
        # Ensure max 30 words
        title_words = title.split()
        if len(title_words) > 30:
            title = ' '.join(title_words[:30]) + '...'
        
        # Ensure reasonable character length
        if len(title) > 250:
            title = title[:247] + "..."
        
        return title
    
    def _simplify_partes(self, partes: str) -> str:
        """
        Simplify partes string to extract main surnames.
        
        Examples:
        - "Demandante: Juan García López / Demandado: Pedro Martínez" → "García vs Martínez"
        - "Agraviado: María Rodríguez / Imputado: Carlos Sánchez" → "Rodríguez vs Sánchez"
        - "Ministerio Público vs José Pérez Torres" → "MP vs Pérez"
        """
        try:
            partes_lower = partes.lower()
            
            # Extract first party
            first_party = None
            if 'ministerio público' in partes_lower or 'mp' in partes_lower:
                first_party = "MP"
            else:
                # Try to extract name after first role keyword
                for keyword in ['demandante:', 'agraviado:', 'demandado:', 'imputado:']:
                    if keyword in partes_lower:
                        idx = partes_lower.index(keyword)
                        name_part = partes[idx + len(keyword):].split('/')[0].strip()
                        words = name_part.split()
                        if len(words) >= 2:
                            first_party = words[1]  # First surname
                        elif len(words) == 1:
                            first_party = words[0]
                        break
            
            # Extract second party
            second_party = None
            if ' vs ' in partes or ' vs. ' in partes or ' contra ' in partes:
                sep = ' vs ' if ' vs ' in partes else (' vs. ' if ' vs. ' in partes else ' contra ')
                second_part = partes.split(sep)[1].strip() if sep in partes else ''
                words = second_part.split()
                if len(words) >= 2:
                    second_party = words[1]
                elif len(words) == 1:
                    second_party = words[0]
            elif '/' in partes:
                second_part = partes.split('/')[1].strip()
                for keyword in ['demandado:', 'imputado:', 'demandante:', 'agraviado:']:
                    second_part = second_part.replace(keyword, '').replace(keyword.title(), '').strip()
                words = second_part.split()
                if len(words) >= 2:
                    second_party = words[1]
                elif len(words) == 1:
                    second_party = words[0]
            
            # Build simplified string
            if first_party and second_party:
                return f"{first_party} vs {second_party}"
            elif first_party:
                return first_party
            elif second_party:
                return second_party
            else:
                return partes[:30] if len(partes) > 30 else partes
                
        except Exception as e:
            logger.warning(f"Error simplifying partes '{partes}': {e}")
            return partes[:30] if len(partes) > 30 else partes
