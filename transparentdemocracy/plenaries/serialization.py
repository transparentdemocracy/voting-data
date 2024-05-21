import itertools
import json
import os
from typing import List, Dict

from transparentdemocracy import CONFIG
from transparentdemocracy.json_serde import DateTimeEncoder
from transparentdemocracy.model import Motion, Plenary, ProposalDiscussion, Proposal, Vote, VoteType, MotionGroup
from transparentdemocracy.plenaries.extraction import extract_from_html_plenary_reports
from transparentdemocracy.plenaries.motion_proposal_linker import link_motions_with_proposals


class MarkdownSerializer:
	def __init__(self, output_path=CONFIG.plenary_markdown_output_path()):
		self.output_path = output_path
		os.makedirs(output_path, exist_ok=True)

	def serialize_plenaries(self, plenaries: List[Plenary], votes: List[Vote]) -> None:
		votes_by_voting_id = dict([(k, list(v)) for k, v in itertools.groupby(votes, lambda v: v.voting_id)])
		for plenary in plenaries:
			markdown_result = ""
			markdown_result += f"# Plenary gathering {plenary.number}\n\n"
			markdown_result += f"Legislature: {plenary.legislature}\n\n"
			markdown_result += f"Source (HTML report): {plenary.pdf_report_url}\n\n"
			markdown_result += f"PDF-formatted alternative: {plenary.html_report_url}\n\n"

			for proposal_discussion in plenary.proposal_discussions:
				markdown_result += self._serialize_proposal_discussions(proposal_discussion)

			for motion in plenary.motions:
				if motion.voting_id:
					motion_votes = dict(votes_by_voting_id).get(motion.voting_id, None)
					motion_votes = list(motion_votes) if motion_votes else []

					markdown_result += self._serialize_motion(motion, motion_votes)

			with open(os.path.join(self.output_path, f"plenary {str(plenary.number).zfill(3)}.md"), "w",
					  encoding="utf-8") as output_file:
				output_file.write(markdown_result)

	def _serialize_proposal_discussions(self, proposal_discussion: ProposalDiscussion) -> None:
		markdown_result = f"## Proposal discussion (agenda item {proposal_discussion.plenary_agenda_item_number})\n\n"
		markdown_result += f"### Description in Dutch:\n\n"
		markdown_result += f"{proposal_discussion.description_nl}\n\n"
		markdown_result += f"### Description in French:\n\n"
		markdown_result += f"{proposal_discussion.description_fr}\n\n"
		markdown_result += "\n\n"

		markdown_result += f"### Discussed proposals:"
		for proposal in proposal_discussion.proposals:
			self._serialize_proposal(proposal)
		markdown_result += "\n\n"

		return markdown_result

	def _serialize_proposal(self, proposal: Proposal) -> None:
		markdown_result = f"## Proposal {proposal.documents_reference}:\n\n"
		markdown_result += f"Title (Dutch): {proposal.title_nl}"
		markdown_result += f"Title (French): {proposal.title_fr}"
		markdown_result += "\n\n"
		return markdown_result

	def _serialize_motion(self, motion: Motion, votes: List[Vote]) -> None:
		markdown_result = f"### Motion {motion.sequence_number}."
		if motion.cancelled:
			markdown_result += " (cancelled)"
		markdown_result += "\n\n"

		markdown_result += self._serialize_votes(votes)

		markdown_result += "\n"

		return markdown_result

	def _serialize_votes(self, votes: List[Vote]) -> None:
		markdown_result = ""
		markdown_result += self._serialize_votes_for_type(votes, "YES", "Yes votes")
		markdown_result += self._serialize_votes_for_type(votes, "NO", "No votes")
		markdown_result += self._serialize_votes_for_type(votes, "ABSTENTION", "Abstentions")
		return markdown_result

	def _serialize_votes_for_type(self, votes: List[Vote], vote_type: VoteType, title: str):
		filtered_votes = [v for v in votes if v.vote_type == vote_type]
		markdown_result = f"#### {title} ({len(filtered_votes)})\n\n"
		markdown_result += ", ".join([vote.politician.full_name for vote in filtered_votes])
		markdown_result += "\n\n"
		return markdown_result


class JsonSerializer:
	def __init__(self, output_path=None):
		self.plenary_output_json_path = CONFIG.plenary_json_output_path() if output_path is None else output_path
		os.makedirs(self.plenary_output_json_path, exist_ok=True)

	def serialize_plenaries(self, plenaries: List[Plenary]) -> None:
		self._serialize_plenaries(plenaries, "plenaries.json")

	def serialize_votes(self, votes: List[Vote]) -> None:
		self._serialize_list([dict(
			voting_id=v.voting_id,
			vote_type=v.vote_type,
			politician_id=v.politician.id) for v
			in votes], "votes.json")

	def _serialize_plenaries(self, plenaries: List[Plenary], output_file: str) -> None:
		# Verify that post-processing of the plenaries (linking motions and proposals) has been run as well:
		if not any(
				motion_group for plenary in plenaries for motion_group in plenary.motion_groups
				if motion_group.proposal_discussion_id
		):
			raise ValueError("No plenaries occur with motion-proposal links. Run the motion_proposal_linker.py before "
							 "serializing plenaries.")

		list_json = json.dumps([self._plenary_to_dict(p) for p in plenaries],
							   default=lambda o: o.__dict__,
							   indent=2,
							   cls=DateTimeEncoder)
		with open(os.path.join(self.plenary_output_json_path, output_file), "w") as output_file:
			output_file.write(list_json)

	def _serialize_list(self, some_list: List, output_file: str) -> None:
		list_json = json.dumps(some_list,
							   indent=2,
							   default=lambda o: o.__dict__)
		with open(os.path.join(self.plenary_output_json_path, output_file), "w") as output_file:
			output_file.write(list_json)

	def _plenary_to_dict(self, plenary: Plenary) -> Dict:
		return dict(
			id=plenary.id,
			number=plenary.number,
			date=plenary.date.isoformat(),
			legislature=plenary.legislature,
			pdf_report_url=plenary.pdf_report_url,
			html_report_url=plenary.html_report_url,
			proposal_discussions=plenary.proposal_discussions,
			motion_groups=plenary.motion_groups,
		)


def serialize(plenaries: List[Plenary], votes: List[Vote]) -> None:
	write_markdown(plenaries, votes)

	write_plenaries_json(plenaries)
	write_votes_json(votes)


def write_markdown(plenaries=None, votes=None):
	if plenaries is None and votes is None:
		plenaries, votes, problems = extract_from_html_plenary_reports()
	MarkdownSerializer().serialize_plenaries(plenaries, votes)


def write_plenaries_json(plenaries=None):
	if plenaries is None:
		plenaries, votes, problems = extract_from_html_plenary_reports()
	link_motions_with_proposals(plenaries)
	JsonSerializer().serialize_plenaries(plenaries)


def write_votes_json(votes=None):
	if votes is None:
		plenaries, votes, problems = extract_from_html_plenary_reports()
	JsonSerializer().serialize_votes(votes)


def load_plenaries():
	path = os.path.join(CONFIG.plenary_json_output_path(), "plenaries.json")
	with open(path, 'r') as fp:
		data = json.load(fp)
	return [_json_to_plenary(p) for p in data]


def _json_to_plenary(data):
	return Plenary(
		id=data['id'],
		number=data['number'],
		date=data['date'],  # TODO: parse to datetime.date
		legislature=data['legislature'],
		pdf_report_url=data['pdf_report_url'],
		html_report_url=data['html_report_url'],
		proposal_discussions=[_json_to_proposal_discussion(pd) for pd in data['proposal_discussions']],
		motion_groups=[_json_to_motion_group(mg) for mg in data['motion_groups']],
	)


def _json_to_proposal_discussion(data):
	return ProposalDiscussion(
		id=data['id'],
		plenary_id=data['plenary_id'],
		plenary_agenda_item_number=data['plenary_agenda_item_number'],
		description_nl=data['description_nl'],
		description_fr=data['description_fr'],
		proposals=[_json_to_proposal(p) for p in data['proposals']],
	)


def _json_to_proposal(data):
	return Proposal(
		id=data['id'],
		documents_reference=data['documents_reference'],
		title_nl=data['title_nl'],
		title_fr=data['title_fr']
	)


def _json_to_motion_group(data):
	return MotionGroup(
		id=data['id'],
		plenary_agenda_item_number=data['plenary_agenda_item_number'],
		title_nl=data['title_nl'],
		title_fr=data['title_fr'],
		documents_reference=data['documents_reference'],
		motions=[_json_to_motion(m) for m in data['motions']],
		proposal_discussion_id=data['proposal_discussion_id'],
	)


def _json_to_motion(data):
	return Motion(
		id=data['id'],
		sequence_number=data['sequence_number'],
		title_nl=data['title_nl'],
		title_fr=data['title_fr'],
		documents_reference=data['documents_reference'],
		voting_id=data['voting_id'],
		cancelled=data['cancelled'],
		description=data['description'],
		proposal_id=data['proposal_id'],
	)


def main():
	write_markdown()


if __name__ == "__main__":
	main()
