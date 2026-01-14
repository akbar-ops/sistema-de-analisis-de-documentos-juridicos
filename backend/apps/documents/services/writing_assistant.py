# apps/documents/services/writing_assistant.py
"""
Asistente de Redacción para Documentos Legales.

Este servicio ayuda a jueces y operadores jurídicos a redactar mejor sus documentos
proporcionando ejemplos de secciones similares de documentos relacionados.

Funcionalidades:
1. Identifica la sección que el usuario quiere redactar
2. Busca documentos similares al caso actual
3. Extrae las mismas secciones de esos documentos
4. Evalúa calidad y presenta los mejores ejemplos
5. Genera sugerencias de estructura y estilo
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

from apps.documents.models import Document
from apps.documents.services.section_extractor import (
    SectionExtractor, 
    LegalSection, 
    DocumentSection
)
from apps.documents.services.similarity_service import DocumentSimilarityService
from apps.documents.services.parsers.text_extraction import TextExtractionService

logger = logging.getLogger(__name__)


def extract_text_from_file(file_path) -> str:
    """Helper function to extract text from a file path or FieldFile"""
    try:
        # Si es un FieldFile de Django, obtener el path real
        if hasattr(file_path, 'path'):
            actual_path = file_path.path
        else:
            actual_path = str(file_path)
            
        with open(actual_path, 'rb') as f:
            content = f.read()
        
        extractor = TextExtractionService()
        text, _ = extractor.extract_text(content, actual_path)
        return text or ""
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
        return ""


@dataclass
class WritingSuggestion:
    """Representa una sugerencia de redacción"""
    document_id: str
    document_title: str
    section_content: str
    quality_score: float
    key_phrases: List[str]
    metadata: Dict  # Metadatos del documento fuente
    similarity_score: float  # Qué tan similar es el documento completo


@dataclass
class WritingAssistanceResult:
    """Resultado completo del asistente de redacción"""
    section_type: str
    section_name: str
    suggestions: List[WritingSuggestion]
    total_found: int
    structure_tips: List[str]
    style_tips: List[str]


class WritingAssistant:
    """
    Asistente de Redacción para Documentos Legales.
    
    Combina:
    - Búsqueda de similitud (SimilarityService)
    - Extracción de secciones (SectionExtractor)
    - Evaluación de calidad
    - Generación de sugerencias
    """
    
    # Tips de estructura por tipo de sección
    STRUCTURE_TIPS = {
        LegalSection.VISTOS: [
            "Incluir el encabezado del expediente (número, partes, materia)",
            "Mencionar los documentos principales que integran el expediente",
            "Referenciar las actuaciones procesales más relevantes",
        ],
        LegalSection.CONSIDERANDOS: [
            "Numerar cada considerando de forma clara (PRIMERO, SEGUNDO, etc.)",
            "Iniciar con el marco normativo aplicable",
            "Desarrollar el análisis jurídico progresivamente",
            "Fundamentar cada conclusión con normas y jurisprudencia",
        ],
        LegalSection.FUNDAMENTOS_DERECHO: [
            "Citar las normas aplicables con su numeración exacta",
            "Explicar la interpretación de cada norma relevante",
            "Incluir jurisprudencia o doctrina que respalde la posición",
            "Conectar las normas con los hechos del caso",
        ],
        LegalSection.ANALISIS_PRUEBAS: [
            "Enumerar cada medio probatorio ofrecido",
            "Valorar cada prueba según los principios procesales",
            "Explicar qué hechos se acreditan con cada prueba",
            "Aplicar la sana crítica y las máximas de la experiencia",
        ],
        LegalSection.PARTE_RESOLUTIVA: [
            "Comenzar con 'SE RESUELVE:' o similar",
            "Numerar cada punto resolutivo",
            "Ser claro, preciso y congruente con los considerandos",
            "Incluir todos los pronunciamientos solicitados",
        ],
        LegalSection.FUNDAMENTOS_HECHO: [
            "Narrar los hechos cronológicamente",
            "Distinguir hechos alegados vs. hechos probados",
            "Ser objetivo y preciso en la descripción",
            "Referenciar las pruebas que sustentan cada hecho",
        ],
    }
    
    # Tips de estilo general
    STYLE_TIPS = {
        LegalSection.VISTOS: [
            "Usar lenguaje formal pero comprensible",
            "Evitar redundancias innecesarias",
        ],
        LegalSection.CONSIDERANDOS: [
            "Utilizar conectores lógicos (por tanto, asimismo, en consecuencia)",
            "Mantener párrafos de extensión moderada (5-10 líneas)",
            "Evitar el lenguaje excesivamente técnico sin explicación",
        ],
        LegalSection.FUNDAMENTOS_DERECHO: [
            "Citar las normas en formato estándar (ej: artículo 123° del Código Civil)",
            "Usar comillas para transcripciones textuales",
            "Explicar términos técnicos cuando sea necesario",
        ],
        LegalSection.ANALISIS_PRUEBAS: [
            "Ser objetivo en la valoración",
            "Fundamentar las conclusiones probatorias",
            "Distinguir entre prueba directa e indiciaria",
        ],
        LegalSection.PARTE_RESOLUTIVA: [
            "Usar verbos en presente de indicativo (DECLARO, ORDENO, DISPONGO)",
            "Ser preciso en las consecuencias jurídicas",
            "Evitar ambigüedades en lo resuelto",
        ],
    }
    
    def __init__(self):
        """Inicializa el asistente de redacción"""
        self.section_extractor = SectionExtractor()
        self.similarity_service = DocumentSimilarityService()
        logger.info("WritingAssistant inicializado")
    
    def get_writing_assistance(
        self,
        document: Document,
        section_type: str,
        max_suggestions: int = 5,
        min_quality: float = 0.6,
        min_similarity: float = 0.6
    ) -> WritingAssistanceResult:
        """
        Obtiene asistencia de redacción para una sección específica.
        
        Flujo:
        1. Buscar documentos similares al documento actual
        2. Extraer la sección solicitada de cada documento similar
        3. Evaluar calidad de cada sección
        4. Ordenar por calidad y similitud
        5. Generar sugerencias y tips
        
        Args:
            document: Documento de referencia (el caso actual del juez)
            section_type: Tipo de sección a redactar (ej: "considerandos")
            max_suggestions: Número máximo de sugerencias a retornar
            min_quality: Score mínimo de calidad de redacción (0.0-1.0)
            min_similarity: Score mínimo de similitud del documento (0.0-1.0)
            
        Returns:
            WritingAssistanceResult con sugerencias y tips
        """
        logger.info(
            f"Generando asistencia de redacción para documento {document.document_id}, "
            f"sección: {section_type}"
        )
        
        # Convertir string a enum
        try:
            section_enum = LegalSection(section_type.lower())
        except ValueError:
            logger.error(f"Tipo de sección inválido: {section_type}")
            return WritingAssistanceResult(
                section_type=section_type,
                section_name=section_type,
                suggestions=[],
                total_found=0,
                structure_tips=[],
                style_tips=[]
            )
        
        # Paso 1: Buscar documentos similares
        similar_docs = self.similarity_service.find_similar_documents(
            document.document_id,
            top_n=20,  # Buscar más documentos para tener más opciones
            use_hybrid_scoring=True,
            min_similarity=min_similarity
        )
        
        if not similar_docs:
            logger.warning("No se encontraron documentos similares")
            return self._create_empty_result(section_enum)
        
        logger.info(f"Encontrados {len(similar_docs)} documentos similares")
        
        # Paso 2 y 3: Extraer y evaluar secciones
        suggestions = []
        
        for similar_doc, hybrid_score, reasons in similar_docs:
            try:
                # Extraer texto del documento
                if not similar_doc.file_path:
                    continue
                
                text = extract_text_from_file(similar_doc.file_path)
                if not text:
                    continue
                
                # Buscar la sección específica
                section = self.section_extractor.extract_specific_section(
                    text,
                    section_enum
                )
                
                if section:
                    # Evaluar calidad
                    quality = self.section_extractor.evaluate_section_quality(section)
                    
                    if quality >= min_quality:
                        # Extraer frases clave
                        key_phrases = self.section_extractor.extract_key_phrases(
                            section, 
                            top_n=3
                        )
                        
                        # Crear sugerencia
                        suggestion = WritingSuggestion(
                            document_id=str(similar_doc.document_id),
                            document_title=similar_doc.title or "Sin título",
                            section_content=section.content,
                            quality_score=quality,
                            key_phrases=key_phrases,
                            metadata={
                                'legal_area': similar_doc.legal_area.name if similar_doc.legal_area else None,
                                'doc_type': similar_doc.doc_type.name if similar_doc.doc_type else None,
                                'legal_subject': similar_doc.legal_subject,
                                'document_date': similar_doc.document_date.isoformat() if similar_doc.document_date else None,
                            },
                            similarity_score=hybrid_score
                        )
                        
                        suggestions.append(suggestion)
            
            except Exception as e:
                logger.error(f"Error procesando documento similar: {e}", exc_info=True)
                continue
        
        # Paso 4: Ordenar por calidad combinada (quality + similarity)
        suggestions.sort(
            key=lambda x: (x.quality_score * 0.6 + x.similarity_score * 0.4),
            reverse=True
        )
        
        # Limitar al máximo solicitado
        suggestions = suggestions[:max_suggestions]
        
        logger.info(f"Generadas {len(suggestions)} sugerencias de calidad")
        
        # Paso 5: Obtener tips de estructura y estilo
        structure_tips = self.STRUCTURE_TIPS.get(section_enum, [])
        style_tips = self.STYLE_TIPS.get(section_enum, [])
        
        return WritingAssistanceResult(
            section_type=section_enum.value,
            section_name=section_enum.value.replace('_', ' ').title(),
            suggestions=suggestions,
            total_found=len(suggestions),
            structure_tips=structure_tips,
            style_tips=style_tips
        )
    
    def _create_empty_result(self, section_enum: LegalSection) -> WritingAssistanceResult:
        """Crea un resultado vacío con tips generales"""
        return WritingAssistanceResult(
            section_type=section_enum.value,
            section_name=section_enum.value.replace('_', ' ').title(),
            suggestions=[],
            total_found=0,
            structure_tips=self.STRUCTURE_TIPS.get(section_enum, []),
            style_tips=self.STYLE_TIPS.get(section_enum, [])
        )
    
    def get_available_sections(self) -> List[Dict[str, str]]:
        """
        Retorna la lista de secciones disponibles para asistencia.
        
        Returns:
            Lista de diccionarios con id y nombre de cada sección
        """
        sections = []
        for section in LegalSection:
            sections.append({
                'id': section.value,
                'name': section.value.replace('_', ' ').title(),
                'description': self._get_section_description(section)
            })
        
        return sections
    
    def _get_section_description(self, section: LegalSection) -> str:
        """Retorna una descripción breve de cada sección"""
        descriptions = {
            LegalSection.VISTOS: "Parte expositiva que presenta el caso y actuaciones procesales",
            LegalSection.CONSIDERANDOS: "Razonamiento jurídico y análisis del caso",
            LegalSection.FUNDAMENTOS_DERECHO: "Marco normativo y legal aplicable",
            LegalSection.FUNDAMENTOS_HECHO: "Narración de los hechos relevantes del caso",
            LegalSection.ANALISIS_PRUEBAS: "Valoración de los medios probatorios",
            LegalSection.PARTE_RESOLUTIVA: "Decisión final y puntos resolutivos",
            LegalSection.PETITORIO: "Solicitud o pretensión de la parte",
            LegalSection.HECHOS: "Relato de los hechos en escritos de las partes",
            LegalSection.ANTECEDENTES: "Contexto y antecedentes del caso",
        }
        return descriptions.get(section, "")
    
    def compare_sections_side_by_side(
        self,
        section_a: str,  # Contenido de la sección A
        section_b: str,  # Contenido de la sección B
        section_type: str
    ) -> Dict:
        """
        Compara dos secciones lado a lado para visualización.
        
        Esta función prepara los datos para una vista comparativa
        en el frontend.
        
        Args:
            section_a: Contenido de la primera sección
            section_b: Contenido de la segunda sección
            section_type: Tipo de sección
            
        Returns:
            Diccionario con datos de comparación
        """
        # Dividir en párrafos para comparación
        paragraphs_a = [p.strip() for p in section_a.split('\n\n') if p.strip()]
        paragraphs_b = [p.strip() for p in section_b.split('\n\n') if p.strip()]
        
        # Estadísticas básicas
        stats_a = {
            'length': len(section_a),
            'paragraphs': len(paragraphs_a),
            'avg_paragraph_length': len(section_a) / len(paragraphs_a) if paragraphs_a else 0
        }
        
        stats_b = {
            'length': len(section_b),
            'paragraphs': len(paragraphs_b),
            'avg_paragraph_length': len(section_b) / len(paragraphs_b) if paragraphs_b else 0
        }
        
        return {
            'section_type': section_type,
            'section_a': {
                'content': section_a,
                'paragraphs': paragraphs_a,
                'stats': stats_a
            },
            'section_b': {
                'content': section_b,
                'paragraphs': paragraphs_b,
                'stats': stats_b
            },
            'comparison': {
                'length_diff': abs(stats_a['length'] - stats_b['length']),
                'paragraph_count_diff': abs(stats_a['paragraphs'] - stats_b['paragraphs'])
            }
        }
    
    def extract_sections_from_document(
        self, 
        document: Document
    ) -> Dict[str, DocumentSection]:
        """
        Extrae todas las secciones de un documento.
        
        Útil para análisis completo del documento.
        
        Args:
            document: Documento del cual extraer secciones
            
        Returns:
            Diccionario con secciones extraídas {section_type: section}
        """
        try:
            if not document.file_path:
                logger.warning(f"Documento {document.document_id} sin archivo")
                return {}
            
            text = extract_text_from_file(document.file_path)
            if not text:
                logger.warning(f"No se pudo extraer texto del documento {document.document_id}")
                return {}
            
            sections = self.section_extractor.extract_sections(text)
            
            # Convertir a diccionario
            sections_dict = {}
            for section in sections:
                # Si hay múltiples secciones del mismo tipo, tomar la primera
                if section.section_type.value not in sections_dict:
                    sections_dict[section.section_type.value] = section
            
            logger.info(f"Extraídas {len(sections_dict)} secciones únicas del documento {document.document_id}")
            return sections_dict
            
        except Exception as e:
            logger.error(f"Error extrayendo secciones del documento {document.document_id}: {e}", exc_info=True)
            return {}
    
    def generate_section_template(self, section_type: str, document: Document) -> str:
        """
        Genera una plantilla/esquema básico para una sección.
        
        Args:
            section_type: Tipo de sección
            document: Documento actual (para personalizar con metadatos)
            
        Returns:
            Texto de plantilla con marcadores de posición
        """
        try:
            section_enum = LegalSection(section_type.lower())
        except ValueError:
            return ""
        
        templates = {
            LegalSection.CONSIDERANDOS: f"""CONSIDERANDO:

PRIMERO: Marco Normativo
[Describir las normas aplicables al caso: {document.area_legal or 'área legal correspondiente'}]

SEGUNDO: Análisis de los Hechos
[Exponer los hechos relevantes probados en el proceso]

TERCERO: Subsunción Jurídica
[Aplicar las normas a los hechos del caso]

CUARTO: Conclusión
[Explicar la decisión a la que se arriba y su fundamentación]
""",
            LegalSection.PARTE_RESOLUTIVA: f"""SE RESUELVE:

PRIMERO: [Pronunciamiento principal sobre la pretensión]

SEGUNDO: [Consecuencias jurídicas, costas, costos si corresponde]

TERCERO: [Disposiciones complementarias]

CUARTO: [Notificaciones y devolución de expediente si corresponde]
""",
            LegalSection.ANALISIS_PRUEBAS: """ANÁLISIS DE LAS PRUEBAS:

1. PRUEBAS DOCUMENTALES:
   - [Enumerar y valorar cada documento]

2. PRUEBAS TESTIMONIALES:
   - [Analizar cada testimonio]

3. PRUEBAS PERICIALES:
   - [Valorar informes periciales si existen]

4. CONCLUSIÓN PROBATORIA:
   [Sintetizar qué hechos han quedado probados]
"""
        }
        
        return templates.get(section_enum, "")
