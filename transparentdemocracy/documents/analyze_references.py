from typing import List, Generator

from transparentdemocracy.documents.references import parse_document_reference
from transparentdemocracy.model import Plenary
from transparentdemocracy.plenaries.serialization import load_plenaries


def analyse_document_references():
    plenaries = load_plenaries()

    collected_doc_refs = collect_document_references(plenaries)
    doc_refs_and_locations = dict(
        (lambda d: [(d[k].append(v) or d) for k, v in collected_doc_refs] and d)(defaultdict(list)))

    doc_refs = []
    for doc_ref_spec in doc_refs_and_locations.keys():
        result = parse_document_reference(doc_ref_spec)

        doc_refs.append(result)

    bad_refs = [d for d in doc_refs if d.document_reference is None]
    print("Bad references:")
    for bad_ref in bad_refs:
        print(f"   {bad_ref.all_documents_reference}")


def collect_document_references(plenaries: List[Plenary]) -> Generator[str, str, None]:
    for plenary in plenaries:
        for discussion in plenary.proposal_discussions:
            for proposal in discussion.proposals:
                if proposal.documents_reference:
                    yield proposal.documents_reference, proposal.id
        for motion_group in plenary.motion_groups:
            if motion_group.documents_reference:
                yield motion_group.documents_reference, motion_group.id
            for motion in motion_group.motions:
                if motion.documents_reference:
                    yield motion.documents_reference, motion.id
