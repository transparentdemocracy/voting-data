import os
import unittest

import transparentdemocracy
from transparentdemocracy import CONFIG
from transparentdemocracy.politicians.extraction import PoliticianExtractor


class TestPoliticians(unittest.TestCase):

	@classmethod
	def setUpClass(cls):
		root_folder = os.path.dirname(os.path.dirname(transparentdemocracy.__file__))
		CONFIG.data_dir = os.path.join(root_folder, "testdata")

	def test_extract(self):
		politicians = PoliticianExtractor().extract_politicians(pattern="7???.json")

		self.assertIsNotNone(politicians)

	def test_get_by_name(self):
		politicians = PoliticianExtractor().extract_politicians(pattern="7???.json")

		actual = politicians.get_by_name("Liekens Goedele")

		self.assertIsNotNone(actual.id, 7448)
