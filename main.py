import logging
import os

from transparentdemocracy import PLENARY_HTML_INPUT_PATH
from transparentdemocracy.plenaries.extraction import extract_plenaries_from_html_reports
from transparentdemocracy.plenaries.serialization import serialize

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main():
	plenaries, votes = extract_plenaries_from_html_reports(os.path.join(PLENARY_HTML_INPUT_PATH, "*.html"), num_reports_to_process=None)
	serialize(plenaries, votes)
	# enrich_plenaries()


if __name__ == "__main__":
	main()
