"""
The data model behind the voting-data repository.

It is split into two parts, which in the end result in two datasets:
- plenaries and their topics: proposals, motions, interpellations.
- votes cast during plenaries: by which politician, on which motion, which vote (yes/no/abstention).
"""

from dataclasses import dataclass
from enum import Enum
from typing import List


# Classes related to the plenaries and their "topics": proposals, motions (and later: interpellations).

@dataclass
class Proposal:
    id: str
    number: str  # sequence number of the proposal in the series of proposals discussed during a plenary.
    plenary_id: str
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
    legislature: int
    pdf_report_url: str
    html_report_url: str
    proposals: List[Proposal]
    motions: List[Motion]


# Classes related to the detail of votes cast in plenaries:

@dataclass
class Politician:
    full_name: str

class VoteType(Enum):
    YES = "YES"
    NO = "NO"
    ABSTENTION = "ABSTENTION"

@dataclass
class Vote:
    politician: Politician
    motion_id: str
    vote_type: VoteType
