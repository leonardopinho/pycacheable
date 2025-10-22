import pickle
import threading
import time
from typing import Any, Dict, Optional, Tuple, OrderedDict

from src.pycacheable.cache_base import CacheBase


class InMemoryCache(CacheBase):
    def __init__(self, max_entries: int = 1024):
        self._store: "OrderedDict[str, Tuple[float, bytes]]" = OrderedDict()
        self._lock = threading.RLock()
        self._max_entries = max_entries

    def get(self, key: str) -> Tuple[bool, Any, str]:
        with self._lock:
            entry = self._store.get(key)
            now = time.time()
            if not entry:
                return False, None, "MISS"
            expire_at, payload = entry
            if expire_at and expire_at < now:
                self._store.pop(key, None)
                return False, None, "EXPIRE"

            self._store.move_to_end(key)
            return True, pickle.loads(payload), "HIT"

    def set(self, key: str, value: Any, ttl_seconds: Optional[int]):
        with self._lock:
            expire_at = (time.time() + ttl_seconds) if ttl_seconds else 0.0
            payload = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
            self._store[key] = (expire_at, payload)
            self._store.move_to_end(key)
            while len(self._store) > self._max_entries:
                self._store.popitem(last=False)

    def clear(self):
        with self._lock:
            self._store.clear()

    def info(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "backend": "InMemoryCache",
                "size": len(self._store),
                "max_entries": self._max_entries,
            }
