from voting_extractors import FederalChamberVotingPdfExtractor
from model import Motion, Proposal

import unittest

class TestFederalChamberVotingPdfExtractor(unittest.TestCase):
    
    def test_extract(self):
        actual = FederalChamberVotingPdfExtractor().extract('../data/input/ip298.pdf')

        self.assertEqual(len(actual), 13)
        self.assertEqual(actual[0].proposal.number, 10)
        expected_description = 'Motions déposées en conclusion'
        self.assertEqual(actual[0].proposal.description[:len(expected_description)], expected_description)
        self.assertEqual(actual[0].num_votes_yes,16) 
        self.assertEqual(len(actual[0].vote_names_yes),16)
        self.assertEqual(actual[0].vote_names_yes[:2], ['Bury Katleen', 'Creyelman Steven'])
        self.assertEqual(actual[0].num_votes_no,116)
        self.assertEqual(len(actual[0].vote_names_no),116)
        self.assertEqual(actual[0].vote_names_no[:2],["Anseeuw Björn","Aouasti Khalil"])
        self.assertEqual(actual[0].num_votes_abstention,1)
        self.assertEqual(actual[0].vote_names_abstention,['Özen Özlem'])
        self.assertEqual(actual[0].cancelled,False)

