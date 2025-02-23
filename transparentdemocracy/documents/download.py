import logging
import os.path
from typing import List

import requests
import tqdm

from transparentdemocracy.documents.analyze_references import collect_document_references
from transparentdemocracy.documents.references import parse_document_reference
from transparentdemocracy.model import Plenary

logger = logging.getLogger(__name__)


def download_referenced_documents(config, document_references):
    """
    Download any documents referenced from the motions in the plenary report that the politicians voted on.
    """
    os.makedirs(config.documents_input_path(), exist_ok=True)

    download_tasks = []
    for doc_ref in document_references:
        if not doc_ref.document_reference:
            continue
        doc_id_str = f"{doc_ref.document_reference:04d}"
        dirname = config.documents_input_path(doc_id_str[:2], doc_id_str[2:])

        urls = doc_ref.sub_document_pdf_urls
        if urls:
            os.makedirs(dirname, exist_ok=True)

        for url in urls:
            filename = os.path.basename(url)
            document_path = config.documents_input_path(dirname, filename)
            download_tasks.append((url, document_path))

    downloaded = []

    download_tasks = list(sorted(dict.fromkeys(download_tasks)))
    for url, path in tqdm.tqdm(download_tasks, "Downloading documents..."):
        if not os.path.exists(path):
            logger.debug('%s -> %s', url, path)
            _download(url, path)
        else:
            logger.debug("%s -> (already exists) %s", url, path)

        # TODO: later on, we should determine which ones to re-summarize
        downloaded.append(path)

    return downloaded


def _download(url, local_path):
    response = requests.get(url, timeout=60)

    if response.status_code != 200:
        logger.info("Failed to download document, status code %d: %s", response.status_code, url)
        return

    with open(local_path, 'wb') as file:
        file.write(response.content)


def print_subdocument_pdf_urls(plenaries: List[Plenary]):
    pdf_urls = get_referenced_document_pdf_urls(plenaries)

    for url in pdf_urls:
        print(url)


def get_referenced_document_pdf_urls(plenaries: List[Plenary]):
    document_references = get_document_references(plenaries)
    return [
        url for document_reference in document_references for url in document_reference.sub_document_pdf_urls]


def get_document_references(plenaries):
    specs = {ref for ref, loc in collect_document_references(plenaries)}
    return [parse_document_reference(spec) for spec in specs]
