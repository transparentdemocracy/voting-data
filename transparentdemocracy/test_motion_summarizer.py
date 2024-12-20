import os
import unittest

from transparentdemocracy import CONFIG
from transparentdemocracy.motions.motion_summarizer import MotionSummarizer


class TestMotionSummarizer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root_folder = os.path.dirname(os.path.dirname(__file__))
        CONFIG.enable_testing(os.path.join(root_folder, "testdata"), "55")

    @unittest.skipIf("OPENAI_API_KEY" not in os.environ, "test needs an openapi key")
    def test_summarize(self):
        motion_description = ("20 Wetsontwerp houdende instemming met het samenwerkingsakkoord van 7 februari 2024 tot "
                              "wijziging van het samenwerkingsakkoord van 19 maart 2020 tussen de Federale Staat, "
                              "de Vlaamse Gemeenschap, de Franse Gemeenschap en de Duitstalige Gemeenschap met "
                              "betrekking tot de bevoegdheden van de gemeenschappen en van de Federale Staat inzake "
                              "het taxshelterstelsel voor audiovisuele werken en podiumwerken en tot "
                              "informatie-uitwisseling, gedaan te Brussel op 7 februari 2024 (3826/1) 20 20 20 "
                              "Wetsontwerp houdende instemming met het samenwerkingsakkoord van 7 februari 2024 tot "
                              "wijziging van het samenwerkingsakkoord van 19 maart 2020 tussen de Federale Staat, "
                              "de Vlaamse Gemeenschap, de Franse Gemeenschap en de Duitstalige Gemeenschap met "
                              "betrekking tot de bevoegdheden van de gemeenschappen en van de Federale Staat inzake "
                              "het taxshelterstelsel voor audiovisuele werken en podiumwerken en tot "
                              "informatie-uitwisseling, gedaan te Brussel op 7 februari 2024 (3826/1) Wetsontwerp "
                              "houdende instemming met het samenwerkingsakkoord van 7 februari 2024 tot wijziging van "
                              "het samenwerkingsakkoord van 19 maart 2020 tussen de Federale Staat, de Vlaamse "
                              "Gemeenschap, de Franse Gemeenschap en de Duitstalige Gemeenschap met betrekking tot de "
                              "bevoegdheden van de gemeenschappen en van de Federale Staat inzake het "
                              "taxshelterstelsel voor audiovisuele werken en podiumwerken en tot "
                              "informatie-uitwisseling, gedaan te Brussel op 7 februari 2024 (3826/1) Wetsontwerp "
                              "houdende instemming met het samenwerkingsakkoord van 7 februari 2024 tot wijziging van "
                              "het samenwerkingsakkoord van 19 maart 2020 tussen de Federale Staat, de Vlaamse "
                              "Gemeenschap, de Franse Gemeenschap en de Duitstalige Gemeenschap met betrekking tot de "
                              "bevoegdheden van de gemeenschappen en van de Federale Staat inzake het "
                              "taxshelterstelsel voor audiovisuele werken en podiumwerken en tot "
                              "informatie-uitwisseling, gedaan te Brussel op 7 februari 2024 (3826/1)")
        summarizer = MotionSummarizer()

        summary = summarizer.summarize(motion_description)

        self.assertIsNotNone(summary)


if __name__ == '__main__':
    unittest.main()
