import io
import os
import os.path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

import transparentdemocracy


class GoogleDriveDocumentRepository:
    def __init__(self, config):
        self.config = config
        self.legislature = config.legislature
        self.local_document_text_dir = self.config.documents_txt_output_path()
        self.local_document_summary_dir = self.config.documents_summary_output_path()

        # TODO use a secret manager with an api (use keepass python library?)
        self.storage_service_secrets_json_file = os.path.join(os.path.dirname(transparentdemocracy.__file__), config.google_service_account_credentials_json)
        self.service = self._create_service()

        self.text_dir_id = self._ensure_text_dir_exists()
        self.summary_dir_id = self._ensure_summary_dir_exists()

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

    def get_all_document_summary_ids(self):
        filenames = self.get_file_id(self.summary_dir_id)
        return [ f[:-8] for f in filenames if f[:-8] == ".summary" ]

    def get_all_document_text_ids(self):
        filenames = self.get_file_id(self.text_dir_id)
        return [ f[:-4] for f in filenames if f[:-4] == ".summary" ]

    def upsert_document_texts(self, document_ids):
        for document_id in document_ids:
            self._upsert_text_file(document_id)

    def _upsert_text_file(self, document_id):
        local_path = self.document_id_to_local_text_path(document_id)
        self._upsert_file(local_path, self.text_dir_id, 'text/plain')

    def existing_remote_text_document(self, document_id):
        existing_files = self.service.files().list(q=f"name='{document_id}' and parents in '{self.text_dir_id}' and trashed=false").execute()['files']
        file_id = existing_files[0]['id'] if existing_files else None
        return file_id

    def existing_remote_summary_document(self, document_id):
        existing_files = self.service.files().list(q=f"name='{document_id}' and parents in '{self.summary_dir_id}' and trashed=false").execute()['files']
        file_id = existing_files[0]['id'] if existing_files else None
        return file_id

    def _replace_remote_file(self, file_id, local_path, mimetype):
        media = MediaFileUpload(local_path, mimetype=mimetype)
        self.service.files().update(
            fileId=file_id,
            media_body=media
        ).execute()

    def document_id_to_local_text_path(self, document_id):
        return self.config.documents_txt_output_path(document_id[3:5], document_id[5:7], f"{document_id}.txt")

    def document_id_to_local_summary_path(self, document_id):
        return self.config.documents_summary_output_path(document_id[3:5], document_id[5:7], f"{document_id}.summary")

    def _ensure_text_dir_exists(self):
        return self.ensure_directories_exist(self.config.google_drive_text_dir.split('/') + [f"leg-{self.legislature}"])

    def _ensure_summary_dir_exists(self):
        return self.ensure_directories_exist(self.config.google_drive_summary_dir.split('/') + [f"leg-{self.legislature}"])

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

        if parent_id == 'root':
            self.share_folder(file['id'], self.storage_share_user)

        return file

    def list_dir(self, directory_id='root'):
        q = f"mimeType='application/vnd.google-apps.folder' and parents in '{directory_id}' and trashed=false"
        results = self.service.files().list(q=q,
                                            fields="nextPageToken, files(id, name, parents)").execute()
        return results.get('files', [])

    def get_file_id(self, filename, parent_dir_id):
        query = f"name='{filename}' and '{parent_dir_id}' in parents and trashed=false"
        results = self.service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get('files', [])
        if not items:
            return None
        return items[0]['id']

    def find_directory_by_name(self, directory_name, parent_id='root'):
        results = self.service.files().list(q=f"mimeType='application/vnd.google-apps.folder' and name='{directory_name}' and parents in '{parent_id}' and trashed=false",
                                            fields="files(id, name, parents)").execute()
        items = results.get('files', [])

        if not items:
            # print(f"No directory found with name '{directory_name}'")
            return None
        else:
            # print(f"Directory found with name '{directory_name}'")
            return items[0]

    def download_document_summary(self, document_id):
        self._download_file(f"{document_id}.summary", self.document_id_to_local_summary_path(document_id), self.summary_dir_id)

    def download_document_text(self, document_id):
        self._download_file(f"{document_id}.txt", self.document_id_to_local_text_path(document_id), self.text_dir_id)

    def _download_file(self, remote_filename, local_path, parent_id='root'):
        file_id = self.get_file_id(remote_filename, parent_id)
        if file_id is None:
            raise Exception(f"Can't find file {remote_filename} in parent {parent_id}")
        request = self.service.files().get_media(fileId=file_id)
        fh = io.FileIO(local_path, mode='wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print("Download %d%%." % int(status.progress() * 100))

    def _upload_text_file(self, local_path):
        self._upload_file(local_path, 'text/plain', self.text_dir_id)

    def _upload_summary_file(self, local_path):
        self._upload_file(local_path, 'application/json', self.summary_dir_id)

    def _upload_file(self, local_path, mimetype, parent_dir_id):
        file_metadata = {'name': os.path.basename(local_path), 'parents': [parent_dir_id]}
        media = MediaFileUpload(local_path, mimetype=mimetype)
        self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    def upsert_document_summary(self, document_id):
        local_path = self.document_id_to_local_summary_path(document_id)
        if not os.path.exists(local_path):
            raise Exception(f"Can't find summary file for document id {document_id} at {local_path}")

        self._upsert_summary_file(local_path)

    def _upsert_summary_file(self, local_path):
        self._upsert_file(local_path, self.summary_dir_id, 'application/json')

    def _upsert_file(self, local_path, parent_dir_id, mimetype):
        file_id = self.get_file_id(os.path.basename(local_path), parent_dir_id)
        if file_id is None:
            self._upload_file(local_path, mimetype, parent_dir_id)
        else:
            self._replace_remote_file(file_id, local_path, mimetype)

    def find_document_summary_ids(self, document_ids):
        filenames = self._get_filenames(self.summary_dir_id)
        ext = ".summary"
        remote_ids = [f[:-len(ext)] for f in filenames if f[-len(ext):] == ext]
        return set(remote_ids) & set(document_ids)

    def find_document_text_ids(self, document_ids):
        filenames = self._get_filenames(self.text_dir_id)
        ext = ".txt"
        remote_ids = [f[:-len(ext)] for f in filenames if f[-len(ext):] == ext]
        return set(remote_ids) & set(document_ids)

    def _get_filenames(self, parent_dir_id):
        query = f"'{parent_dir_id}' in parents and trashed=false"
        results = self.service.files().list(q=query, fields="files(name, id), nextPageToken").execute()
        items = results.get('files', [])
        filenames = [item['name'] for item in items]
        next_page_token = results.get('nextPageToken')
        while next_page_token:
            results = self.service.files().list(q=query, fields="files(name, id), nextPageToken", pageToken=next_page_token).execute()
            items = results.get('files', [])
            filenames.extend([item['name'] for item in items])
            next_page_token = results.get('nextPageToken')
        return filenames

