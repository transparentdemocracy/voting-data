import asyncio
import logging
import os
from collections import defaultdict
from typing import List

from elasticsearch.client import Elasticsearch

from transparentdemocracy.actors.actors import ActorHttpGateway
from transparentdemocracy.config import Config, _create_config, Environments
from transparentdemocracy.documents.convert_to_text import extract_text_from_documents
from transparentdemocracy.documents.document_repository import GoogleDriveDocumentRepository
from transparentdemocracy.documents.download import download_referenced_documents, get_document_references
from transparentdemocracy.documents.summarize import summarize_document_texts, DocumentSummarizer
from transparentdemocracy.infra.dekamer import DeKamerGateway
from transparentdemocracy.plenaries.extraction import extract_plenary_reports
from transparentdemocracy.plenaries.motion_document_proposal_linker import link_motions_with_proposals
from transparentdemocracy.politicians.extraction import PoliticianExtractor
from transparentdemocracy.politicians.serialization import PoliticianJsonSerializer
from transparentdemocracy.publisher.publisher import PlenaryElasticRepository, Publisher, MotionElasticRepository

logger = logging.getLogger(__name__)


class Application:
    """Main application class that encapsulates all key operations."""

    def __init__(self,
                 config: Config,
                 actor_gateway: ActorHttpGateway,
                 de_kamer: DeKamerGateway,
                 plenary_repository: PlenaryElasticRepository,
                 motion_repository: MotionElasticRepository,
                 document_repository: GoogleDriveDocumentRepository):
        self.config = config
        self.actor_gateway = actor_gateway
        self.de_kamer = de_kamer
        self.plenary_repository = plenary_repository
        self.motions_repository = motion_repository
        self.document_repository = document_repository

    def determine_plenaries_to_process(self):
        """
        Process any plenary that has not yet been imported from dekamer.be into our plenary repository,
        or has been imported already, but not yet with its final version.
        Dekamer.be publishes plenary reports in a preliminary version first, and it may take a few weeks until the
        preliminary version is replaced by a final version.
        """
        ### TODO: this returns too much, all plenaries are returned instead of only the ones that aren't final
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

    def download_plenary_reports(self, plenary_ids: List[str], force_overwrite=True):
        self.de_kamer.download_plenary_reports(plenary_ids, force_overwrite)

    def save_document_texts(self, document_references):
        document_ids = self.get_document_ids_from_references(document_references)
        existing_documents_ids = self.document_repository.get_all_document_text_ids()

        missing_document_ids = set(document_ids) - set(existing_documents_ids)

        # ensure local files exist
        pdfs_to_extract = self.document_ids_to_pdf_path(missing_document_ids)
        extract_text_from_documents(self.config, pdfs_to_extract)

        self.document_repository.upsert_document_texts(missing_document_ids)

    def download_document_pdfs(self, document_references):
        return download_referenced_documents(self.config, document_references)

    def get_document_ids_from_references(self, document_references):
        urls = set([url for ref in document_references for url in ref.sub_document_pdf_urls(self.config.legislature)])
        return [os.path.basename(url)[:-4] for url in urls]

    def publish_to_bonsai(self, plenaries, votes, politicians, summaries) -> None:
        """Upload the plenary report summary JSONs to our Bonsai (Elasticsearch stack)."""
        # TODO: rework this
        # - only upload selected plenaries (we don't want to depend on an all-in-one plenaries.json
        # - only upload selected document texts and summaries

        # Prepare data structures
        politicians_by_id = {p["id"]: p for p in politicians}
        votes_by_id = defaultdict(list)
        for vote in votes:
            votes_by_id[vote["voting_id"]].append(vote)

        summaries_by_id = {s["document_id"]: s for s in summaries} if summaries else {}

        # Create and run publisher
        publisher = Publisher(self.plenary_repository, self.motions_repository, politicians_by_id, summaries_by_id, votes_by_id)
        publisher.publish(plenaries)

    def extract_text_from_documents(self, document_references):
        document_ids = self.get_document_ids_from_references(document_references)
        pdf_documents = self.document_ids_to_pdf_path(document_ids)
        extract_text_from_documents(self.config, pdf_documents)

    def document_ids_to_pdf_path(self, document_ids):
        return [self.config.documents_input_path(doc_id[3:5], doc_id[5:7], f"{doc_id}.pdf") for doc_id in document_ids]

    def document_ids_to_txt_path(self, document_ids):
        return [self.config.documents_txt_output_path(doc_id[3:5], doc_id[5:7], f"{doc_id}.txt") for doc_id in document_ids]

    def save_document_summaries(self, document_references):
        document_ids = self.get_document_ids_from_references(document_references)
        text_files = self.document_ids_to_txt_path(document_ids)
        summarize_document_texts(text_files)

        existing_document_summary_ids = self.document_repository.get_all_document_summary_ids()
        missing_document_ids = set(document_ids) - set(existing_document_summary_ids)
        for document_id in missing_document_ids:
            self.document_repository.upsert_document_summary(document_id)

    def generate_summaries(self, document_references):
        document_ids = self.get_document_ids_from_references(document_references)
        print("document ids:", document_ids)

        local_summaries = self._find_local_document_summary_ids(document_ids)
        remote_summaries = self.document_repository.find_document_summary_ids(document_ids)

        local_texts = self._find_local_document_text_ids(document_ids)
        remote_texts = self.document_repository.find_document_text_ids(document_ids)

        for document_id in document_ids:
            summary_state = "".join([('1' if document_id in local_summaries else '0'), ('1' if document_id in remote_summaries else '0')])
            if summary_state == '11':
                print(f"document {document_id} has summary local and remote. No actions needed.")
            elif summary_state == '01':
                print(f"document {document_id} has summary remote. Downloading...")
                self._download_summary(document_id)
            elif summary_state == '10':
                print(f"document {document_id} has summary local. Uploading...")
                self._upload_summary(document_id)
            else:
                text_state = "".join([('1' if document_id in local_texts else '0'), ('1' if document_id in remote_texts else '0')])
                if text_state == '11':
                    print(f"document {document_id} has text local and remote. Summarizing and uploading")
                    print(f"document {document_id} summarizing")
                    self._generate_summary(document_id)
                    print(f"document {document_id} uploading summary")
                    self._upload_summary(document_id)
                elif text_state == '10':
                    print(f"document {document_id} has text local. Will upload, summarize and upload summary")
                    print(f"document {document_id} uploading text")
                    self._upload_text(document_id)
                    print(f"document {document_id} summarizing")
                    self._generate_summary(document_id)
                    print(f"document {document_id} uploading summary")
                    self._upload_summary(document_id)
                elif text_state == '01':
                    print(f"document {document_id} has text remote. Will download text, summarize and upload summary")
                    print(f"document {document_id} downloading text")
                    self._download_text(document_id)
                    print(f"document {document_id} summarizing")
                    self._generate_summary(document_id)
                    print(f"document {document_id} uploading summary")
                    self._upload_summary(document_id)
                else:
                    print(f"document {document_id} has no text or summary. Will download pdf, extract text, upload text, generate summary and upload summmary")
                    print(f"document {document_id} downloading pdf")
                    self._download_document_pdf(document_id)
                    print(f"document {document_id} extracting text from pdf")
                    self._extract_text_from_document(document_id)

                    text_path = self.document_ids_to_txt_path([document_id])[0]
                    if not os.path.exists(text_path):
                        print(f"Text extraction failed on {document_id}.")
                        continue

                    print(f"document {document_id} uploading text")
                    self._upload_text(document_id)
                    print(f"document {document_id} summarizing")
                    self._generate_summary(document_id)
                    print(f"document {document_id} uploading summary")
                    self._upload_summary(document_id)

    def _download_document_pdf(self, document_id):
        self.de_kamer.download_document_pdf(document_id)

    def _extract_text_from_document(self, document_id):
        pdf_documents = self.document_ids_to_pdf_path([document_id])
        extract_text_from_documents(self.config, pdf_documents)

    def _generate_summary(self, document_id):
        DocumentSummarizer(self.config).summarize_documents(self.document_ids_to_txt_path([document_id]))

    def _find_local_document_summary_ids(self, document_ids):
        def exists(doc_id):
            return os.path.exists(self.config.documents_summary_output_path(doc_id[3:5], doc_id[5:7], f"{doc_id}.summary"))

        return [doc_id for doc_id in document_ids if exists(doc_id)]

    def _find_local_document_text_ids(self, document_ids):
        def exists(doc_id):
            return os.path.exists(self.config.documents_txt_output_path(doc_id[3:5], doc_id[5:7], f"{doc_id}.txt"))

        return [doc_id for doc_id in document_ids if exists(doc_id)]

    def _download_summary(self, document_id):
        self.document_repository.download_document_summary(document_id)

    def _upload_summary(self, document_id):
        self.document_repository.upsert_document_summary(document_id)

    def _download_text(self, document_id):
        self.document_repository.download_document_summary(document_id)

    def _upload_text(self, document_id):
        text_path = self.document_ids_to_txt_path(['56K0742003'])[0]
        if os.path.exists(text_path):
            self.document_repository._upload_text_file(text_path)
        else:
            # TODO collect problem
            print(f"Missing text file: {text_path}")

    def update_politicians(self, force_overwrite=False):
        politicians_json = self.config.politicians_json_output_path()
        if os.path.exists(politicians_json) and not force_overwrite:
            print(f"{politicians_json} already exists. Cowardly refusing to overwrite")
            return

        if os.path.exists(politicians_json):
            print(f"{politicians_json} doesn't exist. Creating it now.")

        asyncio.run(self.actor_gateway.download_actors(max_pages=1000))

        serializer = PoliticianJsonSerializer(politicians_json)
        extractor = PoliticianExtractor(self.config)

        politicians = extractor.extract_politicians()
        serializer.serialize_politicians(politicians.politicians)


def create_application(config: Config, env: Environments):
    es_client = create_elastic_client(env)
    return Application(
        config,
        ActorHttpGateway(config),
        DeKamerGateway(config),
        PlenaryElasticRepository(es_client),
        MotionElasticRepository(es_client),
        GoogleDriveDocumentRepository(config)
    )


def create_elastic_client(env: Environments):
    if env == Environments.LOCAL:
        return Elasticsearch("http://localhost:9200")

    if env == Environments.DEV:
        raise Exception("TODO: setup dev environment")

    if env == Environments.PROD:
        auth = os.environ["ES_AUTH"]
        if auth is None:
            raise Exception("Missing ES_AUTH environment variable")
        return Elasticsearch(f"https://{auth}@transparent-democrac-6644447145.eu-west-1.bonsaisearch.net:443")

    raise Exception(f"missing elasticsearch configuration for env {env}")


def main():
    """Extract interesting insights from any plenary reports that have not yet been processed."""

    env = Environments(os.environ.get('WDDP_ENVIRONMENT', 'local'))
    config = _create_config(env, os.environ.get('LEGISLATURE', '56'))
    app = create_application(config, env)

    # this is only needed when there are changes to the voters.
    # in the github pipeline we can just always run it?
    app.update_politicians()
    # return

    # plenary_ids_to_process = app.determine_plenaries_to_process()
    plenary_ids_to_process = ['%s_%03d' % (config.legislature, i) for i in range(1, 32)]
    logging.info("Plenaries to process: %s", plenary_ids_to_process)

    app.download_plenary_reports(plenary_ids_to_process, False)

    report_filenames = [config.plenary_html_input_path("ip%03sx.html" % id[id.index("_") + 1:]) for id in plenary_ids_to_process]

    plenaries, votes, problems = extract_plenary_reports(config, report_filenames)
    link_motions_with_proposals(plenaries)

    # TODO this writes just the plenaries as one big json file (no document summaries)
    # is this what we want to publish or an external repository?
    # write_plenaries_json(config, plenaries)
    # TODO: same for votes
    # write_votes_json(config, votes)

    document_references = get_document_references(plenaries)

    # The end result of this is summary json files (one per document)
    # It won't do any re-summarization and checks local disk and google drive to avoid rework
    app.generate_summaries(document_references)

    print("### PROBLEMS ###")
    for p in problems:
        print(p)

    # TODO: is this 'combined document summaries' file useful for anyone?
    # with open(app.config.documents_summaries_json_output_path(), 'r', encoding="utf-8") as f:
    #    summaries = json.load(f)

    # app.publish_to_bonsai(plenaries, votes, politicians, summaries)


if __name__ == "__main__":
    main()
