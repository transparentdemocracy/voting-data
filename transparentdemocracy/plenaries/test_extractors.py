import logging
import unittest

from transparentdemocracy.config import CONFIG
from transparentdemocracy.model import MotionData
from transparentdemocracy.plenaries.extraction import _extract_motiondata, _read_plenary_html

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logger.setLevel(logging.INFO)


class TestNewMotionDataExtraction(unittest.TestCase):

	def test_extract_ip298_happy_case(self):
		motion_data = self.extract_motiondata('ip298x.html')

		self.assertIsNotNone(motion_data, "motion data")
		self.assertEqual(len(motion_data), 15)  # motions 10 - 24

		self.assert_motion_data(motion_data[0],
								"10",
								"10 Moties ingediend",
								"10 Motions déposées en conclusion des interpellations de")

		self.assert_motion_data(motion_data[1],
								"11",
								"11 Wetsontwerp\nhoudende diverse wijzigingen van het Wetboek van strafvordering II, zoals\ngeamendeerd tijdens de plenaire vergadering van 28 maart 2024 (3515/10)",
								"11 Projet de loi portant diverses modifications du Code d'instruction\ncriminelle II, tel qu'amendé lors de la séance plénière du 28 mars 2024\n(3515/10)")

	def test_extract_ip280_has_1_naamstemming_but_no_identifiable_motion_title(self):
		motion_data = self.extract_motiondata('ip280x.html')

		self.assertIsNotNone(motion_data, "motion data")
		self.assertEqual(len(motion_data), 0)

	def test_extract_ip271(self):
		motion_data = self.extract_motiondata('ip271x.html')

		self.assertIsNotNone(motion_data, "motion data")
		self.assertEqual(len(motion_data), 15)  # todo: check manually

		self.assert_motion_data(motion_data[0],
								'14',
								'14 Moties ingediend tot besluit van de\ninterpellatie van mevrouw Barbara Pas',
								'14 Motions déposées en conclusion de l\'interpellation de Mme Barbara\nPas')

		# FIXME: Do we count 'Goedkeuring van de agenda' as a motion?
		# If we link the motions with their votes we could exclude motions without votes
		self.assert_motion_data(motion_data[-1],
								'28',
								'28 Goedkeuring van de agenda',
								'28 Adoption de l’ordre du jour')

	def test_extract_ip290_has_no_naamstemmingen(self):
		motion_data = self.extract_motiondata('ip290x.html')

		self.assertIsNotNone(motion_data, "motion data")
		self.assertEqual(len(motion_data), 0)

	def assert_motion_data(self, motion_data: MotionData, label: str, nl_title_prefix: str, fr_title_prefix: str):
		self.assertEqual(motion_data.label, label)
		self.assertEqual(nl_title_prefix, motion_data.nl_title[:len(nl_title_prefix)])
		self.assertEqual(fr_title_prefix, motion_data.fr_title[:len(fr_title_prefix)])

	def extract_motiondata(self, plenary_filename):
		path = CONFIG.plenary_html_input_path(plenary_filename)
		return _extract_motiondata(path, _read_plenary_html(path))
