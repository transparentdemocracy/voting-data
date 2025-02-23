import json
import os
from typing import List

from transparentdemocracy import Config
from transparentdemocracy.model import Politician
from transparentdemocracy.politicians.extraction import PoliticianExtractor


class JsonSerializer:
    def __init__(self, output_path):
        self.output_path = output_path
        os.makedirs(self.output_path, exist_ok=True)

    def serialize_politicians(self, politicians: List[Politician]) -> None:
        self._serialize_list(politicians, "politicians.json")

    def _serialize_list(self, some_list: List, output_file: str) -> None:
        list_json = json.dumps(
            some_list,
            default=lambda o: o.__dict__,
            indent=2)
        with open(os.path.join(self.output_path, output_file), "w") as output_file:
            output_file.write(list_json)


# TODO check callers
def create_json(config: Config):
    JsonSerializer(config.plenary_json_output_path()).serialize_politicians(
        PoliticianExtractor(config).extract_politicians().politicians)


def print_politicians_by_party():
    politicians = PoliticianExtractor().extract_politicians()

    politicians.print_by_party()
