import json
import os
from typing import List

from transparentdemocracy.model import Motion, Plenary, Proposal, Vote, VoteType
from transparentdemocracy.plenaries.extraction import OUTPUT_PATH


class MarkdownSerializer:
    def __init__(self):
        self.MARKDOWN_OUTPUT_PATH = os.path.join(OUTPUT_PATH, "plenary", "markdown")
        os.makedirs(self.MARKDOWN_OUTPUT_PATH, exist_ok=True)
    
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
        
            with open(os.path.join(self.MARKDOWN_OUTPUT_PATH, f"plenary {str(plenary.number).zfill(3)}.md"), "w", encoding="utf-8") as output_file:
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
        self.JSON_OUTPUT_PATH = os.path.join(OUTPUT_PATH, "plenary", "json")
        os.makedirs(self.JSON_OUTPUT_PATH, exist_ok=True)

    def serialize_plenaries(self, plenaries: List[Plenary]) -> None:
        self._serialize_list(plenaries, "plenaries.json")

    def serialize_votes(self, votes: List[Vote]) -> None:
        self._serialize_list(votes, "votes.json")

    def _serialize_list(self, some_list: List, output_file: str) -> None:
        list_json = json.dumps(
            some_list, 
            default=lambda o: o.__dict__, 
            indent=4)
        with open(os.path.join(self.JSON_OUTPUT_PATH, output_file), "w") as output_file:
            output_file.write(list_json)


def serialize(plenaries: List[Plenary], votes: List[Vote]) -> None:
    # Serialize the extracted plenaries and votes:
    # ... to human-readable format:
    markdown_serializer = MarkdownSerializer()
    markdown_serializer.serialize_plenaries(plenaries)
    # markdown_serializer.serialize_votes(votes))

    # ... to machine-readable format:
    json_serializer = JsonSerializer()
    json_serializer.serialize_plenaries(plenaries)
    json_serializer.serialize_votes(votes)
