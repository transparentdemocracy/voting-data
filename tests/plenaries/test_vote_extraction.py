import logging
import os

import pytest

import transparentdemocracy
from transparentdemocracy.config import CONFIG
from transparentdemocracy.model import VoteType
from transparentdemocracy.plenaries.extraction import (
    _extract_votes,
    create_plenary_extraction_context,
)
from transparentdemocracy.politicians.extraction import load_politicians

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logger.setLevel(logging.INFO)

ROOT_FOLDER = os.path.dirname(os.path.dirname(transparentdemocracy.__file__))

@pytest.fixture(scope="module")
def setup_config():
    CONFIG.enable_testing(os.path.join(ROOT_FOLDER, "testdata"), "55")

def test_extract_votes_ip298x_go_to_example_report(setup_config):
    # Arrange
    report_path = CONFIG.plenary_html_input_path("ip298x.html")
    politicians = load_politicians()
    ctx = create_plenary_extraction_context(report_path, politicians)

    # Act
    votes = _extract_votes(ctx, "55_298")

    # Assert
    voting1_votes = [vote for vote in votes if vote.voting_id == "55_298_v1"]

    voting1_votes_yes = [vote for vote in voting1_votes if vote.vote_type is VoteType.YES]
    assert len(voting1_votes_yes) == 79
    assert voting1_votes_yes[0].politician.full_name == "Aouasti Khalil"
    assert voting1_votes_yes[1].politician.full_name == "Bacquelaine Daniel"
    assert voting1_votes_yes[-2].politician.full_name == "Wilmès Sophie"
    assert voting1_votes_yes[-1].politician.full_name == "Zanchetta Laurence"

    voting1_votes_no = [vote for vote in voting1_votes if vote.vote_type is VoteType.NO]
    assert len(voting1_votes_no) == 50
    assert voting1_votes_no[0].politician.full_name == "Anseeuw Björn"
    assert voting1_votes_no[1].politician.full_name == "Bruyère Robin"
    assert voting1_votes_no[-2].politician.full_name == "Verreyt Hans"
    assert voting1_votes_no[-1].politician.full_name == "Wollants Bert"

    voting1_votes_abstention = [vote for vote in voting1_votes if vote.vote_type is VoteType.ABSTENTION]
    assert len(voting1_votes_abstention) == 4
    assert voting1_votes_abstention[0].politician.full_name == "Arens Josy"
    assert voting1_votes_abstention[1].politician.full_name == "Daems Greet"
    assert voting1_votes_abstention[-2].politician.full_name == "Rohonyi Sophie"
    assert voting1_votes_abstention[-1].politician.full_name == "Vindevoghel Maria"

    assert len(voting1_votes) == 133

    assert len([v for v in votes if v.voting_id == "55_298_v2"]) == 134
    assert len([v for v in votes if v.voting_id == "55_298_v3"]) == 132
