import json
import os
from typing import List

from transparentdemocracy import PLENARY_MARKDOWN_OUTPUT_PATH, PLENARY_JSON_OUTPUT_PATH
from transparentdemocracy.model import Motion, Plenary, Proposal, Vote, VoteType
from transparentdemocracy.plenaries.extraction import extract_from_html_plenary_report, \
	extract_from_html_plenary_reports


class MarkdownSerializer:
	def __init__(self, output_path=PLENARY_MARKDOWN_OUTPUT_PATH):
		self.output_path = output_path
		os.makedirs(output_path, exist_ok=True)

	def serialize_plenaries(self, plenaries: List[Plenary]) -> None:
		for plenary in plenaries:
			markdown_result = ""
			markdown_result = f"# Plenary gathering {plenary.number}\n\n"
			markdown_result += f"Legislature: {plenary.legislature}\n\n"
			markdown_result += f"Source (HTML report): {plenary.pdf_report_url}\n\n"
			markdown_result += f"PDF-formatted alternative: {plenary.html_report_url}\n\n"

			for proposal in plenary.proposals:
				markdown_result += self._serialize_proposal(proposal)

			for motion in plenary.motions:
				markdown_result += self._serialize_motion(motion)

			with open(os.path.join(self.output_path, f"plenary {str(plenary.number).zfill(3)}.md"), "w",
					  encoding="utf-8") as output_file:
				output_file.write(markdown_result)

	def serialize_votes(self, votes: List[Vote]) -> None:
		markdown_result = ""
		markdown_result += self._serialize_votes_for_type(votes, VoteType.YES)
		markdown_result += self._serialize_votes_for_type(votes, VoteType.NO)
		markdown_result += self._serialize_votes_for_type(votes, VoteType.ABSTENTION)
		return markdown_result

	def _serialize_proposal(self, proposal: Proposal) -> None:
		markdown_result = f"## Proposal {proposal.number}\n\n"
		markdown_result += proposal.description
		markdown_result += "\n\n"
		return markdown_result

	def _serialize_motion(self, motion: Motion) -> None:
		markdown_result = f"Motion # {motion.number}."
		if motion.cancelled:
			markdown_result += " (cancelled)"
		markdown_result += "\n\n"
		return markdown_result

	def _serialize_votes_for_type(votes: List[Vote], vote_type: VoteType):
		markdown_result = ""
		votes_of_type = [vote for vote in votes if vote.vote_type == vote_type]
		markdown_result += f"### {vote_type.name} votes"
		if votes is None:
			markdown_result += "???\n"
		else:
			markdown_result += f" ({len(votes_of_type)})\n"
			markdown_result += ", ".join([vote.politician.full_name for vote in votes_of_type])
		markdown_result += "\n\n"
		return markdown_result


class JsonSerializer:
	def __init__(self):
		self.plenary_output_json_path = PLENARY_JSON_OUTPUT_PATH
		os.makedirs(self.plenary_output_json_path, exist_ok=True)

	def serialize_plenaries(self, plenaries: List[Plenary]) -> None:
		self._serialize_list(plenaries, "plenaries.json")

	def serialize_votes(self, votes: List[Vote]) -> None:
		self._serialize_list(votes, "votes.json")

	def _serialize_list(self, some_list: List, output_file: str) -> None:
		list_json = json.dumps(
			some_list,
			default=lambda o: o.__dict__,
			indent=4)
		with open(os.path.join(self.plenary_output_json_path, output_file), "w") as output_file:
			output_file.write(list_json)


def serialize(plenaries: List[Plenary], votes: List[Vote]) -> None:
	write_markdown(plenaries)

	write_plenaries_json(plenaries)
	write_votes_json(votes)


def write_markdown():
	plenaries, votes = extract_from_html_plenary_reports()
	MarkdownSerializer().serialize_plenaries(plenaries)


def write_plenaries_json():
	plenaries, votes = extract_from_html_plenary_reports()
	JsonSerializer().serialize_plenaries(plenaries)

def write_votes_json():
	plenaries, votes = extract_from_html_plenary_reports()
	JsonSerializer().serialize_votes(votes)


if __name__ == "__main__":
	write_markdown()
