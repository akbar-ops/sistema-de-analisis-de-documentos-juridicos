# apps/documents/services/section_extractor.py
"""
Servicio para identificar y extraer secciones estructuradas de documentos legales.

Este servicio:
1. Identifica secciones comunes en documentos judiciales peruanos
2. Extrae el contenido de cada sección
3. Analiza la calidad de redacción de cada sección (opcional)
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class LegalSection(str, Enum):
    """Secciones comunes en documentos legales peruanos"""
    # Secciones de resoluciones judiciales
    VISTOS = "vistos"
    ANTECEDENTES = "antecedentes"
    CONSIDERANDOS = "considerandos"
    FUNDAMENTOS_DERECHO = "fundamentos_derecho"
    FUNDAMENTOS_HECHO = "fundamentos_hecho"
    ANALISIS_PRUEBAS = "analisis_pruebas"
    PARTE_RESOLUTIVA = "parte_resolutiva"
    DECISION = "decision"
    
    # Secciones de demandas/escritos
    PETITORIO = "petitorio"
    HECHOS = "hechos"
    FUNDAMENTOS_JURIDICOS = "fundamentos_juridicos"
    MEDIOS_PROBATORIOS = "medios_probatorios"
    
    # Otras secciones
    CONCLUSION = "conclusion"
    FIRMA = "firma"
    OTROS = "otros"


@dataclass
class DocumentSection:
    """Representa una sección extraída de un documento"""
    section_type: LegalSection
    title: str  # Título original encontrado en el documento
    content: str  # Contenido de la sección
    start_position: int  # Posición de inicio en el texto
    end_position: int  # Posición de fin en el texto
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    quality_score: Optional[float] = None  # Score de calidad (opcional)


class SectionExtractor:
    """
    Extractor de secciones de documentos legales.
    
    Utiliza regex patterns y heurísticas para identificar secciones
    en documentos judiciales peruanos.
    """
    
    # Patrones regex para identificar secciones
    SECTION_PATTERNS = {
        LegalSection.VISTOS: [
            r'VISTOS?\s*:',
            r'VISTOS?\s+Y\s+CONSIDERANDOS?',
            r'I\.\s*VISTOS?',
        ],
        LegalSection.ANTECEDENTES: [
            r'ANTECEDENTES?\s*:',
            r'I+\.\s*ANTECEDENTES?',
            r'PARTE\s+EXPOSITIVA',
        ],
        LegalSection.CONSIDERANDOS: [
            r'CONSIDERANDOS?\s*:',
            r'Y\s+CONSIDERANDO\s*:',
            r'PARTE\s+CONSIDERATIVA',
        ],
        LegalSection.FUNDAMENTOS_DERECHO: [
            r'FUNDAMENTOS?\s+DE\s+DERECHO\s*:',
            r'FUNDAMENTOS?\s+JUR[IÍ]DICOS?\s*:',
            r'II+\.\s*FUNDAMENTOS?\s+DE\s+DERECHO',
            r'MARCO\s+JUR[IÍ]DICO',
            r'BASE\s+LEGAL',
        ],
        LegalSection.FUNDAMENTOS_HECHO: [
            r'FUNDAMENTOS?\s+DE\s+HECHO\s*:',
            r'FUNDAMENTOS?\s+F[ÁA]CTICOS?\s*:',
            r'I+\.\s*FUNDAMENTOS?\s+DE\s+HECHO',
        ],
        LegalSection.ANALISIS_PRUEBAS: [
            r'AN[ÁA]LISIS\s+DE\s+(LAS?\s+)?PRUEBAS?\s*:',
            r'VALORACI[ÓO]N\s+DE\s+(LAS?\s+)?PRUEBAS?\s*:',
            r'APRECIACI[ÓO]N\s+DE\s+(LAS?\s+)?PRUEBAS?\s*:',
            r'III+\.\s*AN[ÁA]LISIS\s+PROBATORIO',
        ],
        LegalSection.PARTE_RESOLUTIVA: [
            r'PARTE\s+RESOLUTIVA\s*:',
            r'RESUELVE\s*:',
            r'SE\s+RESUELVE\s*:',
            r'IV+\.\s*PARTE\s+RESOLUTIVA',
            r'POR\s+TANTO\s*:',
        ],
        LegalSection.DECISION: [
            r'DECISI[ÓO]N\s*:',
            r'FALLO\s*:',
            r'SE\s+DECLARA\s*:',
            r'SENTENCIA\s*:',
        ],
        LegalSection.PETITORIO: [
            r'PETITORIO\s*:',
            r'SOLICITO\s*:',
            r'PIDO\s*:',
            r'PRETENSIONES?\s*:',
        ],
        LegalSection.HECHOS: [
            r'HECHOS?\s*:',
            r'RELATO\s+DE\s+HECHOS?\s*:',
            r'I+\.\s*HECHOS?',
        ],
        LegalSection.FUNDAMENTOS_JURIDICOS: [
            r'FUNDAMENTOS?\s+JUR[IÍ]DICOS?\s+DE\s+LA\s+DEMANDA\s*:',
            r'SUSTENTO\s+LEGAL\s*:',
        ],
        LegalSection.MEDIOS_PROBATORIOS: [
            r'MEDIOS?\s+PROBATORIOS?\s*:',
            r'PRUEBAS?\s+QUE\s+OFREZCO\s*:',
            r'ANEXOS?\s*:',
        ],
    }
    
    def __init__(self):
        """Inicializa el extractor de secciones"""
        self.compiled_patterns = self._compile_patterns()
        logger.info("SectionExtractor inicializado")
    
    def _compile_patterns(self) -> Dict[LegalSection, List[re.Pattern]]:
        """Compila todos los patterns regex para mejor performance"""
        compiled = {}
        for section, patterns in self.SECTION_PATTERNS.items():
            compiled[section] = [
                re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                for pattern in patterns
            ]
        return compiled
    
    def extract_sections(self, text: str) -> List[DocumentSection]:
        """
        Extrae todas las secciones encontradas en el texto.
        
        Args:
            text: Texto completo del documento
            
        Returns:
            Lista de secciones extraídas, ordenadas por posición
        """
        if not text or not text.strip():
            logger.warning("Texto vacío, no se pueden extraer secciones")
            return []
        
        sections = []
        
        # Buscar todas las secciones
        for section_type, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                matches = list(pattern.finditer(text))
                for match in matches:
                    sections.append({
                        'section_type': section_type,
                        'title': match.group(0).strip(),
                        'start': match.start(),
                        'pattern_used': pattern.pattern
                    })
        
        if not sections:
            logger.warning("No se encontraron secciones en el documento")
            return []
        
        # Ordenar por posición
        sections.sort(key=lambda x: x['start'])
        
        # Extraer contenido de cada sección
        extracted_sections = []
        for i, section in enumerate(sections):
            # El contenido va desde el final del título hasta el inicio de la siguiente sección
            content_start = section['start'] + len(section['title'])
            content_end = sections[i + 1]['start'] if i + 1 < len(sections) else len(text)
            
            content = text[content_start:content_end].strip()
            
            # Solo agregar si tiene contenido significativo
            if len(content) > 50:  # Al menos 50 caracteres
                extracted_sections.append(DocumentSection(
                    section_type=section['section_type'],
                    title=section['title'],
                    content=content,
                    start_position=section['start'],
                    end_position=content_end
                ))
        
        logger.info(f"Extraídas {len(extracted_sections)} secciones del documento")
        return extracted_sections
    
    def extract_specific_section(
        self, 
        text: str, 
        section_type: LegalSection
    ) -> Optional[DocumentSection]:
        """
        Extrae una sección específica del documento.
        Si hay múltiples secciones del mismo tipo, devuelve la de mayor calidad.
        
        Args:
            text: Texto completo del documento
            section_type: Tipo de sección a extraer
            
        Returns:
            Sección extraída o None si no se encuentra
        """
        all_sections = self.extract_sections(text)
        
        # Filtrar secciones del tipo solicitado
        matching_sections = [s for s in all_sections if s.section_type == section_type]
        
        if not matching_sections:
            return None
        
        # Si solo hay una, devolverla
        if len(matching_sections) == 1:
            return matching_sections[0]
        
        # Si hay múltiples, devolver la de mejor calidad
        best_section = None
        best_quality = 0
        
        for section in matching_sections:
            quality = self.evaluate_section_quality(section)
            if quality > best_quality:
                best_quality = quality
                best_section = section
        
        return best_section
    
    def get_section_summary(self, sections: List[DocumentSection]) -> Dict[str, int]:
        """
        Obtiene un resumen de las secciones encontradas.
        
        Args:
            sections: Lista de secciones
            
        Returns:
            Diccionario con conteo por tipo de sección
        """
        summary = {}
        for section in sections:
            section_name = section.section_type.value
            summary[section_name] = summary.get(section_name, 0) + 1
        
        return summary
    
    def evaluate_section_quality(self, section: DocumentSection) -> float:
        """
        Evalúa la calidad de redacción de una sección (heurística básica).
        
        Criterios:
        - Longitud apropiada (no muy corta, no muy larga)
        - Estructura (párrafos, puntuación)
        - Vocabulario legal (presencia de términos técnicos)
        
        Args:
            section: Sección a evaluar
            
        Returns:
            Score de calidad (0.0 - 1.0)
        """
        score = 0.0
        content = section.content
        
        # Criterio 1: Longitud apropiada (20%)
        length = len(content)
        if 200 <= length <= 5000:
            score += 0.2
        elif 100 <= length < 200 or 5000 < length <= 10000:
            score += 0.1
        
        # Criterio 2: Estructura en párrafos (20%)
        paragraphs = [p for p in content.split('\n\n') if p.strip()]
        if 2 <= len(paragraphs) <= 20:
            score += 0.2
        elif len(paragraphs) == 1 or len(paragraphs) > 20:
            score += 0.1
        
        # Criterio 3: Puntuación adecuada (20%)
        sentences = [s for s in re.split(r'[.;]', content) if s.strip()]
        avg_sentence_length = length / len(sentences) if sentences else 0
        if 50 <= avg_sentence_length <= 200:
            score += 0.2
        elif 30 <= avg_sentence_length < 50 or 200 < avg_sentence_length <= 300:
            score += 0.1
        
        # Criterio 4: Vocabulario legal (20%)
        legal_terms = [
            'derecho', 'ley', 'artículo', 'código', 'jurisprudencia',
            'doctrina', 'precedente', 'norma', 'constitución', 'procesal',
            'sustantivo', 'debido proceso', 'tutela', 'jurisdicción',
            'competencia', 'prueba', 'demanda', 'pretensión', 'sentencia'
        ]
        content_lower = content.lower()
        legal_term_count = sum(1 for term in legal_terms if term in content_lower)
        if legal_term_count >= 5:
            score += 0.2
        elif legal_term_count >= 3:
            score += 0.1
        
        # Criterio 5: Coherencia textual (20%)
        # Presencia de conectores lógicos
        connectors = [
            'por tanto', 'en consecuencia', 'asimismo', 'además',
            'sin embargo', 'no obstante', 'por lo expuesto', 'en ese sentido',
            'cabe señalar', 'es menester', 'siendo así'
        ]
        connector_count = sum(1 for conn in connectors if conn in content_lower)
        if connector_count >= 3:
            score += 0.2
        elif connector_count >= 1:
            score += 0.1
        
        return min(score, 1.0)  # Asegurar que no exceda 1.0
    
    def find_similar_sections(
        self,
        target_section: DocumentSection,
        candidate_texts: List[Tuple[str, str]],  # [(doc_id, full_text), ...]
        min_quality: float = 0.5
    ) -> List[Dict]:
        """
        Encuentra secciones similares de buena calidad en otros documentos.
        
        Args:
            target_section: Sección de referencia
            candidate_texts: Lista de tuplas (document_id, full_text) donde buscar
            min_quality: Score mínimo de calidad requerido
            
        Returns:
            Lista de secciones similares con metadata
        """
        similar_sections = []
        
        for doc_id, text in candidate_texts:
            # Buscar la misma sección en el documento candidato
            candidate_section = self.extract_specific_section(
                text, 
                target_section.section_type
            )
            
            if candidate_section:
                # Evaluar calidad
                quality = self.evaluate_section_quality(candidate_section)
                
                if quality >= min_quality:
                    similar_sections.append({
                        'document_id': doc_id,
                        'section': candidate_section,
                        'quality_score': quality
                    })
        
        # Ordenar por calidad (mejor primero)
        similar_sections.sort(key=lambda x: x['quality_score'], reverse=True)
        
        logger.info(
            f"Encontradas {len(similar_sections)} secciones similares de "
            f"tipo {target_section.section_type.value} con calidad >= {min_quality}"
        )
        
        return similar_sections
    
    def extract_key_phrases(self, section: DocumentSection, top_n: int = 5) -> List[str]:
        """
        Extrae frases clave de una sección (útil para mostrar previews).
        
        Args:
            section: Sección de la cual extraer frases
            top_n: Número de frases a extraer
            
        Returns:
            Lista de frases clave
        """
        # Dividir en oraciones
        sentences = re.split(r'[.;]', section.content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
        
        if not sentences:
            return []
        
        # Simple heurística: tomar las primeras N oraciones significativas
        # En una versión más avanzada, usar TF-IDF o similar
        key_phrases = []
        for sentence in sentences[:top_n * 2]:  # Revisar más de lo necesario
            # Filtrar oraciones muy cortas o muy largas
            if 50 <= len(sentence) <= 300:
                key_phrases.append(sentence)
                if len(key_phrases) >= top_n:
                    break
        
        return key_phrases[:top_n]
