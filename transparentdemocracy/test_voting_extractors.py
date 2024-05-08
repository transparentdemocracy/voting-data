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
		plenaries, all_votes = extract_from_html_plenary_reports(os.path.join(PLENARY_HTML_INPUT_PATH, "*.html"))

		self.assertEqual(len(plenaries), 300)

		all_motions = [motion for plenary in plenaries for motion in plenary.motions]
		self.assertEqual(len(all_motions), 2842)

		motions_with_problems = list(filter(lambda m: len(m.parse_problems) > 0, all_motions))

		# TODO: Improve how we handle parsing problems
		self.assertEqual(len(motions_with_problems), 17)

	def test_extract_from_html_plenary_report__ip298x_html__go_to_example_report(self):
		# Plenary report 298 has long been our first go-to example plenary report to test our extraction against.
		# Arrange
		report_file_name = os.path.join(PLENARY_HTML_INPUT_PATH, "ip298x.html")

		# Act
		plenary, votes = extract_from_html_plenary_report(report_file_name)

		# Assert
		# The plenary info is extracted correctly:
		self.assertEqual(plenary.id, "55_298")
		self.assertEqual(plenary.number, 298)
		self.assertEqual(plenary.date, date(2024, 4, 4))
		self.assertEqual(plenary.legislature, 55)
		self.assertEqual(plenary.pdf_report_url, "https://www.dekamer.be/doc/PCRI/pdf/55/ip298.pdf")
		self.assertEqual(plenary.html_report_url, "https://www.dekamer.be/doc/PCRI/html/55/ip298x.html")

		# The proposals are extracted correctly:
		self.assertEqual(len(plenary.proposals), 6)
		self.assertEqual(plenary.proposals[0].id, "55_298_p01")
		self.assertEqual(plenary.proposals[0].plenary_agenda_item_number, 1)
		self.assertEqual(plenary.proposals[0].plenary_id, "55_298")
		self.assertEqual(plenary.proposals[0].title_nl, "Wetsontwerp houdende optimalisatie van de werking van het Centraal Orgaan voor de Inbeslagneming en de Verbeurdverklaring en het Overlegorgaan voor de coördinatie van de invordering van niet-fiscale schulden in strafzaken en houdende wijziging van de Wapenwet")
		self.assertEqual(plenary.proposals[0].title_fr, "Projet de loi optimisant le fonctionnement de l'Organe central pour la Saisie et la Confiscation et de l'Organe de concertation pour la coordination du recouvrement des créances non fiscales en matière pénale et modifiant la loi sur les armes")
		self.assertEqual(plenary.proposals[0].document_reference, "3849/1-4")
		self.assertTrue(plenary.proposals[0].description_nl.startswith("Wij vatten de bespreking van de artikelen aan."))
		self.assertTrue(plenary.proposals[0].description_fr.startswith("Nous passons à la discussion des articles."))
		self.assertTrue(plenary.proposals[0].description_nl.endswith("De bespreking van de artikelen is gesloten. De stemming over het geheel zal later plaatsvinden."))
		self.assertTrue(plenary.proposals[0].description_fr.endswith("La discussion des articles est close. Le vote sur l'ensemble aura lieu ultérieurement."))

		# The motions are extracted correctly:
		self.assertEqual(28, len(plenary.motions))
		self.assertEqual(plenary.motions[0].id, "55_298_1") # TODO modify id creation so it doesn't clash with proposals and sections
		self.assertEqual(False, plenary.motions[0].cancelled)
		self.assertEqual(True, plenary.motions[11].cancelled)

		# The votes are extracted correctly:
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

	def test_extract_from_html_plenary_report__ip261x_html__different_proposals_header(self):
		# This example proposal has "Projets de loi et propositions" as proposals header, rather than "Projets de loi".
		# Also, the proposal description header ("Bespreking van de artikelen") cannot be found, so we fall back to 
		# taking the entire text after the proposal header in a best-effort as the description, both for Dutch and 
		# French.
		# Arrange
		report_file_name = os.path.join(PLENARY_HTML_INPUT_PATH, "ip261x.html")

		# Act
		plenary, votes = extract_from_html_plenary_report(report_file_name)

		# Assert
		# The plenary info is extracted correctly:
		self.assertEqual(plenary.id, "55_261")
		self.assertEqual(plenary.number, 261)
		self.assertEqual(plenary.date, date(2023, 10, 5))
		self.assertEqual(plenary.legislature, 55)
		self.assertEqual(plenary.pdf_report_url, "https://www.dekamer.be/doc/PCRI/pdf/55/ip261.pdf")
		self.assertEqual(plenary.html_report_url, "https://www.dekamer.be/doc/PCRI/html/55/ip261x.html")

		# The proposals are extracted correctly:
		self.assertEqual(len(plenary.proposals), 4)
		self.assertEqual(plenary.proposals[0].id, "55_261_p20")
		self.assertEqual(plenary.proposals[0].plenary_agenda_item_number, 20)
		self.assertEqual(plenary.proposals[0].plenary_id, "55_261")
		self.assertEqual(plenary.proposals[0].title_nl, "Verzoek om advies van de Raad van State")
		self.assertEqual(plenary.proposals[0].title_fr, "Demande d'avis du Conseil d'État")
		self.assertEqual(plenary.proposals[0].document_reference, None)
		self.assertTrue(plenary.proposals[0].description_nl.startswith("20.01  Peter De Roover (N-VA): Mevrouw de voorzitster, "))
		self.assertTrue(plenary.proposals[0].description_fr.startswith("20.01  Peter De Roover (N-VA): Mevrouw de voorzitster, "))
		self.assertTrue(plenary.proposals[0].description_nl.endswith("Bijgevolg zal de voorzitster het advies van de Raad van State vragen met toepassing van artikel 98.3 van het Reglement."))
		self.assertTrue(plenary.proposals[0].description_fr.endswith("Bijgevolg zal de voorzitster het advies van de Raad van State vragen met toepassing van artikel 98.3 van het Reglement."))

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
