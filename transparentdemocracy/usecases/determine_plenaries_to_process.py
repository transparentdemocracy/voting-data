import dataclasses
import logging
from typing import List, Dict

from transparentdemocracy.infra.dekamer import DeKamerGateway
from transparentdemocracy.infra.plenary_json import PlenaryJsonStorage
from transparentdemocracy.publisher.elastic_search import PlenaryElasticRepository

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class PlenaryStatus:
    id: str
    dekamer_final: bool
    elastic_final: bool


class DeterminePlenariesToProcess:
    def __init__(self, de_kamer: DeKamerGateway, plenary_repository: PlenaryElasticRepository,
                 plenary_json_storage: PlenaryJsonStorage):
        self.de_kamer = de_kamer
        self.plenary_repository = plenary_repository
        self.plenary_json_storage = plenary_json_storage

    def determine_plenaries_to_process(self) -> List[PlenaryStatus]:
        """
        Returns a list of PlenaryStatus
        """
        recent_reports = self.de_kamer.find_recent_reports()
        ids = [report.id for report in recent_reports]
        status_by_id = self.plenary_repository.get_statuses(ids)

        result = []
        for report in recent_reports:
            result.append(PlenaryStatus(report.id, report.is_final, status_by_id.get(report.id)))

        to_process = [p for p in result if not p.elastic_final]
        return sorted(to_process, key=lambda p: p.id)

    def determine_plenaries_to_update(self) -> Dict[str, bool]:
        plenary_entries = self.de_kamer.find_recent_reports()

        return {
            plenary_entry.id: plenary_entry.is_final for plenary_entry in plenary_entries
            if not self.plenary_json_storage.is_final(plenary_entry.id)
        }
