import logging
import os

import pytest

import transparentdemocracy
from transparentdemocracy.config import CONFIG
from transparentdemocracy.plenaries.extraction import (
    _extract_motion_report_items,
    create_plenary_extraction_context,
    ReportItem
)
from transparentdemocracy.politicians.extraction import load_politicians

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logger.setLevel(logging.INFO)

ROOT_FOLDER = os.path.dirname(os.path.dirname(transparentdemocracy.__file__))

# Setup fixture to handle class-level setup
@pytest.fixture(scope="module")
def setup_config():
    CONFIG.enable_testing(os.path.join(ROOT_FOLDER, "testdata"), "55")

# Helper function to extract motion report items
def extract_motion_report_items(report_path):
    path = CONFIG.plenary_html_input_path(report_path)
    ctx = create_plenary_extraction_context(path, load_politicians())
    return _extract_motion_report_items(ctx)

# Helper function to assert report items
def assert_report_item(report_item: ReportItem, expected_label: str, expected_nl_title_prefix: str, expected_fr_title_prefix: str):
    assert expected_label == report_item.label
    assert expected_nl_title_prefix == report_item.nl_title[:len(expected_nl_title_prefix)]
    assert expected_fr_title_prefix == report_item.fr_title[:len(expected_fr_title_prefix)]

def test_extract_ip298_happy_case(setup_config):
    report_items = extract_motion_report_items('ip298x.html')

    assert 15 == len(report_items)

    assert_report_item(
        report_items[0],
        "10",
        "10 Moties ingediend",
        "10 Motions déposées en conclusion des interpellations de"
    )

    assert_report_item(
        report_items[1],
        "11",
        "11 Wetsontwerp\nhoudende diverse wijzigingen van het Wetboek van strafvordering II, zoals\ngeamendeerd tijdens de plenaire vergadering van 28 maart 2024 (3515/10)",
        "11 Projet de loi portant diverses modifications du Code d'instruction\ncriminelle II, tel qu'amendé lors de la séance plénière du 28 mars 2024\n(3515/10)"
    )

def test_extract_ip280_has_1_naamstemming_but_no_identifiable_motion_title(setup_config):
    report_items = extract_motion_report_items('ip280x.html')
    assert 0 == len(report_items)

def test_extract_ip271(setup_config):
    report_items = extract_motion_report_items('ip271x.html')

    assert 15 == len(report_items)  # todo: check manually

    assert_report_item(
        report_items[0],
        '14',
        '14 Moties ingediend tot besluit van de\ninterpellatie van mevrouw Barbara Pas',
        '14 Motions déposées en conclusion de l\'interpellation de Mme Barbara\nPas'
    )

    # NOTE: nl/fr title parsing is still off
    assert_report_item(
        report_items[-1],
        "28",
        "",
    "28 Adoption de l'ordre du jour\n28 Goedkeuring van de agenda"
    )

def test_extract_ip290_has_no_naamstemmingen(setup_config):
    report_items = extract_motion_report_items('ip290x.html')
    assert [] == report_items
