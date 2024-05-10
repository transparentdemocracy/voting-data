import logging
import os
import unittest

import transparentdemocracy
from transparentdemocracy.config import CONFIG
from transparentdemocracy.model import ReportItem
from transparentdemocracy.plenaries.extraction import _read_plenary_html, _extract_motion_report_items

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logger.setLevel(logging.INFO)


class TestNewReportItemExtraction(unittest.TestCase):

	@classmethod
	def setUpClass(cls):
		CONFIG.data_dir = os.path.join(os.path.dirname(transparentdemocracy.__file__), "..", "testdata")

	def test_extract_ip298_happy_case(self):
		report_items = self.extract_motion_report_items('ip298x.html')

		self.assertEqual(len(report_items), 14)  # motions 10 - 23 (?)

		self.assert_report_item(report_items[0],
								"TODO - label",
								"10 Moties ingediend",
								"10 Motions déposées en conclusion des interpellations de")

		self.assert_report_item(report_items[1],
								"TODO - label",
								"11 Wetsontwerp\nhoudende diverse wijzigingen van het Wetboek van strafvordering II, zoals\ngeamendeerd tijdens de plenaire vergadering van 28 maart 2024 (3515/10)",
								"11 Projet de loi portant diverses modifications du Code d'instruction\ncriminelle II, tel qu'amendé lors de la séance plénière du 28 mars 2024\n(3515/10)")

	def test_extract_ip280_has_1_naamstemming_but_no_identifiable_motion_title(self):
		report_items = self.extract_motion_report_items('ip280x.html')

		self.assertEqual(len(report_items), 0)

	def test_extract_ip271(self):
		report_items = self.extract_motion_report_items('ip271x.html')

		self.assertEqual(len(report_items), 14)  # todo: check manually

		self.assert_report_item(report_items[0],
								'TODO - label',
								'14 Moties ingediend tot besluit van de\ninterpellatie van mevrouw Barbara Pas',
								'14 Motions déposées en conclusion de l\'interpellation de Mme Barbara\nPas')

		# FIXME: Do we count 'Goedkeuring van de agenda' as a motion?
		# If we link the motions with their votes we could exclude motions without votes
		self.assert_report_item(report_items[-1],
								'TODO - label',
								'27 Wetsontwerp tot\nwijziging',
								'27 Projet de loi visant à modi')

	def test_extract_ip290_has_no_naamstemmingen(self):
		report_items = self.extract_motion_report_items('ip290x.html')

		self.assertEqual(report_items, [])

	def assert_report_item(self, report_item: ReportItem, label: str, nl_title_prefix: str, fr_title_prefix: str):
		self.assertEqual(report_item.label, label)
		self.assertEqual(nl_title_prefix, report_item.nl_title[:len(nl_title_prefix)])
		self.assertEqual(fr_title_prefix, report_item.fr_title[:len(fr_title_prefix)])

	def extract_motion_report_items(self, report_path):
		path = CONFIG.plenary_html_input_path(report_path)
		return _extract_motion_report_items(path, _read_plenary_html(path))
