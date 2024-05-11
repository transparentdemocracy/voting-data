"""
Extract info from HTML-formatted voting reports from the Belgian federal chamber's website,
see https://www.dekamer.be/kvvcr/showpage.cfm?section=/flwb/recent&language=nl&cfm=/site/wwwcfm/flwb/LastDocument.cfm.
"""
import datetime
import glob
import logging
import os
import re
from re import RegexFlag
from typing import Tuple, List, Optional

from bs4 import BeautifulSoup, NavigableString, Tag, PageElement
from nltk.tokenize import WhitespaceTokenizer
from tqdm.auto import tqdm

from transparentdemocracy import CONFIG
from transparentdemocracy.model import Motion, Plenary, Proposal, ProposalDiscussion, Vote, VoteType, ReportItem, \
	BodyTextPart
from transparentdemocracy.politicians.extraction import Politicians, load_politicians

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DAYS_NL = "maandag,dinsdag,woensdag,donderdag,vrijdag,zaterdag,zondag".split(",")
MONTHS_NL = "januari,februari,maart,april,mei,juni,juli,augustus,september,oktober,november,december".split(",")


def extract_from_html_plenary_reports(
		report_file_pattern: str = CONFIG.plenary_html_input_path("*.html"),
		num_reports_to_process: int = None) -> Tuple[List[Plenary], List[Vote]]:
	politicians = load_politicians()
	plenaries = []
	all_votes = []
	logging.info(f"Report files must be found at: {report_file_pattern}.")
	report_filenames = glob.glob(report_file_pattern)
	if num_reports_to_process is not None:
		report_filenames = report_filenames[:num_reports_to_process]
	logging.debug(f"Will process the following input reports: {report_filenames}.")

	for voting_report in tqdm(report_filenames, desc="Processing plenary reports..."):
		try:
			logging.debug(f"Processing input report {voting_report}...")
			if voting_report.endswith(".html"):
				plenary, votes = extract_from_html_plenary_report(voting_report, politicians)
				plenaries.append(plenary)
				all_votes.extend(votes)
			else:
				raise RuntimeError("Plenary reports in other formats than HTML cannot be processed.")

		except Exception as e:
			# raise e
			logging.warning("Failed to process %s", voting_report, exc_info=True)

	return plenaries, all_votes


def extract_from_html_plenary_report(report_filename: str, politicians: Politicians = None) -> Tuple[
	Plenary, List[Vote]]:
	politicians = politicians or load_politicians()
	html = _read_plenary_html(report_filename)
	return _extract_plenary(report_filename, html, politicians)


def _read_plenary_html(report_filename):
	with open(report_filename, "r", encoding="cp1252") as file:
		html_content = file.read()
	html = BeautifulSoup(html_content, "html.parser")  # "lxml")
	return html


def _extract_plenary(report_path: str, html, politicians: Politicians) -> Tuple[Plenary, List[Vote]]:
	plenary_number = os.path.split(report_path)[1][2:5]  # example: ip078x.html -> 078
	legislature = 55  # We currently only process plenary reports from legislature 55 with our download script.
	plenary_id = f"{legislature}_{plenary_number}"  # Concatenating legislature and plenary number to construct a unique identifier for this plenary.
	proposals = __extract_proposal_discussions(report_path, html, plenary_id)
	motion_report_items, motions = _extract_motions(plenary_id, report_path, html)
	votes = _extract_votes(plenary_id, html, politicians)

	return (
		Plenary(
			plenary_id,
			int(plenary_number),
			_get_plenary_date(report_path, html),
			legislature,
			f"https://www.dekamer.be/doc/PCRI/pdf/55/ip{plenary_number}.pdf",
			f"https://www.dekamer.be/doc/PCRI/html/55/ip{plenary_number}x.html",
			proposals,
			motions,
			motion_report_items
		),
		votes
	)


def _extract_motions(plenary_id, report_filename, html):
	motion_report_items = _extract_motion_report_items(report_filename, html)
	motions = _report_items_to_motions(plenary_id, motion_report_items)
	return motion_report_items, motions


def is_article_discussion_item(item: ReportItem) -> bool:
	white = re.compile("\\s+")
	normalized_nl = re.sub(white, " ", item.nl_title).strip().lower()
	return normalized_nl == "bespreking van de artikelen"


def __extract_proposal_discussions(report_path, html, plenary_id: str) -> List[ProposalDiscussion]:
	proposal_discussions = []

	# We'll be able to extract the proposals after the header of the proposals section in the plenary report:
	level1_headers = [
		el for el in html.find_all()
		if is_level1_title(el)
	]

	if not level1_headers:
		raise Exception("no level1 found - analyse and fix if this occurs.")

	proposal_section_headers = [
		el for el in level1_headers if
		el.text.strip().lower() in ["projets de loi", "wetsontwerpen en voorstellen",
									"wetsontwerpen"]
	]
	if not proposal_section_headers:
		raise Exception("no proposal header found - analyse and fix if this occurs.")

	proposal_header_idx = level1_headers.index(proposal_section_headers[-1])
	next_level1_headers = level1_headers[proposal_header_idx + 1:]

	if next_level1_headers:
		proposal_discussion_elements = proposal_section_headers[-1].find_next_siblings()
		next_level1_index = proposal_discussion_elements.index(next_level1_headers[0])
		proposal_discussion_elements = proposal_discussion_elements[:next_level1_index]
	else:
		proposal_discussion_elements = proposal_section_headers[-1].find_next_siblings()

	proposal_discussion_elements = [el for el in proposal_discussion_elements if el.text.strip() != ""]

	# print("PROPOSALS FROM", proposal_discussion_elements[0].text)
	# print("PROPOSALS TO", proposal_discussion_elements[-1].text)

	tag_groups = create_level2_tag_groups(proposal_discussion_elements)
	report_items = find_report_items(report_path, tag_groups)

	for level2_item in report_items:
		nl_proposals = level2_item.nl_title_tags
		fr_proposals = level2_item.fr_title_tags

		if level2_item.label == "??":
			raise Exception("no label", level2_item.fr_title)

		if len(nl_proposals) != len(fr_proposals):
			raise Exception(
				f"{report_path}: {level2_item.label} number of proposal tags nl/fr doesn't match up - analyse and fix if this happens")

		proposal_id = f"{plenary_id}_d{level2_item.label}"

		level3_groups = create_level3_tag_groups(level2_item.body)
		level3_items = find_report_items(report_path, level3_groups, is_level3_title)

		discussion_items = [item for item in level3_items if is_article_discussion_item(item)]
		if not discussion_items:
			raise Exception(f"{proposal_id} could not find announcement of discussion")
		if len(discussion_items) > 1:
			raise Exception(f"{proposal_id} discussion was announced more than once?")

		discussion_item = discussion_items[0]

		proposals = []
		if len(level2_item.nl_title_tags) != len(level2_item.fr_title_tags):
			raise Exception(f"{proposal_id} {level2_item.label} proposal discussion nl/fr title tags does not match")

		white = re.compile("\\s+")

		for nl, fr in zip(level2_item.nl_title_tags, level2_item.fr_title_tags):
			nl_proposal_text = re.sub(white, " ", nl.text).strip()
			fr_proposal_text = re.sub(white, " ", fr.text).strip()
			nl_label, nl_text, nl_doc_ref = __split_proposal_header(nl_proposal_text)
			fr_label, fr_text, fr_doc_ref = __split_proposal_header(fr_proposal_text)
			# TODO: additional verification: are nl label and doc ref equal to fr label and doc ref?
			proposals.append(Proposal(nl_doc_ref, nl_text.strip(), fr_text.strip()))

		pd = ProposalDiscussion(
			proposal_id,
			plenary_id,
			plenary_agenda_item_number=int(level2_item.label, 10),
			description_nl=re.sub(white, " ",
								  " ".join([el.text for el in discussion_item.body_text_parts if el.lang == "nl"])),
			description_fr=re.sub(white, " ",
								  " ".join([el.text for el in discussion_item.body_text_parts if el.lang == "fr"])),
			proposals=proposals
		)

		proposal_discussions.append(pd)

	return proposal_discussions


def _report_items_to_motions(plenary_id: str, report_items: List[ReportItem]):
	# get motions for each report item and flatten
	return [m for item in report_items for m in _report_item_to_motions(plenary_id, item)]


def _report_item_to_motions(plenary_id: str, item: ReportItem) -> List[Motion]:
	proposal_id = f"{plenary_id}_{item.label}"

	stemming_re = re.compile("\\(Stemming/vote\\W+(\\d+)", RegexFlag.MULTILINE)
	canceled_re = re.compile("\\(Stemming\\W\\D*(\\d+).*geannuleerd", RegexFlag.MULTILINE)

	result = []
	for el in item.body:
		match_canceled = canceled_re.match(el.text)
		if match_canceled:
			motion_number = match_canceled.group(1)
			motion_id = f"{plenary_id}_{motion_number}"
			result.append(Motion(motion_id, motion_number, proposal_id, True))
			continue

		if el.name != "table":
			continue

		match_voting = stemming_re.search(el.text)
		if match_voting:
			motion_number = match_voting.group(1)
			motion_id = f"{plenary_id}_{motion_number}"
			cancelled = "geannuleerd" in el.text.lower()
			result.append(Motion(motion_id, motion_number, proposal_id, cancelled))

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
	next_sibling_element, next_sibling_element_name = __get_next_sibling_tag_name(start_element)

	while (next_sibling_element_name is not None and next_sibling_element_name != stop_element_name):
		if filter_tag_name and next_sibling_element_name == filter_tag_name:
			siblings.append(next_sibling_element)

		if filter_class_name and type(next_sibling_element) is not NavigableString \
				and "class" in next_sibling_element.attrs and filter_class_name in next_sibling_element.attrs["class"]:
			siblings.append(next_sibling_element)

		if not filter_tag_name and not filter_class_name:
			siblings.append(next_sibling_element)

		next_sibling_element, next_sibling_element_name = __get_next_sibling_tag_name(next_sibling_element)

	return siblings


def __get_next_sibling_tag_name(element):
	next_element = element.next_sibling
	next_element_name = ""
	if next_element is None:  # There just is no next element anymore.
		next_element_name = None
	elif type(
			next_element) is not NavigableString:  # = Text in the HTML that is not enclosed within tags, it has no .name.
		next_element_name = next_element.name
	return next_element, next_element_name


def __split_proposal_header(proposal_title) -> Tuple[Optional[int], str, str]:
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

	return number, title, doc_ref


def _extract_votes(plenary_id: str, html, politicians: Politicians) -> List[Vote]:
	tokens = WhitespaceTokenizer().tokenize(html.text)

	votings = find_occurrences(tokens, "Vote nominatif - Naamstemming:".split(" "))

	bounds = zip(votings, votings[1:] + [len(tokens)])
	voting_sequences = [tokens[start:end] for start, end in bounds]

	votes = []

	for seq in voting_sequences:
		motion_number = str(int(seq[4], 10))
		motion_id = f"{plenary_id}_{motion_number}"

		# Extract detailed votes:
		yes_start = get_sequence(seq, ["Oui"])
		no_start = get_sequence(seq, ["Non"])
		abstention_start = get_sequence(seq, ["Abstentions"])

		if not (yes_start < no_start < abstention_start):
			raise Exception("Could not parse voting sequence: %s", (" ".join(seq)))

		yes_count = int(seq[yes_start + 1], 10)
		no_count = int(seq[no_start + 1], 10)
		abstention_count = int(seq[abstention_start + 1], 10)

		yes_voter_names = get_names(seq[yes_start + 3: no_start], yes_count, 'yes', motion_id)
		no_voter_names = get_names(seq[no_start + 3:abstention_start], no_count, 'no', motion_id)
		abstention_voter_names = get_names(seq[abstention_start + 3:], abstention_count, 'abstention', motion_id)

		votes.extend(
			create_votes_for_same_vote_type(yes_voter_names, VoteType.YES, motion_id, politicians) +
			create_votes_for_same_vote_type(no_voter_names, VoteType.NO, motion_id, politicians) +
			create_votes_for_same_vote_type(abstention_voter_names, VoteType.ABSTENTION, motion_id, politicians)
		)

	return votes


def _extract_motion_report_items(report_path: str, html: Tag) -> List[ReportItem]:
	naamstemmingen_title = find_naamstemmingen_title(report_path, html)
	if naamstemmingen_title is None:
		return []
	return _extract_report_items(report_path, naamstemmingen_title.find_next_siblings())


def _extract_report_items(report_path: str, elements: List[PageElement]) -> List[ReportItem]:
	if not elements:
		return []

	item_titles = list(filter(is_report_item_title, elements))

	if not item_titles:  # this check doesn't feel
		logger.warning(f"No report item titles after naamstemmingen in {report_path}")
		return []

	tag_groups = create_level2_tag_groups(elements)
	report_items = find_report_items(report_path, tag_groups)

	# TODO: should we filter items that are missing titles of is that not our concern?
	return [item for item in report_items if item.nl_title.strip() != "" and item.fr_title.strip() != ""]


def is_report_item_title(el):
	if el.name == "h2":
		return True
	if el.name == "p" and any([clazz in ["Titre2NL", "Titre2FR"] for clazz in ((el and el.get("class")) or [])]):
		return True

	return False


def find_naamstemmingen_title(report_path: str, html: Tag):
	def is_start_naamstemmingen(el):
		if el.name == "h1" and ("naamstemmingen" == el.text.lower().strip()):
			return True
		if el.name == "p" and ("naamstemmingen" == el.text.lower().strip()) and ("Titre1NL" in el.get("class")):
			return True
		return False

	start_naamstemmingen = list(filter(is_start_naamstemmingen, html.find_all()))
	if not start_naamstemmingen:
		return None

	if len(start_naamstemmingen) > 1:
		logger.warning(f"multiple candidates for start of 'naamstemmingen' in {report_path}.")
		raise Exception("if this happens we need to decide how to resolve this")

	return start_naamstemmingen[0]


def get_class(el):
	classes = el.get("class")
	if not classes:
		return []


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
			tag.name == "p" and any([clazz in ['Titre1FR', 'Titre1NL'] for clazz in tag.get("class")]))


def is_level2_title(tag) -> bool:
	return (tag.name == "h2") or (
			tag.name == "p" and any([clazz in ['Titre2FR', 'Titre2NL'] for clazz in tag.get("class")]))


def is_level3_title(tag) -> bool:
	return (tag.name == "h3") or (
			tag.name == "p" and any([clazz in ['Titre3FR', 'Titre3NL'] for clazz in tag.get("class")]))


def find_report_items(report_path, tag_groups, header_condition=is_level2_title):
	result = []

	for tag_group in tag_groups:
		titles = [tag for tag in tag_group if header_condition(tag)]

		fr_title_tags = [tag for tag in titles if is_french_title(tag)]
		nl_title_tags = [tag for tag in titles if is_dutch_title(tag)]

		fr_title = "\n".join([tag.text for tag in fr_title_tags])
		nl_title = "\n".join([tag.text for tag in nl_title_tags])

		remaining_elements = [tag for tag in tag_group if not header_condition(tag) if tag.text.strip() != ""]

		body_text_parts = [create_body_text_part(el) for el in remaining_elements]

		label_pattern = re.compile("^(\\d+)")
		label_match = re.search(label_pattern, nl_title.strip())
		label = None if not label_match else label_match.group(1)

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
	result = dict()
	vote_re = re.compile("\\(Stemming/vote \\(?(.*)\\)")

	for block in get_motion_blocks(html):
		match = vote_re.search(block[0].strip())
		if match is not None:
			logger.debug("%s: found stemming %s" % (report, match.group(1)))
			nr = int(match.group(1), 10)
			result[nr] = block[1:]

	return result


def get_motion_blocks(html):
	try:
		naamstemmingen = next(filter(lambda s: s and "Naamstemmingen" in s.text, html.find_all('span')))
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
	"""@return like find_sequence but raises ValueError if the query was not found"""
	pos = find_sequence(tokens, query)
	if pos >= 0:
		return pos
	raise ValueError("query %s not found in tokens %s" % (str(query), str(tokens)))


def get_names(sequence, count, log_type, location="unknown location"):
	names = [n.strip().replace(".", "") for n in (" ".join(sequence).strip()).split(",") if n.strip() != '']

	if len(names) != count:
		logging.warning(
			"vote count (%d) ./does not match voters %s (%s) at %s" % (count, str(names), log_type, location))

	return names


def create_votes_for_same_vote_type(voter_names: List[str], vote_type: VoteType, motion_id: str,
									politicians: Politicians) -> List[Vote]:
	if voter_names is None:
		return []
	else:
		return [
			Vote(
				politicians.get_by_name(voter_name),
				motion_id,
				vote_type.value
			) for voter_name in voter_names
		]


def _get_plenary_date(path, html):
	first_table_paragraphs = [p.text for p in html.find('table').select('p')]
	text_containing_weekday = [t.lower() for t in first_table_paragraphs if any([m in t.lower() for m in DAYS_NL])]
	if len(text_containing_weekday) > 0:
		for candidate in text_containing_weekday:
			parts = re.split("\\s+", candidate)
			if len(parts) == 4:
				day = int(parts[1].strip())
				month = MONTHS_NL.index(parts[2].strip()) + 1
				year = int(parts[3].strip())
				if month > 0:
					return datetime.date.fromisoformat("%d-%02d-%02d" % (year, month, day))

	matches = [re.match("(\\d)+-(\\d+)-(\\d{4})", t.strip()) for t in first_table_paragraphs]
	for match in [m for m in matches if m]:
		day = int(match.group(1), 10)
		month = int(match.group(2), 10)
		year = int(match.group(3), 10)
		return datetime.date.fromisoformat("%d-%02d-%02d" % (year, month, day))

	raise Exception(f"Could not find determine date for {path}")


def main():
	extract_from_html_plenary_reports(CONFIG.plenary_html_input_path("*.html"))


if __name__ == "__main__":
	main()
