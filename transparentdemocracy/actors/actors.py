import asyncio
import json
import os

import aiofiles
import aiohttp

from transparentdemocracy import CONFIG


class ActorHttpGateway:
    def __init__(self, config, base_url='https://data.dekamer.be/v0/actr'):
        self.config = config
        self.base_url = base_url

    async def download_pages(self, max_pages, max_concurrent_requests=5):
        os.makedirs(self.config.actor_json_pages_input_path(), exist_ok=True)
        queue = asyncio.Queue(min(max_concurrent_requests, max_concurrent_requests))
        stop_event = asyncio.Event()

        async with (aiohttp.ClientSession() as session):
            producer = self.schedule_pages(max_pages, queue, stop_event)
            consumers = [self.download_page_worker(session, queue, stop_event) for i in range(max_concurrent_requests)]
            await asyncio.gather(producer, *consumers)

    async def schedule_pages(self, max_pages, queue, stop_event):
        page_nr = 0
        while page_nr < max_pages and not stop_event.is_set():
            try:
                await asyncio.wait_for(queue.put(page_nr), timeout=1)
            except asyncio.TimeoutError:
                print("put timed out")
                continue
            page_nr = page_nr + 1
        await queue.put(None)

    async def download_page_worker(self, session, queue: asyncio.Queue, stop_event: asyncio.Event):
        """Asynchronous function to download the content of a URL."""
        page_size = 10

        while not stop_event.is_set():
            try:
                page_number = await asyncio.wait_for(queue.get(), timeout=1)
            except asyncio.TimeoutError:
                continue

            if page_number is None:
                stop_event.set()
                return
            url = f"{self.base_url}?start={page_number * page_size}"
            async with session.get(url, headers={'Accept': 'application/json'}) as response:
                response.raise_for_status()

                path = self.config.actor_json_pages_input_path(f"{page_number}.json")
                json_text = await response.text()
                json_data = json.loads(json_text)
                if len(json_data["items"]) == 0:
                    print(f"page {page_number} has no items. Stopping.")
                    stop_event.set()
                    return
                async with aiofiles.open(path, 'w') as json_file:
                    await json_file.write(json_text)
                    # print(f"written {path}")

    async def download_actors(self, max_concurrent_requests=5):
        os.makedirs(self.config.actor_json_input_path(), exist_ok=True)
        queue = asyncio.Queue(min(max_concurrent_requests, max_concurrent_requests))
        stop_event = asyncio.Event()

        async with (aiohttp.ClientSession() as session):
            producer = self.schedule_actors(queue, stop_event)
            consumers = [self.download_actor_worker(queue, session, stop_event) for i in range(max_concurrent_requests)]
            await asyncio.gather(producer, *consumers)


    async def schedule_actors(self, queue, stop_event):
        pages = os.listdir(self.config.actor_json_pages_input_path())
        for page in pages:
            json_data = json.load(open(self.config.actor_json_pages_input_path(page), 'r'))
            for item in json_data["items"]:
                if stop_event.is_set():
                    return
                if "gaabId" not in item:
                    continue

                queued = False
                while not queued:
                    try:
                        await asyncio.wait_for(queue.put(item["gaabId"]), timeout=1)
                        queued = True
                    except asyncio.TimeoutError:
                        continue

        await queue.put(None)

    async def download_actor_worker(self, queue, session, stop_event):
        while not stop_event.is_set():
            try:
                actor_id = await asyncio.wait_for(queue.get(), timeout=1)
            except asyncio.TimeoutError:
                continue
            if actor_id is None:
                stop_event.set()
                return
            path = self.config.actor_json_pages_input_path(f"{actor_id}.json")

            if os.path.exists(path):
                continue

            url = f"{self.base_url}/{actor_id}"
            print(f"Downloading: {url}")
            try:
                async with session.get(url, headers={'Accept': 'application/json'}) as response:
                    response.raise_for_status()

                    async with aiofiles.open(path, 'w') as json_file:
                        print(f"writing {path}")
                        await json_file.write(await response.text())
            except Exception:
                print("exception! setting stop event")
                stop_event.set()


if __name__ == "__main__":
    gateway = ActorHttpGateway(CONFIG)
    print("download pages started")
    asyncio.run(gateway.download_pages(max_pages=100))
    print("download actors started")
    asyncio.run(gateway.download_actors())
    print("done")
