import asyncio
import os
import random
from pathlib import Path
from typing import AsyncIterator

import httpx
from dotenv import load_dotenv
from lxml import html as lxml_html

from app.db import AsyncSessionLocal
from app.repo import upsert_car
from app.services.scrape_car import HEADERS, enrich_phone, parse_car

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

START_URL = os.getenv("BASE_URL")


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

            print(
                f"{car.title} | {car.price_usd} "
                f"| {car.odometer} | {car.username} | {car.phone_number} "
                f"| {url} | {car.car_vin} | {car.image_url} "
                f"| {car.datatime_found} | {car.images_count}"
            )

        except Exception as e:
            print(f"ERR {url} -> {e}")
        finally:
            queue.task_done()


async def main():
    if not START_URL:
        raise RuntimeError("BASE_URL is not set in .env")

    queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=100)

    workers_count = 5
    sem = asyncio.Semaphore(5)
    phone_sem = asyncio.Semaphore(1)

    async with httpx.AsyncClient(
        headers=HEADERS, timeout=20, follow_redirects=True
    ) as client:
        worker_tasks = [
            asyncio.create_task(worker(i, client, queue, sem, phone_sem))
            for i in range(workers_count)
        ]
        await producer_links(
            client, START_URL, queue, workers_count=workers_count, max_pages=10
        )
        await queue.join()

        for t in worker_tasks:
            await t


if __name__ == "__main__":
    asyncio.run(main())
