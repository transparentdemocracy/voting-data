from voting_extractors import FederalChamberVotingPdfExtractor
from voting_serializers import MotionToMarkdownSerializer
from model import Motion, Proposal

import unittest
import tempfile

class TestMotionToMarkdownSerializer(unittest.TestCase):
    
    def test_serialize_motions(self):
        motions = FederalChamberVotingPdfExtractor().extract('../data/input/ip298.pdf')
        expected_markdown = open('../data/output/plenary 298.md','r').read()

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            markdown_output_path = temp_file.name

            MotionToMarkdownSerializer().serialize_motions(motions, 298, markdown_output_path)

            self.assertEqual(open(markdown_output_path).read(), expected_markdown)
