import json
from collections import defaultdict

from transparentdemocracy.config import CONFIG


def publish():
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

    for plenary in plenaries:
        for mg in plenary["motion_groups"]:
            motions = [to_motion_read_model(plenary, mg, m, votes_by_id, politicians_by_id) for m in mg["motions"]]
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

            publish_motion(doc)

def publish_motion(doc):
    pass # TODO


def to_motion_read_model(p, mg, m, votes_by_id, politicians_by_id):
    if m["voting_id"] is None:
        return None  # TODO log a warning
    votes = votes_by_id[m["voting_id"]]
    if len(votes) == 0:
        return None  # TODO log a warning

    mdoc = dict()
    mdoc["id"] = m["id"]
    mdoc["titleNL"] = m["title_nl"]
    mdoc["titleFR"] = m["title_fr"]
    yes_votes = to_votes(votes, "YES", politicians_by_id)
    mdoc["yesVotes"] = yes_votes
    no_votes = to_votes(votes, "NO", politicians_by_id)
    mdoc["noVotes"] = no_votes
    mdoc["absVotes"] = to_votes(votes, "ABSTENTION", politicians_by_id)
    mdoc["newDocumentReference"] = to_doc_reference(m["documents_reference"])
    mdoc["votingDate"] = p["date"]
    mdoc["votingResult"] = vote_passed(yes_votes, no_votes)
    return mdoc


def to_votes(votes, vote_type, politicians_by_id):
    if len(votes) == 0:
        raise Exception("I don't expect to be called without votes")
    vdoc = dict()

    count_votes_with_type = len([v for v in votes if v["vote_type"] == vote_type])
    vdoc["nrOfVotes"] = count_votes_with_type
    vdoc["votePercentage"] = 0 if len(votes) == 0 else 100.0 * vdoc["nrOfVotes"] / len(votes)

    votes_by_party = defaultdict(int)
    for v in votes:
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


def to_doc_reference(spec):
    return None # TODO
    if spec is None:
        refdoc = dict()
        refdoc["spec"] = spec
        refdoc["documentMainUrl"] = "TODO"
        refdoc["subDocuments"] = []  # TODO
        return refdoc
    return None


def vote_passed(yes_votes, no_votes):
    # TODO: is a simple majority always enough; Cross check this against result found in plenary reports
    return yes_votes["nrOfVotes"] > no_votes["nrOfVotes"]


if __name__ == "__main__":
    publish()
