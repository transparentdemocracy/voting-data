import logging
import os.path

import requests
import tqdm

from transparentdemocracy import CONFIG
from transparentdemocracy.documents.analyze_references import collect_document_references
from transparentdemocracy.documents.references import parse_document_reference
from transparentdemocracy.plenaries.extraction import extract_from_html_plenary_reports
from transparentdemocracy.plenaries.serialization import load_plenaries

logger = logging.getLogger(__name__)


def download_referenced_documents():
    doc_refs = get_document_references()
    os.makedirs(CONFIG.documents_input_path(), exist_ok=True)

    download_tasks = []
    for doc_ref in doc_refs:
        if not doc_ref.document_reference:
            continue
        doc_id_str = "%04d" % doc_ref.document_reference
        dirname = CONFIG.documents_input_path(doc_id_str[:2], doc_id_str[2:])
        urls = doc_ref.sub_document_pdf_urls
        if urls:
            os.makedirs(dirname, exist_ok=True)

        for url in urls:
            filename = os.path.basename(url)
            document_path = CONFIG.documents_input_path(dirname, filename)
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
        logger.info(
            f"Failed to download document, status code {response.status_code}: {url}")
        return

    with open(local_path, 'wb') as file:
        file.write(response.content)


def print_subdocument_pdf_urls():
    pdf_urls = get_referenced_document_pdf_urls()

    for url in pdf_urls:
        print(url)


def get_referenced_document_pdf_urls():
    document_references = get_document_references()
    pdf_urls = [
        url for document_reference in document_references for url in document_reference.sub_document_pdf_urls]
    return pdf_urls


def get_document_references():
    plenaries, votes, problems = extract_from_html_plenary_reports()
    specs = set([ref for ref, loc in collect_document_references(plenaries)])
    document_references = [parse_document_reference(spec) for spec in specs]
    return document_references


def main():
    # analyse_document_references()
    # print_subdocument_pdf_urls()
    download_referenced_documents()


if __name__ == "__main__":
    main()
