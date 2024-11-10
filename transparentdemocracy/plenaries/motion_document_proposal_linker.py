"""
Link motion groups and motions with proposal discussions and proposal, using the document references mentioned on each
of these objects.

# Why

This allows to easily display the votes of politicians (stored in our motions objects)
and what they were actually voting for (stored in our proposals objects).

# Why here, not during extraction

The objects to be linked have been extracted from plenary session reports.
Motions can appear, however, also in later plenary sessions than the one in which the proposal has been presented in
parliament.
Next to that, this linking of objects is not strictly part of the extraction of objects from the session reports itself.
Therefore, we solve this problem here, in a post-processing task immediately after the extraction task.
"""
import enum
import os
from dataclasses import dataclass
from typing import List, Tuple

from tqdm.auto import tqdm

from transparentdemocracy.documents.references import parse_document_reference
from transparentdemocracy.model import Plenary, ProposalDiscussion, MotionGroup, Proposal, Motion, DocumentsReference


class LinkProblemType(enum.Enum):
    pass  # 2 existing problem types resolved.


@dataclass
class LinkProblem:
    report_file_name: str
    problem_type: LinkProblemType


def link_motions_with_proposals(plenaries: List[Plenary]) -> Tuple[List[Plenary], List[DocumentsReference], List[LinkProblem]]:
    """
    Link motion groups and motions with proposal discussions and proposals, using the document references mentioned on
    each of these objects.

    Our politicians cast votes for proposed ideas, which are explained in a document, or series of documents (a main
    document and sub-documents, often amendments to the originally proposed idea).
    The identifier of such documents, which we call the document reference, is included in the plenary sessions reports,
    both when the votes are cast (written traces are found about this in the section that lists motions, bundled in
    groups of motions about the same main document) and when the documents were initially presented (written traces
    about this are found in the section that lists proposal discussions).

    So, we can link between motion groups, motions, proposal discussions and proposals by matching on these documents
    references.
    """
    documents_reference_objects = []
    problems = []

    # Process plenaries in order of occurrence through time, as proposals are not voted for if they have not been
    # presented yet in the same, or an earlier, plenary session.
    for plenary in tqdm(sorted(plenaries, key=lambda plenary_: plenary_.number),
                        desc="Linking motions with proposals..."):

        # Motion groups bundles votes cast on an idea proposed in a document and potentially sub-documents.
        # These documents, as a whole, are also presented and discussed during a proposal discussion.
        for motion_group in plenary.motion_groups:
            if motion_group.documents_reference:
                documents_reference_object = get_or_create_documents_reference_object(documents_reference_objects,
                                                                                      motion_group)

                matching_proposal_discussions = find_matching_proposal_discussions(motion_group,
                                                                                   plenaries,
                                                                                   os.path.basename(
                                                                                       plenary.html_report_url),
                                                                                   problems)
                documents_reference_object.proposal_discussion_ids = sorted(
                    [pd.id for pd in matching_proposal_discussions])

                for motion in motion_group.motions:
                    matching_proposals = find_matching_proposals(motion,
                                                                 matching_proposal_discussions,
                                                                 os.path.basename(
                                                                     plenary.html_report_url),
                                                                 problems,
                                                                 exact_match=False)
                    documents_reference_object.proposal_ids = sorted(
                        [p.id for p in matching_proposals])

                documents_reference_objects.append(documents_reference_object)

    return plenaries, documents_reference_objects, problems


def find_matching_proposal_discussions(
    motion_group: MotionGroup,
    plenaries: List[Plenary],
    _report_file_name: str,
    _linking_problems: List[LinkProblem]) -> List[ProposalDiscussion]:
    """
    Find one or more proposal discussions that match (on documents reference) with the given motion group.

    A motion group contains a reference to the main document and the series of sub-documents that contain all ideas
    that will be voted on, for example: "3495/1-5".
    There is a corresponding proposal discussion, which is written up as one or more proposals in the plenary report.
    The _first-mentioned proposal_ will also mention the full reference to the main document _and_ all sub-documents
    that will be discussed.
    """
    matching_proposal_discussions = []

    if motion_group.documents_reference:
        matching_proposal_discussions = [
            proposal_discussion
            for plenary in plenaries
            for proposal_discussion in plenary.proposal_discussions
            # link proposal discussions and proposals with same main document number, but different sub-documents:
            if get_main_document_reference(proposal_discussion.proposals[0].documents_reference)
               == get_main_document_reference(motion_group.documents_reference)
        ]

    return matching_proposal_discussions


def find_matching_proposals(
    motion: Motion,
    proposal_discussions: List[ProposalDiscussion],
    _report_file_name: str,
    _linking_problems: List[LinkProblem],
    exact_match: bool = True) -> List[Proposal]:
    """
    Find one or more proposals that match (on documents reference) with the given motion.
    The proposal is searched within already found proposal discussions.

    The proposal must either share an exactly matching documents reference with the given motion (for example,
    "3495/1-5"), or a match just on the main document reference instead ("3495").
    For now, we are non-exact matching, until we encounter a case where multiple proposals about the same main document
    occur, obliging us to start using exact matching in some way.

    A motion contains a reference to the overarching document and one or more sub-documents (at least the main
    sub-document numbered "1") that will be voted on, for example "3495/1", "3495/2" or "3495/1-4".
    These sub-documents are often amendments, presented during the plenary and have a written trace in the plenary
    report as a specific proposal, with the same document reference.
    """
    matching_proposals = []

    if motion.documents_reference:
        matching_proposals = [
            proposal
            for proposal_discussion in proposal_discussions
            for proposal in proposal_discussion.proposals
            if proposal.documents_reference and
               (
                   (exact_match and proposal.documents_reference == motion.documents_reference) or
                   get_main_document_reference(proposal.documents_reference) == get_main_document_reference(
                   motion.documents_reference)
               )
        ]

    return matching_proposals


def get_or_create_documents_reference_object(documents_reference_objects, motion_group):
    # Find out if a documents reference object has already been created, because the document has been
    # discussed in an earlier plenary, or in an earlier motion group in this plenary.
    # If this document is discussed for the first time, create documents reference object.
    existing_documents_reference_objects = [
        documents_reference_object
        for documents_reference_object in documents_reference_objects
        if documents_reference_object.all_documents_reference == motion_group.documents_reference
    ]
    if len(existing_documents_reference_objects) > 0:
        documents_reference_object = existing_documents_reference_objects[0]
    else:
        documents_reference_object = parse_document_reference(
            motion_group.documents_reference)
    return documents_reference_object


def get_main_document_reference(documents_reference: str):
    if documents_reference is None:
        return None

    if '/' in documents_reference:
        return documents_reference.split('/')[0]

    return documents_reference
