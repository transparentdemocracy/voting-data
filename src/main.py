import glob
import json
import logging
import os

import Levenshtein
from tqdm.auto import tqdm

from src.enrichment import enrich_plenaries
from voting_extractors import FederalChamberVotingHtmlExtractor
from voting_serializers import PlenaryReportToJsonSerializer, PlenaryReportToMarkdownSerializer

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)  # or DEBUG to see debugging info as well.

INPUT_REPORTS_PATH = "./data/input/html"
OUTPUT_PATH = "./data/output"

INPUT_ACTORS_PATH = "./data/input/actors/actor"


def extract_voting_data_from_plenary_reports():
	# Process all input reports:
	voting_reports = glob.glob(os.path.join(INPUT_REPORTS_PATH, "*.html"))
	logging.debug(f"Will process the following input reports: {voting_reports}.")

	markdown_dir = os.path.join(OUTPUT_PATH, "plenary", "markdown")
	json_dir = os.path.join(OUTPUT_PATH, "plenary", "json")
	os.makedirs(markdown_dir, exist_ok=True)
	os.makedirs(json_dir, exist_ok=True)

	for voting_report in tqdm(voting_reports, desc="Processing plenary reports..."):
		try:
			# Extract the interesting voting info:
			logging.debug(f"Processing input report {voting_report}...")
			voting_extractor = FederalChamberVotingHtmlExtractor()
			plenary = voting_extractor.extract_from_plenary_report(voting_report)

			# Serialize the extracted voting info:
			# ... to human-readable format:
			voting_serializer = PlenaryReportToMarkdownSerializer()
			voting_serializer.serialize(plenary, os.path.join(markdown_dir, f"plenary {plenary.id.serialize_in_3chars()}.md")) # TODO

			# ... to machine-readable format:
			voting_serializer = PlenaryReportToJsonSerializer()
			voting_serializer.serialize(plenary, os.path.join(json_dir, f"plenary {plenary.id}.json"))

		except Exception:
			# TODO rare errors to fix + in some documents, no motions could be extracted - to fix.
			logging.warning("failed to process %s", voting_report, exc_info=True)


def print_html_extraction_problems():
	# Process all html files and print parse problems
	voting_reports = glob.glob(os.path.join(INPUT_REPORTS_PATH, "*.html"))
	print(len(voting_reports))
	logging.debug(f"Will process the following input reports: {voting_reports}.")

	problems = []
	for voting_report in tqdm(voting_reports, desc="Processing plenary reports..."):
		try:
			# Extract the interesting voting info:
			logging.debug(f"Processing input report {voting_report}...")
			voting_extractor = FederalChamberVotingHtmlExtractor()
			plenary = voting_extractor.extract_from_plenary_report(voting_report)

			for motion in plenary.motions:
				for parse_problem in motion.parse_problems:
					problems.append("plenary %d, motion %s: %s" % (plenary.id, motion.proposal.id, parse_problem))
		except Exception:
			logger.warning("problem parsing %s", voting_report, exc_info=True)

	print("Parse problems:")
	for problem in problems:
		print(problem)


def main():
	# TODO: make a CLI tool so we can choose which action to run without changing code.
	# extract_voting_data_from_plenary_reports()

	# print_html_extraction_problems()

	# enrich_plenaries()


if __name__ == "__main__":
	main()
