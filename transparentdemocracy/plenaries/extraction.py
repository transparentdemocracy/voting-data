"""
Extract info from HTML-formatted voting reports from the Belgian federal chamber's website,
see https://www.dekamer.be/kvvcr/showpage.cfm?section=/flwb/recent&language=nl&cfm=/site/wwwcfm/flwb/LastDocument.cfm.
"""
import datetime
import glob
import logging
import os
import re
from dataclasses import dataclass
from typing import Tuple, List, Optional, Union

from bs4 import BeautifulSoup, NavigableString, Tag, PageElement
from nltk.tokenize import WhitespaceTokenizer
from tqdm.auto import tqdm

from transparentdemocracy import CONFIG
from transparentdemocracy.model import Motion, Plenary, Proposal, ProposalDiscussion, Vote, VoteType, MotionGroup
from transparentdemocracy.politicians.extraction import Politicians, load_politicians

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

WHITESPACE = re.compile("\\s+")

DAYS_NL = "maandag,dinsdag,woensdag,donderdag,vrijdag,zaterdag,zondag".split(
    ",")
MONTHS_NL = "januari,februari,maart,april,mei,juni,juli,augustus,september,oktober,november,december".split(
    ",")


@dataclass
class BodyTextPart:
    lang: str
    text: str


@dataclass
class ReportItem:
    label: str
    nl_title: str
    nl_title_tags: List[PageElement]
    fr_title: str
    fr_title_tags: List[PageElement]
    body_text_parts: List[BodyTextPart]
    body: List[PageElement]


@dataclass
class ParseProblem:
    report_path: str
    problem_type: str
    location: Optional[str]


class PlenaryExtractionContext:
    def __init__(self, report_path, politicians: Politicians, html=None):
        self.report_path = report_path
        self.politicians = politicians
        self.html = html
        self.problems = []

    def add_problem(self, problem_type: str, location: str = None):
        self.problems.append(ParseProblem(
            self.report_path, problem_type, location))


def create_plenary_extraction_context(report_path: str, politicians) -> PlenaryExtractionContext:
    html = _read_plenary_html(report_path)
    return PlenaryExtractionContext(report_path, politicians, html)


def extract_from_html_plenary_reports(
    report_file_pattern: Union[str, List[str]] = CONFIG.plenary_html_input_path("*.html"),
    num_reports_to_process: int = None) -> Tuple[List[Plenary], List[Vote], List[ParseProblem]]:
    politicians = load_politicians()
    all_problems = []
    plenaries = []
    all_votes = []
    logging.info("Report files must be found at: %s.", report_file_pattern)

    if isinstance(report_file_pattern, str):
        report_filenames = glob.glob(report_file_pattern)
    else:
        report_filenames = [
            path for pattern in report_file_pattern for path in glob.glob(pattern)]

    if len(report_filenames) == 0:
        raise ValueError("No plenary reports are present in the input folder. Cannot extract any plenaries. "
                         "Check https://github.com/transparentdemocracy/voting-data/tree/main?tab=readme-ov-file#downloading-and-generating-data.")

    # deduplication
    report_filenames = list(dict.fromkeys(report_filenames))

    if num_reports_to_process is not None:
        report_filenames = report_filenames[:num_reports_to_process]
    logging.debug("Will process the following input reports: %s.", report_filenames)

    for report_filename in tqdm(report_filenames, desc="Processing plenary reports..."):
        try:
            logging.debug("Processing input report %s...", report_filename)
            if report_filename.endswith(".html"):
                plenary, votes, problems = extract_from_html_plenary_report(
                    report_filename, politicians)
                plenaries.append(plenary)
                all_votes.extend(votes)
                all_problems.extend(problems)
            else:
                all_problems.append(ParseProblem(
                    report_filename, "NOT_HTML", "filename"))
                continue

        except Exception:
            all_problems.append(ParseProblem(
                report_filename, "EXCEPTION", None))
            logging.warning("Failed to process %s",
                            report_filename, exc_info=True)

    return plenaries, all_votes, all_problems


def extract_from_html_plenary_report(report_path: str, politicians: Politicians = None) \
    -> Tuple[Plenary, List[Vote], List[ParseProblem]]:
    politicians = politicians or load_politicians()
    ctx = create_plenary_extraction_context(report_path, politicians)
    plenary, votes = _extract_plenary(ctx)

    return plenary, votes, ctx.problems


def _read_plenary_html(report_filename):
    with open(report_filename, "r", encoding="cp1252") as file:
        html_content = file.read()
    return BeautifulSoup(html_content, "html.parser")  # "lxml")


def _extract_plenary(ctx: PlenaryExtractionContext) -> Tuple[Plenary, List[Vote]]:
    plenary_number = os.path.split(ctx.report_path)[1][2:5]  # example: ip078x.html -> 078
    legislature = int(CONFIG.legislature)
    # Concatenating legislature and plenary number to construct a unique identifier for this plenary.
    plenary_id = f"{legislature}_{plenary_number}"
    proposals = __extract_proposal_discussions(ctx, plenary_id)
    _motion_report_items, motion_groups = _extract_motion_groups(plenary_id, ctx)
    votes = _extract_votes(ctx, plenary_id)

    return (
        Plenary(
            plenary_id,
            int(plenary_number),
            _get_plenary_date(ctx),
            legislature,
            f"https://www.dekamer.be/doc/PCRI/pdf/{legislature}/ip{plenary_number}.pdf",
            f"https://www.dekamer.be/doc/PCRI/html/{legislature}/ip{plenary_number}x.html",
            proposals,
            motion_groups
        ),
        votes
    )


def _extract_motion_groups(plenary_id: str, ctx: PlenaryExtractionContext) \
    -> Tuple[List[ReportItem], List[MotionGroup]]:
    motion_report_items = _extract_motion_report_items(ctx)
    motion_groups = _report_items_to_motion_groups(
        ctx, plenary_id, motion_report_items)
    return motion_report_items, motion_groups


def is_article_discussion_item(item: ReportItem) -> bool:
    normalized_nl = normalize_whitespace(item.nl_title).lower()
    return normalized_nl == "bespreking van de artikelen"


def normalize_whitespace(text) -> str:
    return re.sub(WHITESPACE, " ", text.strip()).strip()


def __extract_proposal_discussions(ctx: PlenaryExtractionContext, plenary_id: str) -> List[
    ProposalDiscussion]:
    proposal_discussions = []

    # We'll be able to extract the proposals after the header of the proposals section in the plenary report:
    level1_headers = [
        el for el in ctx.html.find_all()
        if el.text.strip() != "" and is_level1_title(el)
    ]

    if not level1_headers:
        ctx.add_problem("NO_LEVEL1_TITLE", None)
        logging.warning("No 'level1' (h1) section titles found (Plenary report %s). "
                        "No proposal discussions will be added to the data about this plenary.", os.path.basename(ctx.report_path))
        return proposal_discussions

    proposal_section_headers = [
        el for el in level1_headers
        if "wetsontwerp" in el.text.strip().lower()
           or "voorstel" in el.text.strip().lower()
           or el.text.strip().lower() in ["projets de loi",
                                          # "Begrotingen" (= financial cost estimates) for the coming year are the replacement
                                          # for normal proposal discussions, but are in fact just another title for what are
                                          # still proposals:
                                          "begrotingen"]
    ]

    if not proposal_section_headers:
        ctx.add_problem("NO_PROPOSAL_HEADER_FOUND")
        logging.warning("No proposal section title found (Plenary report %s). "
                        "No proposal discussions will be added to the data about this plenary.", os.path.basename(ctx.report_path))
        return proposal_discussions

    proposal_header_idx = level1_headers.index(proposal_section_headers[-1])
    next_level1_headers = level1_headers[proposal_header_idx + 1:]

    if next_level1_headers:
        proposal_discussion_elements = proposal_section_headers[-1].find_next_siblings()
        if next_level1_headers[0] in proposal_discussion_elements:
            next_level1_index = proposal_discussion_elements.index(
                next_level1_headers[0])
            proposal_discussion_elements = proposal_discussion_elements[:next_level1_index]
    else:
        proposal_discussion_elements = proposal_section_headers[-1].find_next_siblings()

    proposal_discussion_elements = [el for el in proposal_discussion_elements if el.text.strip() != ""]

    tag_groups = create_level2_tag_groups(proposal_discussion_elements)
    report_items = find_report_items(tag_groups)

    for level2_item in report_items:
        nl_proposal_titles = level2_item.nl_title_tags
        fr_proposal_titles = level2_item.fr_title_tags

        if not level2_item.label:
            # ip182x: Wetsontwerpen en voorstellen has a paragraph before the first proposal start at [15]. We ignore this
            ctx.add_problem("LEVEL2_ITEM_WITHOUT_LABEL",
                            normalize_whitespace(" ".join([level2_item.nl_title, level2_item.fr_title])))
            continue

        if len(nl_proposal_titles) + len(fr_proposal_titles) == 0:
            ctx.add_problem("NO_PROPOSAL_TITLES", level2_item.label)

        if len(nl_proposal_titles) != len(fr_proposal_titles):
            if len(fr_proposal_titles) == 0 and len(nl_proposal_titles) % 2 == 0:
                # Just split into 2. Simply assuming the first half is dutch (we might use tools to recognize languages if this doesn't turn out right
                middle = int(len(nl_proposal_titles) / 2)
                fr_proposal_titles = nl_proposal_titles[middle:]
                nl_proposal_titles = nl_proposal_titles[:middle]
            else:
                ctx.add_problem("NL_FR_TITLE_COUNT_DIFFERENT",
                                level2_item.label)
                continue

        proposal_discussion_id = f"{plenary_id}_d{level2_item.label}"

        level3_groups = create_level3_tag_groups(level2_item.body)
        level3_items = find_report_items(level3_groups, is_level3_title)

        discussion_items = [
            item for item in level3_items if is_article_discussion_item(item)]
        if not discussion_items:
            # 55_261_d20 doesn't have a discussion part -> fall back to the entire text as discussion body
            logger.info(
                "%s does not have a discussion part. Using fallback.", proposal_discussion_id)
            discussion_body = level2_item.body
        else:
            if len(discussion_items) > 1:
                ctx.add_problem(
                    "MULTIPLE_DISCUSSION_ANNOUNCEMENTS", proposal_discussion_id)
                continue

            discussion_item = discussion_items[0]
            discussion_body = discussion_item.body

        proposals = []
        if len(nl_proposal_titles) != len(fr_proposal_titles):
            ctx.add_problem("NL_FR_PROPOSAL_COUNT_MISMATCH",
                            proposal_discussion_id)
            continue

        for proposal_idx, (nl, fr) in enumerate(zip(nl_proposal_titles, fr_proposal_titles)):
            nl_proposal_text = normalize_whitespace(nl.text)
            fr_proposal_text = normalize_whitespace(fr.text)
            _nl_label, nl_text, nl_doc_ref = __split_number_title_doc_ref(
                nl_proposal_text)
            _fr_label, fr_text, _fr_doc_ref = __split_number_title_doc_ref(
                fr_proposal_text)

            if nl_doc_ref != _fr_doc_ref:
                ctx.add_problem("nl_doc_ref and fr_doc_ref are different", f"{plenary_id} proposal {proposal_idx}")
            proposal_id = f"{proposal_discussion_id}_p{proposal_idx}"
            proposals.append(Proposal(proposal_id, nl_doc_ref,
                                      nl_text.strip(), fr_text.strip()))

        if "verzoek om advies van de raad van state" in nl_proposal_text.lower():
            description_nl_tags = [el for el in discussion_body if el.text.strip() != ""]
            description_nl = normalize_whitespace(" ".join([el.text for el in description_nl_tags]))
            description_fr_tags = [el for el in discussion_body if el.text.strip() != ""]
            description_fr = normalize_whitespace(" ".join([el.text for el in description_fr_tags]))
        else:
            description_nl_tags = [
                el
                for el in discussion_body
                if el.text.strip() != "" and determine_discussion_body_language(el) in ["nl", None]
            ]
            description_nl = normalize_whitespace(" ".join([el.text for el in description_nl_tags]))
            description_fr_tags = [
                el
                for el in discussion_body
                if el.text.strip() != "" and determine_discussion_body_language(el) in ["fr", None]
            ]
            description_fr = normalize_whitespace(" ".join(el.text for el in description_fr_tags))

        pd = ProposalDiscussion(
            proposal_discussion_id,
            plenary_id,
            plenary_agenda_item_number=int(level2_item.label, 10),
            description_nl=description_nl,
            description_nl_tags=description_nl_tags,
            description_fr=description_fr,
            description_fr_tags=description_fr_tags,
            proposals=proposals
        )

        proposal_discussions.append(pd)

    return proposal_discussions


def determine_discussion_body_language(el: Tag) -> Optional[str]:
    if tag_has_class(el, "NormalNL"):
        return "nl"
    if tag_has_class(el, "NormalFR"):
        return "fr"
    if el.lang == "NL":
        return "nl"
    if el.lang == "FR":
        return "fr"

    return None


def _report_items_to_motion_groups(ctx: PlenaryExtractionContext, plenary_id: str, report_items: List[ReportItem]) \
    -> List[MotionGroup]:
    # get motions for each report item and flatten
    return [_report_item_to_motion_group(ctx, plenary_id, item, index) for index, item in enumerate(report_items)]


def _report_item_to_motion_group(ctx: PlenaryExtractionContext, plenary_id: str, item: ReportItem,
                                 index: int) -> MotionGroup:
    motion_group_number = int(item.label, 10) if item.label is not None else (- index)
    motion_group_id = f"{plenary_id}_mg_{motion_group_number}"

    _, motion_group_title_nl, doc_ref_nl = __split_number_title_doc_ref(
        normalize_whitespace(item.nl_title))
    _, motion_group_title_fr, doc_ref_fr = __split_number_title_doc_ref(
        normalize_whitespace(item.fr_title))

    if doc_ref_nl != doc_ref_fr:
        ctx.add_problem("DOC_REF_NL_FR_DIFFERENT", motion_group_id)

    motions = []
    motion_tag_groups = split_motion_group_item(ctx, item)
    for group_index, motion_tag_group in enumerate(motion_tag_groups):
        motion = construct_motion(ctx, group_index, motion_group_number, motion_group_id, motion_group_title_fr, motion_group_title_nl,
                                  motion_tag_group, plenary_id, doc_ref_nl)
        motions.append(motion)

    return MotionGroup(
        motion_group_id,
        motion_group_number,
        motion_group_title_nl,
        motion_group_title_fr,
        doc_ref_nl,
        motions)  # The link with a proposal will be filled in later, by the motion_document_proposal_linker.py.


def construct_motion(ctx, index, motion_group_number, motion_group_id, motion_group_title_fr, motion_group_title_nl,
                     motion_tag_group, plenary_id, motion_group_doc_ref) -> Motion:
    motion_id = f"{motion_group_id}_m{index}"
    voting_numbers = find_voting_numbers(motion_tag_group)
    voting_numbers = list(dict.fromkeys(voting_numbers))
    if len(voting_numbers) > 1:
        ctx.add_problem("MOTION_HAS_MULTIPLE_VOTING_IDS", motion_id)
    voting_number = voting_numbers[-1] if voting_numbers else None
    voting_id = f"{plenary_id}_v{voting_number}" if voting_number else None
    cancelled = any("wordt geannuleerd" in normalize_whitespace(
        tag.text).lower() for tag in motion_tag_group)

    # Often, within motion groups, each motion starts with 2 HTML tags that are "Vote sur..." / "Stemming over...",
    # this occurs particularly often when motion groups contain multiple amendments:
    title_tag_nl, title_tag_fr = find_nl_and_fr_tag(motion_tag_group[:2])
    title_fr = title_tag_fr.text.strip()
    title_nl = title_tag_nl.text.strip()
    _label_nl, title_nl, doc_ref_fr = __split_number_title_doc_ref(title_nl)
    _label_fr, title_fr, doc_ref_nl = __split_number_title_doc_ref(title_fr)
    if doc_ref_fr != doc_ref_nl:
        ctx.add_problem("MOTION_DOC_REF_DIFFERENCE_NL_FR", motion_id)

    # However, sometimes, the first two HTML tags within the motion group are NOT Dutch and French titles for the
    # motion. They simply are the start of the textual description of the motion.
    # Then we can use the already extracted title
    # This is particularly often the case when a motion group contains only one motion, but not always: even if a
    # motion group contains only one motion, it sometimes still starts with "Vote sur...", which is the actual
    # motion title.
    # It is safer to look for the absense of "Vote sur..." / "Stemming over..." than to count the motion elements.
    if not title_fr.startswith("Vote sur") and not title_nl.startswith("Stemming over"):
        title_nl, title_fr = motion_group_title_nl, motion_group_title_fr
        doc_ref_nl = motion_group_doc_ref

    description = normalize_whitespace(
        "\n".join([t.text for t in motion_tag_group[2:]]))
    motion = Motion(motion_id, str(motion_group_number), title_nl, title_fr,
                    doc_ref_nl, voting_id, cancelled, description)

    return motion


def find_nl_and_fr_tag(tags: List[Tag]) -> Tuple[Tag, Tag]:
    if len(tags) == 0:
        raise Exception(f"no tags {tags}")
    if len(tags) < 2:
        raise Exception("only 1 tag: {tags}")

    if 'NormalNL' in get_class(tags[0]) or 'NormalFR' in get_class(tags[1]):
        return tags[0], tags[1]

    return tags[1], tags[0]


def find_voting_numbers(motion_tags):
    pattern1 = re.compile("\\(Stemming/vote\\s+(\\d+)", re.IGNORECASE)
    pattern2 = re.compile("\\(Vote/stemming\\s+(\\d+)", re.IGNORECASE)
    result = []

    for tag in motion_tags:
        norm_text = normalize_whitespace(tag.text)
        match1 = pattern1.match(norm_text)
        if match1:
            result.append(match1.group(1))
        match2 = pattern2.match(norm_text)
        if match2:
            result.append(match2.group(1))

    return result


STATE_INTRO = "INTRO"
STATE_VOTE_STARTED = "STARTED"
STATE_VOTE_TABLE_FOUND = "VOTE_TABLE_FOUND"
STATE_VOTE_REUSE_FOUND = "VOTE_REUSE_FOUND"

TAG_CLASS_MISC = "MISC"
TAG_CLASS_EMPTY = "EMPTY"
TAG_CLASS_START_VOTE = "START_VOTE"
TAG_CLASS_VOTE_TABLE = "VOTE_TABLE"
TAG_CLASS_VOTE_REUSE = "VOTE_REUSE"
TAG_CLASS_VOTE_CANCELLED = "VOTE_CANCELLED"


def split_motion_group_item(ctx: PlenaryExtractionContext, item):
    result = []

    motion_tags = []

    state = STATE_INTRO

    # Initialising with 'None' will make us fail fast when the state machine has bugs
    count_since_reuse = None
    count_since_table = None

    for tag in item.body:
        norm_text = normalize_whitespace(tag.text).lower()

        if len(norm_text) == 0:
            tag_class = TAG_CLASS_EMPTY
        elif "begin van de stemming" in norm_text:
            tag_class = TAG_CLASS_START_VOTE
        elif "wordt geannuleerd" in norm_text:
            tag_class = TAG_CLASS_VOTE_CANCELLED
        elif tag.name == "table" and norm_text.startswith("(stemming/vote "):
            tag_class = TAG_CLASS_VOTE_TABLE
        elif norm_text.startswith("(stemming/vote ") or norm_text.startswith("(vote/stemming "):
            tag_class = TAG_CLASS_VOTE_REUSE
        else:
            tag_class = TAG_CLASS_MISC

        motion_tags.append(tag)
        if state == STATE_INTRO:
            if tag_class == TAG_CLASS_START_VOTE:
                state = STATE_VOTE_STARTED
            elif tag_class == TAG_CLASS_VOTE_REUSE:
                state = STATE_VOTE_REUSE_FOUND
                count_since_reuse = 0
        elif state == STATE_VOTE_STARTED:
            motion_tags.append(tag)
            if tag_class == TAG_CLASS_START_VOTE:
                raise Exception(
                    f"Unexpected 'Begin van de stemming' at {ctx.report_path}/{item.label}")
            if tag_class == TAG_CLASS_VOTE_CANCELLED:
                state = STATE_INTRO
            if tag_class == TAG_CLASS_VOTE_TABLE:
                state = STATE_VOTE_TABLE_FOUND
                count_since_table = 0
        elif state == STATE_VOTE_TABLE_FOUND:
            if tag_class != TAG_CLASS_EMPTY:
                # TODO: check if the tags match specific patterns, otherwise report as problem
                count_since_table += 1
            if count_since_table == 2:
                # start new group
                result.append(motion_tags)
                motion_tags = []
                state = STATE_INTRO
                count_since_reuse = None
                count_since_table = None
        elif state == STATE_VOTE_REUSE_FOUND:
            if tag_class != TAG_CLASS_EMPTY:
                # TODO: check if the tags match specific patterns, otherwise report as problem
                count_since_reuse += 1
            if count_since_reuse == 2:
                # start new group
                result.append(motion_tags)
                motion_tags = []
                state = STATE_INTRO
                count_since_reuse = None
                count_since_table = None

    if motion_tags:
        result.append(motion_tags)

    # hacky way to make sure the last group of tags contains at least a vote (not cancelled / cancelled / reused)
    def contains_vote(tag):
        tag_text = normalize_whitespace(tag.text).lower()
        if "wordt geannuleerd" in tag_text:
            return True
        if tag.name == "table" and tag_text.startswith("(stemming/vote "):
            return True
        if tag_text.startswith("(stemming/vote ") or tag_text.startswith("(vote/stemming "):
            return True

        return False

    if len(result) > 1:
        if not any(contains_vote(t) for t in result[-1]):
            last_group = result.pop()
            result[-1].extend(last_group)

    return result


def __find_siblings_between_elements(
    start_element,
    stop_element_name: str,
    filter_tag_name: str = None,
    filter_class_name: str = None):
    """
    Find all sibling elements (tags) between two elements (tags), or until no siblings remain within the parent element.
    The start and stop elements are not included in the results.

    For example, with the following piece of HTML:

    <h1>Header 1</h1>
    <p>Paragraph 1</p>
    <p>Paragraph 2</p>
    <h1>Header 2</h1>

    When calling __find_siblings_between_elements() with the first h1 element as start element,
    and "h1" as stop element, the two paragraphs in between will be returned.
    """
    siblings = []

    # the start element is not included in the results:
    next_sibling_element, next_sibling_element_name = __get_next_sibling_tag_name(
        start_element)

    while (next_sibling_element_name is not None and next_sibling_element_name != stop_element_name):
        if filter_tag_name and next_sibling_element_name == filter_tag_name:
            siblings.append(next_sibling_element)

        if filter_class_name and not isinstance(next_sibling_element, NavigableString) \
            and "class" in next_sibling_element.attrs and filter_class_name in next_sibling_element.attrs["class"]:
            siblings.append(next_sibling_element)

        if not filter_tag_name and not filter_class_name:
            siblings.append(next_sibling_element)

        next_sibling_element, next_sibling_element_name = __get_next_sibling_tag_name(
            next_sibling_element)

    return siblings


def __get_next_sibling_tag_name(element):
    next_element = element.next_sibling
    next_element_name = ""
    if next_element is None:  # There just is no next element anymore.
        next_element_name = None
    elif not isinstance(next_element, NavigableString):  # = Text in the HTML that is not enclosed within tags, it has no .name.
        next_element_name = next_element.name
    return next_element, next_element_name


def __split_number_title_doc_ref(proposal_title) -> Tuple[Optional[int], str, str]:
    # Extract the proposal number and title:
    title = proposal_title

    item_number_pattern = re.compile("^(\\d+)\\W")
    number_match = item_number_pattern.search(title)
    number = int(number_match.group(1), 10) if number_match else None
    if number_match:
        title = title[number_match.end():]

    doc_ref_pattern = re.compile("\\(([\\d/-]*)\\)")
    doc_ref_match = doc_ref_pattern.search(title)
    doc_ref = doc_ref_match.group(1) if doc_ref_match else None
    if doc_ref_match:
        title = title[:doc_ref_match.start()]

    # TODO: detect multiple document references and report as problems

    return number, title.strip(), doc_ref


def _extract_votes(ctx: PlenaryExtractionContext, plenary_id: str) -> List[Vote]:
    tokens = WhitespaceTokenizer().tokenize(ctx.html.text)

    votings = find_occurrences(
        tokens, "Vote nominatif - Naamstemming:".split(" "))

    bounds = zip(votings, votings[1:] + [len(tokens)])
    voting_sequences = [tokens[start:end] for start, end in bounds]

    votes = []

    for seq in voting_sequences:
        voting_number = str(int(seq[4], 10))
        voting_id = f"{plenary_id}_v{voting_number}"

        # Extract detailed votes:
        yes_start = get_sequence(seq, ["Oui"])
        no_start = get_sequence(seq, ["Non"])
        abstention_start = get_sequence(seq, ["Abstentions"])

        if yes_start is None:
            ctx.add_problem("YES_PART_NOT_FOUND", voting_id)
            continue
        if no_start is None:
            ctx.add_problem("NO_PART_NOT_FOUND", voting_id)
            continue
        if abstention_start is None:
            ctx.add_problem("ABSTENTION_PART_NOT_FOUND", voting_id)
            continue
        if not yes_start < no_start < abstention_start:
            ctx.add_problem("VOTES_YES_NO_ABSTENTION_OUT_OF_ORDER", voting_id)
            continue

        yes_count = int(seq[yes_start + 1], 10)
        no_count = int(seq[no_start + 1], 10)
        abstention_count = int(seq[abstention_start + 1], 10)

        yes_voter_names = get_names(
            seq[yes_start + 3: no_start], yes_count, 'yes', voting_id)
        no_voter_names = get_names(
            seq[no_start + 3:abstention_start], no_count, 'no', voting_id)
        abstention_voter_names = get_names(
            seq[abstention_start + 3:], abstention_count, 'abstention', voting_id)

        votes.extend(
            create_votes_for_same_vote_type(yes_voter_names, VoteType.YES, voting_id, ctx.politicians) +
            create_votes_for_same_vote_type(no_voter_names, VoteType.NO, voting_id, ctx.politicians) +
            create_votes_for_same_vote_type(
                abstention_voter_names, VoteType.ABSTENTION, voting_id, ctx.politicians)
        )

    return votes


def _extract_motion_report_items(ctx: PlenaryExtractionContext) -> List[ReportItem]:
    naamstemmingen_title = find_naamstemmingen_title(ctx)
    if naamstemmingen_title is None:
        return []
    return _extract_report_items(ctx.report_path, naamstemmingen_title.find_next_siblings())


def _extract_report_items(report_path: str, elements: List[Tag]) -> List[ReportItem]:
    if not elements:
        return []

    item_titles = list(filter(is_report_item_title, elements))

    if not item_titles:  # this check doesn't feel
        logger.warning("No report item titles after naamstemmingen in %s", report_path)
        return []

    tag_groups = create_level2_tag_groups(elements)
    report_items = find_report_items(tag_groups)

    return [item for item in report_items if (item.nl_title.strip() != "" or item.fr_title.strip() != "")]


def is_report_item_title(el: Tag):
    if el.name == "h2":
        return True
    if el.name == "p" and any(clazz in ["Titre2NL", "Titre2FR"] for clazz in ((el and el.get("class")) or [])):
        return True

    return False


def find_naamstemmingen_title(ctx: PlenaryExtractionContext):
    def is_start_naamstemmingen(el):
        if el.name == "h1" and ("naamstemmingen" == el.text.lower().strip()):
            return True
        if el.name == "p" and ("naamstemmingen" == el.text.lower().strip()) and ("Titre1NL" in el.get("class")):
            return True
        return False

    start_naamstemmingen = list(
        filter(is_start_naamstemmingen, ctx.html.find_all()))
    if not start_naamstemmingen:
        # Not a problem, naamstemmingen doesn't happen in every plenary
        return None

    if len(start_naamstemmingen) > 1:
        ctx.add_problem("MULTIPLE_START_NAAMSTEMMINGEN")
        return None

    return start_naamstemmingen[0]


def get_class(el):
    classes = el.get("class")
    if not classes:
        return []
    return classes


def create_level2_tag_groups(tags):
    return create_tag_groups(tags, is_level2_title)


def create_level3_tag_groups(tags):
    return create_tag_groups(tags, is_level3_title)


def create_tag_groups(tags, header_condition):
    """ Creates groups that consist of consecutive titles followed by non-titles"""

    groups = []
    current_group = []

    # Iterate over tags
    # Every time we switch from non-title to title a new group starts
    last_was_title = True
    for tag in tags:
        if tag.text.strip() == "":  # ignore empty tags (see motion 23 of ip271)
            continue
        if header_condition(tag):
            if not last_was_title and current_group:
                groups.append(current_group)
                current_group = []
            last_was_title = True
        else:
            last_was_title = False

        current_group.append(tag)

    if current_group:
        groups.append(current_group)

    return groups


def is_level1_title(tag):
    return (tag.name == "h1") or (
        tag.name == "p" and any(clazz in ['Titre1FR', 'Titre1NL'] for clazz in tag.get("class")))


def is_level2_title(tag) -> bool:
    return (tag.name == "h2") or (
        tag.name == "p" and any(clazz in ['Titre2FR', 'Titre2NL'] for clazz in tag.get("class")))


def is_level3_title(tag) -> bool:
    return (tag.name == "h3") or (
        tag.name == "p" and any(clazz in ['Titre3FR', 'Titre3NL'] for clazz in tag.get("class")))


def find_report_items(tag_groups, header_condition=is_level2_title):
    result = []

    for tag_group in tag_groups:
        titles = [tag for tag in tag_group if header_condition(tag)]

        fr_title_tags = [tag for tag in titles if is_french_title(tag)]
        nl_title_tags = [tag for tag in titles if is_dutch_title(tag)]

        fr_title = "\n".join([tag.text for tag in fr_title_tags])
        nl_title = "\n".join([tag.text for tag in nl_title_tags])

        remaining_elements = [tag for tag in tag_group if not header_condition(
            tag) if tag.text.strip() != ""]

        body_text_parts = [create_body_text_part(
            el) for el in remaining_elements]

        label_pattern = re.compile("^(\\d+)")
        label = None
        for title in titles:
            label_match = re.search(label_pattern, title.text.strip())
            label = None if not label_match else label_match.group(1)
            if label is not None:
                break

        result.append(ReportItem(label, nl_title, nl_title_tags, fr_title, fr_title_tags, body_text_parts,
                                 remaining_elements))

    return result


def _has_nl_title_class(el):
    return tag_has_class(el, "Titre1NL") or tag_has_class(el, "Titre2NL") or tag_has_class(el, "Titre3NL")


def _has_fr_title_class(el):
    return tag_has_class(el, "Titre1FR") or tag_has_class(el, "Titre2FR") or tag_has_class(el, "Titre3FR")


def is_dutch_title(tag):
    if _has_fr_title_class(tag):
        return False
    return _has_nl_title_class(tag) or (tag.name in ["h1", "h2", "h3"] and tag.select('span[lang="NL"]'))


def is_french_title(tag):
    # may is not a perfect heuristic (esp when tag is not a title tag), but atm it's only used on title tags AND
    # it has nice property of always being the opposite of is_dutch_title
    return not is_dutch_title(tag)


def tag_has_class(tag, clazz):
    class_values = tag.get("class") or []

    if not class_values:
        return False

    return clazz in class_values


def create_body_text_part(el) -> BodyTextPart:
    nl = False
    fr = False

    if 'NormalNL' in (el.get('class') or []):
        nl = True
    if 'NormalFR' in (el.get('class') or []):
        fr = True

    lang = "unknown"
    if nl ^ fr:
        lang = "nl" if nl else "fr"

    # TODO: analyse elements with unknown language more

    # TODO: detect and add structural insights (e.g. finding standard phrases like Begin van de stemming/Einde van de stemming/Uitslag van de stemming/...)

    return BodyTextPart(lang, el.text)


def _elements_between(element1, element2):
    elements = []
    current_element = element1

    while current_element != element2:
        current_element = current_element.find_next()
        if current_element is None:
            break

        # avoid copying script tags, that could be bad
        if current_element.name == "script":
            continue

        elements.append(current_element)

    return elements


def find_occurrences(tokens, query):
    result = []
    pos = find_sequence(tokens, query)
    while pos > -1:
        result.append(pos)
        pos = find_sequence(tokens, query, pos + 1)

    return result


def find_sequence(tokens, query, start_pos=0):
    """@return index where the token sequence 'query' occurs in given tokens or -1 if the query sequence is not found"""
    if query[0] not in tokens:
        return -1
    pos = start_pos
    while query[0] in tokens[pos:]:
        next_pos = tokens.index(query[0], pos)
        if next_pos != -1:
            if tokens[next_pos:next_pos + len(query)] == query:
                return next_pos
        pos = next_pos + 1

    return -1


def get_motion_blocks_by_nr(report, html):
    result = {}
    vote_re = re.compile("\\(Stemming/vote \\(?(.*)\\)")

    for block in get_motion_blocks(html):
        match = vote_re.search(block[0].strip())
        if match is not None:
            logger.debug("%s: found stemming %s", report, match.group(1))
            nr = int(match.group(1), 10)
            result[nr] = block[1:]

    return result


def get_motion_blocks(html):
    try:
        naamstemmingen = next(
            filter(lambda s: s and "Naamstemmingen" in s.text, html.find_all('span')))
    except StopIteration:
        return []

    paragraphs = naamstemmingen.find_all_next()

    sections = []
    in_text = False
    current = ['unknown']
    for el in paragraphs:
        if in_text:
            if el.name == 'table':  # table indicates start of vote section
                in_text = False
                span_in_table = el.find('span')
                if span_in_table:
                    current[0] = span_in_table.text
                    sections.append(current)
            else:
                current.append(el)
        else:
            in_text = True
            current = ['unknown', el]

    return list(filter(lambda section: "Stemming/vote" in section[0], sections))


def get_sequence(tokens, query):
    """@return like find_sequence or None if the query was not found"""
    pos = find_sequence(tokens, query)
    if pos >= 0:
        return pos
    return None


def get_names(sequence, count, log_type, location="unknown location"):
    names = [n.strip().replace(".", "")
             for n in (" ".join(sequence).strip()).split(",") if n.strip() != '']

    if len(names) != count:
        logging.warning(
            "vote count (%d) ./does not match voters %s (%s) at %s", count, str(names), log_type, location)

    return names


def create_votes_for_same_vote_type(voter_names: List[str], vote_type: VoteType, motion_id: str,
                                    politicians: Politicians) -> List[Vote]:
    if voter_names is None:
        return []

    return [
        Vote(
            politicians.get_by_name(voter_name),
            motion_id,
            vote_type
        ) for voter_name in voter_names
    ]


def _get_plenary_date(ctx):
    first_table_paragraphs = [
        p.text for p in ctx.html.find('table').select('p')]
    text_containing_weekday = [t.lower() for t in first_table_paragraphs if any(m in t.lower() for m in DAYS_NL)]
    if len(text_containing_weekday) > 0:
        for candidate in text_containing_weekday:
            parts = re.split("\\s+", candidate)
            if len(parts) == 4:
                day = int(parts[1].strip())
                month = MONTHS_NL.index(parts[2].strip()) + 1
                year = int(parts[3].strip())
                if month > 0:
                    return datetime.date.fromisoformat(f"{year:d}-{month:02d}-{day:02d}")

    matches = [re.match("(\\d)+-(\\d+)-(\\d{4})", t.strip())
               for t in first_table_paragraphs]
    for match in [m for m in matches if m]:
        day = int(match.group(1), 10)
        month = int(match.group(2), 10)
        year = int(match.group(3), 10)
        return datetime.date.fromisoformat(f"{year:d}-{month:02d}-{day:02d}")

    ctx.add_problem("PLENARY_DATE_PARSING_FAILS")
    return None


def main():
    extract_from_html_plenary_reports(CONFIG.plenary_html_input_path("*.html"))


if __name__ == "__main__":
    main()
