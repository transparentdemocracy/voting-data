import glob
import itertools
import json
import os
import logging

from tqdm.asyncio import tqdm

logger = logging.getLogger(__name__)

DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data"))
ACTOR_JSON_DIR = os.path.join(DATA_DIR, "input", "actors", "actor")


def get_simplified_actors():
	return [simplify_actor(a) for a in get_relevant_actors()]


def print_actors_by_fraction():
	actors = get_simplified_actors()
	by_fraction = itertools.groupby(sorted(actors, key=lambda a: a['fraction']),
									key=lambda a: a['fraction'])
	for k, v in by_fraction:
		print(k)
		for actor in v:
			print(f" - {actor['name']}")


def simplify_actor(actor):
	id = actor['id']
	name = f"{actor['name']} {actor['fName']}"
	fraction = get_fraction(actor)
	return dict(
		id=id,
		name=name,
		fraction=fraction
	)


def get_fraction(actor):
	def is_fraction_member(role):
		return role['functionSummary'][
			'fullNameNL'] == "/Beheer objecten/Functiecodes per mandaat/Lid-Kamer/Fractie lid"

	def is_leg_55(role):
		return "Leg 55" in role["ouSummary"]["fullNameNL"]

	membership_roles = list(filter(lambda r: is_leg_55(r) and is_fraction_member(r), actor['role']))

	if len(membership_roles) == 0:
		logger.error(f"could not determine fraction for {actor['id']} {actor['name']} {actor['fName']}")
		return "unknown"

	return membership_roles[-1]["ouSummary"]["fullNameNL"]


def get_relevant_actors():
	actor_files = glob.glob(os.path.join(ACTOR_JSON_DIR, "*.json"))
	actors = []

	for actor_file in tqdm(actor_files, desc="Processing actors..."):
		actor_json = json.load(open(actor_file, 'r'))
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
	print_actors_by_fraction()


if __name__ == "__main__":
	main()
