import os
from dataclasses import dataclass


@dataclass
class Config:
	data_dir: str

	def __init__(self, data_dir):
		self.data_dir = data_dir

	def resolve(self, *path):
		return os.path.join(self.data_dir, *path)

	def plenary_html_input_path(self, *path):
		return self.resolve("input", "plenary", "html", *path)

	def actor_json_input_path(self):
		return self.resolve("input", "actors", "actor")

	# output
	def plenary_markdown_output_path(self):
		return self.resolve("output", "plenary", "markdown")

	def plenary_json_output_path(self):
		return self.resolve("output", "plenary", "json")

	def politicians_json_output_path(self, *path):
		return self.resolve(self.data_dir, "output", "politician", *path)

	def documents_input_path(self, *path):
		return self.resolve(self.data_dir, "input", "documents", *path)

	def documents_txt_output_path(self, *path):
		return self.resolve(self.data_dir, "output", "documents", "txt", *path)


def _create_config():
	root_folder = os.path.dirname(os.path.dirname(__file__))
	return Config(os.path.join(root_folder, "data"))


CONFIG = _create_config()
