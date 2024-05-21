import os.path

import requests
import tqdm

from transparentdemocracy import CONFIG
from transparentdemocracy.documents.references import get_document_references

import logging

logger = logging.getLogger(__name__)

def download_referenced_documents():
	doc_refs = get_document_references()
	os.makedirs(CONFIG.documents_path(), exist_ok=True)

	download_tasks = []
	for doc_ref in doc_refs:
		if not doc_ref.document_reference:
			continue
		doc_id_str = "%04d" % doc_ref.document_reference
		dirname = CONFIG.documents_path(doc_id_str[:2], doc_id_str[2:])
		urls = doc_ref.sub_document_pdf_urls
		if urls:
			os.makedirs(dirname, exist_ok=True)

		for url in urls:
			filename = os.path.basename(url)
			document_path = CONFIG.documents_path(dirname, filename)
			download_tasks.append((url, document_path))

	download_tasks = list(sorted(dict.fromkeys(download_tasks)))
	for url, path in tqdm.tqdm(download_tasks, "Downloading documents..."):
		if not os.path.exists(path):
			logger.debug(f"{url} -> {path}")
			_download(url, path)
		else:
			logger.debug(f"{url} -> (already exists) {path}")


def _download(url, local_path):
	response = requests.get(url)

	if response.status_code != 200:
		logger.info(f"Failed to download document, status code {response.status_code}: {url}")
		return

	with open(local_path, 'wb') as file:
		file.write(response.content)


def main():
	# analyse_document_references()
	# print_subdocument_pdf_urls()
	download_referenced_documents()


if __name__ == "__main__":
	main()
