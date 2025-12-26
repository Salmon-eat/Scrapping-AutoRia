import asyncio
import logging
import random
from typing import AsyncIterator

import httpx
from lxml import html as lxml_html

from app.db import AsyncSessionLocal
from app.repo import upsert_car
from app.services.scrape_car import HEADERS, enrich_phone, parse_car
from app.settings import get_settings

logger = logging.getLogger(__name__)


def parse_listing_links(page_html: str) -> list[str]:
    tree = lxml_html.fromstring(page_html)
    links = tree.xpath('//a[contains(@class,"m-link-ticket")]/@href')
    clean = []
    for link in links:
        if not isinstance(link, str) or not link.startswith("http"):
            continue

        link = link.split("?")[0]
        if "/auto_" not in link:
            continue
        if not link.endswith(".html"):
            continue
        clean.append(link)

    return list(dict.fromkeys(clean))


async def fetch_listing_links(client: httpx.AsyncClient, url: str) -> list[str]:
    response = await client.get(url)
    response.raise_for_status()
    return parse_listing_links(response.text)


RETRY_STATUSES = {429, 503}


async def iter_listing_pages(
    client: httpx.AsyncClient,
    start_url: str,
    start_page: int = 1,
    max_pages: int = 500,
    max_retries: int = 5,
) -> AsyncIterator[str]:
    page = start_page

    while page <= max_pages:
        url = start_url if page == 1 else f"{start_url}?page={page}"

        for attempt in range(1, max_retries + 1):
            r = await client.get(url)

            if r.status_code == 404:
                return

            if r.status_code == 403:
                return

            if r.status_code in RETRY_STATUSES:
                delay = (2**attempt) + random.random()
                await asyncio.sleep(delay)
                continue

            if 500 <= r.status_code < 600:
                delay = (2**attempt) + random.random()
                await asyncio.sleep(delay)
                continue

            r.raise_for_status()
            html = r.text

            links = parse_listing_links(html)
            if not links:
                return

            yield html
            break

        else:
            return

        await asyncio.sleep(0.4)
        page += 1


async def producer_links(
    client: httpx.AsyncClient,
    start_url: str,
    queue: asyncio.Queue[str | None],
    workers_count: int,
    max_pages: int = 500,
) -> None:
    seen: set[str] = set()

    async for page_html in iter_listing_pages(client, start_url, max_pages=max_pages):
        links = parse_listing_links(page_html)

        new_count = 0
        for link in links:
            if link in seen:
                continue
            seen.add(link)

            await queue.put(link)
            new_count += 1

    for _ in range(workers_count):
        await queue.put(None)


async def worker(
    wid: int,
    client: httpx.AsyncClient,
    queue: asyncio.Queue[str | None],
    sem: asyncio.Semaphore,
    phone_sem: asyncio.Semaphore,
) -> None:
    while True:
        url = await queue.get()
        try:
            if url is None:
                return

            async with sem:
                r = await client.get(url)
            r.raise_for_status()

            tree = lxml_html.fromstring(r.text)
            car = parse_car(tree)
            car.url = url

            async with phone_sem:
                car = await enrich_phone(client, car, url)

            async with AsyncSessionLocal() as session:
                await upsert_car(session, car)
                await session.commit()

            logger.info(
                "CAR saved: title=%s price_usd=%s odometer=%s user=%s url=%s vin=%s images=%s found=%s",
                car.title,
                car.price_usd,
                car.odometer,
                car.username,
                url,
                car.car_vin,
                car.images_count,
                car.datatime_found,
            )

        except Exception:
            logger.exception("Worker failed for url=%s", url)
        finally:
            queue.task_done()


async def run_scraper() -> None:
    s = get_settings()

    queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=s.queue_maxsize)

    sem = asyncio.Semaphore(s.workers_count)
    phone_sem = asyncio.Semaphore(s.phone_workers)

    async with httpx.AsyncClient(
        headers=HEADERS, timeout=20, follow_redirects=True
    ) as client:
        worker_tasks = [
            asyncio.create_task(worker(i, client, queue, sem, phone_sem))
            for i in range(s.workers_count)
        ]

        await producer_links(
            client,
            s.base_url,
            queue,
            workers_count=s.workers_count,
            max_pages=s.max_pages,
        )
        await queue.join()

        for worker_task in worker_tasks:
            await worker_task
