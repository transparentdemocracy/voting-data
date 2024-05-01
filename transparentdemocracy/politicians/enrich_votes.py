import glob
import json
import logging
import os
from collections import Counter

import Levenshtein
from tqdm.auto import tqdm

from transparentdemocracy import ENRICHED_VOTES_JSON_OUTPUT_PATH, PLENARY_JSON_OUTPUT_PATH
from transparentdemocracy.politicians.fetch_politicians import PoliticianExtractor

logger = logging.getLogger(__name__)


def enrich_votes():
	politicians = PoliticianExtractor().extract_politicians()
	os.makedirs(ENRICHED_VOTES_JSON_OUTPUT_PATH, exist_ok=True)

	plenary_files = glob.glob(os.path.join(PLENARY_JSON_OUTPUT_PATH, "*.json"))
	for plenary_file in tqdm(plenary_files, "Generating enrichments"):
		with open(plenary_file, 'r') as f:
			plenary = json.load(f)
		enrichment = enrich(plenary, politicians)

		enrichment_file = os.path.join(ENRICHED_VOTES_JSON_OUTPUT_PATH, f"plenary {plenary['id']} votes.json")
		with open(enrichment_file, 'w') as f:
			json.dump(enrichment, f)


def enrich(plenary, politicians):
	return dict(
		[(f"{plenary['id']}/{motion['proposal']['id']}", enrich_votes_for_motion(motion, politicians)) for motion in
		 plenary['motions']])


def get_voter_names():
	names = set()
	json_files = glob.glob(os.path.join(PLENARY_JSON_OUTPUT_PATH, "*.json"))

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


def get_actors_by_voter_name(actors, voter_names):
	actor_names = [a['name'] for a in actors]
	assert Counter(actor_names).most_common(1)[0][1] == 1, "Actor names should be unique"
	actor_names = set(actor_names)
	actors_by_voter_name = dict([(a['name'], a) for a in actors])

	unknown_voter_names = voter_names - set(actor_names)
	for voter_name in unknown_voter_names:
		best_match = find_best_match(voter_name, actor_names)
		logger.warning(f"Non-exact name match: {voter_name} <-> {best_match}")
		actors_by_voter_name[voter_name] = actors_by_voter_name[best_match]

	return actors_by_voter_name


# TODO: use Politicians.get_by_name
def find_best_match(name, names):
	return min([(Levenshtein.distance(name, compare_name), compare_name) for compare_name in names])[1]


def enrich_votes_for_motion(motion, politicians):
	yes_names = motion['vote_names_yes'] or []
	no_names = motion['vote_names_no'] or []
	abstention_names = motion['vote_names_abstention'] or []

	yes_voters = [politicians.get_by_name(name) for name in yes_names]
	no_voters = [politicians.get_by_name(name) for name in no_names]
	abstention_voters = [politicians.get_by_name(name) for name in abstention_names]

	return dict(
		yes=yes_voters,
		no=no_voters,
		abstention=abstention_voters
	)


def main():
	enrich_votes()


if __name__ == "__main__":
	main()
