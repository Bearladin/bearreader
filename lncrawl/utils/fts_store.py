import sqlite3
from typing import Iterable, Mapping, Set, Tuple

from .event_lock import EventLock

# ------------------------------------------------------------------ #
#                             SQL Queries                            #
# ------------------------------------------------------------------ #

_INIT_SQL = """
    CREATE VIRTUAL TABLE store USING fts5(
        key,
        value UNINDEXED,
    );
"""

_SEARCH_SQL = """
    SELECT value FROM store WHERE key MATCH ?
"""

_COUNT_SQL = """
    SELECT COUNT(*) FROM store
"""

_INSERT_SQL = """
    INSERT INTO store(key, value) VALUES (?, ?)
"""

_DELETE_SQL = """
    DELETE FROM store WHERE key = ?
"""

_DELETE_MATCHING_SQL = """
    DELETE FROM store WHERE key MATCH ?
"""

_PURGE_SQL = """
    DELETE FROM store; VACUUM;
"""


def _escape_query(s: str) -> str:
    escaped = s.replace('"', '""')
    return f'"{escaped}"*'


# ------------------------------------------------------------------ #
#                              FTSStore                              #
# ------------------------------------------------------------------ #


class FTSStore:
    """Utility class for key-value substring search using SQLite FTS5."""

    def __init__(self):
        """Initialize the in-memory FTSStore."""
        self._lock = EventLock()
        self._db = sqlite3.connect(":memory:", check_same_thread=False)
        self._db.execute(_INIT_SQL)

    def close(self):
        """Close the database connection."""
        self._lock.abort()
        self._db.close()

    def clear(self):
        """Remove all items, and cleanup memory."""
        with self._lock, self._db:
            self._db.executescript(_PURGE_SQL)

    def count(self) -> int:
        """Returns number of items in the store"""
        with self._lock, self._db:
            c = self._db.execute(_COUNT_SQL)
            return c.fetchone()[0]

    def search(self, query: str) -> Set[str]:
        """Perform a full-text search on key and return values."""
        with self._lock, self._db:
            c = self._db.execute(_SEARCH_SQL, [_escape_query(query)])
            return set([r[0] for r in c.fetchall()])

    def insert_dict(self, mapping: Mapping[str, str]):
        """Insert multiple items from a key-value mapping"""
        with self._lock, self._db:
            self._db.executemany(_DELETE_SQL, [[k] for k in mapping.keys()])
            self._db.executemany(_INSERT_SQL, mapping.items())

    def insert(self, key: str, value: str):
        """Insert a single item."""
        self.insert_dict({key: value})

    def insert_keys(self, keys: Iterable[str], value: str):
        """Assign same value to multiple keys"""
        self.insert_dict({key: value for key in keys})

    def insert_pairs(self, pairs: Iterable[Tuple[str, str]]):
        """Insert multiple items."""
        self.insert_dict(dict(pairs))

    def delete_many(self, keys: Iterable[str]):
        """Insert multiple items by key."""
        with self._lock, self._db:
            self._db.executemany(_DELETE_SQL, [[k] for k in keys])

    def delete(self, key: str):
        """Delete an item by key."""
        self.delete_many([key])

    def search_and_delete(self, query: str):
        """Insert multiple items by key."""
        with self._lock, self._db:
            self._db.execute(_DELETE_MATCHING_SQL, [_escape_query(query)])
