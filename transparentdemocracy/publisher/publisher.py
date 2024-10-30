import json
import logging
import re
from collections import defaultdict

from elasticsearch import Elasticsearch

from transparentdemocracy.config import CONFIG

LOGGER = logging.getLogger(__name__)


class ElasticRepo:
    def __init__(self):
        # local dev doesn't use authentication
        API_KEY = "a0ZfajFKSUJfcXpZQ0Z2aksySHc6ZWNXNGZJSElRWHkzTTJiNXVSbHhkdw=="
        self.es = Elasticsearch("http://localhost:9200")
        # self.es = self.es.options(api_key=API_KEY)

    def publish_motion(self, doc):
        response = self.es.index(index="motions", id=doc["id"], body=doc)
        print(response)


class Publisher():
    def __init__(self, repo, plenaries, votes_by_id, politicians_by_id, summaries_by_id):
        self.repo = repo
        self.plenaries = plenaries
        self.votes_by_id = votes_by_id
        self.politicians_by_id = politicians_by_id
        self.summaries_by_id = summaries_by_id

    def publish(self):
        for plenary in self.plenaries:
            for mg in plenary["motion_groups"]:
                motions = [self.to_motion_read_model(plenary, mg, m) for m in mg["motions"]]
                motions = [m for m in motions if m is not None]
                if len(motions) == 0:
                    # TODO logging
                    continue
                doc = dict()
                doc["id"] = mg["id"]
                doc["titleNL"] = mg["title_nl"]
                doc["titleFR"] = mg["title_fr"]
                doc["motions"] = [m for m in motions if m is not None]
                doc["votingDate"] = plenary["date"]

                self.repo.publish_motion(doc)

    def to_motion_read_model(self, p, mg, m):
        if m["voting_id"] is None:
            return None  # TODO log a warning
        votes = self.votes_by_id[m["voting_id"]]
        if len(votes) == 0:
            return None  # TODO log a warning

        mdoc = dict()
        mdoc["id"] = m["id"]
        mdoc["titleNL"] = m["title_nl"]
        mdoc["titleFR"] = m["title_fr"]
        yes_votes = to_votes(votes, "YES", self.politicians_by_id)
        mdoc["yesVotes"] = yes_votes
        no_votes = to_votes(votes, "NO", self.politicians_by_id)
        mdoc["noVotes"] = no_votes
        mdoc["absVotes"] = to_votes(votes, "ABSTENTION", self.politicians_by_id)
        mdoc["newDocumentReference"] = to_doc_reference(m["documents_reference"], self.summaries_by_id)
        mdoc["votingDate"] = p["date"]
        mdoc["votingResult"] = vote_passed(yes_votes, no_votes)
        return mdoc


def to_votes(votes, vote_type, politicians_by_id):
    if len(votes) == 0:
        raise Exception("I don't expect to be called without votes")
    vdoc = dict()

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
        vdoc["partyVotes"].append(dict(
            partyName=party,
            numberOfVotes=count,
            votePercentage=100.0 * count / len(votes)
        ))

    return vdoc


def to_doc_reference(spec, summaries_by_id={}):
    if not spec:
        return None

    pattern = re.compile("^(\\d+)/(\\d+)(-\\d+)?$")

    match = pattern.match(spec)

    if match is None:
        # TODO: handle these
        # raise Exception("unknown ref spec", spec)
        return None

    docMainNr = int(match.group(1))
    rangeMin = int(match.group(2))
    rangeMax = int(match.group(3)[1:]) if match.group(3) else rangeMin

    if rangeMin > rangeMax:
        raise Exception("Invalid range in spec %s" % (spec))
    if rangeMax - rangeMin > 20:
        raise Exception("Range size over 20. Could be a typo")

    refdoc = dict()
    refdoc["spec"] = spec
    refdoc["documentMainUrl"] = (
        ("https://www.dekamer.be/kvvcr/showpage.cfm?section=/flwb&language=nl&cfm=/site/wwwcfm/flwb/flwbn.cfm?lang=N&legislat=55&dossierID=%04d") % (docMainNr))

    # TODO: previous solutions somewhere filtered out motions with multiple subdocuments because
    # we didn't know how to render them. Figure out where that was and apply here
    refdoc["subDocuments"] = [
        to_subdoc(docMainNr, docSubNr, summaries_by_id)
        for docSubNr in range(rangeMin, rangeMax + 1)
    ]
    return refdoc


def to_subdoc(docMainNr, docSubNr, summaries_by_id={}):
    document_id = "%04d/%03d" % (docMainNr, docSubNr)
    summary = summaries_by_id.get(document_id, None)
    return dict(documentNr=docMainNr,
                documentSubNr=docSubNr,
                documentPdfUrl="https://www.dekamer.be/FLWB/PDF/55/%04d/55K%04d%03d.pdf" % (docMainNr, docMainNr, docSubNr),
                summaryNL=summary["summary_nl"] if summary else None,
                summaryFR=summary["summary_fr"] if summary else None)


def publish():
    repo = ElasticRepo()

    with open(CONFIG.plenary_json_output_path("plenaries.json")) as plenary_file:
        plenaries = json.load(plenary_file)

    with open(CONFIG.plenary_json_output_path("votes.json")) as votes_file:
        votes = json.load(votes_file)

    with open(CONFIG.resolve("output", "politician", "politicians.json")) as politicians_file:
        politicians = json.load(politicians_file)

    politicians_by_id = dict([(p["id"], p) for p in politicians])

    votes_by_id = defaultdict(list)
    for vote in votes:
        votes_by_id[vote["voting_id"]].append(vote)

    with open(CONFIG.documents_summaries_json_output_path()) as summaries_file:
        summaries = json.load(summaries_file)
        summaries_by_id = dict([(s["document_id"], s) for s in summaries])

    publisher = Publisher(repo, plenaries, votes_by_id, politicians_by_id, summaries_by_id)

    publisher.publish()


def vote_passed(yes_votes, no_votes):
    # TODO: is a simple majority always enough; Cross check this against result found in plenary reports
    return yes_votes["nrOfVotes"] > no_votes["nrOfVotes"]


if __name__ == "__main__":
    publish()
