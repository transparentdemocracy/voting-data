import json
import os
from datetime import datetime
from typing import List, Dict

import bs4
from bs4 import Tag

from transparentdemocracy.config import Config
from transparentdemocracy.model import Motion, Plenary, ProposalDiscussion, Proposal, Vote, MotionGroup
from transparentdemocracy.plenaries.json_serde import PlenaryEncoder


class JsonSerializer:
    def __init__(self, config: Config, output_path=None):
        self.plenary_output_json_path = config.plenary_json_output_path() if output_path is None else output_path
        os.makedirs(self.plenary_output_json_path, exist_ok=True)

    def serialize_plenaries(self, plenaries: List[Plenary]) -> None:
        self._serialize_plenaries(plenaries, "plenaries.json")

    def serialize_votes(self, votes: List[Vote]) -> None:
        self._serialize_list(
            [
                {
                    'voting_id': v.voting_id,
                    'vote_type': v.vote_type.value,
                    'politician_id': str(v.politician.id)
                }
                for v in votes],
            "votes.json")

    def serialize_documents_reference_objects(self, legislature, documents_references):
        self._serialize_list([
            {
                'all_documents_reference': doc_ref.all_documents_reference,
                'document_reference': doc_ref.document_reference,
                'main_sub_document_reference': doc_ref.main_sub_document_reference,
                'sub_document_references': doc_ref.sub_document_references,
                'proposal_discussion_ids': doc_ref.proposal_discussion_ids,
                'proposal_ids': doc_ref.proposal_ids,
                'summary_nl': doc_ref.summary_nl,
                'summary_fr': doc_ref.summary_fr,
                'info_url': doc_ref.info_url(legislature),
                'sub_document_pdf_urls': doc_ref.sub_document_pdf_urls(legislature)
            }
            for doc_ref in documents_references
        ], "documents.json")

    def _serialize_plenaries(self, plenaries: List[Plenary], output_path: str) -> None:
        list_json = json.dumps([self._plenary_to_dict(p) for p in plenaries], indent=2, cls=PlenaryEncoder)
        with open(os.path.join(self.plenary_output_json_path, output_path), "w", encoding="utf-8") as output_file:
            output_file.write(list_json)

    def _serialize_list(self, some_list: List, output_path: str) -> None:
        list_json = json.dumps(some_list, indent=2, default=lambda o: o.__dict__)
        with open(os.path.join(self.plenary_output_json_path, output_path), "w", encoding="utf-8") as output_file:
            output_file.write(list_json)

    def _plenary_to_dict(self, plenary: Plenary) -> Dict:
        return {
            'id': plenary.id,
            'number': plenary.number,
            'date': plenary.date.isoformat(),
            'legislature': plenary.legislature,
            'pdf_report_url': plenary.pdf_report_url,
            'html_report_url': plenary.html_report_url,
            'proposal_discussions': plenary.proposal_discussions,
            'motion_groups': plenary.motion_groups
        }


def write_plenaries_json(config: Config, plenaries: List[Plenary]):
    """
    Write the plenaries as json files
    """
    JsonSerializer(config).serialize_plenaries(plenaries)


def write_votes_json(config: Config, votes: List[Vote]):
    """
    Extract voting behavior of the politicians from the plenary report and write it to a JSON output format.
    This can also be run with the command `td plenaries votes-json`.
    """
    JsonSerializer(config).serialize_votes(votes)


# JSON to object serialization:
# -----------------------------
def load_plenaries(config):
    path = os.path.join(config.plenary_json_output_path(), "plenaries.json")
    with open(path, 'r', encoding="utf-8") as fp:
        data = json.load(fp)
    return [_json_to_plenary(p) for p in data]


def _json_to_plenary(data):
    return Plenary(
        id=data['id'],
        number=data['number'],
        date=datetime.fromisoformat(data['date']),
        legislature=data['legislature'],
        pdf_report_url=data['pdf_report_url'],
        html_report_url=data['html_report_url'],
        proposal_discussions=[_json_to_proposal_discussion(pd) for pd in data['proposal_discussions']],
        motion_groups=[_json_to_motion_group(mg) for mg in data['motion_groups']],
    )


def _json_to_proposal_discussion(data):
    description_nl_tags = parse_tags(data.get('description_nl_tags', []))
    description_fr_tags = parse_tags(data.get('description_fr_tags', []))

    return ProposalDiscussion(
        id=data['id'],
        plenary_id=data['plenary_id'],
        plenary_agenda_item_number=data['plenary_agenda_item_number'],
        description_nl=data['description_nl'],
        description_nl_tags=description_nl_tags,
        description_fr=data['description_fr'],
        description_fr_tags=description_fr_tags,
        proposals=[_json_to_proposal(p) for p in data['proposals']],
    )


def parse_tags(html_snippets) -> List[Tag]:
    if html_snippets:
        return bs4.BeautifulSoup("".join(html_snippets)).contents
    return []


def _json_to_proposal(data):
    return Proposal(
        id=data['id'],
        documents_reference=data['documents_reference'],
        title_nl=data['title_nl'],
        title_fr=data['title_fr']
    )


def _json_to_motion_group(data):
    return MotionGroup(
        id=data['id'],
        plenary_agenda_item_number=data['plenary_agenda_item_number'],
        title_nl=data['title_nl'],
        title_fr=data['title_fr'],
        documents_reference=data['documents_reference'],
        motions=[_json_to_motion(m) for m in data['motions']],
    )


def _json_to_motion(data):
    return Motion(
        id=data['id'],
        sequence_number=data['sequence_number'],
        title_nl=data['title_nl'],
        title_fr=data['title_fr'],
        documents_reference=data['documents_reference'],
        voting_id=data['voting_id'],
        cancelled=data['cancelled'],
        description=data['description'],
    )
