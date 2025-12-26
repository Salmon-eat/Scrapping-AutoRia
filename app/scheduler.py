import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.dump_db import dump_db
from app.services.global_scrape_cars import run_scraper
from app.settings import get_settings

logger = logging.getLogger(__name__)


KYIV_TZ = ZoneInfo("Europe/Kyiv")


def next_run_dt(hhmm, tz=KYIV_TZ) -> datetime:
    now = datetime.now(tz)
    run = now.replace(hour=hhmm.hour, minute=hhmm.minute, second=0, microsecond=0)
    if run <= now:
        run += timedelta(days=1)
    return run


async def _sleep_until(dt: datetime) -> None:
    now = datetime.now(dt.tzinfo)
    sec = max(0, (dt - now).total_seconds())
    await asyncio.sleep(sec)


async def loop_daily(job_name: str, when, coro_func):
    while True:
        run_at = next_run_dt(when)
        await _sleep_until(run_at)
        try:
            await coro_func()
        except Exception:
            logger.exception("SCHEDULER %s: ERROR", job_name)


async def main():
    s = get_settings()

    s.dumps_dir.mkdir(parents=True, exist_ok=True)

    await asyncio.gather(
        loop_daily("SCRAPE", s.scrape_time, run_scraper),
        loop_daily("DUMP", s.dump_time, dump_db),
    )


if __name__ == "__main__":
    asyncio.run(main())
