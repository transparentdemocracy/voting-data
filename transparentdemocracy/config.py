import os
from dataclasses import dataclass


@dataclass
class Config:
    data_dir: str
    legislature: str
    leg_dir: str

    def __init__(self, data_dir, legislature="55"):
        self.data_dir = data_dir
        self.set_legislature(legislature)

    def enable_testing(self, data_dir, legislature):
        self.data_dir = data_dir
        self.set_legislature(legislature)

    def set_legislature(self, value):
        self.legislature = value
        self.leg_dir = f"leg-{self.legislature}"

    def resolve(self, *path):
        return os.path.join(self.data_dir, *path)

    def plenary_html_input_path(self, *path):
        return self.resolve("input", "plenary", "html", self.leg_dir, *path)

    def actor_json_input_path(self):
        return self.resolve("input", "actors", "actor")

    # output
    def plenary_markdown_output_path(self):
        return self.resolve("output", "plenary", "markdown", self.leg_dir)

    def plenary_json_output_path(self, *args):
        return self.resolve("output", "plenary", "json", self.leg_dir, *args)

    def politicians_json_output_path(self, *path):
        return self.resolve(self.data_dir, "output", "politician", self.leg_dir, *path)

    def documents_input_path(self, *path):
        return self.resolve(self.data_dir, "input", "documents", self.leg_dir, *path)

    def documents_txt_output_path(self, *path):
        return self.resolve(self.data_dir, "output", "documents", "txt", self.leg_dir, *path)

    def documents_summary_output_path(self, *path):
        return self.resolve(self.data_dir, "output", "documents", "summary", self.leg_dir, *path)

    def documents_summaries_json_output_path(self):
        return self.resolve(self.data_dir, "output", "documents", self.leg_dir, "summaries.json")


def _create_config():
    root_folder = os.path.dirname(os.path.dirname(__file__))
    return Config(os.path.join(root_folder, "data"), legislature=os.environ.get("LEGISLATURE"))


CONFIG = _create_config()
