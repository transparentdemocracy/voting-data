import glob
import itertools
import json
import logging
import os

import Levenshtein
from tqdm.asyncio import tqdm

from transparentdemocracy.config import Config
from transparentdemocracy.model import Politician

logger = logging.getLogger(__name__)


class Politicians:
    def __init__(self, politicians):
        if not politicians:
            raise Exception("empty list of politicians")
        self.politicians = politicians
        self.politicians_by_name = dict((p.full_name, p) for p in politicians)
        self.politicians_by_id = dict((p.id, p) for p in politicians)

    def get_by_name(self, name):
        if name in self.politicians_by_name:
            return self.politicians_by_name[name]

        result = self._find_best_match(name)
        self.politicians_by_name[name] = result
        logger.warning("Non exact name match: %s -> %s", name, result.full_name)
        return result

    def _find_best_match(self, name):
        best_name = min((Levenshtein.distance(name, compare_name), compare_name)
                        for compare_name in
                        self.politicians_by_name.keys())[1]
        return self.politicians_by_name[best_name]

    def __getitem__(self, item):
        return self.politicians_by_id[item]

    def print_by_party(self) -> None:
        by_party = itertools.groupby(sorted(self.politicians, key=lambda p: p.party),
                                     key=lambda a: a.party)
        for k, v in by_party:
            print(k)
            for actor in v:
                print(f" - {actor.full_name}")


class PoliticianExtractor:
    def __init__(self, config: Config):
        self.config = config
        self.actors_path = config.actor_json_input_path()

    def extract_politicians(self, pattern="*.json") -> Politicians:
        return Politicians([simplify_actor(self.config, a) for a in get_relevant_actors(self.config, self.actors_path, pattern)])


def simplify_actor(config, actor):
    actor_id = actor['id']
    full_name = f"{actor['name']} {actor['fName']}"
    party = get_party(config, actor)
    return Politician(
        id=actor_id,
        full_name=full_name,
        party=party
    )


def get_party(config, actor):
    # Temproary workaround because https://data.dekamer.be/v0/actr/8051 is not up to date yet
    if config.legislature == "56" and actor["id"] == "8051":
        return "Vooruit"

    def is_party_member(role):
        return role['functionSummary']['fullNameNL'] == "/Beheer objecten/Functiecodes per mandaat/Lid-Kamer/Fractie lid"

    def is_current_leg(role):
        leg = f"Leg {config.legislature}"
        return leg in role["ouSummary"]["fullNameNL"]

    membership_roles = list(filter(lambda r: is_current_leg(r) and is_party_member(r), actor['role']))

    if len(membership_roles) == 0:
        logger.info("could not determine party for %s %s %s", actor["id"], actor["name"], actor["fName"])
        return "unknown"

    faction_full = membership_roles[-1]["ouSummary"]["fullNameNL"]
    recognized_prefix = f"/Wetgevende macht/Kvvcr/Leg {config.legislature}/Politieke fracties/Erkende/"
    non_recognized_prefix = f"/Wetgevende macht/Kvvcr/Leg {config.legislature}/Politieke fracties/Niet erkende/"

    if faction_full.startswith(recognized_prefix):
        return faction_full[len(recognized_prefix):]

    if faction_full.startswith(non_recognized_prefix):
        return faction_full[len(non_recognized_prefix):]

    raise Exception(f"could not determine faction for {actor['name']} {actor['fName']}")


def get_relevant_actors(config, actors_path, pattern="*.json"):
    actor_files = glob.glob(os.path.join(actors_path, pattern))
    actors = []

    for actor_file in tqdm(actor_files, desc="Processing actors..."):
        with open(actor_file, 'r', encoding="utf-8") as actor_fp:
            actor_json = json.load(actor_fp)
        if len(actor_json['items']) != 1:
            raise Exception('weird file: %s', actor_file)

        actor = actor_json['items'][0]

        role = get_current_leg_role(config, actor)
        if role is None:
            continue
        actors.append(actor)

    logger.info("Returning %d relevant actors out of %d", len(actors), len(actor_files))
    return actors


def load_politicians(config: Config) -> Politicians:
    with open(config.politicians_json_output_path("politicians.json"), 'r', encoding="utf-8") as fp:
        return Politicians([json_dict_to_politician(data) for data in json.load(fp)])


def json_dict_to_politician(data):
    return Politician(
        int(data['id']),
        data['full_name'],
        data['party']
    )


def get_current_leg_role(config, actor):
    if actor["id"] == "8051":
        return "Vooruit"

    plenum_fullname = f'/Wetgevende macht/Kvvcr/Leg {config.legislature}/Plenum/PLENUMVERGADERING'

    def has_current_leg_plenum(r):
        return r['ouSummary']['fullNameNL'] == plenum_fullname

    roles = list(filter(has_current_leg_plenum, actor['role']))

    if len(roles) == 0:
        return None

    return roles[-1]
