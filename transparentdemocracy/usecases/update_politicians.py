import asyncio
import logging
import os

from transparentdemocracy.politicians.extraction import PoliticianExtractor
from transparentdemocracy.politicians.serialization import PoliticianJsonSerializer

logger = logging.getLogger(__name__)


class UpdatePoliticians:
    def __init__(self, config, actor_gateway):
        self.config = config
        self.actor_gateway = actor_gateway

    def update_politicians(self, force_overwrite=False, download_actors=True):
        politicians_json = self.config.politicians_json_output_path("politicians.json")
        if os.path.exists(politicians_json) and not force_overwrite:
            logger.info(f"{politicians_json} already exists and force_overwrite is False")
            return

        if not os.path.exists(politicians_json):
            logger.info(f"{politicians_json} doesn't exist. Creating it now.")

        if download_actors:
            asyncio.run(self.actor_gateway.download_actors(max_pages=1000))

        # TODO: create repository for local actor / politician storage
        serializer = PoliticianJsonSerializer(politicians_json)
        extractor = PoliticianExtractor(self.config)

        politicians = extractor.extract_politicians()

        serializer.serialize_politicians(politicians.politicians)
