import asyncio
from datetime import datetime, time, timedelta

from app.renewal.deactivate_old_cars import deactivate_old_cars
from app.services.global_scrape_cars import run_scraper


async def run_daily_scheduler():
    while True:
        now = datetime.now()
        target = datetime.combine(now.date(), time(12, 0))

        if now >= target:
            target += timedelta(days=1)

        sleep_seconds = (target - now).total_seconds()
        await asyncio.sleep(sleep_seconds)

        await deactivate_old_cars()


async def main():
    await asyncio.gather(
        run_scraper(),
        run_daily_scheduler(),
    )


if __name__ == "__main__":
    asyncio.run(main())
