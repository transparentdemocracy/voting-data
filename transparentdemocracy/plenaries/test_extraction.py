import logging
import os
import unittest
from datetime import date

import transparentdemocracy
from transparentdemocracy.config import CONFIG
from transparentdemocracy.model import Motion, Vote, VoteType
from transparentdemocracy.plenaries.extraction import extract_from_html_plenary_reports, \
	extract_from_html_plenary_report, _get_plenary_date, _extract_motion_report_items, \
	_extract_motion_groups, _extract_votes, create_plenary_extraction_context, ReportItem
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

		self.assertEqual(15, len(report_items))

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

		self.assertEqual(0, len(report_items))

	def test_extract_ip271(self):
		report_items = self.extract_motion_report_items('ip271x.html')

		self.assertEqual(15, len(report_items))  # todo: check manually

		self.assert_report_item(report_items[0],
								'14',
								'14 Moties ingediend tot besluit van de\ninterpellatie van mevrouw Barbara Pas',
								'14 Motions déposées en conclusion de l\'interpellation de Mme Barbara\nPas')

		# NOTE: nl/fr title parsing is still off
		self.assert_report_item(report_items[-1],
								'28',
								'',
								'28 Adoption de l’ordre du jour\n28 Goedkeuring van de agenda')

	def test_extract_ip290_has_no_naamstemmingen(self):
		report_items = self.extract_motion_report_items('ip290x.html')

		self.assertEqual([], report_items)

	def assert_report_item(self, report_item: ReportItem,
						   expected_label: str, expected_nl_title_prefix: str, expected_fr_title_prefix: str):
		self.assertEqual(expected_label, report_item.label)
		self.assertEqual(expected_nl_title_prefix, report_item.nl_title[:len(expected_nl_title_prefix)])
		self.assertEqual(expected_fr_title_prefix, report_item.fr_title[:len(expected_fr_title_prefix)])

	def extract_motion_report_items(self, report_path):
		path = CONFIG.plenary_html_input_path(report_path)
		ctx = create_plenary_extraction_context(path, load_politicians())
		return _extract_motion_report_items(ctx)


class MotionExtractionTest(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		CONFIG.data_dir = os.path.join(ROOT_FOLDER, "testdata")

	def test_extract_motions__ip298x_html__go_to_example_report(self):
		# The example report we used for implementing extraction of other sub-objects of a plenary object.
		# Arrange
		report_path = CONFIG.plenary_html_input_path("ip298x.html")
		ctx = create_plenary_extraction_context(report_path, load_politicians())

		# Act
		report_items, motion_groups = _extract_motion_groups("55_298", ctx)

		# Assert
		motions = [m for mg in motion_groups for m in mg.motions]
		self.assertEqual(39, len(motions))

		motion_group10 = motion_groups[0]
		self.assertEqual("55_298_mg_10", motion_group10.id)
		self.assertEqual(10, motion_group10.plenary_agenda_item_number)
		self.assertTrue(motion_group10.title_nl.startswith("Moties ingediend tot besluit van de interpellaties van - Koen Metsu over "))
		self.assertTrue(motion_group10.title_nl.endswith('Comité P over de aanslag van 16 oktober 2023" (nr. 486)'))
		self.assertTrue(motion_group10.title_fr.startswith("Motions déposées en conclusion des interpellations de - Koen Metsu sur"))
		self.assertTrue(motion_group10.title_fr.endswith(' sur l\'attentat du 16 octobre 2023" (n° 486)'))
		self.assertEqual(None, motion_group10.documents_reference)
		self.assertEqual(1, len(motion_group10.motions))

		self.assertEqual("55_298_mg_10_m0", motion_group10.motions[0].id)
		self.assertEqual("0", motion_group10.motions[0].sequence_number)
		self.assertTrue(motion_group10.motions[0].title_nl.startswith(
			"Moties ingediend tot besluit van de interpellaties van - Koen Metsu over "))
		self.assertTrue(motion_group10.motions[0].title_nl.endswith('Comité P over de aanslag van 16 oktober 2023" (nr. 486)'))
		self.assertTrue(motion_group10.motions[0].title_fr.startswith(
			"Motions déposées en conclusion des interpellations de - Koen Metsu sur"))
		self.assertTrue(motion_group10.motions[0].title_fr.endswith(' sur l\'attentat du 16 octobre 2023" (n° 486)'))
		self.assertEqual(None, motion_group10.motions[0].documents_reference)
		self.assertEqual("55_298_v1", motion_group10.motions[0].voting_id)
		self.assertEqual(False, motion_group10.motions[0].cancelled)
		# self.assertTrue(motion_group10.motions[0].description.startswith("Ces interpellations ont été développées en séance plénière de ce jour."))
		self.assertTrue(motion_group10.motions[0].description.endswith("De eenvoudige motie is aangenomen. Bijgevolg vervallen de moties van aanbeveling."))

		motion_group14 = motion_groups[4]
		self.assertEqual("55_298_mg_14", motion_group14.id)
		self.assertEqual(14, motion_group14.plenary_agenda_item_number)
		self.assertTrue("Aangehouden amendementen en artikelen van het wetsontwerp houdende de hervorming van de pensioenen",
						motion_group10.title_nl)
		self.assertTrue("Amendements et articles réservés du projet de loi portant la réforme des pensions",
						motion_group10.title_fr)
		self.assertEqual("3808/1-10", motion_group14.documents_reference)
		self.assertEqual("Aangehouden amendementen en artikelen van het wetsontwerp houdende de hervorming van de pensioenen",
						 motion_group14.title_nl)
		self.assertEqual("Amendements et articles réservés du projet de loi portant la réforme des pensions",
						 motion_group14.title_fr)
		self.assertEqual("3808/1-10", motion_group14.documents_reference)
		self.assertEqual(22, len(motion_group14.motions))

		self.assertEqual("55_298_mg_14_m0", motion_group14.motions[0].id)
		self.assertTrue("0", motion_group14.motions[0].sequence_number)
		self.assertEqual("Stemming over amendement nr. 35 van Ellen Samyn op artikel 2.",
						 motion_group14.motions[0].title_nl)
		self.assertEqual("Vote sur l'amendement n° 35 de Ellen Samyn à l'article 2.",
						 motion_group14.motions[0].title_fr)
		self.assertEqual("3808/10", motion_group14.motions[0].documents_reference)
		self.assertEqual("55_298_v5", motion_group14.motions[0].voting_id)
		self.assertEqual(False, motion_group14.motions[0].cancelled)
		# self.assertEqual("", motion_group14.motions[0].description)

		# Also interesting to test: motion group 22 and 24.

	def test_extract_motions__ip262x_html__go_to_example_report(self):
		# The example report we used for agreeing on how to implement extraction of motions.
		# Arrange
		report_path = CONFIG.plenary_html_input_path("ip262x.html")

		# Act
		plenary, votes, problems = extract_from_html_plenary_report(report_path, load_politicians())
		motion_groups = plenary.motion_groups

		# Assert
		self.assertEqual(15, len(motion_groups))
		self.assertEqual(8, motion_groups[0].plenary_agenda_item_number)
		self.assertEqual(22, motion_groups[-1].plenary_agenda_item_number)

		motion_group12 = motion_groups[4]
		self.assertEqual("55_262_mg_12", motion_group12.id)
		self.assertEqual(12, motion_group12.plenary_agenda_item_number)
		self.assertEqual("Aangehouden amendementen op het wetsontwerp houdende diverse bepalingen inzake sociale zaken",
						 motion_group12.title_nl)
		self.assertEqual("Amendements réservés au projet de loi portant des dispositions diverses en matière sociale",
						 motion_group12.title_fr)
		self.assertEqual("3495/1-5", motion_group12.documents_reference)

		self.assertEqual(3, len(motion_group12.motions))

		self.assertEqual(Motion("55_262_mg_12_m0", "0",
								"Stemming over amendement nr. 4 van Catherine Fonck tot invoeging van een artikel 2/1(n).",
								"Vote sur l'amendement n° 4 de Catherine Fonck tendant à insérer un article 2/1(n).",
								"3495/5",
								"55_262_v5",
								False,
								# TODO: formatting is completely lost, should be fixed somehow
								# actually preserving the original html might not be the worst idea
								"Begin van de stemming / Début du vote. Heeft iedereen gestemd en zijn stem nagekeken? / Tout le monde a-t-il voté et vérifié son vote? Heeft iedereen gestemd en zijn stem nagekeken? / Tout le monde a-t-il voté et vérifié son vote? Einde van de stemming / Fin du vote. Einde van de stemming / Fin du vote. Uitslag van de stemming / Résultat du vote. Uitslag van de stemming / Résultat du vote. (Stemming/vote 5) Ja 6 Oui Nee 100 Non Onthoudingen 28 Abstentions Totaal 134 Total (Stemming/vote 5) Ja 6 Oui Nee 100 Non Onthoudingen 28 Abstentions Totaal 134 Total En conséquence, l'amendement est rejeté. Bijgevolg is het amendement verworpen.",
								# There is no separate proposal mentioned in plenary report 261 for subdocument 3495/5 only. But the proposal discussion has as first title line (and therefore as first proposal) the documents reference 3495/1-5, which _encompasses_ 3495/5 (subdocument 5 is in the range of subdocuments), therefore we can link to proposal 1 of 55_261_d22...
								),
						 motion_group12.motions[0])

		# Outcomes with current implementation:
		motions = plenary.motions
		self.assertEqual(19, len(motions))
		self.assertEqual("55_262_mg_8_m0", motions[0].id)

		self.assertEqual("55_262_mg_9_m0", motions[1].id)

		self.assertEqual("55_262_mg_10_m0", motions[2].id)

		self.assertEqual("55_262_mg_10_m1", motions[3].id)
		self.assertEqual("55_262_mg_11_m0", motions[4].id)

		self.assertEqual("55_262_mg_12_m0", motions[5].id)
		self.assertEqual("55_262_mg_12_m1", motions[6].id)
		self.assertEqual("55_262_mg_12_m2", motions[7].id)

		self.assertEqual("55_262_mg_13_m0", motions[8].id)

		self.assertEqual("55_262_mg_14_m0", motions[9].id)
		self.assertEqual("55_262_mg_14_m1", motions[10].id)

		self.assertEqual("55_262_mg_15_m0", motions[11].id)

		self.assertEqual("55_262_mg_16_m0", motions[12].id)

		self.assertEqual("55_262_mg_17_m0", motions[13].id)

		self.assertEqual("55_262_mg_18_m0", motions[14].id)

		self.assertEqual("55_262_mg_19_m0", motions[15].id)

		self.assertEqual("55_262_mg_20_m0", motions[16].id)

		self.assertEqual("55_262_mg_21_m0", motions[17].id)

		self.assertEqual("55_262_mg_22_m0", motions[18].id)


class VoteExtractionTest(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		CONFIG.data_dir = os.path.join(ROOT_FOLDER, "testdata")

	def test_extract_votes_ip298x__go_to_example_report(self):
		# Arrange
		report_path = CONFIG.plenary_html_input_path("ip298x.html")
		politicians = load_politicians()
		ctx = create_plenary_extraction_context(report_path, politicians)

		# Act
		votes = _extract_votes(ctx, "55_298")

		# Assert
		voting1_votes = [vote for vote in votes if vote.voting_id == "55_298_v1"]

		voting1_votes_yes = [vote for vote in voting1_votes if vote.vote_type is VoteType.YES]
		self.assertEqual(79, len(voting1_votes_yes))
		self.assertEqual("Aouasti Khalil", voting1_votes_yes[0].politician.full_name)
		self.assertEqual("Bacquelaine Daniel", voting1_votes_yes[1].politician.full_name)
		self.assertEqual("Wilmès Sophie", voting1_votes_yes[-2].politician.full_name)
		self.assertEqual("Zanchetta Laurence", voting1_votes_yes[-1].politician.full_name)

		voting1_votes_no = [vote for vote in voting1_votes if vote.vote_type is VoteType.NO]
		self.assertEqual(50, len(voting1_votes_no))
		self.assertEqual("Anseeuw Björn", voting1_votes_no[0].politician.full_name)
		self.assertEqual("Bruyère Robin", voting1_votes_no[1].politician.full_name)
		self.assertEqual("Verreyt Hans", voting1_votes_no[-2].politician.full_name)
		self.assertEqual("Wollants Bert", voting1_votes_no[-1].politician.full_name)

		voting1_votes_abstention = [vote for vote in voting1_votes if vote.vote_type is VoteType.ABSTENTION]
		self.assertEqual(4, len(voting1_votes_abstention))
		self.assertEqual("Arens Josy", voting1_votes_abstention[0].politician.full_name)
		self.assertEqual("Daems Greet", voting1_votes_abstention[1].politician.full_name)
		self.assertEqual("Rohonyi Sophie", voting1_votes_abstention[-2].politician.full_name)
		self.assertEqual("Vindevoghel Maria", voting1_votes_abstention[-1].politician.full_name)

		self.assertEqual(133, len(voting1_votes))

		self.assertEqual(134, len([v for v in votes if v.voting_id == "55_298_v2"]))

		self.assertEqual(132, len([v for v in votes if v.voting_id == "55_298_v3"]))


# More like integration tests, testing the outcome of the execution of all puzzle pieces tested separately above:
# (Maybe at some point I should extract unit tests for __extract_proposal_discussion() from the below tests.)
class PlenaryExtractionTest(unittest.TestCase):

	@classmethod
	def setUpClass(cls):
		CONFIG.data_dir = os.path.join(ROOT_FOLDER, "testdata")

	@unittest.skipIf(os.environ.get("SKIP_SLOW", None) is not None, "This test isn't really slow but requires data")
	def test_currently_failing(self):
		CONFIG.data_dir = os.path.join(ROOT_FOLDER, "data")
		plenary_nrs = "162,161,280,052,111,153,010".split(",")
		patterns = [CONFIG.plenary_html_input_path(f"ip{plenary_nr}x.html") for plenary_nr in plenary_nrs]

		plenaries, all_votes, problems = extract_from_html_plenary_reports(patterns)

		exceptions = [p for p in problems if p.problem_type == "EXCEPTION"]
		for p in exceptions:
			print("FIXME:", p.report_path)
		self.assertEqual(0, len(exceptions))

		self.assertEqual(len(plenary_nrs), len(plenaries))

	@unittest.skipIf(os.environ.get("SKIP_SLOW", None) is not None, "skipping slow tests")
	def test_extract_from_all_plenary_reports_does_not_throw(self):
		CONFIG.data_dir = os.path.join(ROOT_FOLDER, "data")
		plenaries, all_votes, problems = extract_from_html_plenary_reports(CONFIG.plenary_html_input_path("*.html"))

		exceptions = [p for p in problems if p.problem_type == "EXCEPTION"]
		self.assertGreaterEqual(0, len(exceptions))
		self.assertLessEqual(309, len(plenaries))

		all_motions = [motion for plenary in plenaries for motion in plenary.motions]
		self.assertLessEqual(3873, len(all_motions))

		self.assertGreaterEqual(266, len(problems))

	def test_extract_from_html_plenary_report__ip298x_html__go_to_example_report(self):
		# Plenary report 298 has long been our first go-to example plenary report to test our extraction against.
		# Arrange
		report_file_name = CONFIG.plenary_html_input_path("ip298x.html")

		# Act
		plenary, votes, problems = extract_from_html_plenary_report(report_file_name)

		# Assert
		# The plenary info is extracted correctly:
		self.assertEqual("55_298", plenary.id)
		self.assertEqual(298, plenary.number)
		self.assertEqual(date(2024, 4, 4), plenary.date)
		self.assertEqual(55, plenary.legislature)
		self.assertEqual("https://www.dekamer.be/doc/PCRI/pdf/55/ip298.pdf", plenary.pdf_report_url)
		self.assertEqual("https://www.dekamer.be/doc/PCRI/html/55/ip298x.html", plenary.html_report_url)

		# The proposals are extracted correctly:
		self.assertEqual(6, len(plenary.proposal_discussions))
		self.assertEqual("55_298_d01", plenary.proposal_discussions[0].id)
		self.assertEqual("55_298", plenary.proposal_discussions[0].plenary_id)
		self.assertEqual(1, plenary.proposal_discussions[0].plenary_agenda_item_number)

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
		self.assertEqual("3849/1-4", plenary.proposal_discussions[0].proposals[0].documents_reference)

		# The motions are extracted correctly:
		motions = plenary.motions
		self.assertEqual(39, len(motions))
		self.assertEqual("55_298_mg_10_m0", motions[0].id)
		self.assertEqual(False, motions[0].cancelled)

		#### TODO: interesting test case:
		### Vote sur l'amendement n° 44 de Gaby Colebunders tendant à insérer un article 76(n). (3808/10)
		### this is a motion that took a vote which was cancelled, immediately followed by another vote
		### This means that motion <-> name vote it not a 1-1 relationship

		motions = plenary.motions
		self.assertEqual("55_298_mg_14_m15", motions[19].id)
		self.assertEqual(True, motions[19].cancelled)

		# The votes are extracted correctly:
		yes_voters = [vote.politician.full_name for vote in votes if
					  vote.vote_type is VoteType.YES and vote.voting_id == "55_298_v1"]
		no_voters = [vote.politician.full_name for vote in votes if
					 vote.vote_type is VoteType.NO and vote.voting_id == "55_298_v1"]
		abstention_voters = [vote.politician.full_name for vote in votes if
							 vote.vote_type is VoteType.ABSTENTION and vote.voting_id == "55_298_v1"]

		count_yes = len(yes_voters)
		count_no = len(no_voters)
		count_abstention = len(abstention_voters)

		self.assertEqual(79, count_yes)
		self.assertEqual(['Aouasti Khalil', 'Bacquelaine Daniel'], yes_voters[:2])

		self.assertEqual(50, count_no)
		self.assertEqual(["Anseeuw Björn", "Bruyère Robin"], no_voters[:2])

		self.assertEqual(4, count_abstention)
		self.assertEqual(['Arens Josy', 'Daems Greet'], abstention_voters[:2])

	def test_extract_from_html_plenary_report__ip010x_html(self):
		report_path = CONFIG.plenary_html_input_path("ip010x.html")
		plenary, votes, problems = extract_from_html_plenary_report(report_path)

		self.assertIsNotNone(plenary)
		self.assertIsNotNone(votes)
		self.assertIsNotNone(problems)

		motion_groups = plenary.motion_groups
		self.assertEqual(9, len(motion_groups))

		motions = plenary.motions
		motion = next(m for m in motions if m.id == "55_010_mg_27_m0")
		self.assertTrue(motion.cancelled)

	def test_motion_title_language(self):
		report_path = CONFIG.plenary_html_input_path("ip160x.html")
		plenary, votes, problems = extract_from_html_plenary_report(report_path)

		motion = next(m for m in plenary.motions if m.id == "55_160_mg_20_m0")

		self.assertStartsWith("Moties ingediend tot besluit van de interpellatie van mevrouw Annick Ponthier",
							  motion.title_nl)

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

	def test_extract_from_html_plenary_report__ip263x_html(self):
		# This report has no proposal discussion section.
		# Arrange
		report_file_name = CONFIG.plenary_html_input_path("ip263x.html")

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
		motions = plenary.motions
		self.assertEqual(19, len(motions))
		self.assertEqual("55_262_mg_8_m0", motions[0].id)

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
		self.assertEqual("https://www.dekamer.be/doc/PCRI/pdf/55/ip261.pdf", plenary.pdf_report_url)
		self.assertEqual("https://www.dekamer.be/doc/PCRI/html/55/ip261x.html", plenary.html_report_url)

		# The proposals are extracted correctly:
		self.assertEqual(len(plenary.proposal_discussions), 4)

		self.assertEqual("55_261_d20", plenary.proposal_discussions[0].id)
		self.assertEqual("55_261", plenary.proposal_discussions[0].plenary_id)
		self.assertEqual(20, plenary.proposal_discussions[0].plenary_agenda_item_number)

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
		self.assertEqual("Demande d'avis du Conseil d'État", plenary.proposal_discussions[0].proposals[0].title_fr)
		self.assertIsNone(plenary.proposal_discussions[0].proposals[0].documents_reference)

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
		self.assertEqual("55_224", plenary.id)
		self.assertEqual(224, plenary.number)
		self.assertEqual(date(2022, 12, 21), plenary.date)
		self.assertEqual(55, plenary.legislature)
		self.assertEqual("https://www.dekamer.be/doc/PCRI/pdf/55/ip224.pdf", plenary.pdf_report_url)
		self.assertEqual(plenary.html_report_url, "https://www.dekamer.be/doc/PCRI/html/55/ip224x.html")

		# Regardless of the different section title announcing them, the proposal discussions are found:
		self.assertEqual(len(plenary.proposal_discussions), 4)

		# -> First proposal discussion:
		self.assertEqual("55_224_d01", plenary.proposal_discussions[0].id)
		self.assertEqual("55_224", plenary.proposal_discussions[0].plenary_id)
		self.assertEqual(1, plenary.proposal_discussions[0].plenary_agenda_item_number)

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
		self.assertEqual("2931/1-6", plenary.proposal_discussions[0].proposals[0].documents_reference)

		# ---> Last proposal linked to the first proposal discussion:
		self.assertEqual(plenary.proposal_discussions[0].proposals[4].title_nl,
						 "- Lijst van Beleidsnota's")
		self.assertEqual(plenary.proposal_discussions[0].proposals[4].title_fr,
						 "- Liste des notes de politique générale")
		self.assertEqual("2934/1-30", plenary.proposal_discussions[0].proposals[4].documents_reference)

		# -> Last proposal discussion (no proposal discussion header, so description = all text below the proposal title):
		self.assertEqual("55_224_d04", plenary.proposal_discussions[3].id)
		self.assertEqual("55_224", plenary.proposal_discussions[3].plenary_id)
		self.assertEqual(4, plenary.proposal_discussions[3].plenary_agenda_item_number)

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
		self.assertEqual("1678/1-3", plenary.proposal_discussions[3].proposals[0].documents_reference)

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
		self.assertEqual("55_200", plenary.id)
		self.assertEqual(200, plenary.number)
		self.assertEqual(date(2022, 7, 20), plenary.date)
		self.assertEqual(55, plenary.legislature)
		self.assertEqual("https://www.dekamer.be/doc/PCRI/pdf/55/ip200.pdf", plenary.pdf_report_url)
		self.assertEqual("https://www.dekamer.be/doc/PCRI/html/55/ip200x.html", plenary.html_report_url)

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
		self.assertTrue(VoteType.NO in vote_types_motion_1)

	@unittest.skip(
		"todo - broke since the refactoring of proposal description extraction"
	)
	def test_extract_ip72(self):
		"""vote 2 has an extra '(' in the vote result indicator"""
		actual, votes, problems = extract_from_html_plenary_report(CONFIG.plenary_html_input_path('ip072x.html'))

		self.assertEqual(5, len(actual.get_motions()))

	def test_voter_dots_are_removed_from_voter_names(self):
		actual, votes, problems = extract_from_html_plenary_report(CONFIG.plenary_html_input_path('ip182x.html'))

		names = [v.politician.full_name for v in votes]

		names_with_dots = [name for name in names if "." in name]
		self.assertEqual([], names_with_dots)

	@unittest.skipIf(os.environ.get("SKIP_SLOW", None) is not None, "skipping slow tests")
	def test_votes_must_have_politician(self):
		CONFIG.data_dir = os.path.join(ROOT_FOLDER, "data")
		actual, votes, problems = extract_from_html_plenary_reports()

		for vote in votes:
			self.assertIsNotNone(vote.politician)

	def test_plenary_date1(self):
		plenary_date = self.get_plenary_date("ip123x.html")

		self.assertEqual(date.fromisoformat("2021-07-19"), plenary_date)

	def test_plenary_date2(self):
		plenary_date = self.get_plenary_date("ip007x.html")

		self.assertEqual(date.fromisoformat("2019-10-03"), plenary_date)

	def get_plenary_date(self, filename):
		path = CONFIG.plenary_html_input_path(filename)
		ctx = create_plenary_extraction_context(path, None)  # Politicians not needed for this test
		return _get_plenary_date(ctx)

	def assertStartsWith(self, expected, actual):
		self.assertEqual(expected, actual[:len(expected)])
