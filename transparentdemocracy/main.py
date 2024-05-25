import logging

from transparentdemocracy import CONFIG
from transparentdemocracy.plenaries.extraction import extract_from_html_plenary_reports
from transparentdemocracy.plenaries.serialization import serialize
from transparentdemocracy.plenaries.motion_document_proposal_linker import link_motions_with_proposals

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main():
	plenaries, votes, problems = extract_from_html_plenary_reports(CONFIG.plenary_html_input_path("*.html"), num_reports_to_process=None)
	plenaries, documents_reference_objects, link_problems = link_motions_with_proposals(plenaries)
	serialize(plenaries, votes, documents_reference_objects)


if __name__ == "__main__":
	main()
