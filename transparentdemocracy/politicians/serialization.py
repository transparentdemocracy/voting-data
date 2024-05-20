import json
import os
from typing import List

from transparentdemocracy import CONFIG
from transparentdemocracy.model import Politician
from transparentdemocracy.politicians.extraction import PoliticianExtractor


class JsonSerializer:
	def __init__(self, output_path=CONFIG.politicians_json_output_path()):
		self.output_path = output_path
		os.makedirs(self.output_path, exist_ok=True)

	def serialize_politicians(self, politicians: List[Politician]) -> None:
		self._serialize_list(politicians, "politicians.json")

	def _serialize_list(self, some_list: List, output_file: str) -> None:
		list_json = json.dumps(
			some_list,
			default=lambda o: o.__dict__,
			indent=4)
		with open(os.path.join(self.output_path, output_file), "w") as output_file:
			output_file.write(list_json)


def serialize(politicians: List[Politician]) -> None:
	serialize_json(politicians)


def serialize_json(politicians: List[Politician]) -> None:
	json_serializer = JsonSerializer()
	json_serializer.serialize_politicians(politicians)


def create_json():
	JsonSerializer().serialize_politicians(PoliticianExtractor().extract_politicians().politicians)


def print_politicians_by_party():
	politicians = PoliticianExtractor().extract_politicians()

	politicians.print_by_party()
