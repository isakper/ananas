"""PostgreSQL connection utilities."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg import Connection


class Database:
    """Simple transaction-scoped database helper."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    @contextmanager
    def connection(self) -> Iterator[Connection[tuple[object, ...]]]:
        """Open a connection and auto-commit/rollback around usage."""
        conn = psycopg.connect(self._dsn)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
