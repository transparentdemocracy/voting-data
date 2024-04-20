from voting_extractors import FederalChamberVotingPdfExtractor, FederalChamberVotingHtmlExtractor, TokenizedText
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

class TestFederalChamberVotingHtmlExtractor(unittest.TestCase):
  
  @unittest.skip("WIP")
  def test_extract(self):
    actual = FederalChamberVotingHtmlExtractor().extract('../data/input/ip298x.html')

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

class TestTokenizedText(unittest.TestCase):

	def test_find_sequence(self):
			text = "TO BE OR NOT TO BE"

			tokenized = TokenizedText(text)
			
			self.assertEqual(tokenized.find_sequence(["BALLOON"]), -1)
			self.assertEqual(tokenized.find_sequence(["TO"]), 0)
			self.assertEqual(tokenized.find_sequence(["OR"]), 2)
			self.assertEqual(tokenized.find_sequence(["NOT"]), 3)

			self.assertEqual(tokenized.find_sequence(["TO", "BE"]), 0)

	def test_find_occurrences(self):
			text = "TO BE OR NOT TO BE"

			tokenized = TokenizedText(text)

			self.assertEqual(tokenized.find_occurrences(["BALLOON"]), [])
			self.assertEqual(tokenized.find_occurrences(["TO","BE"]), [0, 4])
			self.assertEqual(tokenized.find_occurrences(["TO","OR"]), [])
			self.assertEqual(tokenized.find_occurrences(["BE","FOO"]), [])
