import logging
import os

import pytest

import transparentdemocracy
from transparentdemocracy.config import CONFIG
from transparentdemocracy.model import Motion
from transparentdemocracy.plenaries.extraction import (
    _extract_motion_groups,
    create_plenary_extraction_context,
    extract_from_html_plenary_report,
)
from transparentdemocracy.politicians.extraction import load_politicians

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logger.setLevel(logging.INFO)

ROOT_FOLDER = os.path.dirname(os.path.dirname(transparentdemocracy.__file__))

@pytest.fixture(scope="module")
def setup_config():
    CONFIG.enable_testing(os.path.join(ROOT_FOLDER, "testdata"), "55")

def test_extract_motions_ip298x_html_go_to_example_report(setup_config):
    # The example report we used for implementing extraction of other sub-objects of a plenary object.
    # Arrange
    report_path = CONFIG.plenary_html_input_path("ip298x.html")
    ctx = create_plenary_extraction_context(report_path, load_politicians())

    # Act
    _, motion_groups = _extract_motion_groups("55_298", ctx)

    # Assert
    motions = [m for mg in motion_groups for m in mg.motions]
    assert len(motions) == 39

    motion_group10 = motion_groups[0]
    assert motion_group10.id == "55_298_mg_10"
    assert motion_group10.plenary_agenda_item_number == 10
    assert motion_group10.title_nl.startswith("Moties ingediend tot besluit van de interpellaties van - Koen Metsu over ")
    assert motion_group10.title_nl.endswith('Comité P over de aanslag van 16 oktober 2023" (nr. 486)')
    assert motion_group10.title_fr.startswith("Motions déposées en conclusion des interpellations de - Koen Metsu sur")
    assert motion_group10.title_fr.endswith(' sur l\'attentat du 16 octobre 2023" (n° 486)')
    assert motion_group10.documents_reference == None
    assert len(motion_group10.motions) == 1

    assert motion_group10.motions[0].id == "55_298_mg_10_m0"
    assert motion_group10.motions[0].sequence_number == "10"
    assert motion_group10.motions[0].title_nl.startswith("Moties ingediend tot besluit van de interpellaties van - Koen Metsu over ")
    assert motion_group10.motions[0].title_nl.endswith('Comité P over de aanslag van 16 oktober 2023" (nr. 486)')
    assert motion_group10.motions[0].title_fr.startswith("Motions déposées en conclusion des interpellations de - Koen Metsu sur")
    assert motion_group10.motions[0].title_fr.endswith(' sur l\'attentat du 16 octobre 2023" (n° 486)')
    assert motion_group10.motions[0].documents_reference == None
    assert motion_group10.motions[0].voting_id == "55_298_v1"
    assert motion_group10.motions[0].cancelled == False
    assert motion_group10.motions[0].description.endswith("De eenvoudige motie is aangenomen. Bijgevolg vervallen de moties van aanbeveling.")

    motion_group14 = motion_groups[4]
    assert motion_group14.id == "55_298_mg_14"
    assert motion_group14.plenary_agenda_item_number == 14
    assert motion_group14.title_nl == "Aangehouden amendementen en artikelen van het wetsontwerp houdende de hervorming van de pensioenen"
    assert motion_group14.title_fr == "Amendements et articles réservés du projet de loi portant la réforme des pensions"
    assert motion_group14.documents_reference == "3808/1-10"
    assert motion_group14.title_nl == "Aangehouden amendementen en artikelen van het wetsontwerp houdende de hervorming van de pensioenen"
    assert motion_group14.title_fr == "Amendements et articles réservés du projet de loi portant la réforme des pensions"
    assert motion_group14.documents_reference == "3808/1-10"
    assert len(motion_group14.motions) == 22

    assert motion_group14.motions[0].id == "55_298_mg_14_m0"
    assert motion_group14.motions[0].sequence_number == "14"
    assert motion_group14.motions[0].title_nl == "Stemming over amendement nr. 35 van Ellen\nSamyn op artikel 2."
    assert motion_group14.motions[0].title_fr == "Vote sur l'amendement n° 35 de Ellen Samyn à\nl'article 2."
    assert motion_group14.motions[0].documents_reference == "3808/10"
    assert motion_group14.motions[0].voting_id == "55_298_v5"
    assert motion_group14.motions[0].cancelled == False

def test_extract_motions_ip262x_html_go_to_example_report(setup_config):
    # The example report we used for agreeing on how to implement extraction of motions.
    # Arrange
    report_path = CONFIG.plenary_html_input_path("ip262x.html")

    # Act
    plenary, _, _ = extract_from_html_plenary_report(report_path, load_politicians())
    motion_groups = plenary.motion_groups

    # Assert
    assert len(motion_groups) == 15
    assert motion_groups[0].plenary_agenda_item_number == 8
    assert motion_groups[-1].plenary_agenda_item_number == 22

    motion_group12 = motion_groups[4]
    assert motion_group12.id == "55_262_mg_12"
    assert motion_group12.plenary_agenda_item_number == 12
    assert motion_group12.title_nl == "Aangehouden amendementen op het wetsontwerp houdende diverse bepalingen inzake sociale zaken"
    assert motion_group12.title_fr == "Amendements réservés au projet de loi portant des dispositions diverses en matière sociale"
    assert motion_group12.documents_reference == "3495/1-5"

    assert len(motion_group12.motions) == 3

    expected_motion = Motion(
        "55_262_mg_12_m0",
        "12",
        "Stemming over amendement nr.\xa04 van\nCatherine Fonck tot invoeging van een artikel 2/1(n).",
        "Vote sur l'amendement n°\xa04 de Catherine\nFonck tendant à insérer un article 2/1(n).",
        "3495/5",
        "55_262_v5",
        False,
        "Begin van de stemming / Début du vote. Heeft iedereen gestemd en zijn stem nagekeken? / Tout le monde a-t-il voté et vérifié "
        "son vote? Heeft iedereen gestemd en zijn stem nagekeken? / Tout le monde a-t-il voté et vérifié son vote? Einde van de "
        "stemming / Fin du vote. Einde van de stemming / Fin du vote. Uitslag van de stemming / Résultat du vote. Uitslag van de "
        "stemming / Résultat du vote. (Stemming/vote 5) Ja 6 Oui Nee 100 Non Onthoudingen 28 Abstentions Totaal 134 Total ("
        "Stemming/vote 5) Ja 6 Oui Nee 100 Non Onthoudingen 28 Abstentions Totaal 134 Total En conséquence, l'amendement est rejeté. "
        "Bijgevolg is het amendement verworpen.",
    )
    assert expected_motion == motion_group12.motions[0]

    # Outcomes with current implementation:
    motions = plenary.motions
    assert len(motions) == 19

    expected_motion_ids = [
        "55_262_mg_8_m0",
        "55_262_mg_9_m0",
        "55_262_mg_10_m0",
        "55_262_mg_10_m1",
        "55_262_mg_11_m0",
        "55_262_mg_12_m0",
        "55_262_mg_12_m1",
        "55_262_mg_12_m2",
        "55_262_mg_13_m0",
        "55_262_mg_14_m0",
        "55_262_mg_14_m1",
        "55_262_mg_15_m0",
        "55_262_mg_16_m0",
        "55_262_mg_17_m0",
        "55_262_mg_18_m0",
        "55_262_mg_19_m0",
        "55_262_mg_20_m0",
        "55_262_mg_21_m0",
        "55_262_mg_22_m0",
    ]

    for expected_id, motion in zip(expected_motion_ids, motions, strict=False):
        assert expected_id == motion.id
