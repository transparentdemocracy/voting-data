import asyncio
import logging
import ssl
from pathlib import Path

import aiofiles
import aiohttp
from aiohttp import ClientSession

from transparentdemocracy import CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ActorHttpGateway:
    def __init__(self, config, base_url='https://data.dekamer.be/v0/actr'):
        self.config = config
        self.base_url = base_url
        self.actors_path = Path(config.actor_json_input_path())
        self.actors_path.mkdir(parents=True, exist_ok=True)

    async def download_actors(self, max_pages: int, max_concurrent_requests: int = 5):
        ssl_context = ssl.create_default_context()

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            actor_queue = asyncio.Queue(maxsize=max_concurrent_requests)

            consumers = [
                asyncio.create_task(self._download_actor_worker(session, actor_queue))
                for _ in range(max_concurrent_requests)
            ]

            try:
                async for actor_id in self._stream_pages(session, max_pages):
                    await actor_queue.put(actor_id)
            finally:
                for _ in range(max_concurrent_requests):
                    await actor_queue.put(None)

            await asyncio.gather(*consumers)

    async def _stream_pages(self, session: ClientSession, max_pages: int):
        page_size = 10

        for page_number in range(max_pages):
            url = f"{self.base_url}?start={page_number * page_size}"

            async with session.get(url, headers={'Accept': 'application/json'}) as response:
                response.raise_for_status()
                page_data = await response.json()

                if not page_data["items"]:
                    logger.info(f"Page {page_number} has no items. Stopping.")
                    break

                for item in page_data["items"]:
                    if "gaabId" in item:
                        yield item["gaabId"]

    async def _download_actor_worker(self, session: ClientSession, queue: asyncio.Queue):
        while True:
            actor_id = await queue.get()
            if actor_id is None:
                break

            try:
                path = self.actors_path / f"{actor_id}.json"
                if path.exists():
                    continue

                url = f"{self.base_url}/{actor_id}"
                logger.info(f"Downloading actor: {url}")

                async with session.get(url, headers={'Accept': 'application/json'}) as response:
                    response.raise_for_status()
                    async with aiofiles.open(path, 'w') as f:
                        await f.write(await response.text())

            except Exception as e:
                logger.error(f"Error downloading actor {actor_id}: {e}")
            finally:
                queue.task_done()


if __name__ == "__main__":
    gateway = ActorHttpGateway(CONFIG)
    asyncio.run(gateway.download_actors(max_pages=100))
    logger.info("Done")
