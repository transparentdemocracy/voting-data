import unittest

from transparentdemocracy.documents.references import parse_document_reference
from transparentdemocracy.model import DocumentsReference


class DocumentReferencesTest(unittest.TestCase):
	def test_parse_document_reference_without_subdocs(self):
		actual = parse_document_reference("1234")

		self.assertEqual(DocumentsReference(
			document_reference=1234,
			all_documents_reference="1234",
			main_document_reference=None,
			sub_document_references=[]
		), actual)

	def test_parse_document_reference_with_single_subdoc(self):
		actual = parse_document_reference("1234/5")

		self.assertEqual(DocumentsReference(
			document_reference=1234,
			all_documents_reference="1234/5",
			main_document_reference=5,
			sub_document_references=[5]
		), actual)

	def test_parse_document_reference_with_subdoc_range(self):
		actual = parse_document_reference("1234/2-5")

		self.assertEqual(DocumentsReference(
			document_reference=1234,
			all_documents_reference="1234/2-5",
			main_document_reference=2,
			sub_document_references=[2,3,4,5]
		), actual)

	def test_parse_bad_doc_reference(self):
		actual = parse_document_reference("1234-2345")

		self.assertIsNone(actual)