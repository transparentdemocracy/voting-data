import glob
import logging
import os
import json

from tqdm.auto import tqdm

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
			voting_serializer.serialize(plenary, os.path.join(markdown_dir, f"plenary {plenary.id}.md"))

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


def print_relevant_actors():
	actors_files = glob.glob(os.path.join(INPUT_ACTORS_PATH, "*.json"))

	for actor_file in actors_files:
		actor_json = json.load(open(actor_file, 'r'))
		if len(actor_json['items']) != 1:
			raise Exception('weird file: %s', actor_file)

		actor = actor_json['items'][0]
		name = actor['name']
		first_name = actor['fName']
		full_name = f"{name} {first_name}"

		role = get_leg55_role(actor)
		if role is None:
			continue

		print(actor_file, full_name)


def get_leg55_role(actor):
	is_active = lambda r: r['status'] == 'active'
	has_leg55_plenum = lambda r: r['ouSummary']['fullNameNL'] == '/Wetgevende macht/Kvvcr/Leg 55/Plenum/PLENUMVERGADERING'
	roles = list(filter(lambda r: has_leg55_plenum(r) and is_active(r), actor['role']))

	if len(roles) == 0:
		return None
	if len(roles) > 1:
		raise Exception('too many roles for ' + str(actor))

	return roles[0]

def main():
	convert_plenary_reports_to_markdown_and_json()
	# print_html_extraction_problems()

	# print_relevant_actors()


if __name__ == "__main__":
	main()
