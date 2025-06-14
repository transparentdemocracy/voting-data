import json
import logging
import os
from collections import defaultdict
from typing import List

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

logger = logging.getLogger(__name__)


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

    def update_politicians(self, force_overwrite=False, download_actors=True):
        self._update_politicians.update_politicians(force_overwrite, download_actors)

    def update_voting_data_json_files(self):
        plenaries_to_update = self._determine_plenaries_to_process.determine_plenaries_to_update()

        self.de_kamer.download_plenary_reports(plenary_ids = list(plenaries_to_update.keys()), force_overwrite=True)

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

    def download_plenary_reports(self, plenary_ids: List[str], force_overwrite=True):
        self.de_kamer.download_plenary_reports(plenary_ids, force_overwrite)

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

    def generate_summaries(self, plenaries):
        document_references = self.get_document_references(plenaries)
        document_ids = self.get_document_ids_from_references(document_references)

        logger.info(f"generating summaries for document ids: {document_ids}")

        local_summaries = self._find_local_document_summary_ids(document_ids)
        remote_summaries = self.document_repository.find_document_summary_ids(document_ids)

        local_texts = self._find_local_document_text_ids(document_ids)
        remote_texts = self.document_repository.find_document_text_ids(document_ids)

        for document_id in document_ids:
            summary_state = "".join(
                [('1' if document_id in local_summaries else '0'), ('1' if document_id in remote_summaries else '0')])
            if summary_state == '11':
                logger.info(f"document {document_id} has summary local and remote. No actions needed.")
            elif summary_state == '01':
                logger.info(f"document {document_id} has summary remote. Downloading...")
                self._download_summary(document_id)
            elif summary_state == '10':
                logger.info(f"document {document_id} has summary local. Uploading...")
                self._upload_summary(document_id)
            else:
                text_state = "".join(
                    [('1' if document_id in local_texts else '0'), ('1' if document_id in remote_texts else '0')])
                if text_state == '11':
                    logger.info(f"document {document_id} has text local and remote. Summarizing and uploading")
                    logger.info(f"document {document_id} summarizing")
                    self._generate_summary(document_id)
                    logger.info(f"document {document_id} uploading summary")
                    self._upload_summary(document_id)
                elif text_state == '10':
                    logger.info(f"document {document_id} has text local. Will upload, summarize and upload summary")
                    logger.info(f"document {document_id} uploading text")
                    self._upload_text(document_id)
                    logger.info(f"document {document_id} summarizing")
                    self._generate_summary(document_id)
                    logger.info(f"document {document_id} uploading summary")
                    self._upload_summary(document_id)
                elif text_state == '01':
                    logger.info(
                        f"document {document_id} has text remote. Will download text, summarize and upload summary")
                    logger.info(f"document {document_id} downloading text")
                    self._download_text(document_id)
                    logger.info(f"document {document_id} summarizing")
                    self._generate_summary(document_id)
                    logger.info(f"document {document_id} uploading summary")
                    self._upload_summary(document_id)
                else:
                    logger.info(
                        f"document {document_id} has no text or summary. Will download pdf, extract text, upload text, generate summary and upload summmary")
                    logger.info(f"document {document_id} downloading pdf")
                    self._download_document_pdf(document_id)
                    logger.info(f"document {document_id} extracting text from pdf")
                    self._extract_text_from_document(document_id)

                    text_path = self.document_ids_to_local_txt_path([document_id])[0]
                    if not os.path.exists(text_path):
                        logger.warning(f"Text extraction failed on {document_id}.")
                        continue

                    logger.info(f"document {document_id} uploading text")
                    self._upload_text(document_id)
                    logger.info(f"document {document_id} summarizing")
                    self._generate_summary(document_id)
                    logger.info(f"document {document_id} uploading summary")
                    self._upload_summary(document_id)

    def _download_document_pdf(self, document_id):
        self.de_kamer.download_document_pdf(document_id)

    def _extract_text_from_document(self, document_id):
        pdf_documents = self.document_ids_to_local_pdf_path([document_id])
        extract_text_from_documents(self.config, pdf_documents)

    def _generate_summary(self, document_id):
        DocumentSummarizer(self.config).summarize_documents(self.document_ids_to_local_txt_path([document_id]))

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

    def check_summaries(self, plenaries):
        doc_refs = self.get_document_references(plenaries)
        document_ids = self.get_document_ids_from_references(doc_refs)

        for doc_id in document_ids:
            summary_path = self.document_id_to_local_summary_file(doc_id)
            print(f"checking {summary_path}")
            with open(summary_path, 'r') as summary_file:
                json.load(summary_file)


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

    env = Environments(os.environ.get('WDDP_ENVIRONMENT', Environments.PROD))
    config = _create_config(env, os.environ.get('LEGISLATURE', '56'))
    app = create_application(config, env)

    # this is only needed when there are changes to the voters.
    # in the github pipeline we can just always run it?
    download_actors = os.environ.get("DOWNLOAD_ACTORS", "false") == "true"
    update_politicians = os.environ.get("UPDATE_POLITICIANS", "false") == "true"
    app.update_politicians(update_politicians, download_actors)

    app.update_voting_data_json_files()

    ## create plenaries.json and votes.json from the list of html files
    plenaries_to_process = app.determine_plenaries_to_process()
    final_plenary_ids = [p.id for p in plenaries_to_process if p.dekamer_final]
    print("Final:", final_plenary_ids)
    print("Non-final:", [p.id for p in plenaries_to_process if not p.dekamer_final])
    plenary_ids_to_process = [p.id for p in plenaries_to_process]

    # final_plenary_ids = []
    # plenary_ids_to_process = ["56_034"]

    logging.info("Plenaries to process: %s", plenary_ids_to_process)

    if os.environ.get("INTERACTIVE", "true") == "true":
        input("Press enter to continue")

    app.download_plenary_reports(plenary_ids_to_process, False)

    report_filenames = [config.plenary_html_input_path("ip%03sx.html" % id[id.index("_") + 1:]) for id in
                        plenary_ids_to_process]

    plenaries, votes, problems = extract_plenary_reports(config, report_filenames)

    voting_reports = app.create_voting_reports(votes)

    link_motions_with_proposals(plenaries)

    # The end result of this is summary json files (one per document)
    # It won't do any re-summarization and checks local disk and google drive to avoid rework
    app.generate_summaries(plenaries)

    app.check_summaries(plenaries)

    logger.info("### PROBLEMS ###")
    for p in problems:
        logger.info(p)

    # TODO: is this 'combined document summaries' file useful for anyone?
    # with open(app.config.documents_summaries_json_output_path(), 'r', encoding="utf-8") as f:
    #    summaries = json.load(f)

    if os.environ.get("INTERACTIVE", "true") == "true":
        print([p.id for p in plenaries])
        input("Press enter to publish these plenaries to Bonsai")

    app.publish_to_elastic_search_backend(plenaries, voting_reports, final_plenary_ids)

    app.print_interesting_votes(plenaries, voting_reports)


if __name__ == "__main__":
    main()
