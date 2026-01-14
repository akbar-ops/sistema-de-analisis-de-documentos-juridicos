# documents/services/modular_processing.py
"""
Servicio de procesamiento modular de documentos.
Permite analizar documentos en 4 partes independientes:
1. Metadatos (metadata)
2. Título (title) - NUEVO
3. Resumen (summary)
4. Personas (persons)

IMPORTANTE: El clean_embedding SIEMPRE se genera (no depende de Ollama).
Se genera automáticamente después de extraer el texto del documento.
"""
import logging
from django.utils import timezone
from typing import List, Dict, Any

from apps.documents.services.metadata_extractor import DocumentMetadataExtractor
from apps.documents.services.title_generator import TitleGenerator
from apps.documents.services.document_summarizer import DocumentSummarizer
from apps.documents.services.person_extractor import PersonExtractor
from apps.documents.services.embedding_service import get_embedding_service
from apps.documents.services.clean_embeddings_service import get_clean_embedding_service
from apps.documents.models import Document, DocumentStatus, AnalysisStatus

logger = logging.getLogger(__name__)


class ModularDocumentProcessor:
    """
    Procesador modular que permite analizar documentos por partes.
    Cada parte puede ser analizada independientemente y en cualquier momento.
    
    IMPORTANTE: El clean_embedding se genera automáticamente con generate_clean_embedding()
    y NO requiere Ollama. Es independiente del resumen.
    """
    
    def __init__(self):
        self.metadata_extractor = DocumentMetadataExtractor()
        self.title_generator = TitleGenerator()
        self.summarizer = DocumentSummarizer()
        self.person_extractor = PersonExtractor()
        self.embedding_service = get_embedding_service()
        self.clean_embedding_service = get_clean_embedding_service()
    
    def generate_clean_embedding(self, document: Document) -> bool:
        """
        Genera el clean_embedding del documento (NO requiere Ollama).
        
        Este embedding se genera sobre el texto LIMPIO (sin stopwords) y es el
        embedding principal para similaridad y clustering.
        
        Puede llamarse:
        - Automáticamente durante el procesamiento inicial
        - Manualmente para regenerar el embedding
        - Como parte de una migración de documentos existentes
        
        Args:
            document: Instancia del documento a procesar
            
        Returns:
            bool: True si fue exitoso, False en caso contrario
        """
        try:
            logger.info(f"Generating clean embedding for document {document.document_id}")
            
            if not document.content:
                raise ValueError("El documento no tiene contenido extraído")
            
            # Generar clean embedding
            clean_embedding = self.clean_embedding_service.generate_document_embedding(
                document.content,
                clean_text=True,
                pooling_strategy='weighted_start'
            )
            
            if clean_embedding is not None:
                document.clean_embedding = clean_embedding.tolist()
                document.save(update_fields=['clean_embedding', 'updated_at'])
                
                # Log statistics
                stats = self.clean_embedding_service.get_text_statistics(document.content)
                logger.info(
                    f"Clean embedding generated: {stats['original_words']} → {stats['cleaned_words']} words "
                    f"({stats['reduction_percent']}% reduction), {stats['num_chunks']} chunks"
                )
                return True
            else:
                logger.warning(f"Clean embedding generation returned None for document {document.document_id}")
                return False
                
        except Exception as e:
            logger.error(
                f"Error generating clean embedding for document {document.document_id}: {e}",
                exc_info=True
            )
            return False
    
    def process_metadata(self, document: Document) -> bool:
        """
        Analiza y extrae metadatos del documento.
        Parte 1: Tipo, área legal, materia, número de caso, etc.
        NO genera el título (eso se hace en process_title por separado).
        
        Args:
            document: Instancia del documento a procesar
            
        Returns:
            bool: True si fue exitoso, False en caso contrario
        """
        try:
            logger.info(f"Starting metadata extraction for document {document.document_id}")
            
            document.metadata_analysis_status = AnalysisStatus.PROCESSING
            document.save(update_fields=['metadata_analysis_status', 'updated_at'])
            
            if not document.content:
                raise ValueError("El documento no tiene contenido extraído")
            
            # Extraer metadatos (sin título)
            metadata = self.metadata_extractor.extract_metadata(document.content)
            
            # Actualizar metadatos (sin título)
            document.doc_type = metadata.get('doc_type')
            document.legal_area = metadata.get('legal_area')
            document.legal_subject = metadata.get('legal_subject')
            document.case_number = metadata.get('case_number')
            document.jurisdictional_body = metadata.get('jurisdictional_body')
            document.resolution_number = metadata.get('resolution_number')
            document.issue_place = metadata.get('issue_place')
            document.document_date = metadata.get('document_date')
            
            document.metadata_analysis_status = AnalysisStatus.COMPLETED
            
            document.save(update_fields=[
                'doc_type', 'legal_area', 'legal_subject', 'case_number',
                'jurisdictional_body', 'resolution_number', 'issue_place', 
                'document_date', 'metadata_analysis_status', 'updated_at'
            ])

            logger.info(
                f"Metadata extraction completed - "
                f"Type: {document.doc_type}, Area: {document.legal_area}, "
                f"Resolution: {document.resolution_number}, Date: {document.document_date}"
            )
            
            # Actualizar enhanced embedding después de cambios
            self._update_enhanced_embedding(document)
            
            return True
            
        except Exception as e:
            logger.error(
                f"Metadata extraction error for document {document.document_id}: {e}",
                exc_info=True
            )
            document.metadata_analysis_status = AnalysisStatus.FAILED
            document.error_message = f"Error en análisis de metadatos: {str(e)}"
            document.save(update_fields=['metadata_analysis_status', 'error_message', 'updated_at'])
            return False
    
    def process_title(self, document: Document) -> bool:
        """
        Genera el título específico del documento usando análisis LLM dedicado.
        Parte 2: Título con formato [Materia] - [Partes] - [Decisión]
        
        Requiere que los metadatos ya estén extraídos.
        
        Args:
            document: Instancia del documento a procesar
            
        Returns:
            bool: True si fue exitoso, False en caso contrario
        """
        try:
            logger.info(f"Starting title generation for document {document.document_id}")
            
            # No hay status específico para título, se considera parte de metadata
            # Pero lo documentamos en logs
            
            if not document.content:
                raise ValueError("El documento no tiene contenido extraídUsually allowedo")
            
            # Extraer partes y decisión de metadata (fueron extraídas en process_metadata)
            metadata = self.metadata_extractor.extract_metadata(document.content)
            partes = metadata.get('partes')
            decision = metadata.get('decision')
            
            # Generar título usando el servicio dedicado
            doc_type_name = document.doc_type.name if document.doc_type else None
            legal_area_name = document.legal_area.name if document.legal_area else None
            
            title = self.title_generator.generate_title(
                document.content,
                doc_type=doc_type_name,
                legal_area=legal_area_name,
                legal_subject=document.legal_subject,
                partes=partes,
                decision=decision
            )
            
            if title and title.strip():
                document.title = title
                logger.info(f"✓ Title generated: {title}")
            else:
                # Fallback to filename
                document.title = document.file_path.name if document.file_path else 'Documento sin título'
                logger.warning(f"Title generation returned empty, using filename")
            
            document.save(update_fields=['title', 'updated_at'])
            
            # Actualizar enhanced embedding con el nuevo título
            self._update_enhanced_embedding(document)
            
            return True
            
        except Exception as e:
            logger.error(
                f"Title generation error for document {document.document_id}: {e}",
                exc_info=True
            )
            # No marcamos como failed, solo logueamos el error
            # El título puede fallar pero el resto del análisis continúa
            if not document.title or not document.title.strip():
                document.title = document.file_path.name if document.file_path else 'Documento sin título'
                document.save(update_fields=['title', 'updated_at'])
            return False
    
    def process_summary(self, document: Document, summarizer_type: str = 'ollama') -> bool:
        """
        Genera el resumen del documento.
        Parte 3: Resumen ejecutivo, fechas relevantes, decisión, palabras clave.
        
        Args:
            document: Instancia del documento a procesar
            summarizer_type: Tipo de generador ('ollama' o 'bart')
            
        Returns:
            bool: True si fue exitoso, False en caso contrario
        """
        try:
            logger.info(f"Starting summary generation for document {document.document_id} using {summarizer_type}")
            
            document.summary_analysis_status = AnalysisStatus.PROCESSING
            document.save(update_fields=['summary_analysis_status', 'updated_at'])
            
            if not document.content:
                raise ValueError("El documento no tiene contenido extraído")
            
            # Generar resumen con el backend seleccionado
            doc_type_name = document.doc_type.name if document.doc_type else 'Documento Legal'
            legal_area_name = document.legal_area.name if document.legal_area else 'General'
            
            summary_data = self.summarizer.generate_summary(
                document.content,
                doc_type_name,
                legal_area_name,
                document.legal_subject,
                summarizer_type=summarizer_type
            )
            
            # Actualizar resumen y tipo de generador usado
            document.summary = summary_data.get('summary_text')
            document.summarizer_type = summarizer_type
            
            # Generar embedding del resumen
            if document.summary:
                try:
                    summary_embedding = self.embedding_service.encode_document_summary(
                        document.summary
                    )
                    if summary_embedding is not None:
                        document.summary_embedding = summary_embedding.tolist()
                        logger.info(f"Generated summary embedding for document {document.document_id}")
                except Exception as e:
                    logger.error(f"Error generating summary embedding: {e}")
            
            document.summary_analysis_status = AnalysisStatus.COMPLETED
            
            document.save(update_fields=[
                'summary', 'summary_embedding', 'summarizer_type', 
                'summary_analysis_status', 'updated_at'
            ])
            
            logger.info(f"Summary generation completed for document {document.document_id}")
            
            # Actualizar enhanced embedding después de cambios
            self._update_enhanced_embedding(document)
            
            return True
            
        except Exception as e:
            logger.error(
                f"Summary generation error for document {document.document_id}: {e}",
                exc_info=True
            )
            document.summary_analysis_status = AnalysisStatus.FAILED
            document.error_message = f"Error en análisis de resumen: {str(e)}"
            document.save(update_fields=['summary_analysis_status', 'error_message', 'updated_at'])
            return False
    
    def process_persons(self, document: Document) -> bool:
        """
        Extrae las personas mencionadas en el documento.
        Parte 4: Demandantes, demandados, jueces, fiscales, testigos, etc.
        
        Args:
            document: Instancia del documento a procesar
            
        Returns:
            bool: True si fue exitoso, False en caso contrario
        """
        try:
            logger.info(f"Starting person extraction for document {document.document_id}")
            
            document.persons_analysis_status = AnalysisStatus.PROCESSING
            document.save(update_fields=['persons_analysis_status', 'updated_at'])
            
            if not document.content:
                raise ValueError("El documento no tiene contenido extraído")
            
            # Extraer personas
            persons_data = self.person_extractor.extract_and_link_persons(
                document.content,
                document
            )
            
            total_persons = sum(len(v) for v in persons_data.values())
            
            document.persons_analysis_status = AnalysisStatus.COMPLETED
            document.save(update_fields=['persons_analysis_status', 'updated_at'])
            
            logger.info(
                f"Person extraction completed - {total_persons} persons linked to document"
            )
            
            # Actualizar enhanced embedding después de cambios
            self._update_enhanced_embedding(document)
            
            return True
            
        except Exception as e:
            logger.error(
                f"Person extraction error for document {document.document_id}: {e}",
                exc_info=True
            )
            document.persons_analysis_status = AnalysisStatus.FAILED
            document.error_message = f"Error en análisis de personas: {str(e)}"
            document.save(update_fields=['persons_analysis_status', 'error_message', 'updated_at'])
            return False
    
    def process_parts(
        self, 
        document: Document, 
        parts: List[str],
        generate_clean_emb: bool = True
    ) -> Dict[str, bool]:
        """
        Procesa las partes especificadas del documento.
        
        Args:
            document: Instancia del documento a procesar
            parts: Lista de partes a procesar ['metadata', 'title', 'summary', 'persons', 'clean_embedding']
            generate_clean_emb: Si True, SIEMPRE genera clean_embedding (default: True)
            
        Returns:
            dict: Diccionario con el resultado de cada parte
        """
        results = {}
        
        # SIEMPRE generar clean_embedding primero (no requiere Ollama)
        if generate_clean_emb and 'clean_embedding' not in parts:
            # Generar automáticamente si no está explícitamente en parts
            results['clean_embedding'] = self.generate_clean_embedding(document)
        
        for part in parts:
            if part == 'metadata':
                results['metadata'] = self.process_metadata(document)
            elif part == 'title':
                results['title'] = self.process_title(document)
            elif part == 'summary':
                results['summary'] = self.process_summary(document)
            elif part == 'persons':
                results['persons'] = self.process_persons(document)
            elif part == 'clean_embedding':
                results['clean_embedding'] = self.generate_clean_embedding(document)
            else:
                logger.warning(f"Unknown analysis part: {part}")
                results[part] = False
        
        # Actualizar estado general del documento
        self._update_document_status(document)
        
        return results
    
    def _update_enhanced_embedding(self, document: Document):
        """
        Actualiza el enhanced embedding del documento combinando todos los campos.
        Se llama automáticamente después de cada análisis completado.
        """
        try:
            logger.info(f"Updating enhanced embedding for document {document.document_id}")
            
            # Refrescar relaciones
            document.refresh_from_db()
            
            # Obtener personas relacionadas
            document_persons = document.document_persons.select_related('person').all()
            persons_data = [
                {
                    'name': dp.person.name,
                    'role': dp.role
                }
                for dp in document_persons
            ]
            
            # Preparar datos para el embedding mejorado
            enhanced_data = {
                'title': document.title,
                'legal_area': document.legal_area.name if document.legal_area else None,
                'legal_subject': document.legal_subject,
                'summary': document.summary,
                'issue_place': document.issue_place,
                'case_number': document.case_number,
                'resolution_number': document.resolution_number,
                'persons': persons_data
            }
            
            # Generar enhanced embedding
            enhanced_embedding = self.embedding_service.encode_enhanced_document(enhanced_data)
            if enhanced_embedding is not None:
                document.enhanced_embedding = enhanced_embedding.tolist()
                document.save(update_fields=['enhanced_embedding', 'updated_at'])
                logger.info(f"Enhanced embedding updated for document {document.document_id}")
            
        except Exception as e:
            logger.error(
                f"Error updating enhanced embedding for document {document.document_id}: {e}",
                exc_info=True
            )
    
    def _update_document_status(self, document: Document):
        """
        Actualiza el estado general del documento basado en los estados de análisis.
        """
        document.refresh_from_db()
        
        statuses = [
            document.metadata_analysis_status,
            document.summary_analysis_status,
            document.persons_analysis_status
        ]
        
        # Si alguno está procesando
        if AnalysisStatus.PROCESSING in statuses:
            document.status = DocumentStatus.PROCESSING
        # Si todos están completados
        elif all(s == AnalysisStatus.COMPLETED for s in statuses):
            document.status = DocumentStatus.PROCESSED
            document.processed_at = timezone.now()
        # Si alguno está completado pero no todos
        elif AnalysisStatus.COMPLETED in statuses:
            document.status = DocumentStatus.PARTIAL
        # Si alguno falló
        elif AnalysisStatus.FAILED in statuses:
            # Si todos fallaron
            if all(s == AnalysisStatus.FAILED for s in statuses):
                document.status = DocumentStatus.FAILED
            else:
                document.status = DocumentStatus.PARTIAL
        # Si todos están pendientes
        else:
            document.status = DocumentStatus.UPLOADED
        
        document.save(update_fields=['status', 'processed_at', 'updated_at'])
        logger.info(f"Document status updated to: {document.status}")
