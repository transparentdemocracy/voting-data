import unittest

from transparentdemocracy.config import _create_config
from transparentdemocracy.main import Environments
from transparentdemocracy.politicians.extraction import PoliticianExtractor


class TestPoliticians(unittest.TestCase):
    config55 = _create_config(Environments.TEST, '55')
    config56 = _create_config(Environments.TEST, '56')

    def test_extract(self):
        politicians = PoliticianExtractor(self.config55).extract_politicians(pattern="7???.json")

        self.assertIsNotNone(politicians)
        self.assertEqual(11, len(politicians.politicians_by_name))

    def test_get_by_name(self):
        politicians = PoliticianExtractor(self.config55).extract_politicians(pattern="7448.json")

        actual = politicians.get_by_name("Liekens Goedele")

        self.assertIsNotNone(actual.id, 7448)

    def test_get_by_name_non_exact_matches_edit_distance_3(self):
        politicians = PoliticianExtractor(self.config55).extract_politicians(pattern="7448.json")

        actual = politicians.get_by_name("AAAkens Goedele")

        self.assertIsNotNone(actual.id, 7448)

    def test_get_by_name_non_exact_matches_edit_distance_4_not_allowed(self):
        politicians = PoliticianExtractor(self.config55).extract_politicians(pattern="7448.json")

        try:
            actual = politicians.get_by_name("AAAAens Goedele")
            self.fail("Politician lookup with edit distance too big should fail")
        except Exception:
            pass

    def test_extraction_niels_tas(self):
        """ Check presence of Niels Tas in leg 56 """
        politicians = PoliticianExtractor(self.config56).extract_politicians(pattern="7921.json")

        actual = politicians.get_by_name("Tas Niels")

        self.assertEqual("Tas Niels", actual.full_name)
        self.assertEqual("Vooruit", actual.party)

    def test_extraction_axel_weydts(self):
        """ Check party for Axel Weydts in leg 56 """
        politicians = PoliticianExtractor(self.config56).extract_politicians(pattern="8051.json")

        actual = politicians.get_by_name("Weydts Axel")

        self.assertEqual("Weydts Axel", actual.full_name)
        self.assertEqual("Vooruit", actual.party)

    def test_extraction_joppe_leybaert(self):
        """ Check party for Axel Weydts in leg 56 """
        politicians = PoliticianExtractor(self.config56).extract_politicians(pattern="7920.json")

        actual = politicians.get_by_name("Leybaert Joppe")

        self.assertEqual("Leybaert Joppe", actual.full_name)
        self.assertEqual("PVDA", actual.party)

