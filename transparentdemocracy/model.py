"""
The data model behind the voting-data repository.

It is split into two parts, which in the end result in two datasets:
- plenaries and their topics: proposals, motions, interpellations.
- votes cast during plenaries: by which politician, on which motion, which vote (yes/no/abstention).
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import List, Optional

from bs4 import PageElement


# Classes related to the plenaries and their "topics": proposals, motions (and later: interpellations).

# not using this yet, but might be an interesting type for the documents_reference attributes below, instead of
# str-typing them.
@dataclass
class DocumentsReference:
	document_reference: int  # example: 3495
	all_documents_reference: str  # example: 3495/1-5, or 3495/5
	main_document_reference: int  # example: 1
	sub_document_references: List[int]  # example: 1 until 5 inclusive.

@dataclass
class Proposal:
	documents_reference: Optional[str]  # official reference in the parliament, as mentioned in plenary reports.
	title_nl: str
	title_fr: str


@dataclass
class ProposalDiscussion:
	id: str
	plenary_id: str
	plenary_agenda_item_number: int  # item number on the agenda in the plenary session during which the proposal was discussed. This is the number surrounded with a black border seen in all plenary reports.
	description_nl: str
	description_fr: str
	proposals: List[Proposal]  # first proposal is the main one under discussion, optional others are linked proposals.


@dataclass
class Motion:
	id: str  # Example: 55_262_m5.
	sequence_number: str  # Example: 5, corresponding with "(Stemming/vote 5)" in the plenary report.
	title_nl: str
	title_fr: str
	documents_reference: str  # example: 3495/1-5
	voting_id: Optional[str]
	cancelled: bool
	description: str
	proposal_id: str


@dataclass
class MotionGroup:
	id: str  # Example: 55_262_mg12.
	plenary_agenda_item_number: int  # the agenda item number in the plenary meeting where the motion group was situated.
	title_nl: str
	title_fr: str
	documents_reference: str  # example: 3495/5
	proposal_discussion_id: str
	motions: List[Motion]


@dataclass
class BodyTextPart:
	lang: str
	text: str


@dataclass
class ReportItem:
	label: str
	nl_title: str
	nl_title_tags: List[PageElement]
	fr_title: str
	fr_title_tags: List[PageElement]
	body_text_parts: List[BodyTextPart]
	body: List[PageElement]


@dataclass
class Plenary:
	id: str
	number: int  # sequence number of the plenary in the series of plenaries during a legislature.
	date: date
	legislature: int
	pdf_report_url: str
	html_report_url: str
	proposal_discussions: List[ProposalDiscussion]
	motions: List[Motion]
	motion_groups: List[MotionGroup]
	report_items: List[ReportItem]


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
