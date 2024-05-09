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


def _create_config():
	return Config(os.path.join(os.path.dirname(__file__), "..", "data"))


CONFIG = _create_config()
