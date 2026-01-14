# documents/services/text_extraction.py
"""
Servicio de Extracción de Texto para múltiples formatos de archivo.

Versión 2.0: Incluye limpieza automática de encabezados/pies de página
repetitivos en documentos judiciales.
"""
import io

import logging
from typing import Optional, Tuple
from django.core.files.uploadedfile import UploadedFile

logger = logging.getLogger(__name__)


class TextExtractionService:
    """
    Service for extracting text from various file formats.
    
    Supported formats:
    - PDF (using PyMuPDF, pdfplumber, or PyPDF2)
    - DOCX
    - TXT
    
    Version 2.0: Added automatic header/footer cleaning for judicial documents.
    """
    
    def __init__(self, clean_headers: bool = True):
        """
        Initialize the extraction service.
        
        Args:
            clean_headers: Whether to clean repetitive headers/footers (default: True)
        """
        self.clean_headers = clean_headers
        self._extractors = self._initialize_extractors()
        self._header_cleaner = None  # Lazy load
    
    @property
    def header_cleaner(self):
        """Lazy load header cleaner."""
        if self._header_cleaner is None and self.clean_headers:
            try:
                from apps.documents.services.header_cleaner_service import get_header_cleaner_service
                self._header_cleaner = get_header_cleaner_service()
            except ImportError:
                logger.warning("HeaderCleanerService not available")
        return self._header_cleaner
    
    def _initialize_extractors(self):
        """Initialize available extractors with fallback order"""
        extractors = []
        
        # Try PyMuPDF first (best for PDFs)
        try:
            import fitz
            extractors.append(('pymupdf', self._extract_with_pymupdf))
        except ImportError:
            logger.warning("PyMuPDF not available")
        
        # Try pdfplumber second
        try:
            import pdfplumber
            extractors.append(('pdfplumber', self._extract_with_pdfplumber))
        except ImportError:
            logger.warning("pdfplumber not available")
        
        # Try PyPDF2 as last resort
        try:
            from PyPDF2 import PdfReader
            extractors.append(('pypdf2', self._extract_with_pypdf2))
        except ImportError:
            logger.warning("PyPDF2 not available")
        
        return extractors
    
    def extract_text(self, file_content: bytes, file_name: str, mime_type: str = None) -> Tuple[Optional[str], dict]:
        """
        Extract text from file content
        
        Returns:
            Tuple of (extracted_text, metadata)
        """
        file_extension = file_name.lower().split('.')[-1] if '.' in file_name else ''
        
        try:
            if file_extension == 'txt' or mime_type == 'text/plain':
                return self._extract_txt(file_content), {}
            
            elif file_extension == 'pdf' or mime_type == 'application/pdf':
                return self._extract_pdf(file_content, file_name)
            
            elif file_extension in ['docx', 'doc']:
                return self._extract_docx(file_content), {}
            
            else:
                logger.warning(f"Unsupported file type: {file_extension}")
                return None, {'error': f'Unsupported file type: {file_extension}'}
                
        except Exception as e:
            logger.error(f"Error extracting text from {file_name}: {str(e)}")
            return None, {'error': str(e)}
    
    def _extract_pdf(self, pdf_bytes: bytes, file_name: str) -> Tuple[Optional[str], dict]:
        """
        Extract text from PDF with fallback strategies and header cleaning.
        
        Version 2.0: Includes automatic header/footer cleaning.
        """
        metadata = {
            'n_hojas': 0,
            'extractor_used': None,
            'has_scanned_pages': False,
            'headers_cleaned': False,
            'chars_removed_by_cleaning': 0
        }
        
        # Try each extractor in order
        for extractor_name, extractor_func in self._extractors:
            try:
                logger.info(f"Trying {extractor_name} for PDF extraction")
                text, extractor_metadata = extractor_func(pdf_bytes)
                metadata.update(extractor_metadata)
                metadata['extractor_used'] = extractor_name
                
                if text and len(text.strip()) > 50:  # Minimum text threshold
                    logger.info(f"Successfully extracted text using {extractor_name}")
                    
                    # V2.0: Aplicar limpieza de encabezados si está disponible
                    if self.clean_headers and self.header_cleaner:
                        original_len = len(text)
                        text = self.header_cleaner.clean_document_text(text)
                        cleaned_len = len(text)
                        chars_removed = original_len - cleaned_len
                        
                        metadata['headers_cleaned'] = True
                        metadata['chars_removed_by_cleaning'] = chars_removed
                        
                        if chars_removed > 0:
                            percent_removed = (chars_removed / original_len) * 100
                            logger.info(
                                f"Header cleaning removed {chars_removed} chars "
                                f"({percent_removed:.1f}%) from {file_name}"
                            )
                    
                    return text, metadata
                    
            except Exception as e:
                logger.warning(f"{extractor_name} failed: {e}")
                continue
        
        logger.error("All PDF extractors failed")
        return None, metadata
    
    def _extract_with_pymupdf(self, pdf_bytes: bytes) -> Tuple[str, dict]:
        """Extract using PyMuPDF (fitz)"""
        import fitz
        metadata = {
            'n_hojas': 0,
            'has_scanned_pages': False
        }
        
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        metadata['n_hojas'] = pdf_document.page_count
        
        text = ""
        scanned_pages = 0
        
        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            page_text = page.get_text()
            
            # Check if page might be scanned
            if len(page_text.strip()) < 100:
                scanned_pages += 1
            
            text += page_text + "\n"
        
        pdf_document.close()
        
        if scanned_pages > 0:
            metadata['has_scanned_pages'] = True
            metadata['scanned_pages_count'] = scanned_pages
        
        return text, metadata
    
    def _extract_with_pdfplumber(self, pdf_bytes: bytes) -> Tuple[str, dict]:
        """Extract using pdfplumber"""
        import pdfplumber
        
        metadata = {'n_hojas': 0}
        text = ""
        
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            metadata['n_hojas'] = len(pdf.pages)
            
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        return text, metadata
    
    def _extract_with_pypdf2(self, pdf_bytes: bytes) -> Tuple[str, dict]:
        """Extract using PyPDF2"""
        from PyPDF2 import PdfReader
        
        metadata = {'n_hojas': 0}
        
        reader = PdfReader(io.BytesIO(pdf_bytes))
        metadata['n_hojas'] = len(reader.pages)
        
        text_pages = []
        for page in reader.pages:
            page_text = page.extract_text()
            text_pages.append(page_text if page_text else "")
        
        return "\n".join(text_pages), metadata
    
    def _extract_txt(self, file_content: bytes) -> str:
        """Extract text from TXT file"""
        try:
            return file_content.decode('utf-8')
        except UnicodeDecodeError:
            return file_content.decode('latin-1')
    
    def _extract_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX file"""
        from docx import Document
        
        doc = Document(io.BytesIO(file_content))
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])