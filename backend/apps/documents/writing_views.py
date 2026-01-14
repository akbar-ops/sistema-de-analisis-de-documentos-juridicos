# apps/documents/writing_views.py
"""
Views para el Asistente de Redacción.

Endpoints:
- GET /api/documents/{id}/writing-assistance/sections/ - Lista secciones disponibles
- POST /api/documents/{id}/writing-assistance/ - Obtiene sugerencias para una sección
- GET /api/documents/{id}/sections/ - Extrae secciones del documento
- POST /api/documents/sections/compare/ - Compara dos secciones
- GET /api/documents/sections/template/{section_type}/ - Obtiene plantilla de sección
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from dataclasses import asdict

from apps.documents.models import Document
from apps.documents.services.writing_assistant import WritingAssistant
from apps.documents.services.section_extractor import LegalSection

logger = logging.getLogger(__name__)


class WritingAssistantViewSet(viewsets.ViewSet):
    """
    ViewSet para el Asistente de Redacción.
    
    Proporciona endpoints para ayudar a los jueces a redactar
    secciones de documentos legales.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.assistant = WritingAssistant()
    
    @action(detail=True, methods=['get'], url_path='available-sections')
    def available_sections(self, request, pk=None):
        """
        GET /api/writing-assistant/{document_id}/available-sections/
        
        Retorna la lista de secciones disponibles para asistencia.
        
        Response:
        {
            "sections": [
                {
                    "id": "considerandos",
                    "name": "Considerandos",
                    "description": "Razonamiento jurídico..."
                },
                ...
            ]
        }
        """
        try:
            sections = self.assistant.get_available_sections()
            
            return Response({
                'sections': sections,
                'total': len(sections)
            })
            
        except Exception as e:
            logger.error(f"Error obteniendo secciones disponibles: {e}", exc_info=True)
            return Response(
                {'error': 'Error al obtener secciones disponibles'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='get-suggestions')
    def get_suggestions(self, request, pk=None):
        """
        POST /api/writing-assistant/{document_id}/get-suggestions/
        
        Obtiene sugerencias de redacción para una sección específica.
        
        Request Body:
        {
            "section_type": "considerandos",
            "max_suggestions": 5,
            "min_quality": 0.6,
            "min_similarity": 0.6
        }
        
        Response:
        {
            "section_type": "considerandos",
            "section_name": "Considerandos",
            "suggestions": [
                {
                    "document_id": "uuid",
                    "document_title": "Título del documento",
                    "section_content": "Contenido de la sección...",
                    "quality_score": 0.85,
                    "similarity_score": 0.78,
                    "key_phrases": ["frase 1", "frase 2"],
                    "metadata": {...}
                },
                ...
            ],
            "total_found": 5,
            "structure_tips": ["tip 1", "tip 2"],
            "style_tips": ["tip 1", "tip 2"]
        }
        """
        try:
            # Obtener documento
            document = get_object_or_404(Document, document_id=pk)
            
            # Validar que el documento esté procesado
            if document.status != 'processed':
                return Response(
                    {
                        'error': 'El documento debe estar completamente procesado',
                        'status': document.status
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Obtener parámetros
            section_type = request.data.get('section_type')
            if not section_type:
                return Response(
                    {'error': 'El parámetro "section_type" es requerido'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validar que el section_type sea válido
            try:
                LegalSection(section_type.lower())
            except ValueError:
                valid_sections = [s.value for s in LegalSection]
                return Response(
                    {
                        'error': f'Tipo de sección inválido: {section_type}',
                        'valid_sections': valid_sections
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            max_suggestions = int(request.data.get('max_suggestions', 5))
            min_quality = float(request.data.get('min_quality', 0.6))
            min_similarity = float(request.data.get('min_similarity', 0.6))
            
            # Validar rangos
            if not (1 <= max_suggestions <= 10):
                max_suggestions = 5
            if not (0.0 <= min_quality <= 1.0):
                min_quality = 0.6
            if not (0.0 <= min_similarity <= 1.0):
                min_similarity = 0.6
            
            logger.info(
                f"Obteniendo sugerencias para documento {pk}, "
                f"sección: {section_type}, max: {max_suggestions}"
            )
            
            # Obtener sugerencias
            result = self.assistant.get_writing_assistance(
                document=document,
                section_type=section_type,
                max_suggestions=max_suggestions,
                min_quality=min_quality,
                min_similarity=min_similarity
            )
            
            # Convertir a diccionario serializable
            response_data = {
                'section_type': result.section_type,
                'section_name': result.section_name,
                'suggestions': [
                    {
                        'document_id': s.document_id,
                        'document_title': s.document_title,
                        'section_content': s.section_content,
                        'quality_score': round(s.quality_score, 3),
                        'similarity_score': round(s.similarity_score, 3),
                        'combined_score': round(s.quality_score * 0.6 + s.similarity_score * 0.4, 3),
                        'key_phrases': s.key_phrases,
                        'metadata': s.metadata
                    }
                    for s in result.suggestions
                ],
                'total_found': result.total_found,
                'structure_tips': result.structure_tips,
                'style_tips': result.style_tips
            }
            
            logger.info(f"Retornando {len(result.suggestions)} sugerencias")
            return Response(response_data)
            
        except ValueError as e:
            logger.error(f"Error de validación: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error obteniendo sugerencias: {e}", exc_info=True)
            return Response(
                {'error': 'Error interno al obtener sugerencias'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], url_path='extract-sections')
    def extract_sections(self, request, pk=None):
        """
        GET /api/writing-assistant/{document_id}/extract-sections/
        
        Extrae todas las secciones del documento.
        
        Response:
        {
            "document_id": "uuid",
            "sections": {
                "considerandos": {
                    "title": "CONSIDERANDO:",
                    "content": "...",
                    "quality_score": 0.75,
                    "start_position": 100,
                    "end_position": 500
                },
                ...
            },
            "total_sections": 5
        }
        """
        try:
            document = get_object_or_404(Document, document_id=pk)
            
            if document.status != 'processed':
                return Response(
                    {
                        'error': 'El documento debe estar procesado',
                        'status': document.status
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            logger.info(f"Extrayendo secciones del documento {pk}")
            
            sections_dict = self.assistant.extract_sections_from_document(document)
            
            # Convertir a formato serializable
            sections_data = {}
            for section_type, section in sections_dict.items():
                quality = self.assistant.section_extractor.evaluate_section_quality(section)
                key_phrases = self.assistant.section_extractor.extract_key_phrases(section, top_n=3)
                
                sections_data[section_type] = {
                    'title': section.title,
                    'content': section.content,
                    'content_preview': section.content[:200] + '...' if len(section.content) > 200 else section.content,
                    'quality_score': round(quality, 3),
                    'start_position': section.start_position,
                    'end_position': section.end_position,
                    'length': len(section.content),
                    'key_phrases': key_phrases
                }
            
            return Response({
                'document_id': str(document.document_id),
                'document_title': document.title,
                'sections': sections_data,
                'total_sections': len(sections_data)
            })
            
        except Exception as e:
            logger.error(f"Error extrayendo secciones: {e}", exc_info=True)
            return Response(
                {'error': 'Error al extraer secciones del documento'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='compare-sections')
    def compare_sections(self, request):
        """
        POST /api/writing-assistant/compare-sections/
        
        Compara dos secciones lado a lado.
        
        Request Body:
        {
            "section_a": "Contenido de la sección A...",
            "section_b": "Contenido de la sección B...",
            "section_type": "considerandos"
        }
        
        Response:
        {
            "section_type": "considerandos",
            "section_a": {
                "content": "...",
                "paragraphs": [...],
                "stats": {...}
            },
            "section_b": {
                "content": "...",
                "paragraphs": [...],
                "stats": {...}
            },
            "comparison": {
                "length_diff": 150,
                "paragraph_count_diff": 2
            }
        }
        """
        try:
            section_a = request.data.get('section_a')
            section_b = request.data.get('section_b')
            section_type = request.data.get('section_type', 'general')
            
            if not section_a or not section_b:
                return Response(
                    {'error': 'Los parámetros "section_a" y "section_b" son requeridos'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            comparison = self.assistant.compare_sections_side_by_side(
                section_a=section_a,
                section_b=section_b,
                section_type=section_type
            )
            
            return Response(comparison)
            
        except Exception as e:
            logger.error(f"Error comparando secciones: {e}", exc_info=True)
            return Response(
                {'error': 'Error al comparar secciones'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], url_path='template/(?P<section_type>[^/.]+)')
    def get_template(self, request, pk=None, section_type=None):
        """
        GET /api/writing-assistant/{document_id}/template/{section_type}/
        
        Obtiene una plantilla base para una sección.
        
        Response:
        {
            "section_type": "considerandos",
            "template": "CONSIDERANDO:\n\nPRIMERO: ..."
        }
        """
        try:
            document = get_object_or_404(Document, document_id=pk)
            
            if not section_type:
                return Response(
                    {'error': 'Tipo de sección no especificado'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            template = self.assistant.generate_section_template(
                section_type=section_type,
                document=document
            )
            
            if not template:
                return Response(
                    {
                        'error': f'No hay plantilla disponible para: {section_type}',
                        'section_type': section_type
                    },
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response({
                'section_type': section_type,
                'template': template,
                'document_context': {
                    'area_legal': document.area_legal,
                    'tipo_documento': document.tipo_documento,
                    'materia': document.materia
                }
            })
            
        except Exception as e:
            logger.error(f"Error obteniendo plantilla: {e}", exc_info=True)
            return Response(
                {'error': 'Error al obtener plantilla'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
