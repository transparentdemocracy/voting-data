import glob
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Optional

import jsonpath
from langchain.chains.combine_documents.base import BaseCombineDocumentsChain
from langchain.chains.summarize import load_summarize_chain
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_ollama import ChatOllama
from langchain_text_splitters import CharacterTextSplitter

from transparentdemocracy.config import Config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Batch size doesn't really matter when using OLLAMA locally, it gets executed sequentially anyway
BATCH_SIZE = 1

OLLAMA_MODEL = "llama3"
PROMPT_STUFF = """Summarize the text in Dutch and in French. Here is the text:

{text}

Answer with a  single json object. The dutch summary should be in string typed property called nl and the french summary should be in a string typed property
called fr. Each summary must not be longer than 5 sentences. They should be written in layman terms, rather than using very judicial or political vocabulary."""

PROMPT_DUTCH = """Summarize the text in Dutch. Your answer must be a single sentence. Respond with a single sentence that contains only the essential
information, without any prefatory language or extraneous words. Here is the text: {text}"""
PROMPT_FRENCH = """Summarize the text in French. Your answer must be a single sentence. Respond with a single sentence that contains only the essential
information, without any prefatory language or extraneous words. Here is the text: {text}"""

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


@dataclass
class Summary:
    id: str
    nl: str
    fr: str


class DocumentSummarizer:
    """
    Summarizes simple text documents.
    """

    def __init__(self, config: Config, custom_prompt=None, target_dir=None):
        self.config = config
        self.summary_document_filename_pattern = re.compile(f"^.*/{re.escape(config.legislature)}K(\\d{{4}})(\\d{{3}}).summary$")

        self.llm = ChatOllama(model=OLLAMA_MODEL)
        self.target_dir = target_dir

        self.stuff_prompt_template = PROMPT_STUFF
        if custom_prompt is not None:
            self.stuff_prompt_template = custom_prompt

        self.llm_chain: BaseCombineDocumentsChain = self.create_stuff_chain()
        self.text_splitter = CharacterTextSplitter.from_tiktoken_encoder(chunk_size=40_000, chunk_overlap=100)

    def summarize_documents(self, document_txt_paths):
        batch_to_process = []
        num_docs_summarized = 0

        for text_path in document_txt_paths:
            num_docs_summarized += 1
            summary_path = self.txt_path_to_summary_path(text_path)

            if os.path.exists(summary_path):
                continue

            if not os.path.exists(text_path):
                logger.warning("Missing text file: %s. Skipping summary", text_path)
                continue

            # Transform the document into an input the Langchain framework can use:
            with open(text_path, 'r', encoding="utf-8") as fp:
                doc_part = fp.read(12_000)
            docs = [Document(page_content=doc_part, metadata={"source": text_path})]

            # Split the document into smaller chunks, if necessary:
            doc_splits = self.text_splitter.split_documents(docs)

            # If no chunks were made at all, the document might be empty and we don't need to summarize:
            if len(doc_splits) == 0:
                logger.info("Empty document? %s", text_path)
                continue

            if len(doc_splits) > 1:
                logger.info("Document was split into multiple pieces - We don't support documents this large right now")
                continue

            # Summarize the chunked documents in one batch:
            batch_to_process.append((text_path, doc_splits))

            # -> If by now in this for loop iteration, we haven't yet continued to the next iteration already,
            # then just one document is ready to be summarized, which corresponds with the BATCH_SIZE of 1.
            if len(batch_to_process) == BATCH_SIZE:
                self.summarize_batch(batch_to_process)
                remaining = len(document_txt_paths) - num_docs_summarized
                print(f"{remaining} docs still need to be summarized")
                batch_to_process = []

        # -> If documents remain in the batch to process, they can be summarized too:
        if batch_to_process:
            self.summarize_batch(batch_to_process)

    def summarize_batch(self, batch_to_process, tries = 3):
        print(f"Summarizing {len(batch_to_process)} small documents")

        failures = []

        for doc in batch_to_process:
            path, doc_splits = doc
            print(path)
            llm_result = self.llm_chain.invoke(doc_splits)
            source = llm_result['input_documents'][0].metadata['source']
            doc_id = os.path.basename(source)[:-4]  # removing the .txt extension
            output_text = llm_result['output_text']

            summary = self.parse_llm_output(doc_id, output_text)
            # TODO: add retry mechanism?
            if summary is None:
                logger.warning("Failed to parse json response from LLM")
                print("summary:", output_text)
                failures.append(doc)
                continue

            self.write_summary(summary)

        if failures and tries > 1:
            self.summarize_batch(failures, tries - 1)

    def parse_llm_output(self, doc_id, output:str):
        return parse_json_summary(doc_id, output)

    def write_summary(self, summary: Summary):
        doc_id = summary.id
        output_path = self.config.documents_summary_output_path(doc_id[3:5], doc_id[5:7], f"{doc_id}.summary")
        output_summary = json.dumps({'nl': summary.nl, 'fr': summary.fr}, indent=4, ensure_ascii=False)

        print(f"Writing {output_path}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding="utf-8") as fp:
            fp.write(output_summary)

    def determine_documents_to_summarize(self, docs, min_size_inclusive, max_size_exclusive):
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

    def txt_path_to_summary_path(self, doc_txt_path):
        abs_document_path = os.path.abspath(doc_txt_path)
        abs_txt_path = os.path.abspath(self.config.documents_txt_output_path())

        if not abs_document_path.startswith(abs_txt_path):
            raise Exception(f"Documents must be under {abs_txt_path}")

        txt_relative = abs_document_path[len(abs_txt_path) + 1:]
        summary_relative = os.path.join(os.path.dirname(txt_relative), os.path.join(os.path.basename(txt_relative)[:-4]) + ".summary")
        return self.config.documents_summary_output_path(summary_relative)

    def write_summaries_json(self):
        """Write the plenary report summaries to a JSON output format."""
        summary_paths = glob.glob(config.documents_summary_output_path("**/*.summary"), recursive=True)

        summaries, bad_files = self.get_summary_pairs(summary_paths)

        if bad_files:
            print("Could not detect json summaries in the following files:")
            for path in bad_files:
                print(f"  {path}")

        summaries.sort(key=lambda s: s['document_id'])
        path = self.config.documents_summaries_json_output_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding="utf-8") as fp:
            json.dump(summaries, fp, indent=2)

        print(f"Wrote {path}")

    def get_summary_pairs(self, summary_paths):
        result = []
        bad_files = []

        for path in summary_paths:
            filename_match = self.summary_document_filename_pattern.match(path)
            if not filename_match:
                bad_files.append(path)

            document_id = f"{filename_match.group(1)}/{filename_match.group(2)}"

            summary_data = parse_json_summary(document_id, path)
            if summary_data is None:
                bad_files.append(path)
            else:
                result.append(summary_data)

        return result, bad_files


def parse_json_summary(doc_id, text) -> Optional[Summary]:
    lines = text.split("\n")

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
            return Summary(doc_id, summary_nl, summary_fr)
        return None
    except JSONDecodeError as e:
        return None


def get_text(data, expressions):
    for expr in expressions:
        result = expr.find(data)
        if len(result) == 1 and isinstance(result[0], str) and len(result[0]) > 3:
            return result[0]
    return None


def summarize_document_texts(documents, max_size=5_000_000, min_size=0):
    """Summarize the text extracted from the documents referenced in the plenary PDF reports."""
    summarizer = DocumentSummarizer()
    docs_to_summarize = summarizer.determine_documents_to_summarize(documents, min_size, max_size)
    summarizer.summarize_documents(docs_to_summarize)


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <min-size> <max-size>")
        sys.exit(1)

    min_size = int(sys.argv[1], 10)
    max_size = int(sys.argv[2], 10)

    summarize_document_texts(max_size, min_size)


if __name__ == "__main__":
    main()
