import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from app.settings import get_settings

logger = logging.getLogger(__name__)

KYIV_TZ = ZoneInfo("Europe/Kyiv")


async def dump_db() -> None:
    s = get_settings()
    s.dumps_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(KYIV_TZ).strftime("%Y-%m-%d_%H-%M-%S")
    out_file = s.dumps_dir / f"autoria_{ts}.sql"

    cmd = [
        "docker",
        "exec",
        "-i",
        "autoria_db",
        "pg_dump",
        "-U",
        "autoria",
        "-d",
        "autoria",
    ]

    logger.info("DUMP writing to %s", out_file)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(f"pg_dump failed: {stderr.decode('utf-8', 'ignore')}")

    out_file.write_bytes(stdout)
    logger.info("DUMP done: %s", out_file)
