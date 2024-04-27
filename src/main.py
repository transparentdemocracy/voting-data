import glob
import json
import logging
import os

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


def get_relevant_actors():
	actors_files = glob.glob(os.path.join(INPUT_ACTORS_PATH, "*.json"))
	actors = []

	for actor_file in tqdm(actors_files, desc="Processing actors..."):
		actor_json = json.load(open(actor_file, 'r'))
		if len(actor_json['items']) != 1:
			raise Exception('weird file: %s', actor_file)

		actor = actor_json['items'][0]

		role = get_leg55_role(actor)
		if role is None:
			continue
		actors.append(actor)

	logger.info(f"Returning {len(actors)} relevant actors out of {len(actors_files)}")
	return actors


def get_leg55_role(actor):
	plenum_fullname = '/Wetgevende macht/Kvvcr/Leg 55/Plenum/PLENUMVERGADERING'

	def has_leg55_plenum(r):
		return r['ouSummary']['fullNameNL'] == plenum_fullname

	roles = list(filter(has_leg55_plenum, actor['role']))

	if len(roles) == 0:
		return None

	return roles[-1]


def get_voter_names():
	names = set()
	json_files = glob.glob(os.path.join(OUTPUT_PATH, "plenary", "json", "*.json"))

	total_votes = 0
	for json_file in tqdm(json_files, "Processing plenary json files"):
		plenary = json.load(open(json_file, 'r'))
		for motion in plenary['motions']:
			vote_names_yes = motion.get('vote_names_yes', []) or []
			vote_names_no = motion.get('vote_names_no', []) or []
			vote_names_abstention = motion.get('vote_names_abstention', []) or []

			all_names = vote_names_yes + vote_names_no + vote_names_abstention
			total_votes += len(all_names)
			names.update(all_names)

	logger.info(f"Got {len(names)} names from {total_votes} votes")

	return names


def analyze_voter_names():
	actors = get_relevant_actors()
	actor_names = [f"{a['name']} {a['fName']}" for a in actors]
	assert len(set(actor_names)) == len(actor_names), "actor names should be unique"
	actor_names = set(actor_names)

	voter_names = get_voter_names()
	print("actor names", len(actor_names))

	unknown_voter_names = voter_names - set(actor_names)
	print(f"these {len(unknown_voter_names)} actors have voted but we don't have them in our set:")
	for n in unknown_voter_names:
		print(n)


def main():
	# TODO: make a CLI tool so we can choose which action to run without changing code.
	extract_voting_data_from_plenary_reports()

	# print_html_extraction_problems()

	# analyze_voter_names()

if __name__ == "__main__":
	main()
