from django.test import TestCase
from django.core.files.base import ContentFile
from apps.documents.models import Document, DocumentStatus
from apps.documents.services.document_processing import DocumentProcessingService


# class DocumentProcessingTests(TestCase):
# 	def test_classification_and_save_tipo_documento(self):
# 		# Create a dummy document file
# 		doc = Document.objects.create(
# 			nombre='test_doc.pdf',
# 			archivo_original=ContentFile(b'This is a fake pdf content', 'test_doc.pdf'),
# 			mime_type='application/pdf',
# 			tamaño_archivo=1234,
# 		)

# 		# Monkeypatch the classifier to return a known label without calling LLM
# 		service = DocumentProcessingService()

# 		original_classifier = service.classifier.classify_document

# 		try:
# 			service.classifier.classify_document = lambda text: 'Contrato'

# 			result = service.process_document(doc)

# 			# Reload from DB
# 			doc.refresh_from_db()

# 			self.assertTrue(result)
# 			self.assertEqual(doc.estado, DocumentStatus.PROCESSED)
# 			self.assertEqual(doc.tipo_documento, 'Contrato')

# 		finally:
# 			service.classifier.classify_document = original_classifier
