"""
The data model behind the voting-data repository.

It is split into two parts, which in the end result in two datasets:
- plenaries and their topics: proposals, motions, interpellations.
- votes cast during plenaries: by which politician, on which motion, which vote (yes/no/abstention).
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import List, Any


# Classes related to the plenaries and their "topics": proposals, motions (and later: interpellations).

@dataclass
class Proposal:
    id: str
    number: str  # sequence number of the proposal in the series of proposals discussed during a plenary.
    plenary_id: str
    title_fr: str
    title_nl: str
    document_reference: str
    description: str

@dataclass
class Motion:
    id: str
    number: str  # sequence number of the motion in the series of motions held towards the end of a plenary.
    proposal_id: str
    cancelled: bool

@dataclass
class Plenary:
    id: str
    number: int  # sequence number of the plenary in the series of plenaries during a legislature.
    date: date
    legislature: int
    pdf_report_url: str
    html_report_url: str
    proposals: List[Proposal]
    motions: List[Motion]
    sections: List[Any]


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
    def __init__(self, politician: Politician, motion_id: str, vote_type: VoteType):
        assert politician is not None, "politician can not be None"
        assert motion_id is not None, "motion_id can not be None"
        assert vote_type is not None, "vote_type can not be None"
        self.politician = politician
        self.motion_id = motion_id
        self.vote_type = vote_type

    politician: Politician
    motion_id: str
    vote_type: VoteType
