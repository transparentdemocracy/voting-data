import json
import os
from typing import List

from transparentdemocracy.model import Politician
from transparentdemocracy.politicians.extraction import PoliticianExtractor


class PoliticianJsonSerializer:
    def __init__(self, politicians_json_path):
        self.politicians_json_path = politicians_json_path

    def serialize_politicians(self, politicians: List[Politician]) -> None:
        self._serialize_list(politicians)

    def _serialize_list(self, some_list: List) -> None:
        os.makedirs(os.path.dirname(self.politicians_json_path), exist_ok=True)
        list_json = json.dumps(
            some_list,
            default=lambda o: o.__dict__,
            indent=2)
        with open(self.politicians_json_path, "w") as output_file:
            output_file.write(list_json)


def print_politicians_by_party():
    politicians = PoliticianExtractor().extract_politicians()

    politicians.print_by_party()
