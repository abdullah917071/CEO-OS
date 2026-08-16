from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


@asynccontextmanager
async def open_checkpointer(database_url: str) -> AsyncIterator[Any]:
    if database_url.startswith("sqlite+aiosqlite:///"):
        path = database_url.removeprefix("sqlite+aiosqlite:///")
        async with AsyncSqliteSaver.from_conn_string(path) as saver:
            await saver.setup()
            yield saver
        return

    connection_string = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    async with AsyncPostgresSaver.from_conn_string(connection_string) as saver:
        await saver.setup()
        yield saver
