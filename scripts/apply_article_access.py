"""Apply the access_level migration if it has not run yet."""

import asyncio
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from backend.database.db import get_conn

SQL = (Path(__file__).resolve().parents[1] / "backend/database/migrations/002_article_access.sql").read_text()


async def main():
    conn = await get_conn()
    try:
        await conn.execute(SQL)
        print("Article access migration applied (or already present).")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
