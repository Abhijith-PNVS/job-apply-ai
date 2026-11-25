"""Durable local LangGraph checkpoint configuration."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver


@contextmanager
def sqlite_checkpointer(path: Path) -> Iterator[SqliteSaver]:
    """Yield a SQLite saver and close its connection after graph use."""

    resolved = path.resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(resolved, check_same_thread=False)
    try:
        yield SqliteSaver(connection)
    finally:
        connection.close()
