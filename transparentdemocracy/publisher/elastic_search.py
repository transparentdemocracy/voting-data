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
from transparentdemocracy.model import VoteType, Motion, MotionGroup, Plenary, VotingReport
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
    voting_reports: dict[str, VotingReport]


class MotionElasticRepository:
    """
    A repository for CRUD actions against our ElasticSearch backend for motion groups and motions.
    The ElasticSearch index we query against here is called `motions` but stores motion groups *and* within each of
    those, all motions within that motion group.
    """
    def __init__(self, config: Config, es_client: Elasticsearch):
        self.config = config
        self.elastic_search = es_client
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
        doc = self._motion_group_to_dict(publishing_data, plenary, motion_group)
        if doc is None:
            return
        response = self.elastic_search.index(index="motions", id=doc["id"], body=doc)
        print(response)

    def _motion_group_to_dict(self, publishing_data, plenary, motion_group):
        motions = [
            _to_motion_read_model(self.config, publishing_data, plenary, motion_group, motion)
            for motion in motion_group.motions
            if motion is not None
        ]
        if len(motions) == 0:
            logging.warning("No motions in motion group with ID %s.", motion_group.id)
            return None

        motion_group_doc = {
            'id': motion_group.id,
            'legislature': plenary.legislature,
            'plenaryNr': plenary.number,
            'titleNL': motion_group.title_nl,
            'titleFR': motion_group.title_fr,
            'motions': motions,
            'votingDate': plenary.date.isoformat()
        }

        return motion_group_doc

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
    def __init__(self, config: Config, elastic_search: Elasticsearch):
        self.elastic_search = elastic_search
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


class Publisher:
    def __init__(self,
                 config: Config,
                 plenary_repo: PlenaryElasticRepository,
                 motions_repo: MotionElasticRepository,
                 politicians: Politicians,
                 summaries_by_id,
                 voting_reports: dict[str, VotingReport]):
        self.config = config
        self.plenary_repo = plenary_repo
        self.motions_repo = motions_repo
        self.publishing_data = PublishingData(politicians, summaries_by_id, voting_reports)

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
    voting_report = publishing_data.voting_reports[m.voting_id]
    if voting_report is None or voting_report.total_votes == 0:
        LOGGER.warning("no votes found in %s", m.id)
        return None

    doc_reference = to_doc_reference(config, m.documents_reference, publishing_data.summaries_by_id)

    yes_votes = to_votes(voting_report, VoteType.YES)
    no_votes = to_votes(voting_report, VoteType.NO)
    abs_votes = to_votes(voting_report, VoteType.ABSTENTION)
    voting_result = voting_report.total_yes_votes() > voting_report.total_no_votes()

    mdoc = {
        "id": m.id,
        "titleNL": m.title_nl,
        "titleFR": m.title_fr,
        "yesVotes": yes_votes,
        "noVotes": no_votes,
        "absVotes": abs_votes,
        "newDocumentReference": doc_reference,
        "votingDate": p.date.isoformat(),
        "votingResult": voting_result,
    }
    return mdoc


def to_votes(voting_report: VotingReport, vote_type: VoteType):
    vdoc = {}

    number_of_votes = voting_report.count_votes_by_type(vote_type)
    vdoc["nrOfVotes"] = number_of_votes
    vdoc["votePercentage"] = 0 if voting_report.total_votes() == 0 else (100.0 * number_of_votes / voting_report.total_votes())

    votes_by_party = defaultdict(int)
    for party, votes in voting_report.parties.items():
        votes_by_party[party] = len([vote for vote in votes if vote.vote_type == vote_type])

    vdoc["partyVotes"] = []
    for party, votes in voting_report.parties.items():
        vdoc["partyVotes"].append({
            'partyName': party,
            'numberOfVotes': votes_by_party[party],
            'votePercentage': 100.0 * votes_by_party[party] / voting_report.total_votes()
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
