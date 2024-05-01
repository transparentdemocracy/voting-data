"""
Extract info from HTML-formatted voting reports from the Belgian federal chamber's website,
see https://www.dekamer.be/kvvcr/showpage.cfm?section=/flwb/recent&language=nl&cfm=/site/wwwcfm/flwb/LastDocument.cfm.
"""

import glob
import logging
import os
import re
from typing import Tuple, List

from bs4 import BeautifulSoup
from nltk.tokenize import WhitespaceTokenizer
from tqdm.auto import tqdm

from transparentdemocracy import DATA_PATH
from transparentdemocracy.model import Motion, Plenary, Politician, Proposal, Vote, VoteType


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

OUTPUT_PATH = os.path.join(DATA_PATH, "output")
MARKDOWN_OUTPUT_PATH = os.path.join(OUTPUT_PATH, "plenary", "markdown")
JSON_OUTPUT_PATH = os.path.join(OUTPUT_PATH, "plenary", "json")


def extract_voting_data_from_plenary_reports(
		report_file_pattern: str,
		num_reports_to_process: int = None) -> Tuple[List[Plenary], List[Vote]]:
	plenaries = []
	all_votes = []
	logging.info(f"Report files must be found at: {report_file_pattern}.")
	report_filenames = glob.glob(report_file_pattern)
	if num_reports_to_process is not None:
		report_filenames = report_filenames[:num_reports_to_process]
	logging.info(f"Will process the following input reports: {report_filenames}.")

	for voting_report in tqdm(report_filenames, desc="Processing plenary reports..."):
		try:
			logging.debug(f"Processing input report {voting_report}...")
			if voting_report.endswith(".html"):
				plenary, votes = extract_from_html_plenary_report(voting_report)
				plenaries.append(plenary)
				all_votes.extend(votes)
			else:
				raise RuntimeError("Plenary reports in other formats than HTML cannot be processed.")
				
		except Exception:
			logging.warning("Failed to process %s", voting_report, exc_info=True)

	return plenaries, all_votes

def extract_from_html_plenary_report(report_filename: str) -> Tuple[Plenary, List[Vote]]:
	with open(report_filename, "r", encoding="cp1252") as file:
		html_content = file.read()

	html = BeautifulSoup(html_content, "html.parser")
	
	return __extract_plenary(report_filename, html)

def __extract_plenary(report_filename: str, html) -> Tuple[Plenary, List[Vote]]:
	plenary_number = os.path.split(report_filename)[1][2:5] # example: ip078x.html -> 078
	legislature = 55  # We currently only process plenary reports from legislature 55 with our download script.
	plenary_id = f"{legislature}_{plenary_number}"  # Concatenating legislature and plenary number to construct a unique identifier for this plenary.
	proposals, motions, votes = __extract_motions(report_filename, plenary_id, html)
	
	return (
		Plenary(
			plenary_id,
			int(plenary_number),
			legislature,
			f"https://www.dekamer.be/doc/PCRI/pdf/55/ip{plenary_number}.pdf",
			f"https://www.dekamer.be/doc/PCRI/html/55/ip{plenary_number}x.html",
			proposals,
			motions
		),
		votes
	)

def __extract_motions(plenary_report: str, plenary_id: str, html) -> Tuple[Proposal, List[Motion], List[Vote]]:
	tokens = WhitespaceTokenizer().tokenize(html.text)

	votings = find_occurrences(tokens, "Vote nominatif - Naamstemming:".split(" "))

	bounds = zip(votings, votings[1:] + [len(tokens)])
	voting_sequences = [tokens[start:end] for start, end in bounds]

	motion_blocks_by_nr = get_motion_blocks_by_nr(plenary_report, html)
	proposals = []
	motions = []
	votes = []

	for seq in voting_sequences:
		motion_number = int(seq[4], 10)
		motion_id = f"{plenary_id}_{motion_number}"

		proposal_id = motion_id
		proposal_number = motion_number
		proposal_description = "\n".join([el.text for el in motion_blocks_by_nr[motion_number][1:]]) \
			if motion_number in motion_blocks_by_nr \
			else "??? text not found ???"
		
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

		yes_voter_names = get_names(seq[yes_start + 3: no_start], yes_count)
		no_voter_names = get_names(seq[no_start + 3:abstention_start], no_count)
		abstention_voter_names = get_names(seq[abstention_start + 3:], abstention_count)

		# Create the votes:
		votes.extend(
			create_votes_for_same_vote_type(yes_voter_names, VoteType.YES, motion_id) +
			create_votes_for_same_vote_type(no_voter_names, VoteType.NO, motion_id) +
			create_votes_for_same_vote_type(abstention_voter_names, VoteType.ABSTENTION, motion_id)
		)

		# Create the proposal:
		proposal = Proposal(
			proposal_id,
			proposal_number,
			plenary_id,
			proposal_description
		)
		proposals.append(proposal)

		# Create the motion:
		motions.append(Motion(
			motion_id,
			motion_number,
			proposal_id,
			cancelled
		))

	return proposals, motions, votes

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

def get_names(sequence, count):
	names = [n.strip().replace(".", "") for n in (" ".join(sequence).strip()).split(",") if n.strip() != '']

	if len(names) != count:
		logging.warning("vote count (%d) does not match voters %s" % (count, str(names)))
		return None

	return names

def create_votes_for_same_vote_type(voter_names: List[str], vote_type: VoteType, motion_id: str) -> List[Vote]:
	if voter_names is None:
		return []
	else:
		return [
			Vote(
				Politician(voter_name),
				motion_id,
				vote_type.value
			) for voter_name in voter_names
		]
