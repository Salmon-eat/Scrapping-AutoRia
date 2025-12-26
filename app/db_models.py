from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CarDB(Base):
    __tablename__ = "cars"

    id: Mapped[int] = mapped_column(primary_key=True)

    url: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False, default="")
    price_usd: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    odometer: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    username: Mapped[str] = mapped_column(String, nullable=False, default="")
    phone_number: Mapped[str | None] = mapped_column(String, nullable=True)

    image_url: Mapped[str] = mapped_column(String, nullable=False, default="")
    images_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    car_number: Mapped[str] = mapped_column(String, nullable=False, default="")
    car_vin: Mapped[str] = mapped_column(String, nullable=False, default="")

    datetime_found: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (UniqueConstraint("url", name="uq_cars_url"),)
