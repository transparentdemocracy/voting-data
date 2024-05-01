import unittest

from transparentdemocracy.politicians.fetch_politicians import PoliticianExtractor


class TestPoliticians(unittest.TestCase):

	def test_extract(self):
		politicians = PoliticianExtractor().extract_politicians(pattern="7???.json")

		self.assertIsNotNone(politicians)

	def test_get_by_name(self):
		politicians = PoliticianExtractor().extract_politicians(pattern="7???.json")

		actual = politicians.get_by_name("Liekens Goedele")

		self.assertIsNotNone(actual.id, 7448)
