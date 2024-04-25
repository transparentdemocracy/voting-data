import tempfile
import unittest

from voting_extractors import FederalChamberVotingPdfExtractor
from voting_serializers import PlenaryReportToMarkdownSerializer


class TestMotionToMarkdownSerializer(unittest.TestCase):

	@unittest.skip("todo replace extractor with html")
	def test_serialize(self):
		plenary = FederalChamberVotingPdfExtractor().extract('../data/input/pdf/ip298.pdf')
		expected_markdown = open('../data/output/markdown/plenary 298.md', 'r').read()

		with tempfile.NamedTemporaryFile(delete=False) as temp_file:
			markdown_output_path = temp_file.name

			PlenaryReportToMarkdownSerializer().serialize(plenary, markdown_output_path)

			self.assertEqual(open(markdown_output_path).read(), expected_markdown)
