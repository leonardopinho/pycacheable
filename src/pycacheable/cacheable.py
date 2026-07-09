"""Decorator de cache com backends plugáveis."""
import functools
from typing import Any, Callable, Dict, Optional, Tuple

from .backend_sqlite import SQLiteCache
from .cache_base import CacheBackend
from .hashing import _build_key_from_call


def cacheable(
        ttl: Optional[int] = 300,
        backend: Optional[CacheBackend] = None,
        *,
        include_self: bool = False,
        key_fn: Optional[Callable[[Callable, Tuple[Any, ...], Dict[str, Any]], str]] = None,
        logger: Optional[Callable[[str], None]] = None,
        backend_factory: Optional[Callable[..., CacheBackend]] = None,
):
    """
    Decorator de cache com backend configurável.

    Ciclo de vida do backend (ordem de prioridade):
    1. Se backend_factory fornecido: chamado por chamada (per-instance ou per-param)
    2. Se wrapper.cache_backend foi atribuído externamente: usa esse override
    3. Se backend fornecido: usa esse (compartilhado entre chamadas)
    4. Padrão: cria SQLiteCache novo

    Args:
        ttl: Tempo de vida em segundos (None = sem expiração)
        backend: Instância de CacheBackend compartilhada
        include_self: Se True, inclui 'self' na chave (para estado de instância)
        key_fn: Função customizada de geração de chave
        logger: Função para log de eventos cache
        backend_factory: Callable que retorna CacheBackend por chamada

    Exemplo:
        >>> @cacheable(ttl=60, backend=InMemoryCache())
        ... def get_user(user_id: int):
        ...     return fetch_from_db(user_id)

        >>> # Override backend em teste:
        >>> get_user.cache_backend = test_backend
    """
    # Resolve backend padrão uma única vez
    default_backend = backend or SQLiteCache(path="./.cache/db.sqlite3")

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Resolve qual backend usar (com fallback chain)
            be = None

            if backend_factory is not None:
                try:
                    be = backend_factory(*args, **kwargs)
                except TypeError:
                    # Fallback: tenta com first positional arg (self em métodos)
                    try:
                        be = backend_factory(args[0]) if args else None
                    except Exception:
                        pass

            # Se factory falhou ou não existe, usa cache_backend ou padrão
            if be is None:
                be = getattr(wrapper, "cache_backend", default_backend)

            # Gera chave estável
            key = (
                key_fn(func, args, kwargs)
                if key_fn
                else _build_key_from_call(func, args, kwargs, include_self)
            )

            # Tenta obter do cache
            hit, value, status = be.get(key)
            if hit:
                if logger:
                    logger(f"[CACHE {status}] {func.__qualname__} {key[:10]}…")
                return value

            # Cache miss: executa função
            if logger:
                logger(f"[CACHE {status}] {func.__qualname__} {key[:10]}… -> calling")

            result = func(*args, **kwargs)

            # Tenta armazenar no cache
            try:
                be.set(key, result, ttl)
                if logger:
                    logger(f"[CACHE SET] {func.__qualname__} {key[:10]}… ttl={ttl}")
            except Exception as e:
                if logger:
                    logger(f"[CACHE ERROR SET] {func.__qualname__}: {e}")

            return result

        # Atributos públicos para inspeção/controle
        wrapper.cache_backend = default_backend
        wrapper.cache_clear = lambda: wrapper.cache_backend.clear()
        wrapper.cache_info = lambda: wrapper.cache_backend.info()

        return wrapper

    return decorator
