from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Car:
    # url: str
    title: str
    price_usd: int
    odometer: int
    username: str
    phone_number: Optional[str]
    image_url: str
    images_count: int
    car_number: Optional[str]
    car_vin: Optional[str]
    datatime_found: datetime


def now_time() -> datetime:
    return datetime.now(timezone.utc)
