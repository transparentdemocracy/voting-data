import json
import os
from typing import Dict, List

from transparentdemocracy.model import Plenary, VotingReport, Proposal, Vote


class PlenaryJsonStorage:

    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def save(self, plenary: Plenary, voting_reports: List[VotingReport], is_final: bool):
        print("writing plenary to json: %s" % plenary.id)
        plenary_json_path = self.plenary_json_path(plenary.id)
        final_marker_json_path = self._final_marker(plenary.id)
        votes_json_path = os.path.join(self.output_dir, f"plenary-{plenary.id[3:]}-votes.json")

        os.makedirs(os.path.dirname(plenary_json_path), exist_ok=True)

        with open(plenary_json_path, 'w') as f:
            json.dump(self.plenary_to_json(plenary), f, indent=2)

        with open(votes_json_path, 'w') as f:
            json.dump(self.voting_reports_to_json(voting_reports), f, indent=2)

        if is_final:
            with open(final_marker_json_path, 'a'):
                pass

    def _final_marker(self, plenary_id):
        return self.plenary_json_path(plenary_id) + ".final"

    def plenary_json_path(self, plenary_id):
        return os.path.join(self.output_dir, f"plenary-{plenary_id[3:]}.json")

    def plenary_to_json(self, plenary: Plenary) -> Dict:
        return {
            'id': plenary.id,
            'number': plenary.number,
            'date': plenary.date.isoformat(),
            'legislature': plenary.legislature,
            'pdf_report_url': plenary.pdf_report_url,
            'html_report_url': plenary.html_report_url,
            'proposal_discussions': self.proposal_discussions_to_json(plenary.proposal_discussions),
            # 'motion_groups': plenary.motion_groups
        }

    def proposal_discussions_to_json(self, proposal_discussions) -> List[Dict]:
        return [self.proposal_discussion_to_json(discussion) for discussion in proposal_discussions]

    def proposal_discussion_to_json(self, proposal_discussion) -> Dict:
        return {
            "id": proposal_discussion.id,
            "plenary_id": proposal_discussion.plenary_id,
            "plenary_agenda_item_number": proposal_discussion.plenary_agenda_item_number,
            "description_nl": proposal_discussion.description_nl,
            "description_fr": proposal_discussion.description_fr,
            "proposals": self.proposals_to_json(proposal_discussion.proposals)
        }

    def voting_reports_to_json(self, voting_reports: List[VotingReport]) -> Dict:
        return {
            "voting_reports": [self.voting_report_to_json(report) for report in voting_reports]
        }

    def proposals_to_json(self, proposals: List[Proposal]):
        return [self.proposal_to_json(proposal) for proposal in proposals]

    def proposal_to_json(self, proposal: Proposal):
        return {
            "id": proposal.id,
            "documents_reference": proposal.documents_reference,
            "title_nl": proposal.title_nl,
            "title_fr": proposal.title_fr,
        }

    def voting_report_to_json(self, voting_report: VotingReport) -> Dict:
        return {
            "voting_id": voting_report.voting_id,
            "parties": {k: self.votes_to_json(v) for k, v in voting_report.parties.items()},
        }

    def plenary_json_exists(self, plenary_id):
        return os.path.exists(self.plenary_json_path(plenary_id))

    def is_final(self, plenary_id):
        return os.path.exists(self._final_marker(plenary_id))

    def votes_to_json(self, votes: list[Vote]):
        return [
            {
                "voter_id": vote.politician.id,
                "voter_name": vote.politician.full_name,
                "vote_type": vote.vote_type.value
            }
            for vote in votes
        ]
