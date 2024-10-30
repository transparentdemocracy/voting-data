from unittest import TestCase

from transparentdemocracy.publisher import to_doc_reference


class Test(TestCase):
    def test_to_doc_reference_single(self):
        ref = to_doc_reference("0001/2")
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
        ref = to_doc_reference("0001/2-4")
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
