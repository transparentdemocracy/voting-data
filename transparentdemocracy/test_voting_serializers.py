import tempfile
import unittest
import os

from transparentdemocracy import PLENARY_HTML_INPUT_PATH
from transparentdemocracy.plenaries.extraction import extract_from_html_plenary_report
from transparentdemocracy.plenaries.serialization import MarkdownSerializer


class TestMotionToMarkdownSerializer(unittest.TestCase):

	def test_serialize(self):
		tmp_markdown_output_dir = tempfile.mkdtemp("plenary-markdown-")
		with open(os.path.join('fixtures', 'plenary 298.md'), 'r') as md_file:
			expected_markdown = md_file.read()
		plenary, votes = extract_from_html_plenary_report(os.path.join(PLENARY_HTML_INPUT_PATH, 'ip298x.html'))

		MarkdownSerializer(tmp_markdown_output_dir).serialize_plenaries([plenary])

		with open(os.path.join(tmp_markdown_output_dir, 'plenary 298.md')) as plenary_file:
			self.assertEqual(plenary_file.read(), expected_markdown)
