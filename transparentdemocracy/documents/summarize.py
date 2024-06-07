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
from jsonpath import JSONPathFindError
from langchain.chains.combine_documents.base import BaseCombineDocumentsChain
from langchain.chains.summarize import load_summarize_chain
from langchain_community.chat_models import ChatOllama
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_text_splitters import CharacterTextSplitter

from transparentdemocracy import CONFIG

logger = logging.getLogger("__name__")
logger.setLevel(logging.INFO)

# Batch size doesn't really matter when using OLLAMA locally, it gets executed sequentially anyway
BATCH_SIZE = 1
SUMMARY_DOCUMENT_FILENAME_PATTERN = re.compile("^.*/55K(\\d{4})(\\d{3}).summary$")

OLLAMA_MODEL = "llama3"
PROMPT_STUFF = """Summarize the text in Dutch and in French. Here is the text:

{text}

Answer with a single json object. The dutch summary should be in string typed property called nl and the french summary should be in a string typed property
called fr."""


class DocumentSummarizer:
    def __init__(self, custom_prompt=None, target_dir=None):
        self.llm = ChatOllama(model=OLLAMA_MODEL)
        self.target_dir = target_dir

        self.stuff_prompt_template = PROMPT_STUFF
        if custom_prompt is not None:
            self.stuff_prompt_template = custom_prompt

        self.stuff_chain: BaseCombineDocumentsChain = self.create_stuff_chain()

        self.text_splitter = CharacterTextSplitter.from_tiktoken_encoder(chunk_size=40_000, chunk_overlap=100)

    def summarize_documents(self, document_paths):
        batch = []

        summarized = 0

        # TODO: evaluate performance with vs without tqdm here
        for document_path in document_paths:
            output_path = self.txt_path_to_summary_path(document_path)

            summarized += 1
            if os.path.exists(output_path):
                continue

            with open(document_path, 'r') as fp:
                doc_part = fp.read(12_000)
            docs = [Document(page_content=doc_part, metadata={"source": document_path})]
            split_documents = self.text_splitter.split_documents(docs)

            if len(split_documents) == 0:
                logger.info(f"Empty document? {document_path}")
                continue

            if len(split_documents) > 1:
                logger.info(f"Document was split into multiple pieces - We don't handle this right now")
                continue

            batch.append((document_path, split_documents))

            if len(batch) == BATCH_SIZE:
                self.batch_stuff(batch)
                remaining = len(document_paths) - summarized
                print(f"{remaining} docs still need to be summarized")
                batch = []

        if batch:
            self.batch_stuff(batch)

    def batch_stuff(self, small_bucket):
        print(f"Summarizing {len(small_bucket)} small documents")
        for doc in small_bucket:
            print(doc[0])
        result = self.stuff_chain.batch([doc[1] for doc in small_bucket])
        self.write_summaries(result)

    def write_summaries(self, result):

        for r in result:
            input_docs = r['input_documents']
            output_text = r['output_text']
            if len(input_docs) > 1:
                logger.warn("multiple input docs")
                for doc in input_docs:
                    print(doc.metadata['source'])
            input_path = input_docs[0].metadata['source']
            output_path = self.txt_path_to_summary_path(input_path)

            print(f"Writing {output_path}")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w') as fp:
                fp.write(output_text)

    def determine_documents_to_summarize(self, min_size_inclusive, max_size_exclusive):
        docs = glob.glob(CONFIG.documents_txt_output_path(
            "**/*.txt"), recursive=True)
        docs = [path
                for path in docs
                if (os.path.getsize(path) >= min_size_inclusive) and (os.path.getsize(path) < max_size_exclusive)
                ]
        docs.sort(key=lambda path: os.path.getsize(path))
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


def write_json():
    summary_paths = glob.glob(CONFIG.documents_summary_output_path("**/*.summary"), recursive=True)

    summaries, bad_files = get_summary_pairs(summary_paths)

    if bad_files:
        print("Could not detect json summaries in the following files:")
        for path in bad_files:
            print(f"  {path}")

    summaries.sort(key=lambda s: s['document_id'])
    with open(CONFIG.documents_summaries_json_output_path(), 'w') as fp:
        json.dump(summaries, fp, indent=2)


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


NL_IDENTIFIERS = ['nl', 'dutch', 'Dutch', 'Nederlands', 'summary_nl']
FR_IDENTIFIERS = ['french', 'French', 'francais', 'Francais', 'summary_fr']

PATTERNS = ["$.%s",
            "$.%s.summary",
            "$.text.%s",
            "$.%s.text",
            "$.%s.summary.text",
            "$.summary.%s"]

NL_EXPRESSIONS = [jsonpath.parse(pattern % identifier) for identifier in NL_IDENTIFIERS for pattern in PATTERNS]
FR_EXPRESSIONS = [jsonpath.parse(pattern % identifier) for identifier in FR_IDENTIFIERS for pattern in PATTERNS]

def parse_summary_file(document_id, path):
    with open(path, 'r') as fp:
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
        summary_fr = get_text(data, NL_EXPRESSIONS)
        if summary_nl is not None and summary_fr is not None:
            return dict(document_id=document_id, summary_nl=summary_nl, summary_fr=summary_fr)
        return None
    except JSONDecodeError:
        return None


def get_text(data, expressions):
    for expr in expressions:
        result = expr.find(data)
        if len(result) == 1 and isinstance(result[0], str):
            return result
    return None

def get_summary(data, json_path):
    try:
        result = jsonpath.parse(json_path).find(data)
        if len(result) == 1 and isinstance(result[0], str):
            return result
    except JSONPathFindError:
        return None
    return None


def to_summary(path):
    match = SUMMARY_DOCUMENT_FILENAME_PATTERN.match(path)
    if not match:
        print("no match", path)
        return None
    doc_id = int(match.group(1), 10)
    sub_doc_id = int(match.group(2), 10)
    with open(path) as fp:
        text = fp.read()
    return Summary(f"{doc_id}/{sub_doc_id}", text)


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <min-size> <max-size>")
        sys.exit(1)

    min_size = int(sys.argv[1], 10)
    max_size = int(sys.argv[2], 10)

    summarizer = DocumentSummarizer()
    docs = summarizer.determine_documents_to_summarize(min_size, max_size)
    summarizer.summarize_documents(docs)


def fixup_summaries():
    known_actions = load_known_actions()
    save_known_actions(known_actions)

    print("known actions", known_actions)

    files_to_check = []
    glob_path = CONFIG.documents_summary_output_path("**/*.summary")
    print(f"summaries to process: {len(glob.glob(glob_path, recursive=True))}")
    for path in glob.glob(glob_path, recursive=True):
        with open(path, 'r') as fp:
            lines = fp.readlines()

        if len(lines) < 3 or lines[1].strip() != '' or lines[2].strip() == '':
            continue

        if lines[0].strip() in known_actions:
            action = known_actions[lines[0].strip()]
            apply_action(action, path)
            continue

        print("adding", lines[0].strip())
        files_to_check.append((path, lines[0].strip()))

    files_by_first_line = dict((k, [pair[0] for pair in v]) for k, v in itertools.groupby(files_to_check, lambda pair: pair[1]))

    print(f"{len(files_by_first_line)} phrases")
    phrases = [k for k in files_by_first_line.keys()]
    phrases.sort(key=lambda k: -len(files_by_first_line[k]))
    for phrase in phrases:
        if not ("summary" in phrase or "résumé" in phrase or "samenvatting" in phrase):
            continue

        print(f"Phrase: {phrase}")
        paths = files_by_first_line[phrase]
        print("Paths:", paths)

        while True:
            action = input("Choose an action; (S)kip, (I)gnore, (D)elete, (F)ixup, (Q)uit").strip().upper()
            if action in "SIDF":
                break

            if action in "IDF":
                known_actions[phrase] = action
            if action == "S":
                continue
            if action == "Q":
                save_known_actions(known_actions)
                sys.exit(0)
            for path in paths:
                apply_action(action, path)

    save_known_actions(known_actions)


def load_known_actions():
    if not os.path.exists('known-actions.json'):
        return dict()
    with open('known-actions.json', 'r') as fp:
        return json.load(fp)


def save_known_actions(known_actions):
    with open('known-actions.json', 'w') as fp:
        json.dump(known_actions, fp, indent=2)


def apply_action(action, path):
    if action == "I":
        pass
    elif action == "D":
        os.remove(path)
        return
    elif action == "F":
        with open(path, 'r') as fp:
            lines = fp.readlines()

        lines = lines[2:]
        with open(path, 'w') as fp:
            fp.writelines(lines)

    else:
        raise Exception(f"Unknown action {action}")


if __name__ == "__main__":
    main()
