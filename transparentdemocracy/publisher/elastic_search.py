"""
Interfacing with ElasticSearch, our backend towards the watdoetdepolitiek.be frontend application.
This includes connecting with ElasticSearch, writing data to it, reading data from it, and viewmodels for the data
exchange.
On longer term, the view models might be moved elsewhere, so they can be reused when publishing to another type of
backend.
"""
import logging
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import List

from elasticsearch.client import Elasticsearch

from transparentdemocracy.config import Config, Environments
from transparentdemocracy.model import VoteType, Motion, MotionGroup, Plenary, Vote
from transparentdemocracy.politicians.extraction import Politicians

LOGGER = logging.getLogger(__name__)

MOTIONS_MAPPING = {
    "mappings": {
        "properties": {
            "votingDate": {
                "type": "date",
            }
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1
    }
}

PLENARIES_MAPPING = {
    "mappings": {
        "properties": {
            "date": {
                "type": "date",
            }
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1
    }
}

@dataclass
class PublishingData:
    politicians: Politicians
    summaries_by_id: dict
    votes_by_id: dict


class MotionElasticRepository:
    """
    A repository for CRUD actions against our ElasticSearch backend for motion groups and motions.
    The ElasticSearch index we query against here is called `motions` but stores motion groups *and* within each of
    those, all motions within that motion group.
    """
    def __init__(self, config: Config, env: Environments):
        self.config = config
        self.elastic_search = create_elastic_client(config, env)
        # TODO: put this back, disabled temporarily to avoid repetitively calling bonsai
        # self.create_index()

    def create_index(self):
        response = self.elastic_search.indices.create(
            index="motions",
            body=MOTIONS_MAPPING,
            ignore=400,
        )
        print(response)

    def upsert_motion_group(self, publishing_data, plenary, motion_group):
        motions = [
            _to_motion_read_model(self.config, publishing_data, plenary, motion_group, motion)
            for motion in motion_group.motions
            if motion is not None
        ]
        if len(motions) == 0:
            logging.warning("No motions in motion group with ID %s.", motion_group.id)
            return

        motion_group_doc = {
            'id': motion_group.id,
            'legislature': plenary.legislature,
            'plenaryNr': plenary.number,
            'titleNL': motion_group.title_nl,
            'titleFR': motion_group.title_fr,
            'motions': motions,
            'votingDate': plenary.date.isoformat()
        }
        response = self.elastic_search.index(index="motions", id=motion_group_doc["id"], body=motion_group_doc)
        print(response)

    def get_motion_groups(self, from_date_incl: datetime, until_date_incl: datetime):
        """Get all motion groups in a (voting) date range, both ends of the range included."""
        return self.elastic_search.search(index="motions", body={
            "query": {
                "bool": {
                    "filter": [
                        {
                            "range": {
                                "votingDate": {
                                    "gte": from_date_incl.isoformat(),
                                    "lte": until_date_incl.isoformat()
                                }
                            }
                        }
                    ]
                }
            }
        })


class PlenaryElasticRepository:
    def __init__(self, config: Config, env: Environments):
        self.elastic_search = create_elastic_client(config, env)
        self.config = config
        # TODO: put this back, disabled temporarily to avoid repetitively calling bonsai
        # self.create_index()

    def create_index(self):
        response = self.elastic_search.indices.create(
            index="plenaries",
            body=PLENARIES_MAPPING,
            ignore=400,
        )
        print(response)

    def upsert_plenary(self, plenary: Plenary, final_plenary_ids):
        doc = {
            'id': plenary.id,
            'title': plenary.date.isoformat(),
            'legislature': plenary.legislature,
            'date': plenary.date.isoformat(),
            'pdfReportUrl': plenary.pdf_report_url,
            'htmlReportUrl': plenary.html_report_url,
            'motionGroups': _to_motion_groups_doc(plenary.motion_groups),
            'is_final': plenary.id in final_plenary_ids
        }

        response = self.elastic_search.index(index="plenaries", id=doc["id"], body=doc)
        print(response)

    def get_statuses(self, plenary_ids: List[tuple[str, bool]]):
        query = {
            "_source": ["is_final"],
            "query": {
                "terms": {
                    "_id": plenary_ids
                }
            }
        }

        if len(plenary_ids) > 1000:
            # there are no legislatures with this many plenaries, I figure it's safe for now.
            raise Exception("too many plenary ids")

        es_result = self.elastic_search.search(index="plenaries", body=query, size=1000)
        es_status = dict([(hit["_id"], hit["_source"].get("is_final", False)) for hit in es_result["hits"]["hits"]])
        return dict([(plenary_id, es_status.get(plenary_id, None)) for plenary_id in plenary_ids])


class Publisher():
    # TODO find constructor usages (pass config)
    def __init__(self,
                 config: Config,
                 plenary_repo: PlenaryElasticRepository,
                 motions_repo: MotionElasticRepository,
                 politicians: Politicians,
                 summaries_by_id,
                 votes_by_id):
        self.config = config
        self.plenary_repo = plenary_repo
        self.motions_repo = motions_repo
        self.publishing_data = PublishingData(politicians, summaries_by_id, votes_by_id)

    def publish(self, plenaries, final_plenary_ids):
        self._publish_motions(plenaries)
        self._publish_plenaries(plenaries, final_plenary_ids)

    def _publish_motions(self, plenaries):
        for plenary in plenaries:
            for mg in plenary.motion_groups:
                self.motions_repo.upsert_motion_group(self.publishing_data, plenary, mg)

    def _publish_plenaries(self, plenaries, final_plenary_ids):
        # TODO: document structure in elastic
        for plenary in plenaries:
            self.plenary_repo.upsert_plenary(plenary, final_plenary_ids)


def _to_motion_groups_doc(motion_groups):
    return [_to_motion_group_doc(m) for m in motion_groups]


def _to_motion_group_doc(motion_group):
    return {
        'motionGroupId': motion_group.id,
        'titleNL': motion_group.title_nl,
        'titleFR': motion_group.title_fr,
        'motionLinks': [_to_motion_link_doc(m) for m in motion_group.motions]
    }


def _to_motion_link_doc(motion):
    voting_id = motion.voting_id
    return {
        'motionId': motion.id,
        'agendaSeqNr': motion.sequence_number,
        'voteSeqNr': None if voting_id is None else voting_id.rsplit('_', 1)[-1],
        'titleNL': motion.title_nl,
        'titleFR': motion.title_fr
    }


def _to_motion_read_model(config, publishing_data: PublishingData, p: Plenary, _mg: MotionGroup, m: Motion):
    if m.voting_id is None:
        LOGGER.warning("motion without voting_id: %s", m.id)
        return None
    votes = publishing_data.votes_by_id[m.voting_id]
    if len(votes) == 0:
        LOGGER.warning("no votes found in %s", m.id)
        return None

    yes_votes = to_votes(votes, VoteType.YES, publishing_data.politicians)
    no_votes = to_votes(votes, VoteType.NO, publishing_data.politicians)
    abs_votes = to_votes(votes, VoteType.ABSTENTION, publishing_data.politicians)
    doc_reference = to_doc_reference(config, m.documents_reference, publishing_data.summaries_by_id)
    voting_result = vote_passed(yes_votes, no_votes)

    mdoc = {
        "id": m.id,
        "titleNL": m.title_nl,
        "titleFR": m.title_fr,
        "yesVotes": yes_votes,
        "noVotes": no_votes,
        "absVotes": abs_votes,
        "newDocumentReference": doc_reference,
        "votingDate": p.date,
        "votingResult": voting_result,
    }
    return mdoc


def to_votes(votes: List[Vote], vote_type: VoteType, politicians: Politicians):
    if len(votes) == 0:
        raise Exception("I don't expect to be called without votes")
    vdoc = {}

    votes_with_type = [v for v in votes if v.vote_type == vote_type]
    count_votes_with_type = len(votes_with_type)
    vdoc["nrOfVotes"] = count_votes_with_type
    vdoc["votePercentage"] = 0 if len(votes) == 0 else 100.0 * vdoc["nrOfVotes"] / len(votes)

    votes_by_party = defaultdict(int)
    for vote in votes_with_type:
        votes_by_party[vote.politician.party] += 1

    vdoc["partyVotes"] = []
    for party, count in votes_by_party.items():
        vdoc["partyVotes"].append({
            'partyName': party,
            'numberOfVotes': count,
            'votePercentage': 100.0 * count / len(votes)
        })

    return vdoc


def to_doc_reference(config, spec, summaries_by_id):
    if not spec:
        return None

    pattern = re.compile("^(\\d+)/(\\d+)(-\\d+)?$")

    match = pattern.match(spec)

    if match is None:
        return None
        # TODO: look into this scenario
        raise Exception("unknown ref spec", spec)

    doc_main_nr = int(match.group(1))
    range_min = int(match.group(2))
    range_max = int(match.group(3)[1:]) if match.group(3) else range_min

    if range_min > range_max:
        raise Exception(f"Invalid range in spec {spec}")
    if range_max - range_min > 20:
        raise Exception("Range size over 20. Could be a typo")

    refdoc = {
        "spec": spec,
        "documentMainUrl": (
            "https://www.dekamer.be/kvvcr/showpage.cfm?section=/flwb&language=nl&cfm=/site/wwwcfm/flwb/flwbn.cfm?lang=N&legislat="
            f"{config.legislature}&dossierID={doc_main_nr:04d}"),
        "subDocuments": [
            to_subdoc(config, doc_main_nr, doc_sub_nr, summaries_by_id)
            for doc_sub_nr in range(range_min, range_max + 1)
        ]}

    # TODO: previous solutions somewhere filtered out motions with multiple subdocuments because
    # we didn't know how to render them. Figure out where that was and apply here
    return refdoc


def to_subdoc(config, doc_main_nr, doc_sub_nr, summaries_by_id):
    if summaries_by_id is None:
        summaries_by_id = {}
    document_id = f"{config.legislature}K{doc_main_nr:04d}{doc_sub_nr:03d}"
    summary = summaries_by_id.get(document_id, None)
    return {
        'documentNr': doc_main_nr,
        'documentSubNr': doc_sub_nr,
        # TODO: various places construct this url. Merge to 1 code path
        'documentPdfUrl': f"https://www.dekamer.be/FLWB/PDF/{config.legislature}/{doc_main_nr:04d}/{config.legislature}K{doc_main_nr:04d}{doc_sub_nr:03d}.pdf",
        'summaryNL': summary["nl"] if summary else None,
        'summaryFR': summary["fr"] if summary else None
    }


def vote_passed(yes_votes, no_votes):
    # TODO: is a simple majority always enough; Cross check this against result found in plenary reports
    return yes_votes["nrOfVotes"] > no_votes["nrOfVotes"]


def create_elastic_client(config: Config, env: Environments):
    if env == Environments.LOCAL:
        return Elasticsearch("http://localhost:9200")

    if env == Environments.DEV:
        raise Exception("TODO: setup dev environment")

    if env == Environments.PROD:
        auth = os.environ.get("WDDP_PROD_ES_AUTH", None)
        if auth is None:
            raise Exception("Missing WDDP_PROD_ES_AUTH environment variable")
        host = config.elastic_host
        return Elasticsearch(f"https://{auth}@{host}:443")

    raise Exception(f"missing elasticsearch configuration for env {env}")
