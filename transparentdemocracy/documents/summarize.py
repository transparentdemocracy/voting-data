import glob
import itertools
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from json import JSONDecodeError

import jsonpath
from langchain.chains.combine_documents.base import BaseCombineDocumentsChain
from langchain.chains.summarize import load_summarize_chain
from langchain_community.chat_models import ChatOllama
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_text_splitters import CharacterTextSplitter

from transparentdemocracy import CONFIG

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Batch size doesn't really matter when using OLLAMA locally, it gets executed sequentially anyway
BATCH_SIZE = 1
SUMMARY_DOCUMENT_FILENAME_PATTERN = re.compile(f"^.*/{re.escape(CONFIG.legislature)}K(\\d{{4}})(\\d{{3}}).summary$")

OLLAMA_MODEL = "llama3"
PROMPT_STUFF = """Summarize the text in Dutch and in French. Here is the text:

{text}

Answer with a  single json object. The dutch summary should be in string typed property called nl and the french summary should be in a string typed property
called fr. Each summary must not be longer than 5 sentences. They should be written in layman terms, rather than using very judicial or political vocabulary."""

NL_IDENTIFIERS = ['nl', 'dutch', 'Dutch', 'Nederlands', 'summary_nl']
FR_IDENTIFIERS = ['fr', 'french', 'French', 'francais', 'Francais', 'summary_fr']

PATTERNS = ["$.%s",
            "$.%s.summary",
            "$.text.%s",
            "$.%s.text",
            "$.%s.summary.text",
            "$.summary.%s"]

NL_EXPRESSIONS = [jsonpath.parse(pattern % identifier) for identifier in NL_IDENTIFIERS for pattern in PATTERNS]
FR_EXPRESSIONS = [jsonpath.parse(pattern % identifier) for identifier in FR_IDENTIFIERS for pattern in PATTERNS]

class DocumentSummarizer:
    """
    Summarizes simple text documents.
    """
    def __init__(self, custom_prompt=None, target_dir=None):
        self.llm = ChatOllama(model=OLLAMA_MODEL)
        self.target_dir = target_dir

        self.stuff_prompt_template = PROMPT_STUFF
        if custom_prompt is not None:
            self.stuff_prompt_template = custom_prompt

        self.stuff_chain: BaseCombineDocumentsChain = self.create_stuff_chain()
        self.text_splitter = CharacterTextSplitter.from_tiktoken_encoder(chunk_size=40_000, chunk_overlap=100)

    def summarize_documents(self, document_paths):
        batch_to_process = []
        num_docs_summarized = 0

        for document_path in document_paths:
            num_docs_summarized += 1
            summary_path = self.txt_path_to_summary_path(document_path)

            # Skip summarizing a document, if it has already been summarized before:
            if os.path.exists(summary_path):
                continue

            # Transform the document into an input the Langchain framework can use:
            with open(document_path, 'r', encoding="utf-8") as fp:
                doc_part = fp.read(12_000)
            docs = [Document(page_content=doc_part, metadata={"source": document_path})]

            # Split the document into smaller chunks, if necessary:
            doc_splits = self.text_splitter.split_documents(docs)

            # If no chunks were made at all, the document might be empty and we don't need to summarize:
            if len(doc_splits) == 0:
                logger.info("Empty document? %s", document_path)
                continue

            # TODO If multiple chunks were made, we skip summarizing, until we support this.
            if len(doc_splits) > 1:
                logger.info("Document was split into multiple pieces - We don't handle this right now")
                continue

            # Summarize the chunked documents in one batch:
            batch_to_process.append((document_path, doc_splits))
            # TODO pass summary_path too, so it must not be recomputed in write_summaries()?

            # -> If by now in this for loop iteration, we haven't yet continued to the next iteration already,
            # then just one document is ready to be summarized, which corresponds with the BATCH_SIZE of 1.
            # We can summarize this already.
            # TODO: can this not be discarded, in favour of the next if block below? Since it executes batch_stuff() also only on each item in batch_to_process one by one...
            if len(batch_to_process) == BATCH_SIZE:
                self.batch_stuff(batch_to_process)
                remaining = len(document_paths) - num_docs_summarized
                print(f"{remaining} docs still need to be summarized")
                batch_to_process = []

        # -> If documents remain in the batch to process, they can be summarized too:
        if batch_to_process:
            self.batch_stuff(batch_to_process)

    def batch_stuff(self, batch_to_process):
        print(f"Summarizing {len(batch_to_process)} small documents")
        summarization_results = []
        for doc in batch_to_process:
            path, doc_splits = doc
            print(path)
            summarization_results = self.stuff_chain.batch(doc_splits)
        self.write_summaries(summarization_results)

    def write_summaries(self, summarization_results):
        """Write the summary texts to a file."""
        for summarization_result in summarization_results:
            input_document = summarization_result['input_documents']
            if len(input_document) > 1:
                logger.warning("multiple input docs")
                for doc in input_document:
                    print(doc.metadata['source'])
            input_path = input_document[0].metadata['source']

            output_path = self.txt_path_to_summary_path(input_path)
            output_summary = summarization_result['output_text']

            print(f"Writing {output_path}")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding="utf-8") as fp:
                fp.write(output_summary)

    def determine_documents_to_summarize(self, min_size_inclusive, max_size_exclusive):
        docs = glob.glob(CONFIG.documents_txt_output_path(
            "**/*.txt"), recursive=True)
        docs = [path for path in docs
                if (os.path.getsize(path) >= min_size_inclusive) and (os.path.getsize(path) < max_size_exclusive)]
        docs.sort(key=os.path.getsize)
        not_summarized = [
            path
            for path in docs
            if not os.path.exists(self.txt_path_to_summary_path(path))
        ]
        print(f"Documents matching size criteria: {len(docs)}")
        print(f"Documents not yet summarized matching criteria: {len(not_summarized)}")

        return not_summarized

    def create_stuff_chain(self):
        prompt = PromptTemplate.from_template(self.stuff_prompt_template)
        return load_summarize_chain(self.llm, chain_type="stuff", prompt=prompt, document_variable_name="text")

    @staticmethod
    def txt_path_to_summary_path(doc_txt_path):
        abs_document_path = os.path.abspath(doc_txt_path)
        abs_txt_path = os.path.abspath(CONFIG.documents_txt_output_path())

        if not abs_document_path.startswith(abs_txt_path):
            raise Exception(f"Documents must be under {abs_txt_path}")

        txt_relative = abs_document_path[len(abs_txt_path) + 1:]
        summary_relative = os.path.join(os.path.dirname(txt_relative), os.path.join(os.path.basename(txt_relative)[:-4]) + ".summary")
        return CONFIG.documents_summary_output_path(summary_relative)


def write_summaries_json():
    """Write the plenary report summaries to a JSON output format."""
    summary_paths = glob.glob(CONFIG.documents_summary_output_path("**/*.summary"), recursive=True)

    summaries, bad_files = get_summary_pairs(summary_paths)

    if bad_files:
        print("Could not detect json summaries in the following files:")
        for path in bad_files:
            print(f"  {path}")

    summaries.sort(key=lambda s: s['document_id'])
    path = CONFIG.documents_summaries_json_output_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding="utf-8") as fp:
        json.dump(summaries, fp, indent=2)

    print(f"Wrote {path}")


@dataclass
class Summary:
    document_id: str
    text: str


def get_summary_pairs(summary_paths):
    result = []
    bad_files = []

    for path in summary_paths:
        filename_match = SUMMARY_DOCUMENT_FILENAME_PATTERN.match(path)
        if not filename_match:
            bad_files.append(path)

        document_id = f"{filename_match.group(1)}/{filename_match.group(2)}"

        summary_data = parse_summary_file(document_id, path)
        if summary_data is None:
            bad_files.append(path)
        else:
            result.append(summary_data)

    return result, bad_files


def parse_summary_file(document_id, path):
    with open(path, 'r', encoding="utf-8") as fp:
        lines = fp.readlines()

    marker_lines = [
        i for i in range(len(lines))
        if lines[i].startswith("```")
    ]

    if len(marker_lines) == 2:
        json_str = "".join(lines[marker_lines[0] + 1:marker_lines[1]])
    else:
        full_text = "".join(lines)
        start = full_text.find("{")
        end = full_text.rfind("}")
        if start == -1 or end == -1:
            return None
        json_str = full_text[start:end + 1]

    try:
        data = json.loads(json_str)
        summary_nl = get_text(data, NL_EXPRESSIONS)
        summary_fr = get_text(data, FR_EXPRESSIONS)
        if summary_nl is not None and summary_fr is not None:
            return {'document_id': document_id, 'summary_nl': summary_nl, 'summary_fr': summary_fr}
        return None
    except JSONDecodeError:
        return None


def get_text(data, expressions):
    for expr in expressions:
        result = expr.find(data)
        if len(result) == 1 and isinstance(result[0], str) and len(result[0]) > 3:
            return result[0]
    return None


def summarize_document_texts(max_size=5_000_000, min_size=0):
    """Summarize the text extracted from the documents referenced in the plenary PDF reports."""
    summarizer = DocumentSummarizer()
    docs = summarizer.determine_documents_to_summarize(min_size, max_size)
    summarizer.summarize_documents(docs)


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <min-size> <max-size>")
        sys.exit(1)

    min_size = int(sys.argv[1], 10)
    max_size = int(sys.argv[2], 10)

    summarize_document_texts(max_size, min_size)
    write_summaries_json()


if __name__ == "__main__":
    main()
