import os
import unittest

from transparentdemocracy.config import _create_config
from transparentdemocracy.main import Environments
from transparentdemocracy.politicians.extraction import PoliticianExtractor


class TestPoliticians(unittest.TestCase):
    config55 = _create_config(Environments.TEST, '55')
    config56 = _create_config(Environments.TEST, '56')
    config56_local = _create_config(Environments.LOCAL, '56')

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
        """ Check party for Leybaert Joppe in leg 56 """
        politicians = PoliticianExtractor(self.config56).extract_politicians(pattern="7920.json")

        actual = politicians.get_by_name("Leybaert Joppe")

        self.assertEqual("Leybaert Joppe", actual.full_name)
        self.assertEqual("PVDA-PTB", actual.party)

    def test_party_names_not_null_for_christophe_bombled(self):
        politicians = PoliticianExtractor(self.config56).extract_politicians(pattern="6934.json")

        actual = politicians.get_by_name("Bombled Christophe")

        self.assertEqual("Bombled Christophe", actual.full_name)
        self.assertEqual("MR", actual.party)

    # TODO: test for Philippe Close (bxl)
    # TODO: test for 7133, Boukili, Nabil: {'PVDA-PTB', 'PTB-PVDA'}
    def test_politicians_leg_56_no_unknown_parties(self):
        politicians = PoliticianExtractor(self.config56).extract_politicians(pattern="????.json")

        for politician in politicians.politicians_by_name.values():
            self.assertIsNotNone(politician.party, f"Politician {politician.full_name} has no party")
            self.assertNotEquals("unknown", politician.party)

    def test_party_names(self):
        politicians = PoliticianExtractor(self.config56).extract_politicians(pattern="????.json")
        party_names = sorted(set([p.party for p in politicians.politicians_by_id.values()]))

        self.assertEqual(['MR', 'PVDA-PTB', 'Vooruit'], party_names)

    @unittest.skipIf(os.environ.get("SKIP_SLOW", None) is not None, "This test isn't really slow but requires data")
    def test_parties_leg_56(self):
        #politicians = load_politicians(self.config56_local)
        politicians = PoliticianExtractor(self.config56_local).extract_politicians(pattern="????.json")

        # read kamer56_leden.csv
        with open(os.path.join(os.path.dirname(__file__), "kamer56_leden.csv"), "r") as f:
            reference = [ f.strip().split("\t", 2) for f in f.readlines() ]
            reference = { r[0]: r[1] for r in reference }

        accepted_parties = set(reference.values())

        mismatches = []
        bad_parties = []
        for politician in politicians.politicians:
            if politician.party not in accepted_parties:
                bad_parties.append((politician.id, politician.full_name, politician.party))
            if politician.full_name not in reference:
                # 'opvolgers' are not in the reference list
                continue
            if reference[politician.full_name] != politician.party:
                mismatches.append((politician.full_name, reference[politician.full_name], politician.party))

        self.assertEquals(150, len(reference))
        self.assertListEqual(mismatches, [])
        self.assertListEqual(bad_parties, [])
