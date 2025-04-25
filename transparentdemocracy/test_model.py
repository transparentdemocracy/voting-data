import unittest
from dataclasses import dataclass
from collections import Counter
from enum import Enum
from typing import List

from transparentdemocracy.model import VotingReport


# Assuming these are your existing classes
class VoteType(Enum):
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"


@dataclass
class Politician:
    name: str


@dataclass
class Vote:
    politician: Politician
    voting_id: str
    vote_type: VoteType


class TestVotingReport(unittest.TestCase):
    def setUp(self):
        # Create some test data
        self.politician1 = Politician("John Doe")
        self.politician2 = Politician("Jane Smith")
        self.politician3 = Politician("Bob Johnson")

        # Create test votes
        vote1 = Vote(self.politician1, "vote123", VoteType.YES)
        vote2 = Vote(self.politician2, "vote123", VoteType.NO)
        vote3 = Vote(self.politician3, "vote123", VoteType.ABSTAIN)

        # Create a voting report with multiple parties and votes
        self.voting_report = VotingReport(
            voting_id="vote123",
            parties={
                "Party A": [vote1, vote2],
                "Party B": [vote3],
                "Party C": []  # Empty party to test edge case
            }
        )

    def test_total_votes(self):
        # Test the total number of votes
        total = self.voting_report.total_votes()
        self.assertEqual(total, 3)

    def test_total_votes_empty_parties(self):
        # Test with empty parties dictionary
        empty_report = VotingReport(
            voting_id="vote123",
            parties={}
        )
        self.assertEqual(empty_report.total_votes(), 0)

    def test_total_votes_empty_party_lists(self):
        # Test with parties that have no votes
        no_votes_report = VotingReport(
            voting_id="vote123",
            parties={
                "Party A": [],
                "Party B": []
            }
        )
        self.assertEqual(no_votes_report.total_votes(), 0)


if __name__ == '__main__':
    unittest.main()
