"""Interface abstrata para implementações de cache."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple


class CacheBackend(ABC):
    """Interface clara e tipada para backends de cache."""

    @abstractmethod
    def get(self, key: str) -> Tuple[bool, Any, str]:
        """
        Recupera um valor do cache.

        Retorna:
            (hit: bool, value: Any, status: str)
            - hit: True se encontrou, não expirou e desserializou com sucesso
            - value: o valor cacheado (None se miss/expire/erro)
            - status: "HIT", "MISS", "EXPIRE", ou "DESERIALIZE_ERROR"
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: Optional[int]) -> None:
        """Armazena um valor no cache com TTL opcional."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Remove todos os itens do cache."""
        pass

    @abstractmethod
    def info(self) -> Dict[str, Any]:
        """Retorna informações sobre o estado do cache."""
        pass


# Alias para compatibilidade com código existente
CacheBase = CacheBackend

