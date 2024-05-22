import os
import unittest

import transparentdemocracy
from transparentdemocracy import CONFIG
from transparentdemocracy.plenaries.extraction import extract_from_html_plenary_reports
from transparentdemocracy.plenaries.motion_proposal_linker import link_motions_with_proposals


ROOT_FOLDER = os.path.dirname(os.path.dirname(transparentdemocracy.__file__))


class MotionProposalLinkerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        CONFIG.data_dir = os.path.join(ROOT_FOLDER, "testdata")

    @unittest.skipIf(os.environ.get("SKIP_SLOW", None) is not None, "This test isn't really slow but requires data")
    def test_link_motions_with_proposals__all_plenaries__not_throwing(self):
        # Arrange
        CONFIG.data_dir = os.path.join(ROOT_FOLDER, "data")
        plenaries, votes, problems = extract_from_html_plenary_reports(
            CONFIG.plenary_html_input_path("ip*x.html"))

        # Act
        plenaries, link_problems = link_motions_with_proposals(plenaries)

        # Assert
        # The exact amount doesn't matter. We just want to make sure it doesn't crash.
        # Ideally, less is better, but if there are 0 problems it could also indicate a problem with the data
        self.assertGreater(0, len(link_problems))

    @unittest.skip("work in progress - investigating why proposal in linked plenary was not created.")
    def test_link_motions_with_proposals__ip_298x_html__links_to_correct_proposals(self):
        # Checking first and foremost whether ip298x.html, a first example report we used for agreeing on how to
        # implement extraction of motions, can be processed correctly by our linker task.
        # Arrange
        plenaries, votes, problems = extract_from_html_plenary_reports(
            CONFIG.plenary_html_input_path("ip29*x.html"))  # Linking of motions in report 298 with discussion from 296.

        # Act
        plenaries, link_problems = link_motions_with_proposals(plenaries)

        # Assert: link proposal discussions and proposals with same main document number, but different sub-documents:
        plenary298 = [plenary for plenary in plenaries if plenary.number == 298][0]
        motion_group11 = plenary298.motion_groups[1]
        self.assertEqual("3515/10", motion_group11.documents_reference)
        self.assertEqual("55_296_d26", motion_group11.proposal_discussion_id)

        plenary296 = [plenary for plenary in plenaries if plenary.number == 296][0]
        matching_proposal_discussion26 = [proposal_discussion for proposal_discussion in plenary296.proposal_discussions
                                          if proposal_discussion.id == "55_296_d26"][0]
        self.assertEqual(1, len(matching_proposal_discussion26.proposals))
        self.assertEqual("3515/1-9", matching_proposal_discussion26.proposals[0].documents_reference)

        self.assertEqual("3515/10", motion_group11.motions[0].documents_reference)
        self.assertEqual("55_296_d26_p0", motion_group11.motions[0].proposal_id)

        matching_proposal0 = [proposal for proposal in matching_proposal_discussion26.proposals
                              if proposal.id == "55_296_d26_p0"][0]
        self.assertEqual("3515/1-9", matching_proposal0.documents_reference)

    def test_link_motions_with_proposals__ip_262x_html__links_to_correct_proposals(self):
        # Checking first and foremost whether ip262x.html, the example report we used for agreeing on how to implement
        # extraction of motions, can be processed correctly by our linker task.
        # Arrange
        plenaries, votes, problems = extract_from_html_plenary_reports(
            CONFIG.plenary_html_input_path("ip26*x.html"))  # Linking of motions in report 262 with discussion from 261.

        # Act
        plenaries, link_problems = link_motions_with_proposals(plenaries)

        # Assert
        plenary262 = [plenary for plenary in plenaries if plenary.number == 262][0]
        motion_group12 = plenary262.motion_groups[4]
        self.assertEqual("3495/1-5", motion_group12.documents_reference)
        self.assertEqual("55_261_d22", motion_group12.proposal_discussion_id)

        self.assertEqual("3495/5", motion_group12.motions[0].documents_reference)
        self.assertEqual("55_261_d22_p0", motion_group12.motions[0].proposal_id)

        self.assertEqual("3495/5", motion_group12.motions[1].documents_reference)
        self.assertEqual("55_261_d22_p0", motion_group12.motions[1].proposal_id)

        self.assertEqual("3495/5", motion_group12.motions[1].documents_reference)
        self.assertEqual("55_261_d22_p0", motion_group12.motions[1].proposal_id)
