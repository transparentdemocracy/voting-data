from dataclasses import dataclass, field
from enum import Enum
from typing import List


@dataclass
class ParseProblem:
    report: str
    vote_nr: str
    description: str

@dataclass
class Politician:
    first_name: str
    last_name: str


@dataclass
class Proposal:
    number: int
    description: str


@dataclass
class Motion:
    proposal: Proposal
    num_votes_yes: int
    vote_names_yes: List[str]
    num_votes_no: int
    vote_names_no: List[str]
    num_votes_abstention: int
    vote_names_abstention: List[str]
    cancelled: bool
    parse_problems: list[str] = field(default_factory=list)


class VoteType(Enum):
    YES = "YES"
    NO = "NO"
    ABSTENTION = "ABSTENTION"


@dataclass
class Vote:
    politician: Politician
    motion: Motion
    vote_type: VoteType
