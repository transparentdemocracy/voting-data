import glob
import itertools
import json
import logging
import os
import re
import sys
from dataclasses import dataclass

from langchain.chains.combine_documents.base import BaseCombineDocumentsChain
from langchain.chains.summarize import load_summarize_chain
from langchain_community.chat_models import ChatOllama
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_text_splitters import CharacterTextSplitter

from transparentdemocracy import CONFIG

logger = logging.getLogger("__name__")
logger.setLevel(logging.INFO)

SUMMARY_DOCUMENT_FILENAME_PATTERN = re.compile("^.*/55K(\\d{4})(\\d{3}).summary$")

# Config for llama3
OLLAMA_MODEL = "llama3"  # 7b parameters
# must match model, see https://en.wikipedia.org/wiki/Llama_(language_model)
CONTEXT_WINDOW = 8912

#
SUMMARY_SIZE = 400  # number of tokens for each summary
# A word is +- 1.3 tokens
WORDS_PER_DOCUMENT = int((CONTEXT_WINDOW - SUMMARY_SIZE) / 1.3)

PROMPT_BRIEFNESS_NL = "Begin direct, zonder introductie."
PROMPT_VOCAB_NL = "Gebruik woordenschat die geschikt is voor leken"

PROMPT_BRIEFNESS_FR = "N'introduisez pas la réponse, rédigez simplement le résumé"
PROMPT_VOCAB_FR = "Utilisez un vocabulaire adapté aux novices"

PROMPT_STUFF_NL = """Schrijf een samenvatting van de onderstaande tekst in het Nederlands. Geen introductie, alleen de samenvatting. Dit is de tekst:

{text}

Dit is de samenvatting in het Nederlands:"""

PROMPT_MAP_NL = f"""Vat de volgende tekst samen in het Nederlands. {PROMPT_BRIEFNESS_NL}.
                 {{text}}
                 BONDIGE SAMENVATTING:"""
PROMPT_REDUCE_NL = f"""Hierna volgen enkele samenvattingen. Maak een geconsolideerde samenvatting.  {PROMPT_BRIEFNESS_NL}. {PROMPT_VOCAB_NL}.
                {{text}}
                BONDIGE SAMENVATTING:"""

PROMPT_STUFF_FR = f""""Résumez le texte suivant en français. {PROMPT_BRIEFNESS_FR}. {PROMPT_VOCAB_FR}.
                 {{text}}
                 Résumé concis:"""
PROMPT_MAP_FR = f"""Résumez le texte suivant en français. {PROMPT_BRIEFNESS_FR}.
                 {{text}}
                 Résumé concis:"""
PROMPT_REDUCE_FR = f"""Ci-dessous quelques résumés. Créez un résumé consolidé en français.  {PROMPT_BRIEFNESS_FR}. {PROMPT_VOCAB_FR}.
                {{text}}
                Résumé concis:"""

PROMPTS = dict(
    nl=(PROMPT_STUFF_NL, PROMPT_MAP_NL, PROMPT_REDUCE_NL),
    fr=(PROMPT_STUFF_FR, PROMPT_MAP_FR, PROMPT_REDUCE_FR)
)


class DocumentSummarizer():
    def __init__(self, language="nl", custom_prompt=None, target_dir=None):
        self.llm = ChatOllama(model=OLLAMA_MODEL)
        self.target_dir = target_dir
        self.language = language

        self.stuff_prompt_template = PROMPTS[language][0]
        if custom_prompt is not None:
            self.stuff_prompt_template = custom_prompt
        self.map_prompt_template = PROMPTS[language][1]
        self.reduce_prompt_template = PROMPTS[language][2]

        # Used for documents that fit in the context window
        self.stuff_chain: BaseCombineDocumentsChain = self.create_stuff_chain()

        # Used for documents that do not fit in the context window
        self.map_reduce_chain: BaseCombineDocumentsChain = self.create_map_reduce_chain()
        self.text_splitter = CharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=WORDS_PER_DOCUMENT, chunk_overlap=100
        )

    def summarize_documents(self, document_paths):
        small_bucket = []
        large_bucket = []

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

            if len(split_documents) == 1:
                small_bucket.append((document_path, split_documents))
            else:
                large_bucket.append((document_path, split_documents))

            if len(small_bucket) == 10:
                self.batch_stuff(small_bucket)
                remaining = len(document_paths) - summarized
                print(f"{remaining} docs still need to be summarized")
                small_bucket = []
            if len(large_bucket) == 10:
                self.batch_map_reduce(large_bucket)
                remaining = len(document_paths) - summarized
                print(f"{remaining} docs still need to be summarized")
                large_bucket = []

        if small_bucket:
            self.batch_stuff(small_bucket)
        if large_bucket:
            self.batch_map_reduce(large_bucket)

    def batch_stuff(self, small_bucket):
        print(f"Summarizing {len(small_bucket)} small documents")
        for doc in small_bucket:
            print(doc[0])
        result = self.stuff_chain.batch([doc[1] for doc in small_bucket])
        self.write_summaries(result)

    def batch_map_reduce(self, large_bucket):
        print(f"Summarizing {len(large_bucket)} large documents")
        result = self.map_reduce_chain.batch([doc[1] for doc in large_bucket])
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

    def create_map_reduce_chain(self):
        map_prompt = PromptTemplate.from_template(self.map_prompt_template)
        reduce_prompt = PromptTemplate.from_template(self.reduce_prompt_template)

        return load_summarize_chain(
            self.llm,
            chain_type="map_reduce",
            map_prompt=map_prompt,
            combine_prompt=reduce_prompt,
            combine_document_variable_name="text",
            map_reduce_document_variable_name="text",
        )

    def txt_path_to_summary_path(self, doc_txt_path):
        abs_document_path = os.path.abspath(doc_txt_path)
        abs_txt_path = os.path.abspath(CONFIG.documents_txt_output_path())

        if not abs_document_path.startswith(abs_txt_path):
            raise Exception(f"Documents must be under {abs_txt_path}")

        txt_relative = abs_document_path[len(abs_txt_path) + 1:]
        summary_relative = os.path.join(os.path.dirname(txt_relative), os.path.join(os.path.basename(txt_relative)[:-4]) + ".summary")
        return CONFIG.documents_summary_output_path(self.language, summary_relative)


def write_json():
    summary_paths = glob.glob(CONFIG.documents_summary_output_path("**/*.summary"), recursive=True)
    summary_pairs = get_summary_pairs(summary_paths)
    summary_jsons = [dict(
        document_id=s[0],
        summary_nl=s[1].text,
        summary_fr=s[2].text) for s in summary_pairs]
    with open(CONFIG.documents_summaries_json_output_path(), 'w') as fp:
        json.dump(summary_jsons, fp, indent=2)


@dataclass
class Summary:
    document_id: str
    text: str


def get_summary_pairs(summary_paths):
    nl_files = [to_summary(path) for path in summary_paths if "/nl/" in path]
    fr_files = [to_summary(path) for path in summary_paths if "/fr/" in path]

    nl_by_id = dict((summary.document_id, summary) for summary in nl_files if summary is not None)
    fr_by_id = dict((summary.document_id, summary) for summary in fr_files if summary is not None)

    missing_fr = nl_by_id.keys() - fr_by_id.keys()
    missing_nl = fr_by_id.keys() - nl_by_id.keys()
    if missing_fr:
        print(f"{len(missing_fr)} fr summaries are missing")
    if missing_nl:
        print(f"{len(missing_nl)} nl summaries are missing")

    return [(s.document_id, s, fr_by_id.get(s.document_id)) for s in nl_by_id.values() if s.document_id in fr_by_id.keys()]


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
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <language> <min-size> <max-size>")
        sys.exit(1)

    language = sys.argv[1]
    min_size = int(sys.argv[2], 10)
    max_size = int(sys.argv[3], 10)

    docs = DocumentSummarizer(language).determine_documents_to_summarize(min_size, max_size)
    summarizer = DocumentSummarizer(language)
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
    phrases.sort(key = lambda k: -len(files_by_first_line[k]))
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
