import logging
import os
import unittest
from datetime import date

from transparentdemocracy import PLENARY_HTML_INPUT_PATH
from transparentdemocracy.plenaries.extraction import extract_from_html_plenary_reports, \
	extract_from_html_plenary_report

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logger.setLevel(logging.INFO)


class TestFederalChamberVotingHtmlExtractor(unittest.TestCase):

	@unittest.skipIf(os.environ.get("SKIP_SLOW", None) is not None, "skipping slow tests")
	def test_extract_from_all_plenary_reports_does_not_throw(self):
		actual = extract_from_html_plenary_reports(os.path.join(PLENARY_HTML_INPUT_PATH, "*.html"))

		self.assertEqual(len(actual), 300)

		all_motions = [motion for plenary in actual for motion in plenary.motions]
		self.assertEqual(len(all_motions), 2842)

		motions_with_problems = list(filter(lambda m: len(m.parse_problems) > 0, all_motions))

		# TODO: Improve how we handle parsing problems
		self.assertEqual(len(motions_with_problems), 17)

	@unittest.skip(
		"suppressed for now - we can't make the distinction between 'does not match voters' problem and actually having 0 votes right now")
	def test_extract_ip67(self):
		actual, votes = extract_from_html_plenary_report(os.path.join(PLENARY_HTML_INPUT_PATH, 'ip067x.html'))

		vote_types_motion_1 = set([v.vote_type for v in votes if v.motion_id == "55_067_1"])
		self.assertTrue("NO" in vote_types_motion_1)

	def test_extract_ip72(self):
		"""vote 2 has an extra '(' in the vote result indicator"""
		actual, votes = extract_from_html_plenary_report(os.path.join(PLENARY_HTML_INPUT_PATH, 'ip072x.html'))

		self.assertEqual(len(actual.motions), 5)

	def test_extract_ip298(self):
		actual, votes = extract_from_html_plenary_report(os.path.join(PLENARY_HTML_INPUT_PATH, 'ip298x.html'))

		self.assertEqual(28, len(actual.motions))
		self.assertEqual(actual.motions[0].id, "55_298_1")

		# TODO: there's introductory stuff here that shouldn't be part of the proposal description
		expected_description_start = "\nVotes\nnominatifs\nVotes\nnominatifs\n\n\xa0\n\xa0\n\xa0\n09.02 \xa0Sofie Merckx (PVDA-PTB): Mevrouw de voorzitster, mevrouw Verhaert moest ons\nverlaten en mevrouw Daems zal haar stemgedrag daarvoor aanpassen."
		self.assertEqual(actual.proposals[0].description[:len(expected_description_start)],
						 expected_description_start)

		yes_voters = [vote.politician.full_name for vote in votes if
					  vote.vote_type == "YES" and vote.motion_id == "55_298_1"]
		no_voters = [vote.politician.full_name for vote in votes if
					 vote.vote_type == "NO" and vote.motion_id == "55_298_1"]
		abstention_voters = [vote.politician.full_name for vote in votes if
							 vote.vote_type == "ABSTENTION" and vote.motion_id == "55_298_1"]

		count_yes = len(yes_voters)
		count_no = len(no_voters)
		count_abstention = len(abstention_voters)

		self.assertEqual(79, count_yes)
		self.assertEqual(['Aouasti Khalil', 'Bacquelaine Daniel'], yes_voters[:2])

		self.assertEqual(50, count_no)
		self.assertEqual(["Anseeuw Björn", "Bruyère Robin"], no_voters[:2])

		self.assertEqual(4, count_abstention)
		self.assertEqual(['Arens Josy', 'Daems Greet'], abstention_voters[:2])

		self.assertEqual(False, actual.motions[0].cancelled)
		self.assertEqual(True, actual.motions[11].cancelled)

	def test_voter_dots_are_removed_from_voter_names(self):
		actual, votes = extract_from_html_plenary_report(os.path.join(PLENARY_HTML_INPUT_PATH, 'ip182x.html'))

		names = [v.politician.full_name for v in votes]

		names_with_dots = [name for name in names if "." in name]
		self.assertEqual([], names_with_dots)

	@unittest.skipIf(os.environ.get("SKIP_SLOW", None) is not None, "skipping slow tests")
	def test_votes_must_have_politician(self):
		actual, votes = extract_from_html_plenary_reports()

		for vote in votes:
			self.assertIsNotNone(vote.politician)

	def test_plenary_date1(self):
		plenary, votes = extract_from_html_plenary_report(os.path.join(PLENARY_HTML_INPUT_PATH, "ip123x.html"))

		self.assertEqual(plenary.date, date.fromisoformat("2021-07-19"))

	def test_plenary_date2(self):
		plenary, votes = extract_from_html_plenary_report(os.path.join(PLENARY_HTML_INPUT_PATH, "ip007x.html"))

		self.assertEqual(plenary.date, date.fromisoformat("2019-10-03"))

	def test_votes_must_have_politician(self):
		actual, votes = extract_from_html_plenary_reports()

		for vote in votes:
			self.assertIsNotNone(vote.politician)

