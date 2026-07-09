"""Cache em memória com LRU e TTL."""
import threading
import time
from collections import OrderedDict
from typing import Any, Dict, Optional, Tuple

from .cache_base import CacheBackend
from .serializers import SafeSerializer


class InMemoryCache(CacheBackend):
    """Cache em memória com LRU e TTL, thread-safe."""

    def __init__(self, max_entries: int = 1024, serializer=None):
        """
        Args:
            max_entries: Máximo de itens antes de evicção LRU
            serializer: Instância de serializer (padrão: SafeSerializer)
        """
        self._store: OrderedDict[str, Tuple[float, bytes]] = OrderedDict()
        self._lock = threading.RLock()
        self._max_entries = max_entries
        self._serializer = serializer or SafeSerializer()

    def get(self, key: str) -> Tuple[bool, Any, str]:
        with self._lock:
            entry = self._store.get(key)
            now = time.time()

            if not entry:
                return False, None, "MISS"

            expire_at, payload = entry

            # Verifica expiração
            if expire_at and expire_at < now:
                self._store.pop(key, None)
                return False, None, "EXPIRE"

            # Move para fim (LRU)
            self._store.move_to_end(key)

            # Desserializa
            try:
                value = self._serializer.loads(payload)
                return True, value, "HIT"
            except Exception:
                # Se falhar na desserialização, remove do cache
                self._store.pop(key, None)
                return False, None, "DESERIALIZE_ERROR"

    def set(self, key: str, value: Any, ttl_seconds: Optional[int]) -> None:
        with self._lock:
            expire_at = (time.time() + ttl_seconds) if ttl_seconds else 0.0

            try:
                payload = self._serializer.dumps(value)
            except Exception:
                # Se falhar na serialização, pula (não armazena)
                return

            self._store[key] = (expire_at, payload)
            self._store.move_to_end(key)

            # Evicção LRU
            while len(self._store) > self._max_entries:
                self._store.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def info(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "backend": "InMemoryCache",
                "size": len(self._store),
                "max_entries": self._max_entries,
            }
