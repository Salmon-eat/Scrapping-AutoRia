from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models import CarDB
from app.models import Car


async def upsert_car(session: AsyncSession, car: Car) -> None:
    now = datetime.now(timezone.utc)

    stmt = insert(CarDB).values(
        url=car.url,
        title=car.title or "",
        price_usd=car.price_usd or 0,
        odometer=int(car.odometer or 0),
        username=car.username or "",
        phone_number=car.phone_number,
        image_url=car.image_url or "",
        images_count=car.images_count or 0,
        car_number=car.car_number or "",
        car_vin=car.car_vin or "",
        datetime_found=car.datatime_found,
        last_seen_at=now,
        is_active=True,
    )

    stmt = stmt.on_conflict_do_update(
        constraint="uq_cars_url",
        set_={
            "title": stmt.excluded.title,
            "price_usd": stmt.excluded.price_usd,
            "odometer": stmt.excluded.odometer,
            "username": stmt.excluded.username,
            "phone_number": stmt.excluded.phone_number,
            "image_url": stmt.excluded.image_url,
            "images_count": stmt.excluded.images_count,
            "car_number": stmt.excluded.car_number,
            "car_vin": stmt.excluded.car_vin,
            "last_seen_at": stmt.excluded.last_seen_at,
            "is_active": True,
        },
    )

    await session.execute(stmt)
