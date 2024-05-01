import logging
import os

from transparentdemocracy import DATA_PATH
from transparentdemocracy.plenaries.extraction import extract_voting_data_from_plenary_reports
from transparentdemocracy.plenaries.serialization import serialize

INPUT_REPORTS_PATH = os.path.join(DATA_PATH, "input", "plenary", "html")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main():
	plenaries, votes = extract_voting_data_from_plenary_reports(os.path.join(INPUT_REPORTS_PATH, "*.html"), num_reports_to_process=None)
	serialize(plenaries, votes)
	# enrich_plenaries()


if __name__ == "__main__":
	main()
