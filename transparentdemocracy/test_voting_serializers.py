import json
import os
import tempfile
import unittest

from transparentdemocracy import CONFIG
from transparentdemocracy.plenaries.extraction import extract_from_html_plenary_report
from transparentdemocracy.plenaries.motion_document_proposal_linker import link_motions_with_proposals
from transparentdemocracy.plenaries.serialization import MarkdownSerializer, JsonSerializer


class TestPlenaryMarkdownSerializer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        root_folder = os.path.dirname(os.path.dirname(__file__))
        CONFIG.enable_testing(os.path.join(root_folder, "testdata"), "55")

    @unittest.skip("Markdown serialization is deprecated now.")
    def test_serialize(self):
        tmp_markdown_output_dir = tempfile.mkdtemp("plenary-markdown-")
        with open(os.path.join(os.path.dirname(__file__), 'fixtures', 'plenary 298.md'), 'r') as md_file:
            expected_markdown = md_file.read()

        plenary, votes, problems = extract_from_html_plenary_report(
            CONFIG.plenary_html_input_path('ip298x.html'))
        plenaries, documents_reference_objects, link_problems = link_motions_with_proposals([
            plenary])

        MarkdownSerializer(tmp_markdown_output_dir).serialize_plenaries(
            [plenary], votes, documents_reference_objects)

        with open(os.path.join(tmp_markdown_output_dir, 'plenary 298.md')) as plenary_file:
            actual_markdown = plenary_file.read()

        self.assertEqual(expected_markdown, actual_markdown)


class TestPlenaryJsonSerializer(unittest.TestCase):

    def test_serialize(self):
        tmp_json_output_dir = tempfile.mkdtemp("plenary-json")
        serializer = JsonSerializer(tmp_json_output_dir)
        plenary, votes, problems = extract_from_html_plenary_report(
            CONFIG.plenary_html_input_path('ip298x.html'))

        link_motions_with_proposals([plenary])
        serializer.serialize_plenaries([plenary])

        with open(os.path.join(tmp_json_output_dir, "plenaries.json")) as fp:
            actual_json = json.load(fp)
        self.assertEqual("55_298", actual_json[0]['id'])
        self.assertEqual("2024-04-04", actual_json[0]['date'])
