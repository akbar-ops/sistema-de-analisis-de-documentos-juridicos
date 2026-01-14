# apps/documents/services/chunking_service.py
"""
Servicio de Chunking Inteligente para Documentos Jurídicos.

Este servicio:
1. Extrae texto de PDFs preservando estructura de páginas
2. LIMPIA encabezados/pies de página repetitivos (nuevo!)
3. Aplica RecursiveCharacterTextSplitter respetando límites semánticos
4. Mantiene metadatos de páginas y contexto
5. GENERA embeddings de 768d para RAG de alta calidad (v3.0)

Versión 3.0: Incluye generación automática de embeddings de 768d
"""
import logging
import io
from typing import List, Dict, Optional, Tuple
from langchain_text_splitters import RecursiveCharacterTextSplitter
from PyPDF2 import PdfReader

from apps.documents.models import Document, DocumentChunk
from apps.documents.services.header_cleaner_service import get_header_cleaner_service
from apps.documents.services.chunk_embedding_service import get_chunk_embedding_service

logger = logging.getLogger(__name__)


class ChunkingService:
    """
    Service for extracting and chunking documents intelligently using LangChain.
    
    This service:
    1. Extracts text from PDF preserving page structure
    2. CLEANS repetitive headers/footers from each page (v2.0)
    3. Applies RecursiveCharacterTextSplitter respecting semantic boundaries
    4. Maintains metadata about page numbers and context
    
    Version 2.0: Added header/footer cleaning for judicial documents
    """
    
    # Optimized separators for legal documents in Spanish
    LEGAL_SEPARATORS = [
        "\n\n## PÁGINA ",       # Page markers (if we add them)
        "\n\nARTÍCULO",        # Article breaks
        "\n\nCAPÍTULO",        # Chapter breaks  
        "\n\nCONSIDERANDO",    # Considerations
        "\n\nRESUELVE",        # Resolutions
        "\n\nVISTOS",          # Legal basis
        "\n\nPOR TANTO",       # Therefore clauses
        "\n\nY TENIENDO PRESENTE",  # And considering
        "\n\nANTECEDENTES",    # Background
        "\n\nFUNDAMENTOS",     # Legal foundations
        "\n\nPRIMERO",         # PRIMERO.- (legal sections)
        "\n\nSEGUNDO",         # SEGUNDO.-
        "\n\nTERCERO",         # TERCERO.-
        "\n\n",                # Double line breaks (paragraphs)
        "\n",                  # Single line breaks
        ". ",                  # Sentences
        "; ",                  # Semicolons
        ", ",                  # Commas
        " ",                   # Words
        "",                    # Characters (last resort)
    ]
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200, clean_headers: bool = True):
        """
        Initialize the chunking service.
        
        Args:
            chunk_size: Maximum size of each chunk in characters
            chunk_overlap: Number of characters to overlap between chunks
            clean_headers: Whether to clean repetitive headers/footers (default: True)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.clean_headers = clean_headers
        
        # Initialize header cleaner
        if self.clean_headers:
            self.header_cleaner = get_header_cleaner_service()
        else:
            self.header_cleaner = None
        
        # Initialize RecursiveCharacterTextSplitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=self.LEGAL_SEPARATORS,
            length_function=len,
            is_separator_regex=False,
        )
        
        logger.info(
            f"ChunkingService initialized: chunk_size={chunk_size}, "
            f"overlap={chunk_overlap}, clean_headers={clean_headers}"
        )
    
    def extract_text_by_pages(self, pdf_path: str) -> List[Tuple[int, str]]:
        """
        Extract text from PDF preserving page structure.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of tuples (page_number, page_text)
        """
        try:
            reader = PdfReader(pdf_path)
            pages_text = []
            
            for page_num, page in enumerate(reader.pages, start=1):
                try:
                    text = page.extract_text()
                    if text and text.strip():
                        pages_text.append((page_num, text.strip()))
                    else:
                        logger.warning(f"Page {page_num} has no extractable text")
                        pages_text.append((page_num, ""))
                except Exception as e:
                    logger.error(f"Error extracting text from page {page_num}: {e}")
                    pages_text.append((page_num, ""))
            
            logger.info(f"Extracted text from {len(pages_text)} pages")
            
            # V2.0: Limpiar encabezados/pies repetitivos si está habilitado
            if self.clean_headers and self.header_cleaner and len(pages_text) > 1:
                original_total = sum(len(t) for _, t in pages_text)
                pages_text = self.header_cleaner.clean_pages_text(pages_text)
                cleaned_total = sum(len(t) for _, t in pages_text)
                removed_percent = ((original_total - cleaned_total) / original_total * 100) if original_total > 0 else 0
                logger.info(f"Headers cleaned: removed {removed_percent:.1f}% of text ({original_total - cleaned_total} chars)")
            
            return pages_text
            
        except Exception as e:
            logger.error(f"Error reading PDF: {e}", exc_info=True)
            return []
    
    def create_contextual_text(self, pages_text: List[Tuple[int, str]]) -> str:
        """
        Create a single text with page markers for context.
        
        Mejora v2: Los marcadores de página se agregan de forma inline
        para evitar chunks muy pequeños que solo contengan el marcador.
        
        Args:
            pages_text: List of (page_number, text) tuples
            
        Returns:
            Combined text with page markers
        """
        contextual_parts = []
        
        for page_num, text in pages_text:
            if text.strip():
                # Agregar marcador de página de forma más sutil (inline)
                # Esto evita crear chunks que solo tengan el marcador
                page_marker = f"[Página {page_num}] "
                contextual_parts.append(f"{page_marker}{text}")
        
        return "\n\n".join(contextual_parts)
    
    def split_text_with_context(self, text: str) -> List[Dict]:
        """
        Split text into chunks preserving context information.
        
        Args:
            text: Text to split (with page markers)
            
        Returns:
            List of dictionaries with chunk info: {
                'content': str,
                'page_start': int,
                'page_end': int,
                'order': int
            }
        """
        if not text or not text.strip():
            return []
        
        # Split using RecursiveCharacterTextSplitter
        raw_chunks = self.text_splitter.split_text(text)
        
        chunks_with_context = []
        
        for order, chunk_content in enumerate(raw_chunks, start=1):
            # Extract page numbers from chunk
            page_start = self._extract_page_start(chunk_content)
            page_end = self._extract_page_end(chunk_content)
            
            # Clean page markers from content (optional - keep for context)
            # cleaned_content = self._clean_page_markers(chunk_content)
            
            chunks_with_context.append({
                'content': chunk_content.strip(),
                'page_start': page_start,
                'page_end': page_end,
                'order': order
            })
        
        logger.info(f"Created {len(chunks_with_context)} chunks with context")
        return chunks_with_context
    
    def _extract_page_start(self, text: str) -> Optional[int]:
        """Extract the first page number mentioned in the chunk."""
        import re
        # Buscar formato nuevo [Página X] o formato antiguo ## PÁGINA X
        match = re.search(r'\[Página (\d+)\]|## PÁGINA (\d+)', text)
        if match:
            return int(match.group(1) or match.group(2))
        return None
    
    def _extract_page_end(self, text: str) -> Optional[int]:
        """Extract the last page number mentioned in the chunk."""
        import re
        matches = re.findall(r'\[Página (\d+)\]|## PÁGINA (\d+)', text)
        if matches:
            # Cada match es una tupla, obtener el valor no vacío
            last_match = matches[-1]
            return int(last_match[0] or last_match[1])
        return None
    
    def _clean_page_markers(self, text: str) -> str:
        """Remove page markers from text."""
        import re
        # Limpiar ambos formatos
        text = re.sub(r'\[Página \d+\]\s*', '', text)
        text = re.sub(r'\n*## PÁGINA \d+\n*', '\n\n', text)
        return text.strip()
    
    def create_chunks_for_document(
        self, 
        document: Document,
        method: str = 'contextual'
    ) -> int:
        """
        Create chunks for a document from its PDF file.
        
        This is the main method that:
        1. Extracts text from PDF by pages
        2. Creates contextual text with page markers
        3. Splits into chunks using RecursiveCharacterTextSplitter
        4. Saves chunks with metadata to database
        
        Args:
            document: Document instance with file_path
            method: 'contextual' (with page info) or 'simple' (just text)
            
        Returns:
            Number of chunks created
        """
        if not document.file_path:
            logger.warning(
                f"Document {document.document_id} has no file_path"
            )
            return 0
        
        try:
            # Get the file path
            file_path = document.file_path.path
            
            # Extract text by pages
            pages_text = self.extract_text_by_pages(file_path)
            
            if not pages_text:
                logger.warning(
                    f"No text extracted from document {document.document_id}"
                )
                return 0
            
            # Create contextual text
            if method == 'contextual':
                full_text = self.create_contextual_text(pages_text)
                chunks_info = self.split_text_with_context(full_text)
            else:
                # Simple method: just concatenate all pages
                full_text = "\n\n".join([text for _, text in pages_text if text])
                raw_chunks = self.text_splitter.split_text(full_text)
                chunks_info = [
                    {
                        'content': chunk,
                        'page_start': None,
                        'page_end': None,
                        'order': i
                    }
                    for i, chunk in enumerate(raw_chunks, start=1)
                ]
            
            if not chunks_info:
                logger.warning(
                    f"No chunks created for document {document.document_id}"
                )
                return 0
            
            # Delete existing chunks
            existing_count = DocumentChunk.objects.filter(document_id=document).count()
            if existing_count > 0:
                DocumentChunk.objects.filter(document_id=document).delete()
                logger.info(
                    f"Deleted {existing_count} existing chunks for document "
                    f"{document.document_id}"
                )
            
            # Create DocumentChunk objects
            chunk_objects = []
            for chunk_info in chunks_info:
                chunk_obj = DocumentChunk(
                    document_id=document,
                    order_number=chunk_info['order'],
                    content=chunk_info['content'],
                    # Store page info in content if available
                    # You could add page_start/page_end fields to model if needed
                )
                chunk_objects.append(chunk_obj)
            
            # Bulk create
            DocumentChunk.objects.bulk_create(chunk_objects)
            
            num_chunks = len(chunk_objects)
            chunk_sizes = [len(c.content) for c in chunk_objects]
            avg_size = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0
            
            logger.info(
                f"Created {num_chunks} chunks for document {document.document_id} "
                f"(avg size: {avg_size:.0f} chars, method: {method})"
            )
            
            # Generar embeddings de 768d para RAG de alta calidad
            try:
                embedding_service = get_chunk_embedding_service()
                embedded_count = embedding_service.embed_document_chunks(document)
                logger.info(
                    f"Generated 768d embeddings for {embedded_count} chunks "
                    f"of document {document.document_id}"
                )
            except Exception as embed_error:
                logger.warning(
                    f"Could not generate 768d embeddings for document "
                    f"{document.document_id}: {embed_error}. "
                    "RAG will use fallback 384d embeddings."
                )
            
            return num_chunks
            
        except Exception as e:
            logger.error(
                f"Error creating chunks for document {document.document_id}: {e}",
                exc_info=True
            )
            return 0
    
    def get_chunk_stats(self, document: Document) -> Dict:
        """Get statistics about chunks for a document."""
        chunks = DocumentChunk.objects.filter(document_id=document)
        
        if not chunks.exists():
            return {
                'total_chunks': 0,
                'avg_chunk_size': 0,
                'min_chunk_size': 0,
                'max_chunk_size': 0,
                'total_content_size': 0,
            }
        
        chunk_sizes = [len(chunk.content) for chunk in chunks]
        
        return {
            'total_chunks': len(chunk_sizes),
            'avg_chunk_size': sum(chunk_sizes) / len(chunk_sizes),
            'min_chunk_size': min(chunk_sizes),
            'max_chunk_size': max(chunk_sizes),
            'total_content_size': sum(chunk_sizes),
        }
    