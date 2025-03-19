import dataclasses
import logging
import os.path
from typing import List

import bs4
import requests

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class PlenaryEntry:
    id: str
    url: str
    is_final: bool


class DeKamerGateway:
    def __init__(self, config):
        self.config = config

    def find_recent_reports(self):
        latest_page = (f"https://www.dekamer.be/kvvcr/showpage.cfm?section=/cricra&language=nl&cfm=dcricra.cfm?type=plen&cricra=CRI&count=all&legislat="
                       f"{self.config.legislature}")
        found_plenaries = []

        response = requests.get(latest_page)
        response.raise_for_status()
        soup = bs4.BeautifulSoup(response.text, 'html.parser')
        rows = soup.select('div#story table tr')
        if not rows:
            logger.error("no rows found in dekamer plenary list")
            logger.error("response: %s", response.text)
            raise Exception("no rows found in dekamer plenary list")
        for row in rows:
            plenary_nr = int(row.find_all("td")[0].text.strip(), 10)
            html_link = row.find_all("td")[3].find("a", title="Kopieervriendelijke HTML versie")
            is_final = "definitieve versie" in row.find_all("td")[4].text

            found_plenaries.append(PlenaryEntry(f"{self.config.legislature}_{plenary_nr:03d}", html_link.get("href"), is_final))

        return found_plenaries

    def download_plenary_reports(self, plenary_ids: List[str], force_overwrite: bool):
        os.makedirs(self.config.plenary_html_input_path(), exist_ok=True)

        for plenary_id in plenary_ids:
            plenary_nr = plenary_id.split("_")[1]
            path = self.config.plenary_html_input_path(f"ip{plenary_nr}x.html")

            if os.path.exists(path) and not force_overwrite:
                print(f"skipping download of {plenary_id} because {path} exists")
                continue

            response = requests.get(f"https://www.dekamer.be/doc/PCRI/html/{self.config.legislature}/ip{plenary_nr}x.html")
            response.raise_for_status()

            with open(path, 'wb') as f:
                print(f"writing {path}")
                f.write(response.content)

    def download_document_pdf(self, document_id: str, force_overwrite: bool = False):
        local_path = self.config.documents_input_path(document_id[3:5], document_id[5:7], f"{document_id}.pdf")
        url = f"https://www.dekamer.be/FLWB/PDF/{self.config.legislature}/{document_id[3:7]}/{document_id}.pdf"
        if os.path.exists(local_path) and not force_overwrite:
            print(f"{local_path} already exists, not downloading again")
        else:
            print(f"downloading {url} to {local_path}")
            self._download_file(url, local_path)

    def _download_file(self, url, local_path):
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            response = requests.get(url, stream=True)
            response.raise_for_status()  # Raise an exception for HTTP errors
            with open(local_path, 'wb') as file:
                # TODO: use temp files and move them to avoid having half-downloaded files when something is broken
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            print(f"PDF downloaded successfully to {local_path}")
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except Exception as err:
            print(f"An error occurred: {err}")
