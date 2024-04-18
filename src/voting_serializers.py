from typing import List
from model import Motion


class MotionToMarkdownSerializer:
    def serialize_motions(self, motions: List[Motion], plenary_number: int, output_file_path: str) -> None:
        if len(motions) > 0:
            heading = f"# Plenary gathering {plenary_number}\n\n"
            with open(output_file_path, "w", encoding="utf-8") as output_file:
                output_file.write(heading)
            for motion in motions:
                self.serialize(motion, output_file_path)
    
    def serialize(self, motion: Motion, output_file_path: str) -> None:
        result = f"## Motion {motion.proposal.number}\n\n"
        result += motion.proposal.description
        result += "\n\n"

        result += f"### Yes votes ({motion.num_votes_yes})\n"
        result += "\n"
        result += ", ".join(motion.vote_names_yes)
        result += "\n\n"

        result += f"### No votes ({motion.num_votes_no})\n"
        result += "\n"
        result += ", ".join(motion.vote_names_no)
        result += "\n\n"

        result += f"### Abstentions ({motion.num_votes_abstention})\n"
        result += "\n"
        result += ", ".join(motion.vote_names_abstention)
        result += "\n\n\n"

        with open(output_file_path, "a", encoding="utf-8") as output_file:
            output_file.write(result)
