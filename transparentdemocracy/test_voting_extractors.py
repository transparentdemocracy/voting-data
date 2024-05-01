import logging
import os
import unittest

from transparentdemocracy.model import VoteType
from transparentdemocracy.plenaries.extraction import extract_voting_data_from_plenary_reports, __extract_plenary, \
	extract_from_html_plenary_report

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logger.setLevel(logging.INFO)

DATA_DIR=os.path.join("..", "data")
PLENARY_HTML_DIR=os.path.join(DATA_DIR, "input", "plenary", "html")

class TestFederalChamberVotingHtmlExtractor(unittest.TestCase):

	@unittest.skipIf(os.environ.get("SKIP_SLOW", None) is not None, "skipping slow tests")
	def test_extract_from_all_plenary_reports_does_not_throw(self):
		actual = extract_voting_data_from_plenary_reports(os.path.join(PLENARY_HTML_DIR, "*.html"))

		self.assertEqual(len(actual), 300)

		all_motions = [motion for plenary in actual for motion in plenary.motions]
		self.assertEqual(len(all_motions), 2842)

		motions_with_problems = list(filter(lambda m: len(m.parse_problems) > 0, all_motions))

		# TODO: Improve how we handle parsing problems
		self.assertEqual(len(motions_with_problems), 17)

	def test_extract_ip67(self):
		actual = extract_from_html_plenary_report(os.path.join(PLENARY_HTML_DIR, 'ip067x.html'))

		self.assertEqual(len(actual.motions), 18)
		self.assertEqual(actual.motions[0].parse_problems,
						 ["vote count (51) does not match voters []"])

	def test_extract_ip72(self):
		"""vote 2 has an extra '(' in the vote result indicator"""
		actual, votes = extract_from_html_plenary_report(os.path.join(PLENARY_HTML_DIR, 'ip072x.html'))

		self.assertEqual(len(actual.motions), 5)

	def test_extract_ip298(self):
		actual, votes = extract_from_html_plenary_report(os.path.join(PLENARY_HTML_DIR, 'ip298x.html'))

		self.assertEqual(28, len(actual.motions))
		self.assertEqual(actual.motions[0].id, "55_298_1")

		# TODO: there's introductory stuff here that shouldn't be part of the proposal description
		expected_description_start = "\nVotes\nnominatifs\nVotes\nnominatifs\n\n\xa0\n\xa0\n\xa0\n09.02 \xa0Sofie Merckx (PVDA-PTB): Mevrouw de voorzitster, mevrouw Verhaert moest ons\nverlaten en mevrouw Daems zal haar stemgedrag daarvoor aanpassen."
		self.assertEqual(actual.proposals[0].description[:len(expected_description_start)],
						 expected_description_start)

		print([vote for vote in votes if vote.motion_id == "55_298_1" and vote.vote_type == VoteType.NO][0])
		count_yes = sum([1 for vote in votes if vote.vote_type == "YES" and vote.motion_id == "55_298_1"])
		count_no = sum([1 for vote in votes if vote.vote_type == VoteType.NO and vote.motion_id == "55_298_1"])
		count_abstention = sum([1 for vote in votes if vote.vote_type == VoteType.ABSTENTION and vote.motion_id == "55_298_1"])

		self.assertEqual(79, count_yes)
		# self.assertEqual(79, len(vote0.vote_names_yes))
		# self.assertEqual(['Aouasti Khalil', 'Bacquelaine Daniel'], vote0.vote_names_yes[:2])

		self.assertEqual(50, count_no)
		# self.assertEqual(50, len(vote0.vote_names_no))
		# self.assertEqual(["Anseeuw Björn", "Bruyère Robin"], vote0.vote_names_no[:2])

		self.assertEqual(4, count_abstention)
		# self.assertEqual(4, len(vote0.vote_names_abstention))
		# self.assertEqual(['Arens Josy', 'Daems Greet'], vote0.vote_names_abstention[:2])

		self.assertEqual(False, vote0.cancelled)
		self.assertEqual(True, actual.motions[11].cancelled)

	def test_voter_dots_are_removed_from_voter_names(self):
		actual = extract_from_html_plenary_report(os.path.join(PLENARY_HTML_DIR, 'ip182x.html'))

		names = [name for m in actual.motions for name in m.vote_names_abstention ]

		names_with_dots = [ name for name in names if "." in name ]
		self.assertEqual([], names_with_dots)


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
