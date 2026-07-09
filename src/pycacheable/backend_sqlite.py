"""Cache persistente em SQLite com TTL."""
import os
import sqlite3
import threading
import time
from typing import Any, Dict, Optional, Tuple

from .cache_base import CacheBackend
from .serializers import SafeSerializer


class SQLiteCache(CacheBackend):
    """Cache persistente em SQLite com TTL, thread-safe."""

    def __init__(self, path: str, serializer=None):
        """
        Args:
            path: Caminho para arquivo SQLite
            serializer: Instância de serializer (padrão: SafeSerializer)
        """
        self._path = path
        self._lock = threading.RLock()
        self._serializer = serializer or SafeSerializer()

        # Cria diretório se não existir
        dir_path = os.path.dirname(os.path.abspath(path))
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        # Inicializa banco
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    k TEXT PRIMARY KEY,
                    expire_at REAL,
                    v BLOB
                )
            """)
            conn.execute("PRAGMA journal_mode=WAL;")

    def _conn(self):
        """Cria nova conexão (autocommit mode)."""
        return sqlite3.connect(self._path, timeout=30, isolation_level=None)

    def get(self, key: str) -> Tuple[bool, Any, str]:
        with self._lock, self._conn() as conn:
            row = conn.execute(
                "SELECT expire_at, v FROM cache WHERE k=?", (key,)
            ).fetchone()

            now = time.time()

            if not row:
                return False, None, "MISS"

            expire_at, blob = row

            # Verifica expiração
            if expire_at and expire_at < now:
                conn.execute("DELETE FROM cache WHERE k=?", (key,))
                return False, None, "EXPIRE"

            # Desserializa
            try:
                value = self._serializer.loads(blob)
                return True, value, "HIT"
            except Exception:
                # Se falhar na desserialização, remove do cache
                conn.execute("DELETE FROM cache WHERE k=?", (key,))
                return False, None, "DESERIALIZE_ERROR"

    def set(self, key: str, value: Any, ttl_seconds: Optional[int]) -> None:
        expire_at = (time.time() + ttl_seconds) if ttl_seconds else 0.0

        try:
            blob = self._serializer.dumps(value)
        except Exception:
            # Se falhar na serialização, pula
            return

        with self._lock, self._conn() as conn:
            conn.execute(
                "REPLACE INTO cache (k, expire_at, v) VALUES (?, ?, ?)",
                (key, expire_at, sqlite3.Binary(blob))
            )

    def clear(self) -> None:
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
