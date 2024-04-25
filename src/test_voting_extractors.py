import logging
import os
import unittest

from voting_extractors import FederalChamberVotingPdfExtractor, FederalChamberVotingHtmlExtractor, TokenizedText, \
	find_sequence, find_occurrences

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
logger.setLevel(logging.DEBUG)


class TestFederalChamberVotingHtmlExtractor(unittest.TestCase):

	@unittest.skipIf(os.environ.get("SKIP_SLOW", None) is not None, "skipping slow tests")
	def test_extract_from_all_plenary_reports_does_not_throw(self):
		actual = FederalChamberVotingHtmlExtractor().extract_from_all_plenary_reports('../data/input/html/*.html')

		self.assertEqual(len(actual), 300)

		all_motions = [motion for plenary in actual for motion in plenary.motions]
		self.assertEqual(len(all_motions), 2842)

		motions_with_problems = list(filter(lambda m: len(m.parse_problems) > 0, all_motions))

		# TODO: Improve how we handle parsing problems
		self.assertEqual(len(motions_with_problems), 17)

	def test_extract_ip67(self):
		actual = FederalChamberVotingHtmlExtractor().parse_plenary_report('./data/input/ip067x.html')

		self.assertEqual(len(actual.motions), 18)
		self.assertEqual(actual.motions[0].parse_problems,
						 ["vote count (51) does not match voters []"])

	def test_extract_ip72(self):
		"""vote 2 has an extra '(' in the vote result indicator"""
		actual = FederalChamberVotingHtmlExtractor().extract_from_plenary_report('../data/input/html/ip072x.html')

		self.assertEqual(len(actual.motions), 5)

	def test_extract_ip298(self):
		actual = FederalChamberVotingHtmlExtractor().extract_from_plenary_report('../data/input/html/ip298x.html')

		self.assertEqual(28, len(actual.proposals))
		self.assertEqual(actual.motions[0].proposal.id, "1")

		# TODO: there's introductory stuff here that shouldn't be part of the proposal description
		expected_description_start = "\nVotes\nnominatifs\nVotes\nnominatifs\n\n\xa0\n\xa0\n\xa0\n09.02 \xa0Sofie Merckx (PVDA-PTB): Mevrouw de voorzitster, mevrouw Verhaert moest ons\nverlaten en mevrouw Daems zal haar stemgedrag daarvoor aanpassen."
		self.assertEqual(actual.motions[0].proposal.description[:len(expected_description_start)],
						 expected_description_start)
		motion0 = actual.motions[0]

		self.assertEqual(79, motion0.num_votes_yes)
		self.assertEqual(79, len(motion0.vote_names_yes))
		self.assertEqual(['Aouasti Khalil', 'Bacquelaine Daniel'], motion0.vote_names_yes[:2])

		self.assertEqual(50, motion0.num_votes_no, )
		self.assertEqual(50, len(motion0.vote_names_no))
		self.assertEqual(["Anseeuw Björn", "Bruyère Robin"], motion0.vote_names_no[:2])

		self.assertEqual(4, motion0.num_votes_abstention)
		self.assertEqual(4, len(motion0.vote_names_abstention))
		self.assertEqual(['Arens Josy', 'Daems Greet'], motion0.vote_names_abstention[:2])

		self.assertEqual(False, motion0.cancelled)
		self.assertEqual(True, actual.motions[11].cancelled)


class TestTokenizedText(unittest.TestCase):

	def test_find_sequence(self):
		text = "TO BE OR NOT TO BE"

		tokens = TokenizedText(text).tokens

		self.assertEqual(find_sequence(tokens, ["BALLOON"]), -1)
		self.assertEqual(find_sequence(tokens, ["TO"]), 0)
		self.assertEqual(find_sequence(tokens, ["OR"]), 2)
		self.assertEqual(find_sequence(tokens, ["NOT"]), 3)

		self.assertEqual(find_sequence(tokens, ["TO", "BE"]), 0)

	def test_find_occurrences(self):
		text = "TO BE OR NOT TO BE"

		tokens = TokenizedText(text).tokens

		self.assertEqual(find_occurrences(tokens, ["BALLOON"]), [])
		self.assertEqual(find_occurrences(tokens, ["TO", "BE"]), [0, 4])
		self.assertEqual(find_occurrences(tokens, ["TO", "OR"]), [])
		self.assertEqual(find_occurrences(tokens, ["BE", "FOO"]), [])
