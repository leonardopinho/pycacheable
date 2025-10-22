import os
import pickle
import sqlite3
import threading
import time
from typing import Any, Dict, Optional, Tuple

from src.pycacheable.cache_base import CacheBase


class SQLiteCache(CacheBase):
    def __init__(self, path: str):
        self._path = path
        self._lock = threading.RLock()
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

        with self._conn() as conn:
            conn.execute("""
                         CREATE TABLE IF NOT EXISTS cache
                         (
                             k
                             TEXT
                             PRIMARY
                             KEY,
                             expire_at
                             REAL,
                             v
                             BLOB
                         )
                         """)

            conn.execute("PRAGMA journal_mode=WAL;")

    def _conn(self):
        return sqlite3.connect(self._path, timeout=30, isolation_level=None)

    def get(self, key: str) -> Tuple[bool, Any, str]:
        with self._lock, self._conn() as conn:
            row = conn.execute("SELECT expire_at, v FROM cache WHERE k=?", (key,)).fetchone()
            now = time.time()
            if not row:
                return False, None, "MISS"
            expire_at, blob = row
            if expire_at and expire_at < now:
                conn.execute("DELETE FROM cache WHERE k=?", (key,))
                return False, None, "EXPIRE"
            return True, pickle.loads(blob), "HIT"

    def set(self, key: str, value: Any, ttl_seconds: Optional[int]):
        expire_at = (time.time() + ttl_seconds) if ttl_seconds else 0.0
        blob = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
        with self._lock, self._conn() as conn:
            conn.execute(
                "REPLACE INTO cache (k, expire_at, v) VALUES (?, ?, ?)",
                (key, expire_at, sqlite3.Binary(blob))
            )

    def clear(self):
        with self._lock, self._conn() as conn:
            conn.execute("DELETE FROM cache")

    def info(self) -> Dict[str, Any]:
        with self._lock, self._conn() as conn:
            row = conn.execute("SELECT COUNT(*) FROM cache").fetchone()
            size = int(row[0]) if row else 0
            return {
                "backend": "SQLiteCache",
                "size": size,
                "path": self._path,
            }
