import json
import os
import tempfile
import unittest

from transparentdemocracy.config import _create_config
from transparentdemocracy.main import Environments
from transparentdemocracy.plenaries.extraction import extract_from_html_plenary_report
from transparentdemocracy.plenaries.motion_document_proposal_linker import link_motions_with_proposals
from transparentdemocracy.plenaries.serialization import JsonSerializer


class TestPlenaryJsonSerializer(unittest.TestCase):
    config = _create_config(Environments.TEST, '55')

    def test_serialize(self):
        tmp_json_output_dir = tempfile.mkdtemp("plenary-json")
        serializer = JsonSerializer(self.config, tmp_json_output_dir)
        plenary, _mmm, _ = extract_from_html_plenary_report(self.config, self.config.plenary_html_input_path('ip298x.html'))

        link_motions_with_proposals([plenary])
        serializer.serialize_plenaries([plenary])

        with open(os.path.join(tmp_json_output_dir, "plenaries.json")) as fp:
            actual_json = json.load(fp)
        self.assertEqual("55_298", actual_json[0]['id'])
        self.assertEqual("2024-04-04", actual_json[0]['date'])
