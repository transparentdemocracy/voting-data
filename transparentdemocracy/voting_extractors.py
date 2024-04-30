import glob
import logging
import os
import re
from dataclasses import dataclass, field
from typing import List

from bs4 import BeautifulSoup
from nltk.tokenize import WhitespaceTokenizer

from transparentdemocracy.model import Motion, Plenary, Proposal

logger = logging.getLogger(__name__)


class TokenizedText:

	def __init__(self, text):
		self.text = text
		self.tokens = WhitespaceTokenizer().tokenize(text)


class FederalChamberVotingHtmlExtractor:
	"""
	Extract voting behavior from a voting report on the Belgian federal chamber's website,
	for example at https://www.dekamer.be/kvvcr/showpage.cfm?section=/flwb/recent&language=nl&cfm=/site/wwwcfm/flwb/LastDocument.cfm.
	"""

	def extract_from_all_plenary_reports(self, file_pattern: str, limit: int = None) -> List[Plenary]:
		report_names = glob.glob(file_pattern)
		if limit is not None:
			report_names = report_names[:limit]

		return [self.extract_from_plenary_report(report_name) for report_name in report_names]

	def extract_from_plenary_report(self, plenary_report: str) -> Plenary:
		with open(plenary_report, "r", encoding="cp1252") as file:
			html_content = file.read()

		html = BeautifulSoup(html_content, "html.parser")
		# this extracts the proposal texts (a bit rough, some cleanups still needed)
		motion_blocks_by_nr = self.get_motion_blocks_by_nr(plenary_report, html)
		return self.__extract_plenary(plenary_report, html)

	def __extract_plenary(self, plenary_report: str, html) -> Plenary:
		plenary_id = int(os.path.split(plenary_report)[1][2:5]) # example: ip278x.html -> 278
		motions = self.__extract_motions(plenary_report, html)
		return Plenary(
			int(plenary_id),
			f"https://www.dekamer.be/doc/PCRI/pdf/55/ip{plenary_id}.pdf",
			f"https://www.dekamer.be/doc/PCRI/html/55/ip{plenary_id}x.html",
			motions
		)

	def __extract_motions(self, plenary_report: str, html) -> List[Motion]:
		tokenized_text = TokenizedText(html.text)
		tokens = tokenized_text.tokens

		votings = find_occurrences(tokens, "Vote nominatif - Naamstemming:".split(" "))

		bounds = zip(votings, votings[1:] + [len(tokens)])
		voting_sequences = [tokens[start:end] for start, end in bounds]

		motion_blocks_by_nr = self.get_motion_blocks_by_nr(plenary_report, html)
		motions = []

		for seq in voting_sequences:
			motion_nr = int(seq[4], 10)
			ctx = MotionContext(plenary_report, motion_nr)

			cancelled = sum([1 if "geannuleerd" in token else 0 for token in seq[4:8]]) > 0
			yes_start = get_sequence(seq, ["Oui"])
			no_start = get_sequence(seq, ["Non"])
			abstention_start = get_sequence(seq, ["Abstentions"])

			if not (yes_start < no_start < abstention_start):
				raise Exception("Could not parse voting sequence: %s", (" ".join(seq)))

			yes_count = int(seq[yes_start + 1], 10)
			no_count = int(seq[no_start + 1], 10)
			abstention_count = int(seq[abstention_start + 1], 10)

			yes_voters = self.get_names(ctx, seq[yes_start + 3: no_start], yes_count)
			no_voters = self.get_names(ctx, seq[no_start + 3:abstention_start], no_count)
			abstention_voters = self.get_names(ctx, seq[abstention_start + 3:], abstention_count)

			proposal_text = "\n".join([el.text for el in motion_blocks_by_nr[motion_nr][1:]]) \
				if motion_nr in motion_blocks_by_nr \
				else "??? text not found ???"

			motions.append(Motion(
				Proposal(str(motion_nr), proposal_text),
				num_votes_yes=yes_count,
				vote_names_yes=yes_voters,
				num_votes_no=no_count,
				vote_names_no=no_voters,
				num_votes_abstention=abstention_count,
				vote_names_abstention=abstention_voters,
				cancelled=cancelled,
				parse_problems=ctx.problems))

		return motions

	def get_motion_blocks_by_nr(self, report, html):
		result = dict()
		vote_re = re.compile("\\(Stemming/vote \\(?(.*)\\)")

		for block in self.get_motion_blocks(html):
			match = vote_re.search(block[0].strip())
			if match is not None:
				logger.debug("%s: found stemming %s" % (report, match.group(1)))
				nr = int(match.group(1), 10)
				result[nr] = block[1:]

		return result

	def get_motion_blocks(self, html):
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

	def get_names(self, ctx, sequence, count):
		names = [n.strip().replace(".", "") for n in (" ".join(sequence).strip()).split(",") if n.strip() != '']

		if len(names) != count:
			ctx.problems.append("vote count (%d) does not match voters %s" % (count, str(names)))
			return None

		return names


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


@dataclass
class MotionContext:
	report: str
	motion_nr: int
	problems: list[str] = field(default_factory=list)


def get_sequence(tokens, query):
	"""@return like find_sequence but raises ValueError if the query was not found"""
	pos = find_sequence(tokens, query)
	if pos >= 0:
		return pos
	raise ValueError("query %s not found in tokens %s" % (str(query), str(tokens)))


def find_occurrences(tokens, query):
	result = []
	pos = find_sequence(tokens, query)
	while pos > -1:
		result.append(pos)
		pos = find_sequence(tokens, query, pos + 1)

	return result


if __name__ == "__main__":
	voting_extractor = FederalChamberVotingHtmlExtractor()

	# Extract the interesting voting info:
	voting_extractor.extract("../data/input/html/ip298x.html")
