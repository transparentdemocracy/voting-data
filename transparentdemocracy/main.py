import json
import logging
import os
from collections import defaultdict
from typing import List

from elasticsearch.client import Elasticsearch

from transparentdemocracy import CONFIG
from transparentdemocracy.config import Config
from transparentdemocracy.documents.convert_to_text import extract_text_from_documents
from transparentdemocracy.documents.download import download_referenced_documents
from transparentdemocracy.documents.summarize import summarize_document_texts, write_summaries_json
from transparentdemocracy.infra.dekamer import DeKamerGateway
from transparentdemocracy.plenaries.serialization import write_plenaries_json, write_votes_json
from transparentdemocracy.publisher.publisher import PlenariesElasticRepository, Publisher, MotionsElasticRepository

logger = logging.getLogger(__name__)


class Application:
    """Main application class that encapsulates all key operations."""

    def __init__(self, config: Config, de_kamer, plenary_repository, motions_repository):
        self.config = config
        self.de_kamer = de_kamer
        self.plenary_repository = plenary_repository
        self.motions_repository = motions_repository

    def determine_plenaries_to_process(self):
        """
        Process any plenary that has not yet been imported from dekamer.be into our plenary repository,
        or has been imported already, but not yet with its final version.
        Dekamer.be publishes plenary reports in a preliminary version first, and it may take a few weeks until the
        preliminary version is replaced by a final version.
        """
        recent_reports = self.de_kamer.find_recent_reports()

        ids = [report[0] for report in recent_reports]

        status_by_id = self.plenary_repository.get_statuses(ids)

        to_process = []

        for report in recent_reports:
            plenary_id, href, is_final = report

            if plenary_id not in status_by_id:
                raise Exception("status wasn't returned by plenary_repository")

            if status_by_id[plenary_id]:
                print(f"{plenary_id} is already final in elastic")
                continue

            to_process.append(plenary_id)

        print("to process: ", to_process)
        return sorted(to_process)

    def download_plenary_reports(self, plenary_ids: List[int], force_overwrite=True):
        self.de_kamer.download_plenary_reports(plenary_ids, force_overwrite)


    def publish_to_bonsai(self) -> None:
        """Upload the plenary report summary JSONs to our Bonsai (Elasticsearch stack)."""
        # TODO: which data should be present beforehand, which can be assumed to be present?
        # TODO: pass plenary ids to publish?

        with open(self.config.plenary_json_output_path("plenaries.json"), 'r', encoding="utf-8") as f:
            plenaries = json.load(f)

        with open(self.config.plenary_json_output_path("votes.json"), 'r', encoding="utf-8") as f:
            votes = json.load(f)

        with open(self.config.politicians_json_output_path("politicians.json"), 'r', encoding="utf-8") as f:
            politicians = json.load(f)

        with open(self.config.documents_summaries_json_output_path(), 'r', encoding="utf-8") as f:
            summaries = json.load(f)

        # Prepare data structures
        politicians_by_id = {p["id"]: p for p in politicians}
        votes_by_id = defaultdict(list)
        for vote in votes:
            votes_by_id[vote["voting_id"]].append(vote)

        summaries_by_id = {s["document_id"]: s for s in summaries} if summaries else {}

        # Create and run publisher
        publisher = Publisher(self.plenary_repository, self.motions_repository, politicians_by_id, summaries_by_id, votes_by_id)
        publisher.publish(plenaries)


def create_application(config: Config):
    es_client = create_elastic_client()
    return Application(config, DeKamerGateway(config), PlenariesElasticRepository(es_client), MotionsElasticRepository(es_client))


def create_elastic_client():
    # Local, no auth required
    # return Elasticsearch("http://localhost:9200")

    # Bonsai
    auth = os.environ["ES_AUTH"]
    return Elasticsearch(f"https://{auth}@transparent-democrac-6644447145.eu-west-1.bonsaisearch.net:443")


def main():
    """Extract interesting insights from any plenary reports that have not yet been processed."""
    app = create_application(CONFIG)
    plenary_ids_to_process = app.determine_plenaries_to_process()
    app.download_plenary_reports(plenary_ids_to_process, False)
    write_plenaries_json()
    write_votes_json()  # TODO optimize, this calls extract_from_html_plenary_reports() again.
    download_referenced_documents()
    extract_text_from_documents()
    summarize_document_texts()
    write_summaries_json()
    app.publish_to_bonsai()


if __name__ == "__main__":
    main()
