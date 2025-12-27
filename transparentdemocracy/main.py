import dataclasses
import json
import logging
import os
from collections import defaultdict
from functools import wraps
from typing import List

from src.keepass_reader import keepass_dotenv
from transparentdemocracy.actors.actors import ActorHttpGateway
from transparentdemocracy.config import Config, _create_config, Environments
from transparentdemocracy.documents.analyze_references import collect_document_references
from transparentdemocracy.documents.convert_to_text import extract_text_from_documents
from transparentdemocracy.documents.document_repository import GoogleDriveDocumentRepository
from transparentdemocracy.documents.download import download_referenced_documents
from transparentdemocracy.documents.references import parse_document_reference
from transparentdemocracy.documents.summarize import summarize_document_texts, DocumentSummarizer
from transparentdemocracy.infra.dekamer import DeKamerGateway
from transparentdemocracy.infra.plenary_json import PlenaryJsonStorage
from transparentdemocracy.model import VoteType, Plenary, VotingReport
from transparentdemocracy.plenaries.extraction import extract_plenary_reports
from transparentdemocracy.plenaries.motion_document_proposal_linker import link_motions_with_proposals
from transparentdemocracy.politicians.extraction import load_politicians
from transparentdemocracy.publisher.elastic_search import PlenaryElasticRepository, Publisher, MotionElasticRepository, \
    create_elastic_client
from transparentdemocracy.usecases.determine_plenaries_to_process import DeterminePlenariesToProcess, PlenaryStatus
from transparentdemocracy.usecases.update_politicians import UpdatePoliticians

log_level = os.environ.get("LOG_LEVEL", "WARNING")
# Setup logging - force configuration
root_logger = logging.getLogger()
root_logger.setLevel(getattr(logging, log_level, logging.WARNING))
# Clear any existing handlers
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)
# Add our handler
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S'))
root_logger.addHandler(handler)

# Suppress third-party noise
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('google').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class DocumentActions:
    download_text: List[str] = dataclasses.field(default_factory=list)
    download_pdf: List[str] = dataclasses.field(default_factory=list)
    extract_text: List[str] = dataclasses.field(default_factory=list)
    upload_text: List[str] = dataclasses.field(default_factory=list)

    download_summary: List[str] = dataclasses.field(default_factory=list)
    generate_summary: List[str] = dataclasses.field(default_factory=list)
    upload_summary: List[str] = dataclasses.field(default_factory=list)


def phase(name, desc=""):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            print(f"\n{'=' * 60}")
            print(f"PHASE: {name}")
            if desc: print(f"Description: {desc}")
            print("=" * 60)
            try:
                return func(*args, **kwargs)
            finally:
                print(f"✓ PHASE COMPLETED: {name}\n")

        return wrapper

    return decorator


def prompt_continue(msg="Press enter to continue", interactive=None):
    if interactive is None:
        interactive = os.environ.get("INTERACTIVE", "true") == "true"

    if interactive: input(f"{msg}...")


class Application:
    """Main application class that encapsulates all key operations."""

    def __init__(self,
                 config: Config,
                 actor_gateway: ActorHttpGateway,
                 de_kamer: DeKamerGateway,
                 plenary_repository: PlenaryElasticRepository,
                 motion_repository: MotionElasticRepository,
                 document_repository: GoogleDriveDocumentRepository,
                 plenary_json_storage: PlenaryJsonStorage,
                 _update_politicians: UpdatePoliticians,
                 _determine_plenaries_to_process: DeterminePlenariesToProcess):
        self.config = config
        self.actor_gateway = actor_gateway
        self.de_kamer = de_kamer
        self.plenary_repository = plenary_repository
        self.motions_repository = motion_repository
        self.document_repository = document_repository
        self._plenary_json_storage = plenary_json_storage
        self._update_politicians = _update_politicians
        self._determine_plenaries_to_process = _determine_plenaries_to_process

    def update_voting_data_json_files(self):
        plenaries_to_update = self._determine_plenaries_to_process.determine_plenaries_to_update()

        self.de_kamer.download_plenary_reports(plenary_ids=list(plenaries_to_update.keys()), force_overwrite=True)

        report_filenames = [self.config.plenary_html_input_path("ip%03sx.html" % plenary_id[3:])
                            for plenary_id in plenaries_to_update.keys()]

        plenaries, votes, problems = extract_plenary_reports(self.config, report_filenames)
        voting_reports = self.create_voting_reports(votes)
        link_motions_with_proposals(plenaries)

        for plenary in plenaries:
            plenary_votings = [
                report for voting_id, report in voting_reports.items()
                if report.voting_id.startswith(plenary.id)
            ]
            is_final = plenaries_to_update[plenary.id]
            self._plenary_json_storage.save(plenary, plenary_votings, is_final)

    def determine_plenaries_to_process(self) -> List[PlenaryStatus]:
        return self._determine_plenaries_to_process.determine_plenaries_to_process()

    def save_document_texts(self, document_references):
        document_ids = self.get_document_ids_from_references(document_references)
        existing_documents_ids = self.document_repository.get_all_document_text_ids()

        missing_document_ids = set(document_ids) - set(existing_documents_ids)

        # ensure local files exist
        pdfs_to_extract = self.document_ids_to_local_pdf_path(missing_document_ids)
        extract_text_from_documents(self.config, pdfs_to_extract)

        self.document_repository.upsert_document_texts(missing_document_ids)

    def download_document_pdfs(self, document_references):
        return download_referenced_documents(self.config, document_references)

    def get_document_ids_from_references(self, document_references):
        urls = set([url for ref in document_references for url in ref.sub_document_pdf_urls(self.config.legislature)])
        return [os.path.basename(url)[:-4] for url in urls]

    def publish_to_elastic_search_backend(self, plenaries, voting_reports, final_plenary_ids) -> None:
        """
        Publish to our ElasticSearch back-end, so our watdoetdepolitiek.be Angular frontend can query all voting data.
        """
        document_references = self.get_document_references(plenaries)
        document_ids = self.get_document_ids_from_references(document_references)

        politicians = load_politicians(self.config)

        summaries_by_id = {}
        for doc_id in document_ids:
            aummary_path = self.document_id_to_local_summary_file(doc_id)
            if os.path.exists(aummary_path):
                print("reading summary from ", aummary_path)
                summaries_by_id[doc_id] = json.load(open(aummary_path, 'r'))

        # Create and run publisher
        publisher = Publisher(self.config, self.plenary_repository, self.motions_repository, politicians,
                              summaries_by_id, voting_reports)
        publisher.publish(plenaries, final_plenary_ids)

    def print_interesting_votes(self, plenaries: List[Plenary], voting_reports: dict[str, VotingReport]):
        print("Interesting votes are votes where at least one party has different vote types")
        all_motion_groups = [mg for plenary in plenaries for mg in plenary.motion_groups]

        # TODO: group this output by plenary id so we can easily identify interesting votes for the most recent plenaries
        for voting_id, report in voting_reports.items():
            counts = report.get_count_by_party()
            interesting_counts = {party: counter for party, counter in counts.items() if
                                  counter.get(VoteType.NO, 0) > 0 and counter.get(VoteType.YES, 0) > 0}
            if interesting_counts:
                motion_group = next(
                    (mg for mg in all_motion_groups if next((m for m in mg.motions if m.voting_id == voting_id), None)),
                    None)
                print(f"# voting report for {voting_id}")
                if motion_group is not None:
                    print("# Motion group: " + f"https://wddp-dev.pages.dev/motions/{motion_group.id}")
                for party, counter in interesting_counts.items():
                    print("       -", party, counter)
                    for vote in sorted(report.parties[party], key=lambda v: (str(v.vote_type), v.politician.full_name)):
                        print(vote.vote_type, vote.politician.full_name)

    def extract_text_from_documents(self, document_references):
        document_ids = self.get_document_ids_from_references(document_references)
        pdf_documents = self.document_ids_to_local_pdf_path(document_ids)
        extract_text_from_documents(self.config, pdf_documents)

    def document_id_to_local_summary_file(self, doc_id: str) -> str:
        return self.config.documents_summary_output_path(doc_id[3:5], doc_id[5:7], f"{doc_id}.summary")

    def document_ids_to_local_pdf_path(self, document_ids):
        return [self.config.documents_input_path(doc_id[3:5], doc_id[5:7], f"{doc_id}.pdf") for doc_id in document_ids]

    def document_ids_to_local_txt_path(self, document_ids):
        return [self.config.documents_txt_output_path(doc_id[3:5], doc_id[5:7], f"{doc_id}.txt") for doc_id in
                document_ids]

    def save_document_summaries(self, document_references):
        document_ids = self.get_document_ids_from_references(document_references)
        text_files = self.document_ids_to_local_txt_path(document_ids)
        summarize_document_texts(text_files)

        existing_document_summary_ids = self.document_repository.get_all_document_summary_ids()
        missing_document_ids = set(document_ids) - set(existing_document_summary_ids)
        for document_id in missing_document_ids:
            self.document_repository.upsert_document_summary(document_id)

    def _download_document_pdf(self, document_id):
        self.de_kamer.download_document_pdf(document_id)

    def _extract_text_from_document(self, document_id):
        pdf_documents = self.document_ids_to_local_pdf_path([document_id])
        extract_text_from_documents(self.config, pdf_documents)


    def _find_local_document_summary_ids(self, document_ids):
        def exists(doc_id):
            return os.path.exists(
                self.config.documents_summary_output_path(doc_id[3:5], doc_id[5:7], f"{doc_id}.summary"))

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
        text_path = self.document_ids_to_local_txt_path([document_id])[0]
        if os.path.exists(text_path):
            self.document_repository._upload_text_file(text_path)
        else:
            logger.warning(f"Missing text file: {text_path}")

    def get_document_references(self, plenaries):
        specs = {ref for ref, loc in collect_document_references(plenaries)}
        return [parse_document_reference(spec) for spec in specs]

    def create_voting_reports(self, votes):
        votes_by_voting_id = defaultdict(list)

        for vote in votes:
            votes_by_voting_id[vote.voting_id].append(vote)

        return {voting_id: self.create_voting_report(voting_id, vote_group) for voting_id, vote_group in
                votes_by_voting_id.items()}

    def create_voting_report(self, voting_id, votes):
        """ creates a report that counts votes by politician party and by vote type """
        # group votes by party and vote type
        votes_by_party = defaultdict(list)
        for vote in votes:
            votes_by_party[vote.politician.party].append(vote)

        return VotingReport(voting_id, votes_by_party)

    def verify_summaries_are_valid_json(self, document_ids):
        for doc_id in document_ids:
            summary_path = self.document_id_to_local_summary_file(doc_id)
            print(f"checking {summary_path}")
            if not os.path.exists(summary_path):
                print(f"  !! {summary_path} does not exist")
                continue
            with open(summary_path, 'r') as summary_file:
                json.load(summary_file)

    @phase("0. DOWNLOAD ACTORS AND UPDATE POLITICIANS", "Make sure we have up-to-date per-legislation data")
    def update_politicians(self):
        download_actors = os.environ.get("DOWNLOAD_ACTORS", "false") == "true"
        update_politicians = os.environ.get("UPDATE_POLITICIANS", "false") == "true"

        if not update_politicians and not download_actors:
            logger.info("  (skipped - DOWNLOAD_ACTORS and UPDATE_POLITICIANS both != true)")
            return

        prompt_continue(
            f"Press enter to download actors ({download_actors}) and update politicians ({update_politicians})")
        if update_politicians or download_actors:
            self._update_politicians.update_politicians(update_politicians, download_actors)

    @phase("1. IDENTIFY PLENARIES TO UPDATE", "Identifying which plenary sessions need processing")
    def identify_plenaries_to_update(self):
        prompt_continue("Press enter to start this phase")

        plenaries_to_process = self.determine_plenaries_to_process()
        final_plenary_ids = [p.id for p in plenaries_to_process if p.dekamer_final]
        plenary_ids_to_process = [p.id for p in plenaries_to_process]

        logger.info(f"  Found {len(plenary_ids_to_process)} plenaries to process")
        logger.info(f"  Final: {final_plenary_ids}")
        logger.info(f"  Non-final: {[p.id for p in plenaries_to_process if not p.dekamer_final]}")

        print(f"Number of plenaries ids to process: {len(plenary_ids_to_process)}")
        print(f"Number of plenaries that are final (i.e. this should be their last update): {len(final_plenary_ids)}")
        return plenary_ids_to_process, final_plenary_ids

    @phase("2. DOWNLOAD REPORTS", "Downloading HTML plenary reports from dekamer.be")
    def download_reports(self, plenary_ids_to_process):
        print(f"Number of reports to download: {len(plenary_ids_to_process)}")
        prompt_continue("Press enter to execute phase")
        self.de_kamer.download_plenary_reports(plenary_ids_to_process, False)

    @phase("3. ANALYZE PLENARY REPORTS",
           "Extracting voting data and identifying referenced documents from plenary reports")
    def analyze_plenary_reports(self, plenary_ids_to_process):
        report_filenames = [self.config.plenary_html_input_path("ip%03sx.html" % plenary_id[plenary_id.index("_") + 1:])
                            for plenary_id in
                            plenary_ids_to_process]
        prompt_continue(f"Will analyse {len(report_filenames)} HTML reports. Press Enter to continue")

        report_filenames = [self.config.plenary_html_input_path("ip%03sx.html" % plenary_id[plenary_id.index("_") + 1:])
                            for plenary_id in
                            plenary_ids_to_process]
        plenaries, votes, problems = extract_plenary_reports(self.config, report_filenames)
        voting_reports = self.create_voting_reports(votes)
        link_motions_with_proposals(plenaries)
        document_references = self.get_document_references(plenaries)
        document_ids = self.get_document_ids_from_references(document_references)

        logger.info(f"  Found {len(document_ids)} documents to process")
        logger.info(f"  Extracted {len(votes)} votes from {len(plenaries)} plenaries")
        if problems:
            logger.warning(f"  Found {len(problems)} processing problems")
            for problem in problems[:3]:
                logger.debug(f"    {problem}")

        return plenaries, votes, voting_reports, document_ids

    @phase("4. SUMMARIZE DOCUMENTS AND SYNC WITH CLOUD STORAGE", "Make sure all documents have summaries both local and in the cloud")
    def summarize_documents(self, document_ids):
        actions = self._determine_document_actions(document_ids)
        prompt_continue("Press enter to perform these actions")
        self._perform_document_actions(actions)

    def _determine_document_actions(self, document_ids):
        logger.debug(f"Document IDs to process: {document_ids}")
        print(f"Analyzing {len(document_ids)} documents...")
        local_summaries = self._find_local_document_summary_ids(document_ids)
        remote_summaries = self.document_repository.find_document_summary_ids(document_ids)
        local_texts = self._find_local_document_text_ids(document_ids)
        remote_texts = self.document_repository.find_document_text_ids(document_ids)

        processed = 0

        document_actions = DocumentActions()

        for document_id in document_ids:
            processed += 1

            summary_state = "".join(
                [('1' if document_id in local_summaries else '0'),
                 ('1' if document_id in remote_summaries else '0')])

            if summary_state == '11':
                # summary is remote and local, no more work needed
                pass
            elif summary_state == '01':
                # summary is remote but not local, download it
                document_actions.download_summary.append(document_id)
            elif summary_state == '10':
                # summary is local but not remote, upload it
                document_actions.upload_summary.append(document_id)
            else:
                # summary needs to be generated
                document_actions.generate_summary.append(document_id)

                text_state = "".join(
                    [('1' if document_id in local_texts else '0'), ('1' if document_id in remote_texts else '0')])

                if text_state == '11':
                    # text is remote and local, create summary and upload it
                    document_actions.upload_summary.append(document_id)
                elif text_state == '10':
                    # text is local but not remote, upload it
                    document_actions.upload_text.append(document_id)
                    document_actions.upload_summary.append(document_id)
                elif text_state == '01':
                    document_actions.download_text.append(document_id)
                    document_actions.upload_summary.append(document_id)
                else:
                    document_actions.download_pdf.append(document_id)
                    document_actions.extract_text.append(document_id)
                    document_actions.upload_text.append(document_id)
                    document_actions.upload_summary.append(document_id)

        print("Planned document actions:")
        print(f" - download_pdf: {len(document_actions.download_pdf)}")
        print(f" - extract_text: {len(document_actions.extract_text)}")
        print(f" - download_text: {len(document_actions.download_text)}")
        print(f" - upload_text: {len(document_actions.upload_text)}")
        print(f" - generate_summary: {len(document_actions.generate_summary)}")
        print(f" - download_summary: {len(document_actions.download_summary)}")
        print(f" - upload_summary: {len(document_actions.upload_summary)}")
        return document_actions

    def _perform_document_actions(self, document_actions: DocumentActions):
        print(f"Downloading {len(document_actions.download_pdf)} document pdfs")
        for doc_id in document_actions.download_pdf:
            self._download_document_pdf(doc_id)

        print(f"Downloading text for {len(document_actions.download_text)} documents")
        for doc_id in document_actions.download_text:
            self._download_text(doc_id)

        print(f"Extracting text from {len(document_actions.extract_text)} pdf documents")
        for doc_id in document_actions.extract_text:
            self._extract_text_from_document(doc_id)

        print(f"Uploading text for {len(document_actions.upload_text)} documents")
        for doc_id in document_actions.upload_text:
            self._upload_text(doc_id)

        print(f"Downloading summaries for {len(document_actions.download_summary)} documents")
        for doc_id in document_actions.download_summary:
            self._download_summary(doc_id)

        print(f"Generating {len(document_actions.generate_summary)} summaries")
        DocumentSummarizer(self.config).summarize_documents(self.document_ids_to_local_txt_path(document_actions.generate_summary))

        print(f"Checking {len(document_actions.upload_summary)} summaries before uploading")
        self.verify_summaries_are_valid_json(document_actions.upload_summary)

        print(f"Uploading {len(document_actions.upload_summary)} summaries")
        for doc_id in document_actions.upload_summary:
            self._upload_summary(doc_id)

    @phase("5. PUBLISH RESULTS", "Publishing processed data to ElasticSearch backend")
    def phase_5_publish_results(self, plenaries, voting_reports, final_plenary_ids):
        logger.info(f"  Will publish {len(plenaries)} plenaries to backend")
        logger.info(f"  Final plenaries being published: {final_plenary_ids}")

        prompt_continue("Press enter to execute phase")
        self.publish_to_elastic_search_backend(plenaries, voting_reports, final_plenary_ids)

def create_application(config: Config, env: Environments):
    es_client = create_elastic_client(config, env)
    actor_gateway = ActorHttpGateway(config)
    de_kamer = DeKamerGateway(config)
    plenary_repository = PlenaryElasticRepository(config, es_client)
    plenary_json_storage = PlenaryJsonStorage(config.plenary_json_output_path())

    return Application(
        config,
        actor_gateway,
        de_kamer,
        plenary_repository,
        MotionElasticRepository(config, es_client),
        GoogleDriveDocumentRepository(config),
        plenary_json_storage,
        UpdatePoliticians(config, actor_gateway),
        DeterminePlenariesToProcess(de_kamer, plenary_repository, plenary_json_storage)
    )


def main():
    """Extract interesting insights from any plenary reports that have not yet been processed."""
    keepass_dotenv()

    env = Environments(os.environ.get('WDDP_ENVIRONMENT', Environments.DEV))
    config = _create_config(env, os.environ.get('LEGISLATURE', '56'))
    app = create_application(config, env)

    # phase 0
    app.update_politicians()

    # phase 1
    plenary_ids_to_process, final_plenary_ids = app.identify_plenaries_to_update()

    # phase 2
    app.download_reports(plenary_ids_to_process)

    # phase 3
    plenaries, votes, voting_reports, document_ids = app.analyze_plenary_reports(plenary_ids_to_process)

    # phase 4
    app.summarize_documents(document_ids)

    # phase 5
    app.publish_results(plenaries, voting_reports, final_plenary_ids)

    app.print_interesting_votes(plenaries, voting_reports)

    logger.info("🎉 Processing completed successfully!")


if __name__ == "__main__":
    main()
