import json
import logging
import os
import re
from collections import defaultdict

from elasticsearch import Elasticsearch

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


class ElasticRepo:
    def __init__(self):
        # Local, no auth required
        # self.es = Elasticsearch("http://localhost:9200")

        # Bonsai
        auth = os.environ["ES_AUTH"]
        self.es = Elasticsearch("https://%s@transparent-democrac-6644447145.eu-west-1.bonsaisearch.net:443" % (auth))

        self.create_indices()

    def create_indices(self):
        self.create_index("motions", MOTIONS_MAPPING)
        self.create_index("plenaries", PLENARIES_MAPPING)

    def create_index(self, index_name, mapping):
        response = self.es.indices.create(
            index=index_name,
            body=mapping,
            ignore=400,
        )
        print(response)

    def publish_motion(self, doc):
        response = self.es.index(index="motions", id=doc["id"], body=doc)
        print(response)

    def publish_plenary(self, doc):
        response = self.es.index(index="plenaries", id=doc["id"], body=doc)
        print(response)


class Publisher():
    def __init__(self, repo, plenaries, votes_by_id, politicians_by_id, summaries_by_id):
        self.repo = repo
        self.plenaries = plenaries
        self.votes_by_id = votes_by_id
        self.politicians_by_id = politicians_by_id
        self.summaries_by_id = summaries_by_id

    def publish(self):
        self.publish_motions()
        self.publish_plenaries()

    def publish_motions(self):
        for plenary in self.plenaries:
            for mg in plenary["motion_groups"]:
                motions = [self.to_motion_read_model(plenary, mg, m) for m in mg["motions"]]
                motions = [m for m in motions if m is not None]
                if len(motions) == 0:
                    logging.warning("no motions in group %s", mg["id"])
                    continue
                doc = {
                    'id': mg["id"],
                    'legislature': plenary["legislature"],
                    'plenaryNr': plenary["number"],
                    'titleNL': mg["title_nl"],
                    'titleFR': mg["title_fr"],
                    'motions': [m for m in motions if m is not None],
                    'votingDate': plenary["date"]
                }

                self.repo.publish_motion(doc)

    def publish_plenaries(self):
        for plenary in self.plenaries:
            doc = dict(
                id=plenary["id"],
                title=plenary["date"],
                legislature=plenary["legislature"],
                date=plenary["date"],
                pdfReportUrl=plenary["pdf_report_url"],
                htmlReportUrl=plenary["html_report_url"],
                motionGroups=self.to_motion_groups_doc(plenary["motion_groups"])
            )

            self.repo.publish_plenary(doc)

    def to_motion_groups_doc(self, motion_groups):
        return [self.to_motion_group_doc(m) for m in motion_groups]

    def to_motion_group_doc(self, motion_group):
        return {
            'motionGroupId': motion_group["id"],
            'titleNL': motion_group["title_nl"],
            'titleFR': motion_group["title_fr"],
            'motionLinks': [self.to_motion_link_doc(m) for m in motion_group["motions"]]
        }

    def to_motion_link_doc(self, motion):
        voting_id = motion["voting_id"]
        return {
            'motionId': motion["id"],
            'agendaSeqNr': motion["sequence_number"],
            'voteSeqNr': None if voting_id is None else voting_id.rsplit('_', 1)[-1],
            'titleNL': motion["title_nl"],
            'titleFR': motion["title_fr"]
        }

    def to_motion_read_model(self, p, _mg, m):
        if m["voting_id"] is None:
            LOGGER.warning("motion without voting_id: %s", m["id"])
            return None
        votes = self.votes_by_id[m["voting_id"]]
        if len(votes) == 0:
            LOGGER.warning("no votes found in %s", m["id"])
            return None

        yes_votes = to_votes(votes, "YES", self.politicians_by_id)
        no_votes = to_votes(votes, "NO", self.politicians_by_id)
        abs_votes = to_votes(votes, "ABSTENTION", self.politicians_by_id)
        doc_reference = to_doc_reference(m["documents_reference"], self.summaries_by_id)
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
        # TODO: handle these
        # raise Exception("unknown ref spec", spec)
        return None

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
        'documentPdfUrl': f"https://www.dekamer.be/FLWB/PDF/{CONFIG.legislature}/{doc_main_nr:04d}/55K{doc_main_nr:04d}{doc_sub_nr:03d}.pdf",
        'summaryNL': summary["summary_nl"] if summary else None,
        'summaryFR': summary["summary_fr"] if summary else None
    }


def publish():
    repo = ElasticRepo()

    with open(CONFIG.plenary_json_output_path("plenaries.json"), 'r', encoding="utf-8") as plenary_file:
        plenaries = json.load(plenary_file)

    with open(CONFIG.plenary_json_output_path("votes.json"), 'r', encoding="utf-8") as votes_file:
        votes = json.load(votes_file)

    with open(CONFIG.politicians_json_output_path("politicians.json"), 'r', encoding="utf-8") as politicians_file:
        politicians = json.load(politicians_file)

    politicians_by_id = {p["id"]: p for p in politicians}

    votes_by_id = defaultdict(list)
    for vote in votes:
        votes_by_id[vote["voting_id"]].append(vote)

    with open(CONFIG.documents_summaries_json_output_path(), 'r', encoding="utf-8") as summaries_file:
        summaries = json.load(summaries_file)
        summaries_by_id = {s["document_id"]: s for s in summaries}

    publisher = Publisher(repo, plenaries, votes_by_id, politicians_by_id, summaries_by_id)

    publisher.publish()


def vote_passed(yes_votes, no_votes):
    # TODO: is a simple majority always enough; Cross check this against result found in plenary reports
    return yes_votes["nrOfVotes"] > no_votes["nrOfVotes"]


if __name__ == "__main__":
    publish()
