import glob
import itertools
import json
import logging
import os

import Levenshtein
from tqdm.asyncio import tqdm

from transparentdemocracy import ACTOR_JSON_INPUT_PATH
from transparentdemocracy.model import Politician
from transparentdemocracy.politicians.serialization import JsonSerializer

logger = logging.getLogger(__name__)


class Politicians:
	def __init__(self, politicians):
		if not politicians:
			raise Exception("empty list of politicians")
		self.politicians = politicians
		self.politicians_by_name = dict((p.full_name, p) for p in politicians)

	def get_by_name(self, name):
		if name in self.politicians_by_name:
			return self.politicians_by_name[name]
		else:
			result = self._find_best_match(name)
			self.politicians_by_name[name] = result
			logger.warning(f"Non exact name match: {name} -> {result.full_name}")
			return result

	def _find_best_match(self, name):
		best_name = min([(Levenshtein.distance(name, compare_name), compare_name) for compare_name in
						 self.politicians_by_name.keys()])[1]
		return self.politicians_by_name[best_name]

	def print_by_party(self) -> None:
		by_party = itertools.groupby(sorted(self.politicians, key=lambda p: p.party),
										key=lambda a: a.party)
		for k, v in by_party:
			print(k)
			for actor in v:
				print(f" - {actor.full_name}")


class PoliticianExtractor(object):
	def __init__(self, actors_path=ACTOR_JSON_INPUT_PATH):
		self.actors_path = actors_path

	def extract_politicians(self, pattern="*.json") -> Politicians:
		return Politicians([simplify_actor(a) for a in get_relevant_actors(self.actors_path, pattern)])


def print_politicians_by_party():
	politicians = PoliticianExtractor().extract_politicians()

	politicians.print_by_party()


def simplify_actor(actor):
	id = actor['id']
	full_name = f"{actor['name']} {actor['fName']}"
	party = get_party(actor)
	return Politician(
		id=id,
		full_name=full_name,
		party=party
	)


def get_party(actor):
	def is_party_member(role):
		return role['functionSummary'][
			'fullNameNL'] == "/Beheer objecten/Functiecodes per mandaat/Lid-Kamer/Fractie lid"

	def is_leg_55(role):
		return "Leg 55" in role["ouSummary"]["fullNameNL"]

	membership_roles = list(filter(lambda r: is_leg_55(r) and is_party_member(r), actor['role']))

	if len(membership_roles) == 0:
		logger.info(f"could not determine party for {actor['id']} {actor['name']} {actor['fName']}")
		return "unknown"

	faction_full = membership_roles[-1]["ouSummary"]["fullNameNL"]
	recognized_prefix = "/Wetgevende macht/Kvvcr/Leg 55/Politieke fracties/Erkende/"
	non_recognized_prefix = "/Wetgevende macht/Kvvcr/Leg 55/Politieke fracties/Niet erkende/"

	if faction_full.startswith(recognized_prefix):
		return faction_full[len(recognized_prefix):]

	if faction_full.startswith(non_recognized_prefix):
		return faction_full[len(non_recognized_prefix):]

	raise Exception(f"could not determine faction for {a['name']} {a['fName']}")


def get_relevant_actors(actors_path=(ACTOR_JSON_INPUT_PATH), pattern="*.json"):
	actor_files = glob.glob(os.path.join(actors_path, pattern))
	actors = []

	for actor_file in tqdm(actor_files, desc="Processing actors..."):
		with open(actor_file, 'r') as actor_fp:
			actor_json = json.load(actor_fp)
		if len(actor_json['items']) != 1:
			raise Exception('weird file: %s', actor_file)

		actor = actor_json['items'][0]

		role = get_leg55_role(actor)
		if role is None:
			continue
		actors.append(actor)

	logger.info(f"Returning {len(actors)} relevant actors out of {len(actor_files)}")
	return actors


def get_leg55_role(actor):
	plenum_fullname = '/Wetgevende macht/Kvvcr/Leg 55/Plenum/PLENUMVERGADERING'

	def has_leg55_plenum(r):
		return r['ouSummary']['fullNameNL'] == plenum_fullname

	roles = list(filter(has_leg55_plenum, actor['role']))

	if len(roles) == 0:
		return None

	return roles[-1]


def main():
	print_politicians_by_party()


def create_json():
	JsonSerializer().serialize_politicians(PoliticianExtractor().extract_politicians().politicians)


if __name__ == "__main__":
	main()
