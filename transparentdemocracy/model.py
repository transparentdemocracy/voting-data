"""
The data model behind the voting-data repository.

It is split into two parts, which in the end result in two datasets:
- documents: ideas proposed in plenaries for voting.
- plenaries and their topics: proposals, motions, interpellations.
- votes cast during plenaries: by which politician, on which motion, which vote (yes/no/abstention).
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import List, Optional

from bs4 import Tag


# Classes related to the plenaries and their "topics": proposals, motions (and later: interpellations).

@dataclass
class DocumentsReference:
	all_documents_reference: str  # example: 3495/1-5, or 3495/5
	document_reference: Optional[int]  # example: 3495 (optional, for unparseable documents references
	main_sub_document_reference: Optional[int]  # example: 1
	sub_document_references: List[int]  # example: 1 until 5 inclusive.
	proposal_discussion_ids: List[str]
	proposal_ids: List[str]
	summary_nl: str
	summary_fr: str

	@property
	def info_url(self):
		if not self.document_reference:
			return None
		return "https://www.dekamer.be/kvvcr/showpage.cfm?section=/flwb&cfm=/site/wwwcfm/flwb/flwbn.cfm?legislat=55&dossierID=%04d" % (
			self.document_reference)

	@property
	def sub_document_pdf_urls(self):
		if not self.document_reference:
			return []
		return [self._sub_document_pdf_url(sub_doc_ref) for sub_doc_ref in self.sub_document_references]

	def _sub_document_pdf_url(self, sub_doc_reference):
		if not self.document_reference:
			return None
		return f"https://www.dekamer.be/FLWB/PDF/55/%04d/55K%04d%03d.pdf" % (
			self.document_reference, self.document_reference, sub_doc_reference)


@dataclass
class Proposal:
	id: str
	documents_reference: Optional[str]  # official reference in the parliament, as mentioned in plenary reports.
	title_nl: str
	title_fr: str


@dataclass
class ProposalDiscussion:
	id: str
	plenary_id: str
	plenary_agenda_item_number: int  # item number on the agenda in the plenary session during which the proposal was discussed. This is the number surrounded with a black border seen in all plenary reports.
	description_nl: str
	description_nl_tags: List[Tag]
	description_fr: str
	description_fr_tags: List[Tag]
	proposals: List[Proposal]  # first proposal is the main one under discussion, optional others are linked proposals.


@dataclass
class Motion:
	id: str  # Example: 55_262_m5.
	sequence_number: str  # Example: 5, corresponding with "(Stemming/vote 5)" in the plenary report.
	title_nl: str
	title_fr: str
	documents_reference: str  # example: 3495/1-4
	voting_id: Optional[str]
	cancelled: bool
	description: str


@dataclass
class MotionGroup:
	id: str  # Example: 55_262_mg12.
	plenary_agenda_item_number: int  # the agenda item number in the plenary meeting where the motion group was situated.
	title_nl: str
	title_fr: str
	documents_reference: str  # example: 3495/1-5
	motions: List[Motion]


@dataclass
class Plenary:
	id: str
	number: int  # sequence number of the plenary in the series of plenaries during a legislature.
	date: date
	legislature: int
	pdf_report_url: str
	html_report_url: str
	proposal_discussions: List[ProposalDiscussion]
	motion_groups: List[MotionGroup]

	@property
	def motions(self) -> List[Motion]:
		return [
			motion
			for motion_group in self.motion_groups
			for motion in motion_group.motions
		]


# Classes related to the detail of votes cast in plenaries:

@dataclass
class Politician:
	id: int
	full_name: str
	party: str


class VoteType(Enum):
	YES = "YES"
	NO = "NO"
	ABSTENTION = "ABSTENTION"


@dataclass
class Vote:
	def __init__(self, politician: Politician, voting_id: str, vote_type: VoteType):
		assert politician is not None, "politician can not be None"
		assert voting_id is not None, "motion_id can not be None"
		assert vote_type is not None, "vote_type can not be None"
		self.politician = politician
		self.voting_id = voting_id
		self.vote_type = vote_type

	politician: Politician
	voting_id: str
	vote_type: VoteType
