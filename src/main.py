import glob
import os
import logging

from tqdm.auto import tqdm

from src.voting_serializers import PlenaryReportToJsonSerializer, PlenaryReportToMarkdownSerializer
from src.voting_extractors import FederalChamberVotingHtmlExtractor, FederalChamberVotingPdfExtractor

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # or DEBUG to see debugging info as well.

INPUT_REPORTS_PATH = "./data/input"
OUTPUT_PATH = "./data/output"


def extract_voting_data_from_plenary_reports():
    # Process all input reports:
    voting_reports = glob.glob(os.path.join(INPUT_REPORTS_PATH, "*.html"))
    logging.debug(f"Will process the following input reports: {voting_reports}.")
    
    for voting_report in tqdm(voting_reports, desc="Processing plenary reports..."):
        try:
            # if voting_report.endswith("ip298x.html"):
            # Extract the interesting voting info:
            logging.debug(f"Processing input report {voting_report}...")
            # voting_extractor = FederalChamberVotingPdfExtractor()
            voting_extractor = FederalChamberVotingHtmlExtractor()
            plenary = voting_extractor.extract_from_plenary_report(voting_report)
            
            # Serialize the extracted voting info:
            # ... to human-readable format:
            voting_serializer = PlenaryReportToMarkdownSerializer()
            voting_serializer.serialize(plenary, os.path.join(OUTPUT_PATH, "markdown", f"plenary {plenary.id}.md"))
            
            # ... to machine-readable format:
            voting_serializer = PlenaryReportToJsonSerializer()
            voting_serializer.serialize(plenary, os.path.join(OUTPUT_PATH, "json", f"plenary {plenary.id}.json"))
                
        except Exception as e:
            logging.warning(e) # TODO rare errors to fix + in some pdfs, no motions could be extracted - to fix.

if __name__ == "__main__":
    extract_voting_data_from_plenary_reports()
