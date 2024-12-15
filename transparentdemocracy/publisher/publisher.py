import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import List

from elasticsearch.client import Elasticsearch

from transparentdemocracy.config import CONFIG

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


class MotionsElasticRepository:
    def __init__(self, elastic_client):
        self.es = elastic_client
        self.create_index()

    def create_index(self):
        response = self.es.indices.create(
            index="motions",
            body=MOTIONS_MAPPING,
            ignore=400,
        )
        print(response)

    def upsert_motion_group(self, publishing_data, plenary, mg):
        # TODO: parameter object 'PublishData'
        motions = [_to_motion_read_model(publishing_data, plenary, mg, m) for m in mg["motions"]]
        motions = [m for m in motions if m is not None]
        if len(motions) == 0:
            logging.warning("no motions in group %s", mg["id"])
            return

        doc = {
            'id': mg["id"],
            'legislature': plenary["legislature"],
            'plenaryNr': plenary["number"],
            'titleNL': mg["title_nl"],
            'titleFR': mg["title_fr"],
            'motions': [m for m in motions if m is not None],
            'votingDate': plenary["date"]
        }

        response = self.es.index(index="motions", id=doc["id"], body=doc)
        print(response)


class PlenariesElasticRepository:
    def __init__(self, elastic_client: Elasticsearch):
        self.es = elastic_client
        self.create_index()

    def create_index(self):
        response = self.es.indices.create(
            index="plenaries",
            body=PLENARIES_MAPPING,
            ignore=400,
        )
        print(response)

    def upsert_plenary(self, plenary):
        doc = {
            'id': plenary["id"],
            'title': plenary["date"],
            'legislature': plenary["legislature"],
            'date': plenary["date"],
            'pdfReportUrl': plenary["pdf_report_url"],
            'htmlReportUrl': plenary["html_report_url"],
            'motionGroups': _to_motion_groups_doc(plenary["motion_groups"]),
            'is_final': False  # TODO: make sure this has the correct value
        }

        response = self.es.index(index="plenaries", id=doc["id"], body=doc)
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

        es_result = self.es.search(index="plenaries", body=query, size=1000)
        es_status = dict([(hit["_id"], hit["_source"].get("is_final", False)) for hit in es_result["hits"]["hits"]])
        return dict([(plenary_id, es_status.get(plenary_id, None)) for plenary_id in plenary_ids])


class Publisher():
    def __init__(self, plenary_repo, motions_repo, politicians_by_id, summaries_by_id, votes_by_id):
        self.plenary_repo = plenary_repo
        self.motions_repo = motions_repo
        self.publishing_data = PublishingData(politicians_by_id, summaries_by_id, votes_by_id)

    def publish(self, plenaries):
        self._publish_motions(plenaries)
        self._publish_plenaries(plenaries)

    def _publish_motions(self, plenaries):
        for plenary in plenaries:
            for mg in plenary["motion_groups"]:
                self.motions_repo.upsert_motion_group(self.publishing_data, plenary, mg)

    def _publish_plenaries(self, plenaries):
        for plenary in plenaries:
            self.plenary_repo.upsert_plenary(plenary)


def _to_motion_groups_doc(motion_groups):
    return [_to_motion_group_doc(m) for m in motion_groups]


def _to_motion_group_doc(motion_group):
    return {
        'motionGroupId': motion_group["id"],
        'titleNL': motion_group["title_nl"],
        'titleFR': motion_group["title_fr"],
        'motionLinks': [_to_motion_link_doc(m) for m in motion_group["motions"]]
    }


def _to_motion_link_doc(motion):
    voting_id = motion["voting_id"]
    return {
        'motionId': motion["id"],
        'agendaSeqNr': motion["sequence_number"],
        'voteSeqNr': None if voting_id is None else voting_id.rsplit('_', 1)[-1],
        'titleNL': motion["title_nl"],
        'titleFR': motion["title_fr"]
    }


def _to_motion_read_model(publishing_data, p, _mg, m):
    if m["voting_id"] is None:
        LOGGER.warning("motion without voting_id: %s", m["id"])
        return None
    votes = publishing_data.votes_by_id[m["voting_id"]]
    if len(votes) == 0:
        LOGGER.warning("no votes found in %s", m["id"])
        return None

    yes_votes = to_votes(votes, "YES", publishing_data.politicians_by_id)
    no_votes = to_votes(votes, "NO", publishing_data.politicians_by_id)
    abs_votes = to_votes(votes, "ABSTENTION", publishing_data.politicians_by_id)
    doc_reference = to_doc_reference(m["documents_reference"], publishing_data.summaries_by_id)
    voting_result = vote_passed(yes_votes, no_votes)

    mdoc = {
        "id": m["id"],
        "titleNL": m["title_nl"],
        "titleFR": m["title_fr"],
        "yesVotes": yes_votes,
        "noVotes": no_votes,
        "absVotes": abs_votes,
        "newDocumentReference": doc_reference,
        "votingDate": p["date"],
        "votingResult": voting_result,
    }
    return mdoc


def to_votes(votes, vote_type, politicians_by_id):
    if len(votes) == 0:
        raise Exception("I don't expect to be called without votes")
    vdoc = {}

    votes_with_type = [v for v in votes if v["vote_type"] == vote_type]
    count_votes_with_type = len(votes_with_type)
    vdoc["nrOfVotes"] = count_votes_with_type
    vdoc["votePercentage"] = 0 if len(votes) == 0 else 100.0 * vdoc["nrOfVotes"] / len(votes)

    votes_by_party = defaultdict(int)
    for v in votes_with_type:
        voter = politicians_by_id[v["politician_id"]]
        party = voter["party"]
        votes_by_party[party] += 1

    vdoc["partyVotes"] = []
    for party, count in votes_by_party.items():
        vdoc["partyVotes"].append({
            'partyName': party,
            'numberOfVotes': count,
            'votePercentage': 100.0 * count / len(votes)
        })

    return vdoc


def to_doc_reference(spec, summaries_by_id=None):
    if not summaries_by_id:
        summaries_by_id = {}
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
            f"{CONFIG.legislature}&dossierID={doc_main_nr:04d}"),
        "subDocuments": [
            to_subdoc(doc_main_nr, doc_sub_nr, summaries_by_id)
            for doc_sub_nr in range(range_min, range_max + 1)
        ]}

    # TODO: previous solutions somewhere filtered out motions with multiple subdocuments because
    # we didn't know how to render them. Figure out where that was and apply here
    return refdoc


def to_subdoc(doc_main_nr, doc_sub_nr, summaries_by_id=None):
    if summaries_by_id is None:
        summaries_by_id = {}
    document_id = f"{doc_main_nr:04d}/{doc_sub_nr:03d}"
    summary = summaries_by_id.get(document_id, None)
    return {
        'documentNr': doc_main_nr,
        'documentSubNr': doc_sub_nr,
        'documentPdfUrl': f"https://www.dekamer.be/FLWB/PDF/{CONFIG.legislature}/{doc_main_nr:04d}/{CONFIG.legislature}K{doc_main_nr:04d}{doc_sub_nr:03d}.pdf",
        'summaryNL': summary["summary_nl"] if summary else None,
        'summaryFR': summary["summary_fr"] if summary else None
    }


def vote_passed(yes_votes, no_votes):
    # TODO: is a simple majority always enough; Cross check this against result found in plenary reports
    return yes_votes["nrOfVotes"] > no_votes["nrOfVotes"]


@dataclass
class PublishingData:
    # TODO typing info
    politicians_by_id: dict
    summaries_by_id: dict
    votes_by_id: dict
