import logging
import os
import unittest
from datetime import date

import transparentdemocracy
from transparentdemocracy.config import CONFIG
from transparentdemocracy.model import ReportItem, Motion, Vote
from transparentdemocracy.plenaries.extraction import extract_from_html_plenary_reports, \
	extract_from_html_plenary_report, _get_plenary_date, _extract_motion_report_items, \
	_extract_motions, _extract_votes, create_plenary_extraction_context
from transparentdemocracy.politicians.extraction import load_politicians

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logger.setLevel(logging.INFO)

ROOT_FOLDER = os.path.dirname(os.path.dirname(transparentdemocracy.__file__))


class ReportItemExtractionTest(unittest.TestCase):

	@classmethod
	def setUpClass(cls):
		CONFIG.data_dir = os.path.join(ROOT_FOLDER, "testdata")

	def test_extract_ip298_happy_case(self):
		report_items = self.extract_motion_report_items('ip298x.html')

		self.assertEqual(len(report_items), 14)  # motions 10 - 23 (?)

		self.assert_report_item(report_items[0],
								"10",
								"10 Moties ingediend",
								"10 Motions déposées en conclusion des interpellations de")

		self.assert_report_item(report_items[1],
								"11",
								"11 Wetsontwerp\nhoudende diverse wijzigingen van het Wetboek van strafvordering II, zoals\ngeamendeerd tijdens de plenaire vergadering van 28 maart 2024 (3515/10)",
								"11 Projet de loi portant diverses modifications du Code d'instruction\ncriminelle II, tel qu'amendé lors de la séance plénière du 28 mars 2024\n(3515/10)")

	def test_extract_ip280_has_1_naamstemming_but_no_identifiable_motion_title(self):
		report_items = self.extract_motion_report_items('ip280x.html')

		self.assertEqual(len(report_items), 0)

	def test_extract_ip271(self):
		report_items = self.extract_motion_report_items('ip271x.html')

		self.assertEqual(len(report_items), 14)  # todo: check manually

		self.assert_report_item(report_items[0],
								'14',
								'14 Moties ingediend tot besluit van de\ninterpellatie van mevrouw Barbara Pas',
								'14 Motions déposées en conclusion de l\'interpellation de Mme Barbara\nPas')

		# FIXME: Do we count 'Goedkeuring van de agenda' as a motion?
		# If we link the motions with their votes we could exclude motions without votes
		self.assert_report_item(report_items[-1],
								'27',
								'27 Wetsontwerp tot\nwijziging',
								'27 Projet de loi visant à modi')

	def test_extract_ip290_has_no_naamstemmingen(self):
		report_items = self.extract_motion_report_items('ip290x.html')

		self.assertEqual(report_items, [])

	def assert_report_item(self, report_item: ReportItem, label: str, nl_title_prefix: str, fr_title_prefix: str):
		self.assertEqual(label, report_item.label)
		self.assertEqual(report_item.nl_title[:len(nl_title_prefix)], nl_title_prefix)
		self.assertEqual(report_item.fr_title[:len(fr_title_prefix)], fr_title_prefix)

	def extract_motion_report_items(self, report_path):
		path = CONFIG.plenary_html_input_path(report_path)
		ctx = create_plenary_extraction_context(path, load_politicians())
		return _extract_motion_report_items(ctx)


class MotionExtractionTest(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		CONFIG.data_dir = os.path.join(ROOT_FOLDER, "testdata")

	def test_extract_motions(self):
		report_path = CONFIG.plenary_html_input_path("ip298x.html")
		ctx = create_plenary_extraction_context(report_path, load_politicians())
		motion_report_items, motions = _extract_motions("55_298", ctx)

		self.assertEqual(28, len(motions))
		self.assertEqual(Motion("55_298_m1", "1", "55_298_10", False, "TODO"), motions[0])


class VoteExtractionTest(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		CONFIG.data_dir = os.path.join(ROOT_FOLDER, "testdata")

	def test_extract_votes_ip298x(self):
		# TODO: create helper function for creating a PlenaryExtractionContext with html
		report_path = CONFIG.plenary_html_input_path("ip298x.html")
		politicians = load_politicians()
		ctx = create_plenary_extraction_context(report_path, politicians)
		votes = _extract_votes(ctx, "55_298")

		# I Honestly didn't count this. This is just to make sure we notice if parsing changes
		self.assertEqual(3732, len(votes))
		self.assertEqual(133, len([v for v in votes if v.motion_id == "55_298_1"]))
		self.assertEqual(134, len([v for v in votes if v.motion_id == "55_298_2"]))
		self.assertEqual(132, len([v for v in votes if v.motion_id == "55_298_3"]))

		expected_vote = Vote(politicians[7124], motion_id="55_298_1", vote_type="YES")
		self.assertEqual(expected_vote, votes[0])


class PlenaryExtractionTest(unittest.TestCase):

	@classmethod
	def setUpClass(cls):
		CONFIG.data_dir = os.path.join(ROOT_FOLDER, "testdata")

	@unittest.skipIf(os.environ.get("SKIP_SLOW", None) is not None, "skipping slow tests")
	def test_extract_from_all_plenary_reports_does_not_throw(self):
		CONFIG.data_dir = os.path.join(ROOT_FOLDER, "data")
		plenaries, all_votes, problems = extract_from_html_plenary_reports(CONFIG.plenary_html_input_path("*.html"))

		self.assertEqual(len(plenaries), 300)

		all_motions = [motion for plenary in plenaries for motion in plenary.motions]
		self.assertEqual(len(all_motions), 2842)

		motions_with_problems = list(filter(lambda m: len(m.parse_problems) > 0, all_motions))

		# TODO: Improve how we handle parsing problems
		self.assertEqual(len(motions_with_problems), 17)

	def test_extract_from_html_plenary_report__ip298x_html__go_to_example_report(self):
		# Plenary report 298 has long been our first go-to example plenary report to test our extraction against.
		# Arrange
		report_file_name = CONFIG.plenary_html_input_path("ip298x.html")

		# Act
		plenary, votes, problems = extract_from_html_plenary_report(report_file_name)

		# Assert
		# The plenary info is extracted correctly:
		self.assertEqual(plenary.id, "55_298")
		self.assertEqual(plenary.number, 298)
		self.assertEqual(plenary.date, date(2024, 4, 4))
		self.assertEqual(plenary.legislature, 55)
		self.assertEqual(plenary.pdf_report_url, "https://www.dekamer.be/doc/PCRI/pdf/55/ip298.pdf")
		self.assertEqual(plenary.html_report_url, "https://www.dekamer.be/doc/PCRI/html/55/ip298x.html")

		# The proposals are extracted correctly:
		self.assertEqual(6, len(plenary.proposal_discussions))
		self.assertEqual("55_298_d01", plenary.proposal_discussions[0].id)
		self.assertEqual(plenary.proposal_discussions[0].plenary_id, "55_298")
		self.assertEqual(plenary.proposal_discussions[0].plenary_agenda_item_number, 1)

		self.assertStartsWith("Wij vatten de bespreking van de artikelen aan.",
							  plenary.proposal_discussions[0].description_nl)
		self.assertTrue(plenary.proposal_discussions[0].description_nl.endswith(
			"De bespreking van de artikelen is gesloten. De stemming over het geheel zal later plaatsvinden."))

		self.assertStartsWith(
			"Nous passons à la discussion des articles.", plenary.proposal_discussions[0].description_fr)
		self.assertTrue(plenary.proposal_discussions[0].description_fr.endswith(
			"La discussion des articles est close. Le vote sur l'ensemble aura lieu ultérieurement."))

		self.assertEqual(
			"Wetsontwerp houdende optimalisatie van de werking van het Centraal Orgaan voor de Inbeslagneming en de Verbeurdverklaring en het Overlegorgaan voor de coördinatie van de invordering van niet-fiscale schulden in strafzaken en houdende wijziging van de Wapenwet",
			plenary.proposal_discussions[0].proposals[0].title_nl)
		self.assertEqual(
			"Projet de loi optimisant le fonctionnement de l'Organe central pour la Saisie et la Confiscation et de l'Organe de concertation pour la coordination du recouvrement des créances non fiscales en matière pénale et modifiant la loi sur les armes",
			plenary.proposal_discussions[0].proposals[0].title_fr)
		self.assertEqual(plenary.proposal_discussions[0].proposals[0].document_reference, "3849/1-4")

		# The motions are extracted correctly:
		self.assertEqual(28, len(plenary.motions))
		self.assertEqual(plenary.motions[0].id,
						 "55_298_m1")  # TODO modify id creation so it doesn't clash with proposals and sections
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

	def test_extract_from_html_plenary_report__ip285x_html(self):
		# This report has no proposal discussions.
		# Arrange
		report_file_name = CONFIG.plenary_html_input_path("ip285x.html")

		# Act
		plenary, votes, problems = extract_from_html_plenary_report(report_file_name)

		# Assert: Regardless of the different proposals section title, the proposal discussions are extracted correctly:
		self.assertEqual(0, len(plenary.proposal_discussions))

	def test_extract_from_html_plenary_report__ip281x_html(self):
		# This report has no proposal discussion section.
		# Arrange
		report_file_name = CONFIG.plenary_html_input_path("ip281x.html")

		# Act
		plenary, votes, problems = extract_from_html_plenary_report(report_file_name)

		# Assert: Regardless of the different proposals section title, the proposal discussions are extracted correctly:
		self.assertEqual(0, len(plenary.proposal_discussions))

	def test_extract_from_html_plenary_report__ip262x_html_motion_proposal_id(self):
		# Test case for motions
		# Arrange
		report_file_name = CONFIG.plenary_html_input_path("ip262x.html")

		# Act
		plenary, votes, problems = extract_from_html_plenary_report(report_file_name)

		# Assert: Regardless of the different proposals section title, the proposal discussions are extracted correctly:
		self.assertEqual(16, len(plenary.motions))
		self.assertEqual(plenary.motions[0].id, "55_262_m1")
		self.assertEqual(plenary.motions[0].proposal_id, "55_262_08")

	def test_extract_from_html_plenary_report__ip263x_html(self):
		# This report has no proposal discussion section.
		# Arrange
		report_file_name = CONFIG.plenary_html_input_path("ip263x.html")

		# Act
		plenary, votes, problems = extract_from_html_plenary_report(report_file_name)

		# Assert: Regardless of the different proposals section title, the proposal discussions are extracted correctly:
		self.assertEqual(0, len(plenary.proposal_discussions))

	def test_extract_from_html_plenary_report__ip261x_html__different_proposals_header(self):
		# This example proposal has "Projets de loi et propositions" as proposals header, rather than "Projets de loi".
		# Also, the proposal description header ("Bespreking van de artikelen") cannot be found in item [20], so we fall back to
		# taking the entire text after the proposal header in a best-effort as the description, both for Dutch and
		# French.
		# Arrange
		report_file_name = CONFIG.plenary_html_input_path("ip261x.html")

		# Act
		plenary, votes, problems = extract_from_html_plenary_report(report_file_name)

		# Assert
		# The plenary info is extracted correctly:
		self.assertEqual(plenary.id, "55_261")
		self.assertEqual(plenary.number, 261)
		self.assertEqual(plenary.date, date(2023, 10, 5))
		self.assertEqual(plenary.legislature, 55)
		self.assertEqual(plenary.pdf_report_url, "https://www.dekamer.be/doc/PCRI/pdf/55/ip261.pdf")
		self.assertEqual(plenary.html_report_url, "https://www.dekamer.be/doc/PCRI/html/55/ip261x.html")

		# The proposals are extracted correctly:
		self.assertEqual(len(plenary.proposal_discussions), 4)

		self.assertEqual(plenary.proposal_discussions[0].id, "55_261_d20")
		self.assertEqual(plenary.proposal_discussions[0].plenary_id, "55_261")
		self.assertEqual(plenary.proposal_discussions[0].plenary_agenda_item_number, 20)

		self.assertStartsWith("20.01 Peter De Roover (N-VA): Mevrouw de voorzitster,",
							  plenary.proposal_discussions[0].description_nl)
		self.assertTrue(plenary.proposal_discussions[0].description_nl.endswith(
			"Bijgevolg zal de voorzitster het advies van de Raad van State vragen met toepassing van artikel 98.3 van het Reglement."))

		self.assertStartsWith("20.01 Peter De Roover (N-VA): Mevrouw de voorzitster,",
							  plenary.proposal_discussions[0].description_fr)
		self.assertTrue(plenary.proposal_discussions[0].description_fr.endswith(
			"Bijgevolg zal de voorzitster het advies van de Raad van State vragen met toepassing van artikel 98.3 van het Reglement."))

		self.assertEqual(plenary.proposal_discussions[0].proposals[0].title_nl,
						 "Verzoek om advies van de Raad van State")
		self.assertEqual(plenary.proposal_discussions[0].proposals[0].title_fr, "Demande d'avis du Conseil d'État")
		self.assertEqual(plenary.proposal_discussions[0].proposals[0].document_reference, None)

	def test_extract_from_html_plenary_report__ip226x_html(self):
		# This report has no proposal discussion section.
		# Arrange
		report_file_name = CONFIG.plenary_html_input_path("ip226x.html")

		# Act
		plenary, votes, problems = extract_from_html_plenary_report(report_file_name)

		# Assert: Regardless of the different proposals section title, the proposal discussions are extracted correctly:
		self.assertEqual(0, len(plenary.proposal_discussions))

	def test_extract_from_html_plenary_report__ip224x_html__different_proposals_header(self):
		# This example plenary report has "Begrotingen" as proposals header, rather than "Projets de loi".
		# Arrange
		report_file_name = CONFIG.plenary_html_input_path("ip224x.html")

		# Act
		plenary, votes, problems = extract_from_html_plenary_report(report_file_name)

		# Assert
		# The plenary info is extracted correctly:
		self.assertEqual(plenary.id, "55_224")
		self.assertEqual(plenary.number, 224)
		self.assertEqual(plenary.date, date(2022, 12, 21))
		self.assertEqual(plenary.legislature, 55)
		self.assertEqual(plenary.pdf_report_url, "https://www.dekamer.be/doc/PCRI/pdf/55/ip224.pdf")
		self.assertEqual(plenary.html_report_url, "https://www.dekamer.be/doc/PCRI/html/55/ip224x.html")

		# Regardless of the different section title announcing them, the proposal discussions are found:
		self.assertEqual(len(plenary.proposal_discussions), 4)

		# -> First proposal discussion:
		self.assertEqual(plenary.proposal_discussions[0].id, "55_224_d01")
		self.assertEqual(plenary.proposal_discussions[0].plenary_id, "55_224")
		self.assertEqual(plenary.proposal_discussions[0].plenary_agenda_item_number, 1)

		self.assertStartsWith(
			"Wij vatten de bespreking van de artikelen aan van het wetsontwerp houdende de Middelenbegroting voor het begrotingsjaar 2023.",
			plenary.proposal_discussions[0].description_nl)
		self.assertTrue(plenary.proposal_discussions[0].description_nl.endswith(
			"en over het geheel van het wetsontwerp houdende de Algemene uitgavenbegroting voor het begrotingsjaar 2023 zal later plaatsvinden."))

		self.assertStartsWith(
			"Nous passons à la discussion des articles du projet de loi contenant le budget des Voies et Moyens pour l'année budgétaire 2023.",
			plenary.proposal_discussions[0].description_fr)
		self.assertTrue(plenary.proposal_discussions[0].description_fr.endswith(
			"l'ensemble du projet de loi contenant le Budget général des dépenses pour l'année budgétaire 2023 aura lieu ultérieurement."))

		# ---> First proposal linked to the first proposal discussion:
		self.assertEqual(plenary.proposal_discussions[0].proposals[0].title_nl,
						 "Wetsontwerp houdende de Middelenbegroting voor het begrotingsjaar 2023")
		self.assertEqual(plenary.proposal_discussions[0].proposals[0].title_fr,
						 "Projet de loi contenant le budget des Voies et Moyens pour l'année budgétaire 2023")
		self.assertEqual("2931/1-6", plenary.proposal_discussions[0].proposals[0].document_reference)

		# ---> Last proposal linked to the first proposal discussion:
		self.assertEqual(plenary.proposal_discussions[0].proposals[4].title_nl,
						 "- Lijst van Beleidsnota's")
		self.assertEqual(plenary.proposal_discussions[0].proposals[4].title_fr,
						 "- Liste des notes de politique générale")
		self.assertEqual("2934/1-30", plenary.proposal_discussions[0].proposals[4].document_reference)

		# -> Last proposal discussion (no proposal discussion header, so description = all text below the proposal title):
		self.assertEqual(plenary.proposal_discussions[3].id, "55_224_d04")
		self.assertEqual(plenary.proposal_discussions[3].plenary_id, "55_224")
		self.assertEqual(plenary.proposal_discussions[3].plenary_agenda_item_number, 4)

		self.assertStartsWith("Discussion", plenary.proposal_discussions[3].description_nl)
		self.assertTrue(plenary.proposal_discussions[3].description_nl.endswith(
			"CRIV 55 PLEN 224 bijlage."))

		self.assertStartsWith("Discussion", plenary.proposal_discussions[3].description_fr)
		self.assertTrue(plenary.proposal_discussions[3].description_fr.endswith(
			"CRIV 55 PLEN 224 bijlage."))

		# ---> First and only proposal linked to the last proposal discussion:
		self.assertEqual(plenary.proposal_discussions[3].proposals[0].title_nl,
						 "Begroting en beleidsnota van de Commissie voor de Regulering van de elektriciteit en het gas (CREG) voor het begrotingsjaar 2023")
		self.assertEqual(plenary.proposal_discussions[3].proposals[0].title_fr,
						 "Budget et note de politique générale de la Commission de Régulation de l'Électricité et du Gaz (CREG) pour l'année 2023")
		self.assertEqual("1678/1-3", plenary.proposal_discussions[3].proposals[0].document_reference)

	def test_extract_from_html_plenary_report__ip245x_html(self):
		# This report has a different proposals section title: "Wetsontwerpen en voorstel".
		# Arrange
		report_file_name = CONFIG.plenary_html_input_path("ip245x.html")

		# Act
		plenary, votes, problems = extract_from_html_plenary_report(report_file_name)

		# Assert: Regardless of the different proposals section title, the proposal discussions are extracted correctly:
		self.assertEqual(5, len(plenary.proposal_discussions))
		self.assertEqual(15, plenary.proposal_discussions[0].plenary_agenda_item_number)
		self.assertEqual(19, plenary.proposal_discussions[-1].plenary_agenda_item_number)

	def test_extract_from_html_plenary_report__ip219x_html(self):
		# This report has a different proposals section title: "Wetsontwerpen en -voorstellen".
		# Arrange
		report_file_name = CONFIG.plenary_html_input_path("ip219x.html")

		# Act
		plenary, votes, problems = extract_from_html_plenary_report(report_file_name)

		# Assert: Regardless of the different proposals section title, the proposal discussions are extracted correctly:
		self.assertEqual(6, len(plenary.proposal_discussions))
		self.assertEqual(11, plenary.proposal_discussions[0].plenary_agenda_item_number)
		self.assertEqual(16, plenary.proposal_discussions[5].plenary_agenda_item_number)

	def test_extract_from_html_plenary_report__ip206x_html(self):
		# This report has no proposal discussion section.
		# Also no level 1 headers. It should not fail.
		# Arrange
		report_file_name = CONFIG.plenary_html_input_path("ip206x.html")

		# Act
		plenary, votes, problems = extract_from_html_plenary_report(report_file_name)

		# Assert: Regardless of the different proposals section title, the proposal discussions are extracted correctly:
		self.assertEqual(0, len(plenary.proposal_discussions))

	def test_extract_from_html_plenary_report__ip200x_html(self):
		report_file_name = CONFIG.plenary_html_input_path("ip200x.html")

		# Act
		plenary, votes, problems = extract_from_html_plenary_report(report_file_name)

		# Assert
		# The plenary info is extracted correctly:
		self.assertEqual(plenary.id, "55_200")
		self.assertEqual(plenary.number, 200)
		self.assertEqual(plenary.date, date(2022, 7, 20))
		self.assertEqual(plenary.legislature, 55)
		self.assertEqual(plenary.pdf_report_url, "https://www.dekamer.be/doc/PCRI/pdf/55/ip200.pdf")
		self.assertEqual(plenary.html_report_url, "https://www.dekamer.be/doc/PCRI/html/55/ip200x.html")

		# The proposals are extracted correctly:
		self.assertEqual(2, len(plenary.proposal_discussions))
		self.assertStartsWith("Projet de loi portant assentiment aux actes internationaux suivants",
							  plenary.proposal_discussions[0].proposals[0].title_fr)
		self.assertStartsWith("Wetsontwerp houdende instemming met volgende internationale akten",
							  plenary.proposal_discussions[0].proposals[0].title_nl)
		self.assertStartsWith("Projet de loi portant assentiment aux actes internationaux suivants",
							  plenary.proposal_discussions[0].proposals[0].title_fr)
		self.assertStartsWith("Wetsontwerp houdende instemming met volgende internationale akten",
							  plenary.proposal_discussions[0].proposals[0].title_nl)

		# The motions are extracted correctly:
		self.assertEqual(0, len(plenary.motions))

	def test_extract_from_html_plenary_report__ip184x_html(self):
		# This report has a different proposals section title: "Voorstellen".
		# Arrange
		report_file_name = CONFIG.plenary_html_input_path("ip184x.html")

		# Act
		plenary, votes, problems = extract_from_html_plenary_report(report_file_name)

		# Assert: Regardless of the different proposals section title, the proposal discussions are extracted correctly:
		self.assertEqual(4, len(plenary.proposal_discussions))
		self.assertEqual(1, plenary.proposal_discussions[0].plenary_agenda_item_number)
		self.assertEqual(4, plenary.proposal_discussions[-1].plenary_agenda_item_number)

	@unittest.skip(
		"Exotic case of 2 proposal discussion sections in one plenary report. Not fixing this for now."
	)
	def test_extract_from_html_plenary_report__ip162x_html(self):
		# 2 proposal discussion sections in one plenary report.
		# Arrange
		report_file_name = CONFIG.plenary_html_input_path("ip162x.html")

		# Act
		plenary, votes, problems = extract_from_html_plenary_report(report_file_name)

		# Assert: Regardless of the different proposals section title, the proposal discussions are extracted correctly:
		self.assertEqual(4, len(plenary.proposal_discussions))
		self.assertEqual(1, plenary.proposal_discussions[0].plenary_agenda_item_number)
		self.assertEqual(4, plenary.proposal_discussions[-1].plenary_agenda_item_number)

	def test_extract_from_html_plenary_report__ip160x_html(self):
		# This report has a different proposals section title: "Wetsontwerp en -voorstellen".
		# Arrange
		report_file_name = CONFIG.plenary_html_input_path("ip160x.html")

		# Act
		plenary, votes, problems = extract_from_html_plenary_report(report_file_name)

		# Assert: Regardless of the different proposals section title, the proposal discussions are extracted correctly:
		self.assertEqual(3, len(plenary.proposal_discussions))
		self.assertEqual(2, len(plenary.proposal_discussions[0].proposals))
		self.assertEqual(1, len(plenary.proposal_discussions[1].proposals))
		self.assertEqual(1, len(plenary.proposal_discussions[2].proposals))

	def test_extract_from_html_plenary_report__ip144x_html(self):
		# This report has a different proposals section title: "Voorstellen en wetsontwerp".
		# Arrange
		report_file_name = CONFIG.plenary_html_input_path("ip144x.html")

		# Act
		plenary, votes, problems = extract_from_html_plenary_report(report_file_name)

		# Assert: Regardless of the different proposals section title, the proposal discussions are extracted correctly:
		self.assertEqual(12, len(plenary.proposal_discussions))
		self.assertEqual(14, plenary.proposal_discussions[0].plenary_agenda_item_number)
		self.assertEqual(25, plenary.proposal_discussions[-1].plenary_agenda_item_number)

	def test_extract_from_html_plenary_report__ip125x_html(self):
		# This report has a different proposals section title: "Voorstellen en wetsontwerp".
		# Arrange
		report_file_name = CONFIG.plenary_html_input_path("ip125x.html")

		# Act
		plenary, votes, problems = extract_from_html_plenary_report(report_file_name)

		# Assert: Regardless of the different proposals section title, the proposal discussions are extracted correctly:
		self.assertEqual(2, len(plenary.proposal_discussions))
		self.assertEqual(3, plenary.proposal_discussions[0].plenary_agenda_item_number)
		self.assertEqual(4, plenary.proposal_discussions[-1].plenary_agenda_item_number)

	def test_extract_from_html_plenary_report__ip099x_html(self):
		# This report has a different proposals section title: "Wetsontwerp en voorstellen".
		# Arrange
		report_file_name = CONFIG.plenary_html_input_path("ip099x.html")

		# Act
		plenary, votes, problems = extract_from_html_plenary_report(report_file_name)

		# Assert: Regardless of the different proposals section title, the proposal discussions are extracted correctly:
		self.assertEqual(14, len(plenary.proposal_discussions))
		self.assertEqual(13, plenary.proposal_discussions[0].plenary_agenda_item_number)
		self.assertEqual(26, plenary.proposal_discussions[-1].plenary_agenda_item_number)

	def test_extract_from_html_plenary_report__ip059x_html(self):
		# This report has no proposal discussions.
		# Also no level 1 headers. It should not fail.
		# Arrange
		report_file_name = CONFIG.plenary_html_input_path("ip059x.html")

		# Act
		plenary, votes, problems = extract_from_html_plenary_report(report_file_name)

		# Assert: Regardless of the different proposals section title, the proposal discussions are extracted correctly:
		self.assertEqual(0, len(plenary.proposal_discussions))

	def test_extract_from_html_plenary_report__ip038x_html(self):
		# This report has a different proposals section title: "Wetsvoorstellen".
		# Arrange
		report_file_name = CONFIG.plenary_html_input_path("ip038x.html")

		# Act
		plenary, votes, problems = extract_from_html_plenary_report(report_file_name)

		# Assert: Regardless of the different proposals section title, the proposal discussions are extracted correctly:
		self.assertEqual(9, len(plenary.proposal_discussions))
		self.assertEqual(10, plenary.proposal_discussions[0].plenary_agenda_item_number)
		self.assertEqual(18, plenary.proposal_discussions[-1].plenary_agenda_item_number)

	def test_extract_from_html_plenary_report__ip021x_html(self):
		# This report has a different proposals section title: "Wetsvoorstel".
		# Arrange
		report_file_name = CONFIG.plenary_html_input_path("ip021x.html")

		# Act
		plenary, votes, problems = extract_from_html_plenary_report(report_file_name)

		# Assert: Regardless of the different proposals section title, the proposal discussions are extracted correctly:
		self.assertEqual(6, len(plenary.proposal_discussions))
		self.assertEqual(11, plenary.proposal_discussions[0].plenary_agenda_item_number)
		self.assertEqual(16, plenary.proposal_discussions[-1].plenary_agenda_item_number)

	def test_extract_from_html_plenary_report__ip007x_html(self):
		# This report has no proposal discussions section.
		# Arrange
		report_file_name = CONFIG.plenary_html_input_path("ip007x.html")

		# Act
		plenary, votes, problems = extract_from_html_plenary_report(report_file_name)

		# Assert: Regardless of the different proposals section title, the proposal discussions are extracted correctly:
		self.assertEqual(0, len(plenary.proposal_discussions))

	def test_extract_from_html_plenary_report__ip005x_html(self):
		# This report has a different proposals section title: "Voorstel van resolutie".
		# Arrange
		report_file_name = CONFIG.plenary_html_input_path("ip005x.html")

		# Act
		plenary, votes, problems = extract_from_html_plenary_report(report_file_name)

		# Assert: Regardless of the different proposals section title, the proposal discussions are extracted correctly:
		self.assertEqual(4, len(plenary.proposal_discussions))
		self.assertEqual(23, plenary.proposal_discussions[0].plenary_agenda_item_number)
		self.assertEqual(26, plenary.proposal_discussions[-1].plenary_agenda_item_number)

	@unittest.skip(
		"suppressed for now - we can't make the distinction between 'does not match voters' problem and actually having 0 votes right now")
	def test_extract_ip67(self):
		actual, votes, problems = extract_from_html_plenary_report(CONFIG.plenary_html_input_path('ip067x.html'))

		vote_types_motion_1 = set([v.vote_type for v in votes if v.motion_id == "55_067_1"])
		self.assertTrue("NO" in vote_types_motion_1)

	@unittest.skip(
		"todo - broke since the refactoring of proposal description extraction"
	)
	def test_extract_ip72(self):
		"""vote 2 has an extra '(' in the vote result indicator"""
		actual, votes, problems = extract_from_html_plenary_report(CONFIG.plenary_html_input_path('ip072x.html'))

		self.assertEqual(len(actual.motions), 5)

	def test_voter_dots_are_removed_from_voter_names(self):
		actual, votes, problems = extract_from_html_plenary_report(CONFIG.plenary_html_input_path('ip182x.html'))

		names = [v.politician.full_name for v in votes]

		names_with_dots = [name for name in names if "." in name]
		self.assertEqual([], names_with_dots)

	@unittest.skipIf(os.environ.get("SKIP_SLOW", None) is not None, "skipping slow tests")
	def test_votes_must_have_politician(self):
		CONFIG.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
		actual, votes, problems = extract_from_html_plenary_reports()

		for vote in votes:
			self.assertIsNotNone(vote.politician)

	def test_plenary_date1(self):
		plenary_date = self.get_plenary_date("ip123x.html")

		self.assertEqual(plenary_date, date.fromisoformat("2021-07-19"))

	def test_plenary_date2(self):
		plenary_date = self.get_plenary_date("ip007x.html")

		self.assertEqual(plenary_date, date.fromisoformat("2019-10-03"))

	def get_plenary_date(self, filename):
		path = CONFIG.plenary_html_input_path(filename)
		ctx = create_plenary_extraction_context(path, None)  # Politicians not needed for this test
		return _get_plenary_date(ctx)

	def assertStartsWith(self, expected, actual):
		self.assertEqual(expected, actual[:len(expected)])
