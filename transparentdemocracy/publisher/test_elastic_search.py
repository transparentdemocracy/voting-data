from unittest import TestCase

from transparentdemocracy.config import _create_config
from transparentdemocracy.main import Environments
from transparentdemocracy.publisher import to_doc_reference


class Test(TestCase):
    config55 = _create_config(Environments.TEST, '55')
    config56 = _create_config(Environments.TEST, '56')

    def test_to_doc_reference_single(self):
        ref = to_doc_reference(self.config55, "0001/2", {})
        self.assertEqual("0001/2", ref["spec"])
        self.assertEqual(("https://www.dekamer.be/kvvcr/showpage.cfm?section=/flwb&language=nl&cfm=/site/wwwcfm/flwb/flwbn.cfm"
                          "?lang=N&legislat=55&dossierID=0001"),
                         ref["documentMainUrl"])
        self.assertEqual([
            {
                "documentNr": 1,
                "documentSubNr": 2,
                "documentPdfUrl": "https://www.dekamer.be/FLWB/PDF/55/0001/55K0001002.pdf",
                "summaryNL": None,
                "summaryFR": None,
            }
        ], ref["subDocuments"])

    def test_to_doc_reference_range(self):
        ref = to_doc_reference(self.config55, "0001/2-4", {})
        self.assertEqual("0001/2-4", ref["spec"])
        self.assertEqual(("https://www.dekamer.be/kvvcr/showpage.cfm?section=/flwb&language=nl&cfm=/site/wwwcfm/flwb/flwbn.cfm"
                          "?lang=N&legislat=55&dossierID=0001"),
                         ref["documentMainUrl"])

        self.assertEqual([
            {
                "documentNr": 1,
                "documentSubNr": 2,
                "documentPdfUrl": "https://www.dekamer.be/FLWB/PDF/55/0001/55K0001002.pdf",
                "summaryNL": None,
                "summaryFR": None,
            },
            {
                "documentNr": 1,
                "documentSubNr": 3,
                "documentPdfUrl": "https://www.dekamer.be/FLWB/PDF/55/0001/55K0001003.pdf",
                "summaryNL": None,
                "summaryFR": None,
            },
            {
                "documentNr": 1,
                "documentSubNr": 4,
                "documentPdfUrl": "https://www.dekamer.be/FLWB/PDF/55/0001/55K0001004.pdf",
                "summaryNL": None,
                "summaryFR": None,
            }
        ], ref["subDocuments"])

    # ## WIP: first fixing unknown party names
    # def test_motions_elastic_format(self):
    #     app = create_application(self.config56, env=Environments.TEST)
    #
    #     plenaries, votes, problems = extract_plenary_reports(self.config56, [(self.config56.plenary_html_input_path("ip037x.html"))])
    #
    #     plenary = plenaries[0]
    #     mg = plenary.motion_groups[0]
    #     voting_reports = app.create_voting_reports(votes)
    #
    #     publishing_data = PublishingData(load_politicians(self.config56), {}, voting_reports=voting_reports)
    #     doc = app.motions_repository._motion_group_to_dict(publishing_data, plenary, mg)
    #
    #     self.assertEqual("2025-03-27", doc['votingDate'])
    #
    #     motion = doc["motions"][0]
    #     self.assertEqual("2025-03-27", motion['votingDate'])
    #     self.assertEqual("56_037_mg_5_m0", motion['id'])
    #
    #     # votePercentage should be correct
    #     self.assertEqual(105, motion["yesVotes"]["nrOfVotes"])
    #
    #     print("TTT", json.dumps(motion["yesVotes"]))
    #     self.assertAlmostEquals(100 * (105 / (105 + 32)), motion["yesVotes"]["votePercentage"], 5)
    #     self.assertAlmostEquals(100 * (103 / (105 + 32)), motion["yesVotes"]["partyVotes"][0]["votePercentage"], 5)
    #     self.assertAlmostEquals(100 * (2 / (105 + 32)), motion["yesVotes"]["partyVotes"][1]["votePercentage"], 5)
    #
    #     # TODO: assert vote percentages for no votes and abstentions
    #
    #     # partyName should never be null
    #     self.assertEqual("Weetniet", motion["yesVotes"]["partyVotes"][0]["partyName"])
    #
    #     # Should be json serializable
    #     try:
    #         json.dumps(doc)
    #     except Exception as e:
    #         self.fail("Should be json serializable but got exception: " + e)
    #
    #
