import os
import os.path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

import transparentdemocracy


class DocumentGoogleDriveRepository:
    # TODO: weird that we need legislature to determine the correct remote dir, but local_document_text_dir contains it
    def __init__(self, legislature, local_document_text_dir):
        self.legislature = legislature
        self.local_document_text_dir = local_document_text_dir

        # TODO use a secret manager with an api. Does keepass have apis?
        self.storage_service_secrets_json_file = os.path.join(os.path.dirname(transparentdemocracy.__file__), "../../secrets/wddp-storage-service.json")
        self.service = self._create_service()

        self.text_dir_id = None
        self.remote_storage_root = 'storage'
        # TOOD: figure out the root_id by name ('storage')
        self.root_id = '1Ve1qV5eyn46GfQhdlscgUGFtZ2r4C5fH'

        # Used to ensure dir is shared with wddpstorage user
        self.storage_share_user = 'wddpstorage@gmail.com'

    def _create_service(self):
        scopes = ['https://www.googleapis.com/auth/drive']
        creds = service_account.Credentials.from_service_account_file(self.storage_service_secrets_json_file, scopes=scopes)
        return build('drive', 'v3', credentials=creds)

    def create_folder(self, parent_id, folder_name):
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }

        return self.service.files().create(body=file_metadata, fields="id", parent_id=parent_id).execute().get('id')

    def share_folder(self, folder_id, reader_email):
        permission = {
            'type': 'user',
            'role': 'reader',
            'emailAddress': reader_email
        }
        return self.service.permissions().create(fileId=folder_id, body=permission).execute().get('id')

    def get_document_text(self, document_id):
        fileId = self.existing_remote_text_document(document_id)
        return self.service.files().get_media(fileId=fileId).execute().decode('utf-8')

    def get_all_document_text_ids(self):
        self.ensure_text_dir_exists()
        files = self.service.files().list(q=f"parents in '{self.text_dir_id}'").execute()['files']
        return [f['name'] for f in files]

    def upsert_document_texts(self, document_ids):
        self.ensure_text_dir_exists()

        for document_id in document_ids:
            local_path = self.document_id_to_text_path(document_id)
            if not os.path.exists(local_path):
                raise Exception(f"Can't find text file for document id {document_id} at {local_path}")

            file_id = self.existing_remote_text_document(document_id)
            if file_id:
                self._replace_remote_file(file_id, local_path)
            else:
                self._upload_text_file(local_path, document_id, self.text_dir_id)

    def existing_remote_text_document(self, document_id):
        existing_files = self.service.files().list(q=f"name='{document_id}' and parents in '{self.text_dir_id}'").execute()['files']
        file_id = existing_files[0]['id'] if existing_files else None
        return file_id

    def _replace_remote_file(self, file_id, local_path):
        media = MediaFileUpload(local_path, mimetype="text/plain")
        self.service.files().update(
            fileId=file_id,
            media_body=media
        ).execute()

    def document_id_to_text_path(self, document_id):
        return os.path.join(self.local_document_text_dir, document_id[3:5], document_id[5:7], f"{document_id}.txt")

    def ensure_text_dir_exists(self):
        if self.text_dir_id is None:
            self.text_dir_id = self.ensure_directories_exist([self.remote_storage_root, 'documents', 'text', f'leg-{self.legislature}'])

    def ensure_directories_exist(self, dir_names):
        parent_id = 'root'
        for dir_name in dir_names:
            found = self.find_directory_by_name(dir_name, parent_id)
            if found is None:
                parent_id = self._create_directory(parent_id, dir_name)['id']
            else:
                parent_id = found['id']
        return parent_id

    def _create_directory(self, parent_id, dir_name):
        file_metadata = {
            'name': dir_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        file = self.service.files().create(body=file_metadata, fields='id').execute()
        return file

    def list_dir(self, directory_id='root'):
        q = f"mimeType='application/vnd.google-apps.folder' and parents in '{directory_id}'"
        results = self.service.files().list(q=q,
                                            fields="nextPageToken, files(id, name, parents)").execute()
        return results.get('files', [])

    def find_directory_by_name(self, directory_name, parent_id='root'):
        results = self.service.files().list(q=f"mimeType='application/vnd.google-apps.folder' and name='{directory_name}' and parents in '{parent_id}'",
                                            fields="nextPageToken, files(id, name, parents)").execute()
        items = results.get('files', [])

        if not items:
            # print(f"No directory found with name '{directory_name}'")
            return None
        else:
            # print(f"Directory found with name '{directory_name}'")
            return items[0]

    def _upload_text_file(self, local_path, name, parent_id='root'):
        file_metadata = {'name': name, 'parents': [parent_id]}
        media = MediaFileUpload(local_path, mimetype="text/plain")
        self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    def upsert_document_summary(self, doc_id, summary_nl, summary_fr):
        raise Exception("TODO: implement summary upsert")
