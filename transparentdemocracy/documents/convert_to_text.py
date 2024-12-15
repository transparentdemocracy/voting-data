import glob
import logging
import os.path

import fitz

from transparentdemocracy import CONFIG

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Note: selected PyMuPDF based on this, but maybe we should run the comparison on our documents
# https://medium.com/social-impact-analytics/comparing-4-methods-for-pdf-text-extraction-in-python-fd34531034f
def convert_to_text():
    docs = glob.glob(CONFIG.documents_input_path("**/*.pdf"), recursive=True)

    for doc_path in docs:
        txt_path = pdf_path_to_txt_path(doc_path)

        if os.path.exists(txt_path):
            logger.info(f"Skipping {doc_path} because {txt_path} already exists")
            continue

        print("Reading", doc_path)
        with fitz.open(doc_path) as pdf_doc:
            text = ''
            for page in pdf_doc:
                text += page.get_text()

            os.makedirs(os.path.dirname(txt_path), exist_ok=True)
            print("Writing", txt_path)
            with open(txt_path, 'w', encoding="utf-8") as f:
                f.write(text)


def pdf_path_to_txt_path(doc):
    doc = doc[len(CONFIG.documents_input_path()) + 1:]
    return CONFIG.documents_txt_output_path(os.path.dirname(doc), os.path.basename(doc)[:-4] + ".txt")


def main():
    convert_to_text()


if __name__ == "__main__":
    main()
