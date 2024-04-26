import glob
import logging
import os

from tqdm.auto import tqdm

from voting_extractors import FederalChamberVotingHtmlExtractor
from voting_serializers import PlenaryReportToJsonSerializer, PlenaryReportToMarkdownSerializer

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # or DEBUG to see debugging info as well.

INPUT_REPORTS_PATH = "./data/input/html"
OUTPUT_PATH = "./data/output"


def extract_voting_data_from_plenary_reports():
    # Process all input reports:
    voting_reports = glob.glob(os.path.join(INPUT_REPORTS_PATH, "*.html"))
    logging.debug(f"Will process the following input reports: {voting_reports}.")

    markdown_dir = os.path.join(OUTPUT_PATH, "plenary", "markdown")
    json_dir = os.path.join(OUTPUT_PATH, "plenary", "json")
    os.makedirs(markdown_dir, exist_ok=True)
    os.makedirs(json_dir, exist_ok=True)

    for voting_report in tqdm(voting_reports, desc="Processing plenary reports..."):
        try:
            # if voting_report.endswith("ip298x.html"):
            # Extract the interesting voting info:
            logging.debug(f"Processing input report {voting_report}...")
            voting_extractor = FederalChamberVotingHtmlExtractor()
            plenary = voting_extractor.extract_from_plenary_report(voting_report)
            
            # Serialize the extracted voting info:
            # ... to human-readable format:
            voting_serializer = PlenaryReportToMarkdownSerializer()
            voting_serializer.serialize(plenary, os.path.join(markdown_dir, f"plenary {plenary.id}.md"))
            
            # ... to machine-readable format:
            voting_serializer = PlenaryReportToJsonSerializer()
            voting_serializer.serialize(plenary, os.path.join(json_dir, f"plenary {plenary.id}.json"))
                
        except Exception:
            # TODO rare errors to fix + in some documents, no motions could be extracted - to fix.
            logging.warning("failed to process %s", voting_report, exc_info=True)

if __name__ == "__main__":
    extract_voting_data_from_plenary_reports()
