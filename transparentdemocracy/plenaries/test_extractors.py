import logging
import os
import unittest

from transparentdemocracy import PLENARY_HTML_INPUT_PATH
from transparentdemocracy.model import MotionData
from transparentdemocracy.plenaries.extraction import extract_from_html_plenary_report

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logger.setLevel(logging.INFO)


class TestNewMotionDataExtraction(unittest.TestCase):

	def test_extract_ip298(self):
		plenary, votes = extract_from_html_plenary_report(os.path.join(PLENARY_HTML_INPUT_PATH, 'ip298x.html'))

		self.assertIsNotNone(plenary.motion_data, "motion data")
		self.assertEqual(len(plenary.motion_data), 15)  # motions 10 - 24

		self.assert_motion_data(plenary.motion_data[0],
								"10",
								"10 Moties ingediend",
								"10 Motions déposées en conclusion des interpellations de")

		self.assert_motion_data(plenary.motion_data[1],
								"11",
								"11 Wetsontwerp\nhoudende diverse wijzigingen van het Wetboek van strafvordering II, zoals\ngeamendeerd tijdens de plenaire vergadering van 28 maart 2024 (3515/10)",
								"11 Projet de loi portant diverses modifications du Code d'instruction\ncriminelle II, tel qu'amendé lors de la séance plénière du 28 mars 2024\n(3515/10)")

	def test_extract_ip298(self):
		plenary, votes = extract_from_html_plenary_report(os.path.join(PLENARY_HTML_INPUT_PATH, 'ip298x.html'))

		self.assertIsNotNone(plenary.motion_data, "motion data")
		self.assertEqual(len(plenary.motion_data), 15)  # motions 10 - 24

		self.assert_motion_data(plenary.motion_data[0],
								"10",
								"10 Moties ingediend",
								"10 Motions déposées en conclusion des interpellations de")

		self.assert_motion_data(plenary.motion_data[1],
								"11",
								"11 Wetsontwerp\nhoudende diverse wijzigingen van het Wetboek van strafvordering II, zoals\ngeamendeerd tijdens de plenaire vergadering van 28 maart 2024 (3515/10)",
								"11 Projet de loi portant diverses modifications du Code d'instruction\ncriminelle II, tel qu'amendé lors de la séance plénière du 28 mars 2024\n(3515/10)")

	def test_extract_ip290(self):
		plenary, votes = extract_from_html_plenary_report(os.path.join(PLENARY_HTML_INPUT_PATH, 'ip290x.html'))

		self.assertIsNotNone(plenary.motion_data, "motion data")
		self.assertEqual(len(plenary.motion_data), 0)  # motions 10 - 24

	def assert_motion_data(self, motion_data: MotionData, label: str, nl_title_prefix: str, fr_title_prefix: str):
		self.assertEqual(motion_data.label, label)
		self.assertEqual(motion_data.nl_title[:len(nl_title_prefix)], nl_title_prefix)
		self.assertEqual(motion_data.fr_title[:len(fr_title_prefix)], fr_title_prefix)
