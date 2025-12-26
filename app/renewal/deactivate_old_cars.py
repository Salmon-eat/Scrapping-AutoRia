from sqlalchemy import text

from app.db import AsyncSessionLocal


async def deactivate_old_cars():
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                """
                UPDATE cars
                SET is_active = false
                WHERE last_seen_at < date_trunc('day', now())
            """
            )
        )
        await session.commit()
