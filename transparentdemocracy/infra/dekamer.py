import os.path
from typing import List

import bs4
import requests


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
        for row in rows:
            plenary_nr = int(row.find_all("td")[0].text.strip(), 10)
            html_link = row.find_all("td")[3].find("a", title="Kopieervriendelijke HTML versie")
            is_final = "definitieve versie" in row.find_all("td")[4].text

            found_plenaries.append((f"{self.config.legislature}_{plenary_nr:03d}", html_link.get("href"), is_final))

        return found_plenaries

    def download_plenary_reports(self, plenary_ids: List[str], force_overwrite: bool):
        for plenary_id in plenary_ids:
            plenary_nr = plenary_id.split("_")[1]
            path = self.config.plenary_html_input_path(f"ip{plenary_nr}x.html")

            if os.path.exists(path) and not force_overwrite:
                print(f"skipping download of {plenary_id} because {path} exists")
                continue

            response = requests.get(f"https://www.dekamer.be/doc/PCRI/html/{self.config.legislature}/ip{plenary_nr}x.html")
            response.raise_for_status()
            with open(path, 'w') as f:
                print(f"writing {path}")
                f.write(response.text)
