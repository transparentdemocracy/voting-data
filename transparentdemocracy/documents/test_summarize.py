import unittest
from unittest import TestCase

from transparentdemocracy.config import _create_config, Environments
from transparentdemocracy.documents.summarize import DocumentSummarizer


class SummarizeTest(unittest.TestCase):

    config = _create_config(Environments.TEST, '56')

    def test_parse_valid(self):
        output = """Here is the summary in Dutch (nl) and French (fr):

{
"nl": "Het huidige financiële jaar is gecharterd en er zijn verschillende factoren die een impact hebben op de begroting. De bijdrage aan de Europese Unie wordt herzien, evenals de provisie voor decommissioning dyssynergies. Er worden ook correcties gemaakt voor het pécule van vacances en de garantiereven voor ouderen. Het totale bedrag dat wordt verlaagd is 1,1 miljard euro. Dit is noodzakelijk om de overheidsdepartementen in goede orde te houden.",
"fr": "L'année financière actuelle est soumise à des facteurs qui ont un impact sur le budget. La contribution à l'Union européenne est révisée, ainsi que la provision pour les \\"decommissioning dyssynergies\\". Il y a également des corrections pour le pécule de vacances et la garantie-revenu des personnes âgées. Le total montant diminué est de 1,1 milliard d'euros. Cela est nécessaire pour maintenir les services publics en bonne santé."
}"""

        result = DocumentSummarizer(self.config).parse_llm_output('testdoc', output)

        self.assertIsNotNone(result)
