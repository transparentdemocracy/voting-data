import unittest

from transparentdemocracy.config import _create_config
from transparentdemocracy.main import Environments
from transparentdemocracy.politicians.extraction import PoliticianExtractor


class TestPoliticians(unittest.TestCase):
    config = _create_config(Environments.TEST, '55')

    def test_extract(self):
        politicians = PoliticianExtractor(self.config).extract_politicians(pattern="7???.json")

        self.assertIsNotNone(politicians)

    def test_get_by_name(self):
        politicians = PoliticianExtractor(self.config).extract_politicians(pattern="7???.json")

        actual = politicians.get_by_name("Liekens Goedele")

        self.assertIsNotNone(actual.id, 7448)
