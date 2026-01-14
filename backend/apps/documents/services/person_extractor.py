"""
Person Extractor Service

Extracts involved persons and entities from legal documents with their roles.
"""
import re
import logging
from typing import Dict, List
from django.db import transaction

from apps.core.services.ollama_agent.llm_service import LLMService
from apps.documents.models import Person, DocumentPerson, PersonRole
from apps.documents.services.constants import LLM_TIMEOUT_PERSONS

logger = logging.getLogger(__name__)


class PersonExtractor:
    """
    Extracts all involved persons/entities from legal documents with role classification.
    
    Supported roles:
    - Demandante (Plaintiff)
    - Demandado (Defendant)
    - Juez (Judge)
    - Fiscal (Prosecutor)
    - Abogado (Lawyer)
    - Testigo (Witness)
    - Perito (Expert)
    - Tercero (Third Party)
    - Otro (Other)
    """
    
    MAX_TEXT_LENGTH = 8000  # Increased from 5000 to capture more context
    NAME_MIN_LENGTH = 3
    NAME_MAX_LENGTH = 255
    
    # Common patterns to skip
    SKIP_PATTERNS = [
        r'^no\s+(aplica|identificado|corresponde|hay)',
        r'^ninguno',
        r'^n/?a\s*$',
        r'^-\s*$',
    ]
    
    def __init__(self):
        self.llm_service = LLMService()
    
    def extract_and_link_persons(self, text: str, document) -> Dict[str, List[str]]:
        """
        Extract persons from document and create database links.
        
        Args:
            text: Full document text
            document: Document model instance
            
        Returns:
            Dictionary with persons grouped by role:
            {
                'demandante': ['Name 1', 'Name 2'],
                'demandado': ['Name 3'],
                'juez': ['Name 4'],
                ...
            }
        """
        try:
            logger.info(f"Starting person extraction for document {document.document_id}")
            
            text_sample = self._get_text_sample(text)
            logger.debug(f"Text sample length: {len(text_sample)} chars")
            
            prompt = self._build_extraction_prompt(text_sample)
            
            # Get LLM response
            logger.info("Requesting LLM person extraction...")
            raw_response = self.llm_service.generate_response(
                prompt,
                timeout=LLM_TIMEOUT_PERSONS,
                task_type="person_extraction"  # Específico para extracción de personas
            )
            
            logger.info(f"LLM response received ({len(raw_response)} chars)")
            logger.debug(f"LLM persons response:\n{raw_response}")
            
            # Parse response
            persons_data = self._parse_persons_response(raw_response)
            
            total_persons = sum(len(names) for names in persons_data.values())
            logger.info(f"✅ LLM extracted {total_persons} persons")
            
            # Log what was found
            for role, names in persons_data.items():
                if names:
                    logger.info(f"  {role}: {', '.join(names)}")
            
            # Fallback if no persons found
            if total_persons == 0:
                logger.warning("⚠️ No persons detected from LLM, trying regex fallback")
                persons_data = self._extract_with_regex(text_sample)
                total_fallback = sum(len(names) for names in persons_data.values())
                
                if total_fallback > 0:
                    logger.info(f"✅ Regex fallback found {total_fallback} persons")
                    for role, names in persons_data.items():
                        if names:
                            logger.info(f"  {role}: {', '.join(names)}")
                else:
                    logger.warning("⚠️ No persons found even with regex fallback")
            
            # Create database entries and links
            self._create_person_links(persons_data, document)
            
            return persons_data
            
        except Exception as e:
            logger.error(f"❌ Error extracting persons: {e}", exc_info=True)
            return self._get_empty_persons_dict()
    
    def _get_text_sample(self, text: str) -> str:
        """Extract representative sample from document text with focus on person mentions."""
        if len(text) <= self.MAX_TEXT_LENGTH:
            return text
        
        # Strategy: Take beginning (parties), middle (body), and end (signatures)
        # This captures where persons are most commonly mentioned
        part_size = self.MAX_TEXT_LENGTH // 3
        
        first_part = text[:part_size]
        middle_start = len(text) // 2 - part_size // 2
        middle_part = text[middle_start:middle_start + part_size]
        last_part = text[-part_size:]
        
        return f"{first_part}\n\n[...]\n\n{middle_part}\n\n[...]\n\n{last_part}"
    
    def _build_extraction_prompt(self, text: str) -> str:
        """Build structured prompt for person extraction."""
        
        prompt = f"""Analiza este documento legal y extrae TODAS las personas mencionadas con sus roles.

IMPORTANTE: Busca personas en TODO el documento, especialmente en:
- Encabezados (partes del proceso, demandante, demandado)
- Cuerpo del documento (jueces, fiscales, abogados, testigos)
- Firmas y suscripciones al final

Responde en este formato EXACTO (cada sección en una línea):

DEMANDANTE: [nombres separados por ; o "No aplica"]
DEMANDADO: [nombres separados por ; o "No aplica"]
JUEZ: [nombres separados por ; o "No identificado"]
FISCAL: [nombres separados por ; o "No aplica"]
ABOGADO: [nombres separados por ; o "No aplica"]
TESTIGO: [nombres separados por ; o "No aplica"]
PERITO: [nombres separados por ; o "No aplica"]
TERCERO: [nombres separados por ; o "No aplica"]
OTRO: [nombres separados por ; o "Ninguno"]

REGLAS:
1. Extrae SOLO nombres reales del documento
2. Usa nombres completos
3. Separa múltiples nombres con punto y coma (;)
4. Ignora texto entre paréntesis
5. Si no encuentras personas para un rol, escribe "No aplica"

DOCUMENTO:
{text}

RESPUESTA:"""
        
        return prompt
    
    def _parse_persons_response(self, response: str) -> Dict[str, List[str]]:
        """Parse persons from LLM response."""
        persons_data = self._get_empty_persons_dict()
        
        if not response:
            return persons_data
        
        try:
            # More flexible patterns - match both singular and plural forms
            role_patterns = {
                'demandante': [
                    r'DEMANDANTE\s*(?:\(S\))?\s*:\s*(.+?)(?=\n\s*[A-Z]+\s*:|$)',
                    r'(?:^|\n)DEMANDANTE[S]?[:\s]+(.+?)(?=\n|$)'
                ],
                'demandado': [
                    r'DEMANDADO\s*(?:\(S\))?\s*:\s*(.+?)(?=\n\s*[A-Z]+\s*:|$)',
                    r'(?:^|\n)DEMANDADO[S]?[:\s]+(.+?)(?=\n|$)'
                ],
                'juez': [
                    r'JUEZ\s*(?:\(CES\))?\s*:\s*(.+?)(?=\n\s*[A-Z]+\s*:|$)',
                    r'(?:^|\n)JU[EÉ]Z(?:CES)?[:\s]+(.+?)(?=\n|$)'
                ],
                'fiscal': [
                    r'FISCAL\s*(?:\(ES\))?\s*:\s*(.+?)(?=\n\s*[A-Z]+\s*:|$)',
                    r'(?:^|\n)FISCAL(?:ES)?[:\s]+(.+?)(?=\n|$)'
                ],
                'abogado': [
                    r'ABOGADO\s*(?:\(S\))?\s*:\s*(.+?)(?=\n\s*[A-Z]+\s*:|$)',
                    r'(?:^|\n)ABOGADO[S]?[:\s]+(.+?)(?=\n|$)'
                ],
                'testigo': [
                    r'TESTIGO\s*(?:\(S\))?\s*:\s*(.+?)(?=\n\s*[A-Z]+\s*:|$)',
                    r'(?:^|\n)TESTIGO[S]?[:\s]+(.+?)(?=\n|$)'
                ],
                'perito': [
                    r'PERITO\s*(?:\(S\))?\s*:\s*(.+?)(?=\n\s*[A-Z]+\s*:|$)',
                    r'(?:^|\n)PERITO[S]?[:\s]+(.+?)(?=\n|$)'
                ],
                'tercero': [
                    r'TERCERO\s*(?:\(S\))?\s*:\s*(.+?)(?=\n\s*[A-Z]+\s*:|$)',
                    r'(?:^|\n)TERCERO[S]?[:\s]+(.+?)(?=\n|$)'
                ],
                'otro': [
                    r'OTRO\s*(?:\(S\))?\s*:\s*(.+?)(?=\n\s*[A-Z]+\s*:|$)',
                    r'(?:^|\n)OTRO[S]?[:\s]+(.+?)(?=\n|$)'
                ],
            }
            
            for role, patterns in role_patterns.items():
                for pattern in patterns:
                    match = re.search(pattern, response, re.DOTALL | re.IGNORECASE | re.MULTILINE)
                    if match:
                        raw_text = match.group(1).strip()
                        names = self._parse_names_list(raw_text)
                        if names:
                            persons_data[role].extend(names)
                            logger.debug(f"Found {len(names)} person(s) for role '{role}': {names}")
            
            # Remove duplicates for each role
            for role in persons_data:
                persons_data[role] = list(set(persons_data[role]))
                    
        except Exception as e:
            logger.error(f"Error parsing persons response: {e}", exc_info=True)
        
        return persons_data
    
    def _parse_names_list(self, text: str) -> List[str]:
        """Parse list of names from text."""
        if not text or self._is_empty_value(text):
            return []
        
        # Split by common separators
        separators = [';', ',', ' y ', ' Y ', '\n']
        names = [text]
        
        for sep in separators:
            new_names = []
            for name in names:
                new_names.extend(name.split(sep))
            names = new_names
        
        # Clean and validate names
        cleaned_names = []
        for name in names:
            name = name.strip()
            name = re.sub(r'\([^)]*\)', '', name)  # Remove parentheses
            name = re.sub(r'\s+', ' ', name).strip()
            
            if self._is_valid_name(name):
                cleaned_names.append(name.upper())
        
        return cleaned_names
    
    def _is_empty_value(self, value: str) -> bool:
        """Check if value is empty or placeholder."""
        if not value or len(value) < self.NAME_MIN_LENGTH:
            return True
        
        value_lower = value.lower().strip()
        return any(re.match(pattern, value_lower) for pattern in self.SKIP_PATTERNS)
    
    def _is_valid_name(self, name: str) -> bool:
        """Validate person/entity name."""
        if not name or len(name) < self.NAME_MIN_LENGTH:
            return False
        
        if len(name) > self.NAME_MAX_LENGTH:
            return False
        
        # Skip if matches empty patterns
        if self._is_empty_value(name):
            return False
        
        # Must contain at least one letter
        if not re.search(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]', name):
            return False
        
        return True
    
    def _extract_with_regex(self, text: str) -> Dict[str, List[str]]:
        """Fallback: Extract persons using regex patterns."""
        persons_data = self._get_empty_persons_dict()
        
        try:
            # More comprehensive patterns for each role
            extraction_patterns = {
                'demandante': [
                    r'DEMANDANTE\s*:\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s]{4,100})(?:\n|$)',
                    r'demandante\s*:\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s]{4,100})(?:\n|$)',
                    r'Demandante\s*:\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s]{4,100})(?:\n|$)',
                ],
                'demandado': [
                    r'DEMANDAD[OA]\s*:\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s]{4,100})(?:\n|$)',
                    r'demandad[oa]\s*:\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s]{4,100})(?:\n|$)',
                    r'Demandad[oa]\s*:\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s]{4,100})(?:\n|$)',
                ],
                'juez': [
                    r'JUEZ\s*:\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s]{4,100})(?:\n|$)',
                    r'Juez\s*:\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s]{4,100})(?:\n|$)',
                    r'(?:Señor|Señora)\s+Ju[eé]z\s*:\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s]{4,100})(?:\n|$)',
                    r'JUEZ SUPERIOR\s*:\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s]{4,100})(?:\n|$)',
                ],
                'fiscal': [
                    r'FISCAL\s*:\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s]{4,100})(?:\n|$)',
                    r'Fiscal\s*:\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s]{4,100})(?:\n|$)',
                    r'FISCAL PROVINCIAL\s*:\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s]{4,100})(?:\n|$)',
                ],
                'abogado': [
                    r'ABOGADO\s*:\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s]{4,100})(?:\n|$)',
                    r'Abogado\s*:\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s]{4,100})(?:\n|$)',
                    r'PATROCINADOR\s*:\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s]{4,100})(?:\n|$)',
                ],
            }
            
            for role, patterns in extraction_patterns.items():
                for pattern in patterns:
                    matches = re.findall(pattern, text)
                    for match in matches:
                        # Clean the name
                        name = match.strip()
                        # Remove common noise
                        name = re.sub(r'\s*\([^)]*\)', '', name)  # Remove parentheses
                        name = re.sub(r'\s*\[[^\]]*\]', '', name)  # Remove brackets
                        name = re.sub(r'\s+', ' ', name).strip()
                        
                        if self._is_valid_name(name):
                            persons_data[role].append(name.upper())
            
            # Remove duplicates
            for role in persons_data:
                persons_data[role] = list(set(persons_data[role]))
            
            total = sum(len(v) for v in persons_data.values())
            logger.info(f"Regex extraction found: {total} persons across all roles")
            
            # Log what was found
            for role, names in persons_data.items():
                if names:
                    logger.debug(f"  {role}: {names}")
                    
        except Exception as e:
            logger.error(f"Error in regex extraction: {e}", exc_info=True)
        
        return persons_data
    
    def _create_person_links(self, persons_data: Dict[str, List[str]], document):
        """Create Person and DocumentPerson entries in database."""
        try:
            with transaction.atomic():
                for role_name, names in persons_data.items():
                    # Map role name to PersonRole enum
                    role_enum = self._map_role_to_enum(role_name)
                    
                    for name in names:
                        # Get or create Person
                        person, created = Person.objects.get_or_create(
                            name=name
                        )
                        
                        if created:
                            logger.debug(f"Created new person: {name}")
                        
                        # Create DocumentPerson link
                        DocumentPerson.objects.get_or_create(
                            document=document,
                            person=person,
                            role=role_enum
                        )
                
                total_links = sum(len(names) for names in persons_data.values())
                logger.info(f"Created/updated {total_links} person links for document")
                        
        except Exception as e:
            logger.error(f"Error creating person links: {e}", exc_info=True)
    
    def _map_role_to_enum(self, role_name: str) -> str:
        """Map Spanish role name to PersonRole enum value."""
        role_mapping = {
            'demandante': PersonRole.PLAINTIFF,
            'demandado': PersonRole.DEFENDANT,
            'juez': PersonRole.JUDGE,
            'fiscal': PersonRole.PROSECUTOR,
            'abogado': PersonRole.LAWYER,
            'testigo': PersonRole.WITNESS,
            'perito': PersonRole.EXPERT,
            'tercero': PersonRole.THIRD_PARTY,
            'otro': PersonRole.OTHER,
        }
        
        return role_mapping.get(role_name.lower(), PersonRole.OTHER)
    
    def _get_empty_persons_dict(self) -> Dict[str, List[str]]:
        """Return empty persons diction`ary structure."""
        return {
            'demandante': [],
            'demandado': [],
            'juez': [],
            'fiscal': [],
            'abogado': [],
            'testigo': [],
            'perito': [],
            'tercero': [],
            'otro': []
        }
