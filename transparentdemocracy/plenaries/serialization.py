import json
import os
from datetime import datetime
from typing import List, Dict

import bs4
from bs4 import Tag

from transparentdemocracy import CONFIG
from transparentdemocracy.model import Motion, Plenary, ProposalDiscussion, Proposal, Vote, MotionGroup, \
    DocumentsReference
from transparentdemocracy.plenaries.extraction import extract_from_html_plenary_reports
from transparentdemocracy.plenaries.json_serde import PlenaryEncoder
from transparentdemocracy.plenaries.motion_document_proposal_linker import link_motions_with_proposals


class JsonSerializer:
    def __init__(self, output_path=None):
        self.plenary_output_json_path = CONFIG.plenary_json_output_path() if output_path is None else output_path
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

    def serialize_documents_reference_objects(self, documents_reference_objects):
        self._serialize_list([
            {
                'all_documents_reference': document.all_documents_reference,
                'document_reference': document.document_reference,
                'main_sub_document_reference': document.main_sub_document_reference,
                'sub_document_references': document.sub_document_references,
                'proposal_discussion_ids': document.proposal_discussion_ids,
                'proposal_ids': document.proposal_ids,
                'summary_nl': document.summary_nl,
                'summary_fr': document.summary_fr,
                'info_url': document.info_url,
                'sub_document_pdf_urls': document.sub_document_pdf_urls
            }
            for document in documents_reference_objects
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


def serialize(plenaries: List[Plenary], votes: List[Vote], documents_reference_objects: List[DocumentsReference]) -> None:
    write_plenaries_json(plenaries)
    write_votes_json(votes)
    write_documents_json(documents_reference_objects)


def write_plenaries_json(plenaries=None):
    if plenaries is None:
        tmp_plenaries, _votes, _problems = extract_from_html_plenary_reports()
        plenaries, _documents_reference_objects, _link_problems = link_motions_with_proposals(tmp_plenaries)
    JsonSerializer().serialize_plenaries(plenaries)


def write_votes_json(votes=None):
    if votes is None:
        _plenaries, votes, _problems = extract_from_html_plenary_reports()
    JsonSerializer().serialize_votes(votes)


def write_documents_json(documents_reference_objects=None):
    if documents_reference_objects is None:
        plenaries, _votes, _problems = extract_from_html_plenary_reports()
        plenaries, documents_reference_objects, _link_problems = link_motions_with_proposals(
            plenaries)
    JsonSerializer().serialize_documents_reference_objects(documents_reference_objects)


# JSON to object serialization:
# -----------------------------
def load_plenaries():
    path = os.path.join(CONFIG.plenary_json_output_path(), "plenaries.json")
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
        proposal_discussions=[_json_to_proposal_discussion(
            pd) for pd in data['proposal_discussions']],
        motion_groups=[_json_to_motion_group(
            mg) for mg in data['motion_groups']],
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


def main():
    write_plenaries_json()
    # write_votes_json()


if __name__ == "__main__":
    main()
