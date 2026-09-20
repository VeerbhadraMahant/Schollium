"""Engine and connection helpers. No tool imports psycopg or SQLAlchemy engine
creation directly; everything goes through here so the DSN is resolved in one
place and tests can point it at a throwaway database.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Connection, Engine, create_engine

from scholium.config import Config


def make_engine(config: Config, *, echo: bool = False) -> Engine:
    return create_engine(config.store.dsn, echo=echo, future=True)


@contextmanager
def connection(config: Config, *, echo: bool = False) -> Iterator[Connection]:
    """One connection, committed on clean exit, rolled back on exception."""
    engine = make_engine(config, echo=echo)
    try:
        with engine.connect() as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    finally:
        engine.dispose()
