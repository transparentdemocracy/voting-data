import os
from dataclasses import dataclass
from enum import Enum

import yaml

import transparentdemocracy


class Environments(Enum):
    TEST = 'test'
    LOCAL = 'local'
    DEV = 'dev'
    PROD = 'prod'


@dataclass
class Config:
    legislature: str

    actors_input_dir: str
    politician_output_dir: str

    plenary_html_dir: str
    plenary_json_dir: str

    document_pdf_dir: str
    document_text_dir: str
    document_summary_dir: str

    google_service_credentials_json: str

    def __init__(self, conf_data, legislature):
        self.legislature = legislature
        local_paths = conf_data['local']
        self.actors_input_dir = self._config_relative_file(local_paths['actors_input_dir'])
        self.politician_output_dir = self._config_relative_file(local_paths['politician_output_dir'])
        self.plenary_html_dir = self._config_relative_file(local_paths['plenary_html_dir'])
        self.plenary_json_dir = self._config_relative_file(local_paths['plenary_json_dir'])
        self.document_pdf_dir = self._config_relative_file(local_paths['document_pdf_dir'])
        self.document_text_dir = self._config_relative_file(local_paths['document_text_dir'])
        self.document_summary_dir = self._config_relative_file(local_paths['document_summary_dir'])

        self.google_service_account_credentials = os.environ["WDDP_STORAGE_SERVICE_ACCOUNT_CREDENTIALS"]
        self.google_drive_text_dir = conf_data['gdrive']['document_text_dir']
        self.google_drive_summary_dir = conf_data['gdrive']['document_summary_dir']

    @property
    def leg_dir(self):
        return f"leg-{self.legislature}"

    def plenary_html_input_path(self, *path):
        return os.path.join(self.plenary_html_dir, self.leg_dir, *path)

    def actor_json_input_path(self):
        return os.path.join(self.actors_input_dir, "actor")

    def actor_json_pages_input_path(self, *args):
        return os.path.join(self.actors_input_dir, "pages", *args)

    def plenary_json_output_path(self, *args):
        return os.path.join(self.plenary_json_dir, self.leg_dir, *args)

    def politicians_json_output_path(self, *path):
        return os.path.join(self.politician_output_dir, self.leg_dir, *path)

    def documents_input_path(self, *path):
        return os.path.join(self.document_pdf_dir, self.leg_dir, *path)

    def documents_txt_output_path(self, *path):
        return os.path.join(self.document_text_dir, self.leg_dir, *path)

    def documents_summary_output_path(self, *path):
        return os.path.join(self.document_summary_dir, self.leg_dir, *path)

    def documents_summaries_json_output_path(self):
        return os.path.join(self.document_summary_dir, self.leg_dir, "summaries.json")

    def _config_relative_file(self, path):
        return os.path.join(os.path.dirname(transparentdemocracy.__file__), "..", path)

def _create_config(environment: Environments, legislature: str):
    env_yaml = os.path.join(os.path.dirname(transparentdemocracy.__file__), f"../environments/{environment.value}.yaml")
    with open(env_yaml, 'r', encoding='utf-8') as fp:
        conf_data = yaml.safe_load(fp)

    return Config(conf_data, legislature=legislature)
