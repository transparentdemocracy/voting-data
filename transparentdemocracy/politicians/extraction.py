import glob
import itertools
import json
import logging
import os
import re

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

        exceptions = {"Mutyebele Ngoi": "Mutyebele Ngoi Lydia"}

        if Levenshtein.distance(name, best_name) > 3:
            if name in exceptions:
                best_name = exceptions[name]
            else:
                raise Exception(f"Got a suspicious match. Add manual rule to procede with this. name: {name}, best match: {best_name}")

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
    def is_party_member(role):
        return role['functionSummary']['fullNameNL'] == "/Beheer objecten/Functiecodes per mandaat/Lid-Kamer/Fractie lid"

    def is_current_leg(role):
        leg = f"Leg {config.legislature}"
        return leg in role["ouSummary"]["fullNameNL"]

    membership_roles = list(filter(lambda r: is_current_leg(r) and is_party_member(r), actor['role']))
    leg_roles = get_current_leg_roles(config, actor)
    roles = membership_roles + leg_roles

    parties = [get_party_from_role(config, role) for role in roles]
    parties = [party for party in parties if party is not None]

    if parties[0] == "PVDA-PTB":
        return "PTB-PVDA"

    if parties[0] == "CD&V":
        return "cd&v"

    if len(parties) == 0:
        raise Exception(f"no party name found for {actor['id']}, {actor['name']}, {actor['fName']}")

    return parties[0]

def get_party_from_role(config, role):
    # TODO: Sometimes the different patterns yield different results.
    # For now we'll just assume going over the patterns in order will be sufficient
    # but some normalization is still needed

    # case: Open VLD & MR

    role_name = role['ouSummary']['fullNameNL']

    match = opvolger_role_pattern(config.legislature).match(role_name)
    if match:
        return match.group(1)

    match = fractie_role_pattern(config.legislature).match(role_name)
    if match:
        return match.group(1)

    match = bxl_role_pattern(config.legislature).match(role_name)
    if match:
        return match.group(1)

    return None


def get_relevant_actors(config, actors_path, pattern="*.json"):
    actor_files = glob.glob(os.path.join(actors_path, pattern))
    actors = []

    for actor_file in tqdm(actor_files, desc="Processing actors..."):
        with open(actor_file, 'r', encoding="utf-8") as actor_fp:
            actor_json = json.load(actor_fp)
        if len(actor_json['items']) != 1:
            raise Exception('weird file: %s', actor_file)

        actor = actor_json['items'][0]

        roles = get_current_leg_roles(config, actor)
        if not roles:
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


def get_current_leg_roles(config, actor):
    def role_matches(r, role_pattern: re.Pattern):
        return re.match(role_pattern, r['ouSummary']['fullNameNL'])

    roles = actor['role']
    plenum_roles = [role for role in roles if role_matches(role, plenum_role_pattern(config.legislature))]
    fractie_roles = [role for role in roles if role_matches(role, fractie_role_pattern(config.legislature))]
    bxl_roles = [role for role in roles if role_matches(role, bxl_role_pattern(config.legislature))]
    opvolger_roles = [role for role in roles if role_matches(role, opvolger_role_pattern(config.legislature))]

    return plenum_roles + fractie_roles + bxl_roles + opvolger_roles


def plenum_role_pattern(legislature):
    return re.compile(f'/Wetgevende macht/Kvvcr/Leg {re.escape(legislature)}/Plenum/PLENUMVERGADERING')


def fractie_role_pattern(legislature):
    return re.compile(f'/Wetgevende macht/Kvvcr/Leg {re.escape(legislature)}/Politieke fracties/Erkende/(.*)')


def bxl_role_pattern(legislature):
    return re.compile(f'/Verkiezing/Kamer - Leg {re.escape(legislature)} \\(.*\\)/Brussel-Hoofdstad/(.*)/Titelvoerenden')


def opvolger_role_pattern(legislature):
    return re.compile(f'/Verkiezing/Kamer - Leg {re.escape(legislature)} \\(.*\\).*/([^/]*)/Opvolgers')
