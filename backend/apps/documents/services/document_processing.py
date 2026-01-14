# documents/services/document_processing.py
import logging
import os
from django.utils import timezone

from apps.documents.services.metadata_extractor import DocumentMetadataExtractor
from apps.documents.services.document_summarizer import DocumentSummarizer
from apps.documents.services.person_extractor import PersonExtractor
from apps.documents.services.chunking_service import ChunkingService
from apps.documents.services.embedding_service import get_embedding_service
from apps.documents.services.clean_embeddings_service import get_clean_embedding_service
from apps.documents.services.parsers.text_extraction import TextExtractionService
from apps.documents.models import Document, DocumentStatus, DocumentFileType, DocumentChunk

logger = logging.getLogger(__name__)


class DocumentProcessingService:
    """
    Orchestrates the complete document processing pipeline.
    
    Uses optimized 3-prompt approach:
    1. Metadata extraction - type, area, subject, case number, title, jurisdictional body
    2. Summary generation - executive summary, dates, decision, keywords
    3. Person extraction - all involved persons with their roles
    """
    
    def __init__(self):
        self.text_extractor = TextExtractionService()
        self.metadata_extractor = DocumentMetadataExtractor()
        self.summarizer = DocumentSummarizer()
        self.person_extractor = PersonExtractor()
        self.chunking_service = ChunkingService(chunk_size=1000, chunk_overlap=200)
        self.embedding_service = get_embedding_service()
        self.clean_embedding_service = get_clean_embedding_service()
        
    def process_document(
        self, 
        document: Document,
        generate_summary: bool = True,
        summarizer_type: str = 'ollama'
    ) -> bool:
        """
        Process document through complete pipeline with error handling.
        
        IMPORTANTE: El clean_embedding SIEMPRE se genera (no depende de Ollama).
        El resumen es OPCIONAL (controlado por generate_summary).
        
        Modos de procesamiento:
        - generate_summary=False: Modo 'chat_only' - Solo extracción + clean_embedding
        - generate_summary=True: Modo 'full_analysis' - Incluye resumen con Ollama
        
        Args:
            document: Document instance to process
            generate_summary: Si True, genera resumen con Ollama (default: True)
            summarizer_type: Tipo de generador de resumen ('ollama' o 'bart')
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            ##### TEXT EXTRACTION #####

            # Update status
            document.status = DocumentStatus.PROCESSING
            document.save(update_fields=['status', 'updated_at'])

            # Detect file type and size
            file_name = getattr(document.file_path, 'name', '')
            file_extension = file_name.lower().split('.')[-1] if '.' in file_name else 'other'
            
            # Map extension to DocumentFileType
            file_type_mapping = {
                'pdf': DocumentFileType.PDF,
                'docx': DocumentFileType.DOCX,
                'doc': DocumentFileType.DOC,
                'txt': DocumentFileType.TXT,
            }
            document.file_type = file_type_mapping.get(file_extension, DocumentFileType.OTHER)
            
            # Get file size
            try:
                document.file_size = document.file_path.size
            except Exception as e:
                logger.warning(f"Could not get file size: {e}")
                document.file_size = 0

            # Read file content
            with document.file_path.open('rb') as f:
                file_content = f.read()
                
            # Extract text
            extracted_text, metadata = self.text_extractor.extract_text(
                file_content,
                file_name,
            )
            
            if not extracted_text:
                document.status = DocumentStatus.FAILED
                document.error_message = "No se pudo extraer texto del documento"
                document.save(update_fields=['status', 'error_message', 'updated_at'])
                return False
            
            # Update document with extracted content and metadata
            document.content = extracted_text
            document.pages = metadata.get('n_hojas', 0)

            ##### PROMPT 1: METADATA EXTRACTION #####
            logger.info(f"Starting metadata extraction for document {document.document_id}")
            
            try:
                metadata = self.metadata_extractor.extract_metadata(document.content)
                
                # Update document with all metadata
                document.title = metadata.get('title', file_name)
                document.doc_type = metadata.get('doc_type')
                document.legal_area = metadata.get('legal_area')
                document.legal_subject = metadata.get('legal_subject')
                document.case_number = metadata.get('case_number')
                document.jurisdictional_body = metadata.get('jurisdictional_body')
                document.resolution_number = metadata.get('resolution_number')
                document.issue_place = metadata.get('issue_place')
                document.document_date = metadata.get('document_date')
                
                logger.info(
                    f"Metadata extraction completed - "
                    f"Type: {document.doc_type}, Area: {document.legal_area}, "
                    f"Resolution: {document.resolution_number}, Date: {document.document_date}"
                )
                
            except Exception as e:
                logger.error(
                    f"Metadata extraction error for document {document.document_id}: {e}",
                    exc_info=True
                )
                # Set defaults if metadata extraction fails
                if not document.title:
                    document.title = file_name

            ##### PROMPT 2: SUMMARY GENERATION (OPTIONAL - requires Ollama) #####
            if generate_summary:
                logger.info(f"Starting summary generation for document {document.document_id} using {summarizer_type}")
                
                try:
                    doc_type_name = document.doc_type.name if document.doc_type else 'Documento Legal'
                    legal_area_name = document.legal_area.name if document.legal_area else 'General'
                    
                    summary_data = self.summarizer.generate_summary(
                        document.content,
                        doc_type_name,
                        legal_area_name,
                        document.legal_subject,
                        summarizer_type=summarizer_type
                    )
                    
                    # Update document with summary
                    document.summary = summary_data.get('summary_text')
                    document.summarizer_type = summarizer_type
                    
                    logger.info(f"Summary generation completed for document {document.document_id}")
                    
                except Exception as e:
                    logger.error(
                        f"Summary generation error for document {document.document_id}: {e}",
                        exc_info=True
                    )
                    # Continue without summary if it fails
            else:
                logger.info(f"Skipping summary generation for document {document.document_id} (generate_summary=False)")

            ##### PROMPT 3: PERSON EXTRACTION #####
            logger.info(f"Starting person extraction for document {document.document_id}")
            
            try:
                persons_data = self.person_extractor.extract_and_link_persons(
                    document.content,
                    document
                )
                
                total_persons = sum(len(v) for v in persons_data.values())
                logger.info(
                    f"Person extraction completed - {total_persons} persons linked to document"
                )
                
            except Exception as e:
                logger.error(
                    f"Person extraction error for document {document.document_id}: {e}",
                    exc_info=True
                )
                # Continue without persons if it fails

            ##### CLEAN EMBEDDING GENERATION (ALWAYS - does NOT require Ollama) #####
            # Generate clean embedding from text WITHOUT stopwords
            # This is the PRIMARY embedding for similarity and clustering
            logger.info(f"Generating clean embedding for document {document.document_id}")
            try:
                clean_embedding = self.clean_embedding_service.generate_document_embedding(
                    document.content,
                    clean_text=True,
                    pooling_strategy='weighted_start'  # Prioritize beginning of document
                )
                if clean_embedding is not None:
                    document.clean_embedding = clean_embedding.tolist()
                    logger.info(f"Generated clean embedding for document {document.document_id}")
                    
                    # Log statistics for monitoring
                    stats = self.clean_embedding_service.get_text_statistics(document.content)
                    logger.info(
                        f"Clean embedding stats: {stats['original_words']} → {stats['cleaned_words']} words "
                        f"({stats['reduction_percent']}% reduction), {stats['num_chunks']} chunks"
                    )
                else:
                    logger.warning(f"Clean embedding generation returned None for document {document.document_id}")
                    
            except Exception as e:
                logger.error(f"Error generating clean embedding for document {document.document_id}: {e}")
                # Continue without clean embedding if it fails
                # This is critical, so log with exc_info
                logger.error("Clean embedding error details:", exc_info=True)

            ##### EMBEDDING GENERATION FOR SUMMARY (only if summary exists) #####
            # Generate embedding for document summary if available
            if document.summary:
                try:
                    summary_embedding = self.embedding_service.encode_document_summary(document.summary)
                    if summary_embedding is not None:
                        document.summary_embedding = summary_embedding.tolist()
                        logger.info(f"Generated summary embedding for document {document.document_id}")
                except Exception as e:
                    logger.error(f"Error generating summary embedding for document {document.document_id}: {e}")
                    # Continue without embedding if it fails
            
            ##### ENHANCED EMBEDDING GENERATION (legacy - kept for compatibility) #####
            # Generate enhanced embedding combining multiple fields for better similarity search
            # NOTE: This is the OLD approach. clean_embedding is now the primary embedding.
            try:
                # Prepare document data for enhanced embedding
                document_persons = document.document_persons.select_related('person').all()
                persons_data = [
                    {
                        'name': dp.person.name,
                        'role': dp.role
                    }
                    for dp in document_persons
                ]
                
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
                
                enhanced_embedding = self.embedding_service.encode_enhanced_document(enhanced_data)
                if enhanced_embedding is not None:
                    document.enhanced_embedding = enhanced_embedding.tolist()
                    logger.info(f"Generated enhanced embedding for document {document.document_id}")
                    
            except Exception as e:
                logger.error(f"Error generating enhanced embedding for document {document.document_id}: {e}")
                # Continue without enhanced embedding if it fails

            # Mark as processed
            document.status = DocumentStatus.PROCESSED
            document.processed_at = timezone.now()
            document.error_message = None  # Clear any previous errors
            
            # List of fields to update
            update_fields = [
                'title', 'content', 'pages', 'status', 'file_type', 'file_size',
                'updated_at', 'processed_at', 'doc_type', 'legal_area', 'legal_subject',
                'summary', 'summarizer_type', 'jurisdictional_body', 'case_number', 'error_message', 
                'summary_embedding', 'enhanced_embedding', 'clean_embedding',
                'resolution_number', 'issue_place', 'document_date'
            ]
            
            document.save(update_fields=update_fields)
            
            ##### CHUNKING #####
            # Create chunks from the PDF with contextual page information
            try:
                num_chunks = self.chunking_service.create_chunks_for_document(
                    document, 
                    method='contextual'  # Extracts from PDF with page context
                )
                logger.info(
                    f"Created {num_chunks} chunks for document {document.document_id}"
                )
                
                ##### EMBEDDING GENERATION FOR CHUNKS #####
                # Generate embeddings for all chunks
                chunks = DocumentChunk.objects.filter(document_id=document).order_by('order_number')
                if chunks.exists():
                    try:
                        chunk_contents = [chunk.content for chunk in chunks]
                        chunk_embeddings = self.embedding_service.encode_chunks_batch(chunk_contents, batch_size=32)
                        
                        # Save embeddings to chunks
                        for chunk, embedding in zip(chunks, chunk_embeddings):
                            chunk.content_embedding = embedding.tolist()
                            chunk.save(update_fields=['content_embedding'])
                        
                        logger.info(f"Generated embeddings for {len(chunk_embeddings)} chunks of document {document.document_id}")
                    except Exception as e:
                        logger.error(f"Error generating chunk embeddings for document {document.document_id}: {e}")
                        # Continue without embeddings if it fails
                
            except Exception as e:
                logger.error(
                    f"Error creating chunks for document {document.document_id}: {e}",
                    exc_info=True
                )
                # Don't fail the entire process if chunking fails
            
            logger.info(f"Successfully processed document: {document.document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing document {document.document_id}: {str(e)}", exc_info=True)
            document.status = DocumentStatus.FAILED
            document.error_message = str(e)
            document.save(update_fields=['status', 'error_message', 'updated_at'])
            return False

    # ============================================================================
    # LIGHT MODE - Process document WITHOUT Ollama/LLM
    # ============================================================================
    
    def process_document_light(self, document: Document) -> bool:
        """
        Process document with ONLY essential operations - NO LLM/Ollama calls.
        
        This mode is designed for bulk uploads where:
        - Speed is critical
        - Ollama is not available or should not be used
        - Basic metadata is sufficient
        - Clean embeddings for similarity/clustering are the priority
        
        Pipeline:
        1. Text extraction (PDF/DOCX parsing)
        2. Regex-only metadata extraction (no LLM)
        3. Clean embedding generation (SentenceTransformers - no Ollama)
        4. Chunk creation with embeddings
        
        SKIPS:
        - Summary generation (requires Ollama)
        - Person extraction (requires Ollama)
        - Enhanced embedding (depends on summary/persons)
        - Summary embedding (depends on summary)
        
        Args:
            document: Document instance to process
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"=== LIGHT MODE PROCESSING for document {document.document_id} ===")
            
            ##### TEXT EXTRACTION #####
            document.status = DocumentStatus.PROCESSING
            document.save(update_fields=['status', 'updated_at'])

            # Detect file type and size
            file_name = getattr(document.file_path, 'name', '')
            file_extension = file_name.lower().split('.')[-1] if '.' in file_name else 'other'
            
            file_type_mapping = {
                'pdf': DocumentFileType.PDF,
                'docx': DocumentFileType.DOCX,
                'doc': DocumentFileType.DOC,
                'txt': DocumentFileType.TXT,
            }
            document.file_type = file_type_mapping.get(file_extension, DocumentFileType.OTHER)
            
            try:
                document.file_size = document.file_path.size
            except Exception as e:
                logger.warning(f"Could not get file size: {e}")
                document.file_size = 0

            # Read and extract text
            with document.file_path.open('rb') as f:
                file_content = f.read()
                
            extracted_text, extraction_metadata = self.text_extractor.extract_text(
                file_content,
                file_name,
            )
            
            if not extracted_text:
                document.status = DocumentStatus.FAILED
                document.error_message = "No se pudo extraer texto del documento"
                document.save(update_fields=['status', 'error_message', 'updated_at'])
                return False
            
            document.content = extracted_text
            document.pages = extraction_metadata.get('n_hojas', 0)
            logger.info(f"Text extracted: {len(extracted_text)} chars, {document.pages} pages")

            ##### REGEX-ONLY METADATA EXTRACTION (NO LLM) #####
            logger.info(f"Starting REGEX-ONLY metadata extraction for document {document.document_id}")
            
            try:
                metadata = self.metadata_extractor.extract_metadata_regex_only(document.content)
                
                document.title = metadata.get('title', file_name)
                document.doc_type = metadata.get('doc_type')
                document.legal_area = metadata.get('legal_area')
                document.legal_subject = metadata.get('legal_subject')
                document.case_number = metadata.get('case_number')
                document.jurisdictional_body = metadata.get('jurisdictional_body')
                document.resolution_number = metadata.get('resolution_number')
                document.issue_place = metadata.get('issue_place')
                document.document_date = metadata.get('document_date')
                
                logger.info(
                    f"Regex metadata extraction completed - "
                    f"Type: {metadata.get('doc_type_name')}, Area: {metadata.get('legal_area_name')}, "
                    f"Resolution: {document.resolution_number}, Date: {document.document_date}"
                )
                
            except Exception as e:
                logger.error(
                    f"Regex metadata extraction error for document {document.document_id}: {e}",
                    exc_info=True
                )
                if not document.title:
                    document.title = file_name

            ##### CLEAN EMBEDDING GENERATION (SentenceTransformers - no Ollama) #####
            logger.info(f"Generating clean embedding for document {document.document_id}")
            try:
                clean_embedding = self.clean_embedding_service.generate_document_embedding(
                    document.content,
                    clean_text=True,
                    pooling_strategy='weighted_start'
                )
                if clean_embedding is not None:
                    document.clean_embedding = clean_embedding.tolist()
                    logger.info(f"Generated clean embedding (768d) for document {document.document_id}")
                    
                    stats = self.clean_embedding_service.get_text_statistics(document.content)
                    logger.info(
                        f"Clean embedding stats: {stats['original_words']} → {stats['cleaned_words']} words "
                        f"({stats['reduction_percent']}% reduction), {stats['num_chunks']} chunks"
                    )
                else:
                    logger.warning(f"Clean embedding generation returned None for document {document.document_id}")
                    
            except Exception as e:
                logger.error(f"Error generating clean embedding for document {document.document_id}: {e}")
                logger.error("Clean embedding error details:", exc_info=True)

            # Mark as processed
            document.status = DocumentStatus.PROCESSED
            document.processed_at = timezone.now()
            document.error_message = None
            
            # Only update the fields we've actually set (no summary, no enhanced_embedding)
            update_fields = [
                'title', 'content', 'pages', 'status', 'file_type', 'file_size',
                'updated_at', 'processed_at', 'doc_type', 'legal_area', 'legal_subject',
                'jurisdictional_body', 'case_number', 'error_message', 'clean_embedding',
                'resolution_number', 'issue_place', 'document_date'
            ]
            
            document.save(update_fields=update_fields)

            ##### CHUNKING (basic - no page context from PDF) #####
            try:
                num_chunks = self.chunking_service.create_chunks_for_document(
                    document, 
                    method='basic'  # Use basic chunking for speed
                )
                logger.info(f"Created {num_chunks} chunks for document {document.document_id}")
                
                # Generate embeddings for chunks
                chunks = DocumentChunk.objects.filter(document_id=document).order_by('order_number')
                if chunks.exists():
                    try:
                        chunk_contents = [chunk.content for chunk in chunks]
                        chunk_embeddings = self.embedding_service.encode_chunks_batch(chunk_contents, batch_size=32)
                        
                        for chunk, embedding in zip(chunks, chunk_embeddings):
                            chunk.content_embedding = embedding.tolist()
                            chunk.save(update_fields=['content_embedding'])
                        
                        logger.info(f"Generated embeddings for {len(chunk_embeddings)} chunks of document {document.document_id}")
                    except Exception as e:
                        logger.error(f"Error generating chunk embeddings for document {document.document_id}: {e}")
                
            except Exception as e:
                logger.error(
                    f"Error creating chunks for document {document.document_id}: {e}",
                    exc_info=True
                )
            
            logger.info(f"=== LIGHT MODE PROCESSING COMPLETE for document {document.document_id} ===")
            return True
            
        except Exception as e:
            logger.error(f"Error in light mode processing document {document.document_id}: {str(e)}", exc_info=True)
            document.status = DocumentStatus.FAILED
            document.error_message = str(e)
            document.save(update_fields=['status', 'error_message', 'updated_at'])
            return False
