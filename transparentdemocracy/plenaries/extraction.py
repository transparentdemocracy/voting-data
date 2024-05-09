"""
Extract info from HTML-formatted voting reports from the Belgian federal chamber's website,
see https://www.dekamer.be/kvvcr/showpage.cfm?section=/flwb/recent&language=nl&cfm=/site/wwwcfm/flwb/LastDocument.cfm.
"""
import datetime
import glob
import logging
import os
import re
from typing import Tuple, List, Any, OrderedDict
import unicodedata

from bs4 import BeautifulSoup, NavigableString
from nltk.tokenize import WhitespaceTokenizer
from tqdm.auto import tqdm

from transparentdemocracy import PLENARY_HTML_INPUT_PATH
from transparentdemocracy.model import Motion, Plenary, Proposal, ProposalDiscussion, Vote, VoteType, MotionData, BodyTextPart
from transparentdemocracy.politicians.extraction import Politicians, load_politicians

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DAYS_NL = "maandag,dinsdag,woensdag,donderdag,vrijdag,zaterdag,zondag".split(",")
MONTHS_NL = "januari,februari,maart,april,mei,juni,juli,augustus,september,oktober,november,december".split(",")


def extract_from_html_plenary_reports(
		report_file_pattern: str = os.path.join(PLENARY_HTML_INPUT_PATH, "*.html"),
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
	html = BeautifulSoup(html_content, "html.parser")   # "lxml")
	return html


def _extract_plenary(report_filename: str, html, politicians: Politicians) -> Tuple[Plenary, List[Vote]]:
	plenary_number = os.path.split(report_filename)[1][2:5]  # example: ip078x.html -> 078
	legislature = 55  # We currently only process plenary reports from legislature 55 with our download script.
	plenary_id = f"{legislature}_{plenary_number}"  # Concatenating legislature and plenary number to construct a unique identifier for this plenary.
	proposals = __extract_proposal_discussions(html, plenary_id)
	motions, votes = __extract_motions(plenary_id, html, politicians)
	motion_data = _extract_motiondata(report_filename, html)
	return (
		Plenary(
			plenary_id,
			int(plenary_number),
			__get_plenary_date(report_filename, html),
			legislature,
			f"https://www.dekamer.be/doc/PCRI/pdf/55/ip{plenary_number}.pdf",
			f"https://www.dekamer.be/doc/PCRI/html/55/ip{plenary_number}x.html",
			proposals,
			motions,
			motion_data
		),
		votes
	)


def __extract_proposal_discussions(html, plenary_id: str) -> List[Proposal]:
	proposal_discussions = []

	# We'll be able to extract the proposals after the header of the proposals section in the plenary report:
	proposals_section_header = [
		h1_span for h1_span in html.select("h1 span") 
		if h1_span.text in ["Projets de loi", "Wetsontwerpen en voorstellen"]
	][0].find_parent("h1")

	# Find all sibling h2 headers, until the next h1 header:
	# (Indeed, proposals_section_header.find_next_siblings("h2") returns headers that are not about proposals anymore, 
	# which are below next h1 section headers.)
	proposal_headers = [
		sibling for sibling in __find_siblings_between_elements(start_element=proposals_section_header, 
														  		stop_element_name="h1", filter_tag_name="h2")
		if type(sibling) is not NavigableString # = Text in the HTML that is not enclosed within tags
	]

	# Extract the proposal number and titles (in Dutch and French):
	previous_proposal_header = None
	header_idx_within_language = 0 # Important for processing multi-line headers: which line is currently processed.

	for proposal_header in proposal_headers:
		plenary_agenda_item_number, title, doc_ref = __split_proposal_header(proposal_header)
		if len(proposal_discussions) == 0 \
			or (plenary_agenda_item_number is not None 
	   			and int(plenary_agenda_item_number) > proposal_discussions[-1].plenary_agenda_item_number):
			# A new plenary agenda item number was found.
			header_idx_within_language = 0
			
			# First, extract the description of the previous proposal and save that:
			if len(proposal_discussions) > 0:
				description_nl, description_fr = __extract_proposal_description(previous_proposal_header) # last header of the previous proposal.
				proposal_discussions[-1].description_nl = description_nl
				proposal_discussions[-1].description_fr = description_fr

			# Then, create the new proposal discussion, corresponding with that plenary agenda item.
			# The first header of this agenda item always is in French.
			# So, we can already add the main proposal under discussion, with the found doc reference and *French* 
			# title:
			discussion_id = f"{plenary_id}_d{plenary_agenda_item_number}"
			proposal_discussions.append(
				ProposalDiscussion(
					discussion_id, plenary_id, int(plenary_agenda_item_number), 
					None, None, # The descriptions will be saved later, when the last h2 header of this proposal has been identified. (The description comes after that.)
					[
						Proposal(doc_ref, None, title)  # French title
					]
				))
		else:
			if plenary_agenda_item_number is None:
				# No plenary agenda item number is in front of the plenary agenda item number.
				# This introduces an additional proposal that is *related* to the discussion.
				# Indeed, sometimes multiple headers in the same language occur on consecutive lines, corresponding 
				# with a proposal discussion about multiple proposals.
				if proposal_discussions[-1].proposals[-1].title_nl is None: # No Dutch title has been saved yet.
					# If we are currently processing French headers, add the new related proposal, with the found 
					# document reference and *French* title:
					proposal_discussions[-1].proposals.append(Proposal(doc_ref, None, title))
				else:
					# If we are currently processing Dutch headers, set the *Dutch* title:
					proposal_discussions[-1].proposals[header_idx_within_language].title_nl = title
					assert doc_ref == proposal_discussions[-1].proposals[header_idx_within_language].document_reference
			else:
				# A plenary agenda item number is in front of the title, equal to the one that is currently being 
				# processed.
				# This introduces the header(s) for the proposal in Dutch.
				# Save the title of this first Dutch header:
				proposal_discussions[-1].proposals[0].title_nl = title
				assert doc_ref == proposal_discussions[-1].proposals[0].document_reference
				assert int(plenary_agenda_item_number) == proposal_discussions[-1].plenary_agenda_item_number
		
		previous_proposal_header = proposal_header
		header_idx_within_language += 1

	# Manual corrections:
	# Some errors after processing proposals are just impossible to correct with a general rule. They are just one-off # "formatting mistakes" in the plenary report that are not in line with the template.
	# We could correct them in our json dumps manually, but when generating the json dumps again, those manual 
	# corrections would be lost.
	# Therefore, we register - or *also* "register" them here:
	
	# - One proposal title was first mentioned in Dutch, instead of French. Switch the resulting titles:
	if plenary_id == "55_261":
		title_nl = proposal_discussions[0].proposals[0].title_nl
		proposal_discussions[0].proposals[0].title_nl = proposal_discussions[0].proposals[0].title_fr
		proposal_discussions[0].proposals[0].title_fr = title_nl

	return proposal_discussions


def __extract_proposal_description(proposal_header) -> Tuple[str, str]:
	"""
	First, still fetch the description of the previous plenary agenda item.
	Extract the description of the proposal, below the "Bespreking van de artikelen" header between the 
	proposal title, and the next proposal title.
	"""
	description_header = [
		sibling_tag for sibling_tag in __find_siblings_between_elements(start_element=proposal_header, 
											stop_element_name="h2", filter_class_name="Titre3NL")
		if type(sibling_tag) is not NavigableString # otherwise .findChild() cannot be used next.
		and sibling_tag.findChild("span").text.strip().replace("\n", " ") == "Bespreking van de artikelen"
	]
	if len(description_header) == 1:
		# If the description header was found, extract the descriptions:
		description_header = description_header[0]
		description_nl = "\n".join([
			description_paragraph.text.strip().replace("\n", " ") 
			for description_paragraph in __find_siblings_between_elements(description_header, "h2", 
																			filter_class_name="NormalNL")
		])
		description_fr = "\n".join([
			description_paragraph.text.strip().replace("\n", " ") 
			for description_paragraph in __find_siblings_between_elements(description_header, "h2", 
																		filter_class_name="NormalFR")
		])
	else:
		# If the description header could not be found, extract the description in a best-effort fallback way as
		# all text starting between the proposal header and the next proposal header.
		# Note: we cannot filter only the NormalNL / NormalFR classes here, to build a separate description in 
		# the respective languages, as the parts of the description are not available in both languages, but 
		# intermittently in one language, then the other.
		description = "\n".join([
			description_paragraph.text.strip().replace("\n", " ") 
			for description_paragraph in __find_siblings_between_elements(proposal_header, "h2")
		])
		description_nl = description
		description_fr = description
	return description_nl.replace(u'\xa0', u' ').strip("\n"), description_fr.replace(u'\xa0', u' ').strip("\n")  # replace non-breaking space characters with regular spaces, etc.


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
	elif type(next_element) is not NavigableString: # = Text in the HTML that is not enclosed within tags, it has no .name.
		next_element_name = next_element.name
	return next_element, next_element_name


def __split_proposal_header(proposal_header):
	# Extract the proposal number and title:
	spans = [span.text.strip().replace("\n", " ") for span in proposal_header.findChildren("span")]
	if len(spans) >= 2:
		number, title = spans[:2] # TODO weirdly enough, sometimes the title occurs multiple times in the result, whereas only once in the html.
	elif len(spans) == 1:
		number = None
		title = spans[0]
	
	# If the proposal title contains proposal document reference at the end, split the title into the actual title and 
	# the document reference (for example, "... les armes (3849/1-4)" should result in "... les armes" and "3849/1-4"):
	match = re.match(r"(.*) \((.*)\)", title)
	if match:
		title, doc_ref = match.groups()
	else:
		doc_ref = None

	return number, title, doc_ref


def __extract_motions(plenary_id: str, html, politicians: Politicians) -> Tuple[
	Proposal, List[Motion], List[Vote], List[Any]]:
	tokens = WhitespaceTokenizer().tokenize(html.text)

	votings = find_occurrences(tokens, "Vote nominatif - Naamstemming:".split(" "))

	bounds = zip(votings, votings[1:] + [len(tokens)])
	voting_sequences = [tokens[start:end] for start, end in bounds]

	motions = []
	votes = []

	for seq in voting_sequences:
		motion_number = int(seq[4], 10)
		motion_id = f"{plenary_id}_{motion_number}"
		cancelled = sum([1 if "geannuleerd" in token else 0 for token in seq[4:8]]) > 0

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

		# Create the votes:
		votes.extend(
			create_votes_for_same_vote_type(yes_voter_names, VoteType.YES, motion_id, politicians) +
			create_votes_for_same_vote_type(no_voter_names, VoteType.NO, motion_id, politicians) +
			create_votes_for_same_vote_type(abstention_voter_names, VoteType.ABSTENTION, motion_id, politicians)
		)

		# Create the motion:
		motions.append(Motion(
			motion_id,
			motion_number,
			"", # TODO fix proposal_id writing
			cancelled
		))

	return motions, votes


def _extract_motiondata(report_path: str, html: BeautifulSoup) -> List[MotionData]:
	def is_start_naamstemmingen(el):
		if el.name == "h1" and ("naamstemmingen" == el.text.lower().strip()):
			return True
		if el.name == "p" and ("naamstemmingen" == el.text.lower().strip()) and ("Titre1NL" in el.get("class")):
			return True
		return False

	start_naamstemmingen = list(filter(is_start_naamstemmingen, html.find_all()))
	if not start_naamstemmingen:
		if "naamstemmingen" in html.text.lower():
			logger.info(f"no naamstemmingen found in {report_path}")
		else:
			# There aren't any naamstemmingen, not even logging it
			pass
		return []

	if len(start_naamstemmingen) > 1:
		logger.info(f"multiple candidates for start of 'naamstemmingen' in {report_path}")
		return []

	def is_motion_title(el):
		if el.name == "h2":
			return True
		if el.name == "p" and el.get("class") in ["Titre2NL", "Titre2FR"]:
			return True
		return False

	motion_titles = list(filter(is_motion_title, start_naamstemmingen[0].find_next_siblings()))
	if not motion_titles:
		logger.warning(f"No motion titles after naamstemmingen in {report_path}")
		return []
	first_motion_title = motion_titles[0]

	grouped_h2_tags = split_on_h2_tags_containing_bordered_span([first_motion_title] + first_motion_title.find_next_siblings())

	motion_data = find_motion_datas(grouped_h2_tags)

	# print(
	# 	json.dumps([dict(label=m.label, nl_title=m.nl_title, fr_title=m.fr_title,
	# 					 body_text_parts=[dict(lang=part.lang, text=part.text) for part in m.body_text_parts]) for m in
	# 				motion_data], indent=2))

	return motion_data


def has_border(attr):
	return "border:solid" in attr


def contains_bordered_span(el):
	return len(find_bordered_span(el)) == 1


def find_bordered_span(el):
	return el.find_all("span", style=has_border)


# Looking for 'bordered spans' is a very flawed strategy, there's no consistency there
# We'll be better off looking for recognisable fixed expressions like "Moties ingediend tot besluit van de interpellaties van"
def split_on_h2_tags_containing_bordered_span(tags):
	groups = []
	current_group = []

	for tag in tags:
		if tag.name == "h2" and contains_bordered_span(tag):
			if current_group:
				groups.append(current_group)
				current_group = []
		current_group.append(tag)

	if current_group:
		groups.append(current_group)

	return groups


def find_motion_datas(tag_groups):
	""" Each of the tag groups starts with a H2 containing a bordered span"""
	groups_by_bordered_span_value = OrderedDict()

	for tag_group in tag_groups:
		bordered_span = find_bordered_span(tag_group[0])[0]

		groups_by_bordered_span_value.setdefault(bordered_span.text, []).append(tag_group)

	result = []
	for k, v in groups_by_bordered_span_value.items():
		if len(v) != 2:
			logger.warning("Motion did not have two groups of h2 tags that start with a bordered span:", k)

		# Assumption: 	first group is always french

		fr_h2_tags = [tag for tag in v[0] if tag.name == 'h2']
		nl_h2_tags = [tag for tag in v[1] if tag.name == 'h2']

		assert fr_h2_tags, "Motion should have fr h2 tags"
		assert nl_h2_tags, "Motion should have nl h2 tags"

		fr_title = "\n".join([tag.text for tag in fr_h2_tags])
		nl_title = "\n".join([tag.text for tag in nl_h2_tags])

		# Assumption: there are no h2 tags other than title elements
		last_nl_h2_index = v[1].index(nl_h2_tags[-1])
		if last_nl_h2_index == -1:
			raise Exception("should not happen - nl h2 tag not found")

		remaining_elements = v[1][last_nl_h2_index + 1:]
		remaining_elements = [el for el in remaining_elements if el.text.strip() != ""]

		body_text_parts = [create_body_text_part(el) for el in remaining_elements]

		result.append(MotionData(k, nl_title, nl_h2_tags, fr_title, fr_h2_tags, body_text_parts, remaining_elements))

	return result


def create_body_text_part(el) -> BodyTextPart:
	nl = False
	fr = False

	if 'NormalNL' in el.get('class'):
		nl = True
	if 'NormalFR' in el.get('class'):
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


def __get_plenary_date(path, html):
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
	extract_from_html_plenary_reports(os.path.join(PLENARY_HTML_INPUT_PATH, "*.html"))

	# test_path = os.path.join(PLENARY_HTML_INPUT_PATH, "ip298x.html")
	# html = read_plenary_html(test_path)
	# _extract_motiondata(test_path, html)


if __name__ == "__main__":
	main()
