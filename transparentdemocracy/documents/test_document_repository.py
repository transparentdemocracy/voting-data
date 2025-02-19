import os
import unittest

import transparentdemocracy
from transparentdemocracy.documents.document_repository import DocumentGoogleDriveRepository

test_document_dir = os.path.join(os.path.dirname(transparentdemocracy.__file__), "../testdata/output/documents/txt")

class DocumentRepositoryTest(unittest.TestCase):
    def test_upsert_document_texts(self):
        repository = DocumentGoogleDriveRepository(56, test_document_dir)

        repository.upsert_document_texts(['56K0055001'])
        text = repository.get_document_text('56K0055001')
        self.assertEqual("18 juli 2024", text[:12])

        # TODO: check that upsert works (modifies file, not adds another file with same name)

    def test_get_all_document_text_ids(self):
        repository = DocumentGoogleDriveRepository(56, test_document_dir)

        repository.upsert_document_texts(['56K0055001'])
        existing_document_ids = repository.get_all_document_text_ids()
        self.assertTrue('56K0055001' in existing_document_ids)

