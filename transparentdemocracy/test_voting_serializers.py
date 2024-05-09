import json
import os
import tempfile
import unittest

from transparentdemocracy import CONFIG
from transparentdemocracy.plenaries.extraction import extract_from_html_plenary_report
from transparentdemocracy.plenaries.serialization import MarkdownSerializer, JsonSerializer


class TestPlenaryMarkdownSerializer(unittest.TestCase):

	@classmethod
	def setUpClass(cls):
		CONFIG.data_dir = os.path.join(os.path.dirname(__file__), "..", "testdata")

	@unittest.skip("broken because proposal parsing fails")
	def test_serialize(self):
		tmp_markdown_output_dir = tempfile.mkdtemp("plenary-markdown-")
		with open(os.path.join(os.path.dirname(__file__), 'fixtures', 'plenary 298.md'), 'r') as md_file:
			expected_markdown = md_file.read()
		plenary, votes = extract_from_html_plenary_report(CONFIG.plenary_html_input_path('ip298x.html'))

		MarkdownSerializer(tmp_markdown_output_dir).serialize_plenaries([plenary], votes)

		with open(os.path.join(tmp_markdown_output_dir, 'plenary 298.md')) as plenary_file:
			self.assertEqual(plenary_file.read(), expected_markdown)


class TestPlenaryJsonSerializer(unittest.TestCase):

	def test_serialize(self):
		tmp_json_output_dir = tempfile.mkdtemp("plenary-json")
		serializer = JsonSerializer(tmp_json_output_dir)
		plenary, votes = extract_from_html_plenary_report(CONFIG.plenary_html_input_path('ip298x.html'))

		serializer.serialize_plenaries([plenary])

		with open(os.path.join(tmp_json_output_dir, "plenaries.json")) as fp:
			actual_json = json.load(fp)
		self.assertEqual(actual_json[0]['id'], "55_298")
		self.assertEqual(actual_json[0]['date'], "2024-04-04")
