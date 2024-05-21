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
from typing import List

from tqdm.auto import tqdm

from transparentdemocracy.model import Plenary, ProposalDiscussion, MotionGroup, Proposal, Motion


class LinkProblemType(enum.Enum):
	MULTIPLE_PROPOSAL_DISCUSSIONS_FOUND = "MULTIPLE_PROPOSAL_DISCUSSIONS_FOUND"
	MULTIPLE_PROPOSALS_FOUND = "MULTIPLE_PROPOSALS_FOUND"


@dataclass
class LinkProblem:
	report_file_name: str
	problem_type: LinkProblemType


def link_motions_with_proposals(plenaries: List[Plenary]):
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
	problems = []

	# Process plenaries in order of occurrence through time, as proposals are not voted for if they have not been
	# presented yet in the same, or an earlier, plenary session.
	for plenary in tqdm(sorted(plenaries, key=lambda plenary_: plenary_.number),
						desc="Linking motions with proposals..."):

		# Motion groups bundles votes cast on an idea proposed in a document and potentially sub-documents.
		# These documents, as a whole, are also presented and discussed during a proposal discussion.
		for motion_group in plenary.motion_groups:
			matching_proposal_discussion = find_matching_proposal_discussion(motion_group,
																			 plenaries,
																			 os.path.basename(plenary.html_report_url),
																			 problems)
			if matching_proposal_discussion:
				motion_group.proposal_discussion_id = matching_proposal_discussion.id

				for motion in motion_group.motions:
					matching_proposal = find_matching_proposal(motion,
															   matching_proposal_discussion,
															   os.path.basename(plenary.html_report_url),
															   problems,
															   exact_match=False)
					if matching_proposal:
						motion.proposal_id = matching_proposal.id

	return plenaries, problems


def find_matching_proposal_discussion(
		motion_group: MotionGroup,
		plenaries: List[Plenary],
		report_file_name: str,
		linking_problems: List[LinkProblem]) -> ProposalDiscussion:
	"""
	Find a proposal discussion that matches (on documents reference) with the given motion group.

	A motion group contains a reference to the main document and the series of sub-documents that contain all ideas
	that will be voted on, for example: "3495/1-5".
	There is a corresponding proposal discussion, which is written up as one or more proposals in the plenary report.
	The _first-mentioned proposal_ will also mention the full reference to the main document _and_ all sub-documents
	that will be discussed.
	"""
	matching_proposal_discussions = [
		proposal_discussion
		for plenary in plenaries
		for proposal_discussion in plenary.proposal_discussions
		if proposal_discussion.proposals[0].documents_reference == motion_group.documents_reference
	]

	matching_proposal_discussion = None

	if len(matching_proposal_discussions) > 0:
		if len(matching_proposal_discussions) > 1:
			linking_problems.append(LinkProblem(
				report_file_name,
				LinkProblemType.MULTIPLE_PROPOSAL_DISCUSSIONS_FOUND
			))

		matching_proposal_discussion = matching_proposal_discussions[0]

	return matching_proposal_discussion


def find_matching_proposal(
		motion: Motion,
		proposal_discussion: ProposalDiscussion,
		report_file_name: str,
		linking_problems: List[LinkProblem],
		exact_match: bool = True) -> Proposal:
	"""
	Find a proposal that matches (on documents reference) with the given motion.
	The proposal is searched within an already found proposal discussion.

	The proposal must either share an exactly matching documents reference with the given motion (for example,
	"3495/1-5"), or a match just on the main document reference instead ("3495").
	For now, we are non-exact matching, until we encounter a case where multiple proposals about the same main document
	occur, obliging us to start using exact matching in some way.

	A motion contains a reference to the overarching document and one or more sub-documents (at least the main
	sub-document numbered "1") that will be voted on, for example "3495/1", "3495/2" or "3495/1-4".
	These sub-documents are often amendments, presented during the plenary and have a written trace in the plenary
	report as a specific proposal, with the same document reference.
	"""
	matching_proposals = [
		proposal
		for proposal in proposal_discussion.proposals
		if motion.documents_reference and (
				(exact_match and proposal.documents_reference == motion.documents_reference) or
				get_main_document_reference(proposal.documents_reference) == get_main_document_reference(
			motion.documents_reference)
		)
	]

	matching_proposal = None

	if len(matching_proposals) > 0:
		if len(matching_proposals) > 1:
			linking_problems.append(LinkProblem(
				report_file_name,
				LinkProblemType.MULTIPLE_PROPOSALS_FOUND
			))

		matching_proposal = matching_proposals[0]

	return matching_proposal


def get_main_document_reference(documents_reference: str):
	if documents_reference is None:
		return None
	if '/' in documents_reference:
		return documents_reference.split('/')[0]
	else:
		return documents_reference
