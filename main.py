import logging
import os

from transparentdemocracy import CONFIG
from transparentdemocracy.plenaries.extraction import extract_from_html_plenary_reports
from transparentdemocracy.plenaries.serialization import serialize

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main():
	plenaries, votes = extract_from_html_plenary_reports(CONFIG.plenary_html_input_path("*.html"), num_reports_to_process=None)
	serialize(plenaries, votes)
	# enrich_plenaries()


if __name__ == "__main__":
	main()
