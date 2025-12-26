import os
from dataclasses import dataclass
from datetime import time
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")


def _parse_hhmm(value: str, field: str) -> time:
    if not value:
        raise RuntimeError(f"{field} is not set in .env")
    try:
        h, m = value.strip().split(":")
        return time(hour=int(h), minute=int(m))
    except Exception:
        raise RuntimeError(f"{field} must be HH:MM (got {value!r})")


@dataclass(frozen=True)
class Settings:
    base_url: str

    scrape_time: time
    dump_time: time
    dumps_dir: Path

    workers_count: int
    phone_workers: int
    queue_maxsize: int
    max_pages: int


def get_settings() -> Settings:
    base_url = os.getenv("BASE_URL")
    if not base_url:
        raise RuntimeError("BASE_URL is not set in .env")

    dumps_dir = os.getenv("DUMPS_DIR", "dumps")

    return Settings(
        base_url=base_url.rstrip("/") + "/",
        scrape_time=_parse_hhmm(os.getenv("SCRAPE_TIME", ""), "SCRAPE_TIME"),
        dump_time=_parse_hhmm(os.getenv("DUMP_TIME", ""), "DUMP_TIME"),
        dumps_dir=(BASE_DIR / dumps_dir),
        workers_count=int(os.getenv("WORKERS_COUNT", "5")),
        phone_workers=int(os.getenv("PHONE_WORKERS", "1")),
        queue_maxsize=int(os.getenv("QUEUE_MAXSIZE", "100")),
        max_pages=int(os.getenv("MAX_PAGES", "500")),
    )
