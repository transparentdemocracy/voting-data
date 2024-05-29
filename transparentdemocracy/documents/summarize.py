import glob
import logging
import os
import sys
from io import StringIO

from langchain.chains.combine_documents.base import BaseCombineDocumentsChain
from langchain.chains.summarize import load_summarize_chain
from langchain_community.chat_models import ChatOllama
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_text_splitters import CharacterTextSplitter

from transparentdemocracy import CONFIG

logger = logging.getLogger("__name__")
logger.setLevel(logging.INFO)

# Config for llama3
OLLAMA_MODEL = "llama3"  # 7b parameters
# must match model, see https://en.wikipedia.org/wiki/Llama_(language_model)
CONTEXT_WINDOW = 8912

#
SUMMARY_SIZE = 400  # number of tokens for each summary
# A word is +- 1.3 tokens
WORDS_PER_DOCUMENT = int((CONTEXT_WINDOW - SUMMARY_SIZE) / 1.3)

PROMPT_BRIEFNESS = "What is the summary of the following document in Dutch? Do not introduce your answer and to not write a conclusion at the end."
PROMPT_VOCAB = "Use vocabulary that's suitable for laypeople."


class DocumentSummarizer():
    def __init__(self):
        self.llm = ChatOllama(model=OLLAMA_MODEL)

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
            output_path = txt_path_to_summary_path(document_path)

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

    @staticmethod
    def write_summaries(result):

        for r in result:
            input_docs = r['input_documents']
            output_text = r['output_text']
            if len(input_docs) > 1:
                logger.warn("multiple input docs")
                for doc in input_docs:
                    print(doc.metadata['source'])
            input_path = input_docs[0].metadata['source']
            output_filename = txt_path_to_summary_path(input_path)
            output_path = os.path.join(
                os.path.dirname(input_path), output_filename)

            print(f"Writing {output_path}")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w') as fp:
                fp.write(output_text)

    def create_stuff_chain(self):
        prompt = PromptTemplate.from_template(
            f"""Summarize the following law proposal or amendment. Your summary must be in Dutch only. {PROMPT_BRIEFNESS} {PROMPT_VOCAB}.
		{{text}}
		CONCISE SUMMARY:""")

        return load_summarize_chain(self.llm, chain_type="stuff", prompt=prompt, document_variable_name="text")

    def create_map_reduce_chain(self):
        map_prompt = PromptTemplate.from_template(
            f"""Summarize the following part of a law proposal or amendment. Your summary must be in Dutch only. {PROMPT_BRIEFNESS}
		{{text}}
		CONCISE SUMMARY:
		""")

        reduce_prompt = PromptTemplate.from_template(f"""The following is set of summaries:
		{{text}}
		Take these and distill it into a final, consolidated summary of the main themes. Your summary must be in Dutch only. {PROMPT_BRIEFNESS} {PROMPT_VOCAB}
		Helpful Answer:""")

        return load_summarize_chain(
            self.llm,
            chain_type="map_reduce",
            map_prompt=map_prompt,
            combine_prompt=reduce_prompt,
            combine_document_variable_name="text",
            map_reduce_document_variable_name="text",
        )


def txt_path_to_summary_path(doc_txt_path):
    abs_document_path = os.path.abspath(doc_txt_path)
    abs_txt_path = os.path.abspath(CONFIG.documents_txt_output_path())

    if not abs_document_path.startswith(abs_txt_path):
        raise Exception(f"Documents must be under {abs_txt_path}")

    txt_relative = abs_document_path[len(abs_txt_path) + 1:]
    summary_relative = os.path.join(os.path.dirname(txt_relative), os.path.join(
        os.path.basename(txt_relative)[:-4]) + ".summary")
    return CONFIG.documents_summary_output_path(summary_relative)


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <min-size> <max-size>")
        sys.exit(1)

    min_size_inclusive = int(sys.argv[1])
    max_size_exclusive = int(sys.argv[2])

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
        if not os.path.exists(txt_path_to_summary_path(path))
    ]
    print(f"Documents matching size criteria: {len(docs)}")
    print(
        f"Documents not yet summarized matching criteria: {len(not_summarized)}")

    summarizer = DocumentSummarizer()
    summarizer.summarize_documents(docs)

    if __name__ == "__main__":
        main()
