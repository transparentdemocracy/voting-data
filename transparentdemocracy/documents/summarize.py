import glob
import logging
import os

import tqdm
from langchain.chains.summarize import load_summarize_chain
from langchain_community.chat_models import ChatOllama
from langchain_community.document_loaders import TextLoader

from transparentdemocracy import CONFIG

logger = logging.getLogger("__name__")
logger.setLevel(logging.INFO)


class DocumentSummarizer():
	def __init__(self):
		self.llm = ChatOllama(model="llama3")
		self.chain = load_summarize_chain(self.llm, chain_type="stuff")

	def summarize_documents(self, num_documents=None):
		document_paths = glob.glob(os.path.join(CONFIG.documents_path(), "??", "??", "*.txt"))
		if num_documents is not None:
			document_paths = document_paths[:num_documents]

		for document_path in tqdm.tqdm(document_paths, "Summarizing documents..."):
			print(f"Summarizing {document_path}")
			dirname = os.path.dirname(document_path)
			summary_filename = os.path.basename(document_path)[:-4] + ".summary"
			summary_path = os.path.join(dirname, summary_filename)

			summary = self.summarize_document(document_path)
			with open(summary_path, 'w') as fp:
				fp.write(summary)

	def summarize_document(self, document_path):
		logger.info(f"Summarizing {document_path}")
		loader = TextLoader(document_path)
		docs = loader.load()
		return self.chain.invoke(docs)['output_text']


def main():
	summarizer = DocumentSummarizer()
	summarizer.summarize_documents()


if __name__ == "__main__":
	main()
