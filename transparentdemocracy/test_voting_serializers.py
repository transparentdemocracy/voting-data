import tempfile
import unittest
import os

from transparentdemocracy.plenaries.extraction import extract_from_html_plenary_report
from transparentdemocracy.plenaries.serialization import MarkdownSerializer

DATA_DIR = "./data"


class TestMotionToMarkdownSerializer(unittest.TestCase):

	def test_serialize(self):
		plenary = extract_from_html_plenary_report(os.path.join(DATA_DIR, './input/pdf/ip298x.html'))
		expected_markdown = open(os.path.join(DATA_DIR, '/output/markdown/plenary 298.md', 'r')).read()

		with tempfile.NamedTemporaryFile(delete=False) as temp_file:
			markdown_output_path = temp_file.name

		MarkdownSerializer().serialize(plenary, markdown_output_path)

		self.assertEqual(open(markdown_output_path).read(), expected_markdown)
