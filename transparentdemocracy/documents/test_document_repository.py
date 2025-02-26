import unittest

from transparentdemocracy.config import _create_config, Environments
from transparentdemocracy.documents.document_repository import GoogleDriveDocumentRepository


class GoogleDriveDocumentRepositoryTest(unittest.TestCase):
    config = _create_config(Environments.TEST, '56')

    def test_upsert_document_texts(self):
        repository = GoogleDriveDocumentRepository(self.config)

        repository.upsert_document_texts(['56K0055001'])
        text = repository.get_document_text('56K0055001')
        self.assertEqual("18 juli 2024", text[:12])

        # TODO: check that upsert works (modifies file, not adds another file with same name)

    def test_get_all_document_text_ids(self):
        repository = GoogleDriveDocumentRepository(self.config)

        repository.upsert_document_texts(['56K0055001'])
        existing_document_ids = repository.get_all_document_text_ids()
        self.assertTrue('56K0055001' in existing_document_ids)

    # def test_ad_hoc_playground(self):
    #     """ use this for experimentation and foefelen """
    #     repository = GoogleDriveDocumentRepository(self.config)
    #
    #     repository.share_folder('1dhBj6kidwjL3q68HyaRGDDjreE2A0CrF', 'wddpstorage@gmail.com')
    #     repository.share_folder('1KGYR2JVqVvG9ju7p-5k23jp-S6_RYU3u', 'wddpstorage@gmail.com')
    #
    #     page = repository.service.files().list().execute()
    #     for f in page['files']:
    #         print(f['name'], f['id'])
    #     self.assertEqual('foo', page)

    # def test_remove_everything(self):
    #     """ use this for experimentation and foefelen """
    #     repository = GoogleDriveDocumentRepository(_create_config(Environments.LOCAL, '56'))
    #
    #     repository.service.files().delete(fileId=repository.summary_dir_id).execute()
    #     repository.service.files().delete(fileId=repository.text_dir_id).execute()
    #
    #     page = repository.service.files().list().execute()
    #     for f in page['files']:
    #         print(f['name'], f['id'])
    #     self.assertEqual('foo', page)

